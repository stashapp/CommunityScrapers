import { relative, resolve } from "@std/path";
import { Ajv, type ErrorObject } from "ajv";
import addFormats from "ajv-formats";
import betterAjvErrors from "better-ajv-errors";
import chalk from "chalk";
import { discoverPackages, listScraperFiles } from "../lib/package.ts";
import { parseScraperYaml, type ScraperData } from "../lib/yaml.ts";

const isSorted = (arr: string[]) => arr.every((v, i, a) => !i || a[i - 1] <= v);

/** Mirrors the shape better-ajv-errors reads from ajv errors */
interface MappingError {
  keyword: string;
  message: string;
  params: { keyword: string };
  dataPath: string;
}

const mappingError = (
  keyword: string,
  message: string,
  dataPath: string,
): MappingError => ({ keyword, message, params: { keyword }, dataPath });

const mappingPattern = /^([a-z]+)By(Fragment|Name|URL)$/;

/** Actions that need a named scraper definition in the given section */
const definedActions: Record<string, { section: string; kind: string }> = {
  scrapeXPath: { section: "xPathScrapers", kind: "XPath" },
  scrapeJson: { section: "jsonScrapers", kind: "JSON" },
};

interface ActionDefinition {
  action?: string;
  scraper?: string;
  url?: string[];
}

type Definitions = Record<string, Record<string, unknown>>;

class Validator {
  stopOnError: boolean;
  sortedURLs: boolean;
  verbose: boolean;
  schema: object;

  constructor(flags: string[]) {
    this.stopOnError = !flags.includes("-a");
    this.sortedURLs = flags.includes("-s");
    this.verbose = flags.includes("-v");

    const schemaPath = resolve(import.meta.dirname!, "./scraper.schema.json");
    this.schema = JSON.parse(Deno.readTextFileSync(schemaPath));
  }

  run(files: string[]): boolean {
    const scrapers =
      files.length > 0
        ? files.map((file) => resolve(file))
        : listScraperFiles(resolve(import.meta.dirname!, "../scrapers"));

    const ajv = new Ajv({ strict: true });
    addFormats.default(ajv);
    ajv.addVocabulary(["deprecationMessage"]);
    const validate = ajv.compile(this.schema);

    let result = true;

    for (const file of scrapers) {
      const relPath = relative(Deno.cwd(), file);
      let data: ScraperData;
      try {
        data = parseScraperYaml(Deno.readTextFileSync(file));
      } catch (error) {
        console.error(`${chalk.red(chalk.bold("ERROR"))} in: ${relPath}:`);
        (error as Error).stack = undefined;
        console.error(error);
        result = false;
        if (this.stopOnError) break;
        else continue;
      }

      let valid = validate(data);

      // If schema validation did not pass, don't try to validate mappings.
      if (valid) {
        const mappingErrors = this.getMappingErrors(data);
        if (mappingErrors.length > 0) {
          validate.errors = (validate.errors || []).concat(
            mappingErrors as unknown as ErrorObject[],
          );
          valid = false;
        }
      }

      if (!valid) {
        const output = betterAjvErrors("scraper", data, validate.errors!, {
          indent: 2,
        });
        console.log(output);
      }

      if (this.verbose || !valid) {
        const validColor = valid ? chalk.green : chalk.red;
        console.log(`${relPath} Valid: ${validColor(valid)}`);
      }

      result = result && valid;

      if (!valid && this.stopOnError) break;
    }

    // Package checks need the whole repository, so they only run on a full pass
    if (result && files.length === 0) {
      result = this.checkPackages();
    }

    if (!this.verbose && result) {
      console.log(chalk.green("Validation passed!"));
    }

    return result;
  }

  checkPackages(): boolean {
    const packages = discoverPackages(
      resolve(import.meta.dirname!, "../scrapers"),
    );
    const ids = new Set(packages.map((pkg) => pkg.id));
    let valid = true;
    for (const pkg of packages) {
      for (const dependency of pkg.headers.requires) {
        if (!ids.has(dependency)) {
          console.log(
            `${chalk.red(chalk.bold("ERROR"))} in package ${pkg.id}: ` +
              `\`# requires: ${dependency}\` is not a package in this repository`,
          );
          valid = false;
        }
      }
    }
    return valid;
  }

  getMappingErrors(data: ScraperData): MappingError[] {
    return [
      ...this.collectConfigMappingErrors(data),
      ...this.collectScraperDefinitionErrors(data),
      ...this.collectCookieErrors(data),
    ];
  }

  collectConfigMappingErrors(data: ScraperData): MappingError[] {
    if (data.sceneByName && !data.sceneByQueryFragment) {
      return [
        mappingError(
          "sceneByName",
          "a `sceneByQueryFragment` configuration is required for `sceneByName` to work",
          "/sceneByName",
        ),
      ];
    }
    return [];
  }

  collectScraperDefinitionErrors(data: ScraperData): MappingError[] {
    const hasStashServer = "stashServer" in data;
    let needsStashServer = false;
    const errors: MappingError[] = [];

    for (const [key, value] of Object.entries(data)) {
      const match = mappingPattern.exec(key);
      if (!match) continue;

      const type = match[1];
      const seenURLs: Record<string, string> = {};
      const multiple = Array.isArray(value);
      const definitions = (multiple ? value : [value]) as ActionDefinition[];

      definitions.forEach(({ action, scraper, url }, idx) => {
        const dataPath = `/${key}${multiple ? `/${idx}` : ""}`;

        if (action === "stash") {
          needsStashServer = true;
          if (!hasStashServer) {
            errors.push(
              mappingError(
                "action",
                "root object should contain a `stashServer` definition",
                dataPath + "/action",
              ),
            );
          }
          return;
        }

        const defined = action && definedActions[action];
        if (!defined) return;

        const section = data[defined.section] as Definitions | undefined;
        if (!section || !Object.hasOwn(section, scraper!)) {
          errors.push(
            mappingError(
              "scraper",
              `${defined.section} should contain a ${defined.kind} scraper definition for \`${scraper}\``,
              dataPath + "/scraper",
            ),
          );
        } else if (!section[scraper!][type]) {
          errors.push(
            mappingError(
              scraper!,
              `\`${scraper}\` should create an object of type \`${type}\``,
              `/${defined.section}/${scraper}`,
            ),
          );
        }

        if (!url) return;

        url.forEach((u, uIdx) => {
          const exists = seenURLs[u];
          if (exists) {
            errors.push(
              mappingError(
                "url",
                `URLs for type \`${type}\` should be unique, already exists on ${exists}`,
                `${dataPath}/url/${uIdx}`,
              ),
            );
          } else {
            seenURLs[u] = `${dataPath}/url/${uIdx}`;
          }
        });

        if (this.sortedURLs && !isSorted(url)) {
          errors.push(
            mappingError(
              "url",
              "URL list should be sorted in ascending alphabetical order",
              dataPath + "/url",
            ),
          );
        }
      });
    }

    if (!needsStashServer && hasStashServer) {
      errors.unshift(
        mappingError(
          "stashServer",
          "`stashServer` is defined, but never used",
          "/stashServer",
        ),
      );
    }

    return errors;
  }

  collectCookieErrors(data: ScraperData): MappingError[] {
    const driver = data.driver as
      { useCDP?: boolean; cookies?: Record<string, unknown>[] } | undefined;
    const usesCDP = Boolean(driver?.useCDP);
    return (driver?.cookies ?? []).flatMap((cookieItem, idx) => {
      const hasCookieURL = "CookieURL" in cookieItem;
      if (!usesCDP && !hasCookieURL) {
        return [
          mappingError(
            "CookieURL",
            "`CookieURL` is required because useCDP is `false`",
            `/driver/cookies/${idx}`,
          ),
        ];
      }
      if (usesCDP && hasCookieURL) {
        return [
          mappingError(
            "CookieURL",
            "Should not have `CookieURL` because useCDP is `true`",
            `/driver/cookies/${idx}/CookieURL`,
          ),
        ];
      }
      return [];
    });
  }
}

export function main(args: string[] = Deno.args): void {
  const flags = args.filter((arg) => arg.startsWith("-"));
  const files = args.filter((arg) => !arg.startsWith("-"));
  const result = new Validator(flags).run(files);
  if (flags.includes("--ci")) {
    Deno.exit(result ? 0 : 1);
  }
}
