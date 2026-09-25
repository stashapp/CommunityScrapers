import { basename, dirname, join } from "@std/path";
import { type Headers, parseHeaders } from "./headers.ts";
import { parseScraperYaml, type ScraperData } from "./yaml.ts";

export const SCRAPERS_DIR = "scrapers";

/** Marks a folder that is published as one package instead of one per scraper file */
export const PACKAGE_FILE = "package";

export interface ScraperFile {
  path: string;
  source: string;
  data: ScraperData;
  headers: Headers;
}

/** A unit of distribution: one entry in the package index and one zip */
export interface ScraperPackage {
  id: string;
  name: string;
  /** Folder shipped in full; unset when the package is a single top-level file */
  folder?: string;
  /** The scraper files this package represents */
  scrapers: ScraperFile[];
  /** Path whose git history versions the package */
  versionPath: string;
  headers: Headers;
}

function walk(dir: string, include: (name: string) => boolean): string[] {
  const found: string[] = [];
  for (const entry of Deno.readDirSync(dir)) {
    if (entry.name.startsWith(".")) continue;
    const path = join(dir, entry.name);
    if (entry.isDirectory) {
      found.push(...walk(path, include));
    } else if (include(entry.name)) {
      found.push(path);
    }
  }
  return found.sort();
}

export function listScraperFiles(root = SCRAPERS_DIR): string[] {
  return walk(root, (name) => name.endsWith(".yml"));
}

export function loadScraperFile(path: string): ScraperFile {
  const source = Deno.readTextFileSync(path);
  return {
    path,
    source,
    data: parseScraperYaml(source),
    headers: parseHeaders(source),
  };
}

function nameOf(file: ScraperFile): string {
  const name = file.data.name;
  if (typeof name !== "string" || name === "") {
    throw new Error(`${file.path}: missing name`);
  }
  return name;
}

const unique = (values: string[]) => [...new Set(values)];

/**
 * Every package in the repository, sorted by id:
 * - a top-level scraper file is a package on its own
 * - a scraper file in a folder is a package that ships the whole folder
 * - a folder with a package file is one package covering all of its scraper files
 */
export function discoverPackages(root = SCRAPERS_DIR): ScraperPackage[] {
  const scraperPaths = listScraperFiles(root);
  const packageFolders = walk(root, (name) => name === PACKAGE_FILE).map(
    dirname,
  );
  const packages: ScraperPackage[] = [];

  for (const path of scraperPaths) {
    const folder = dirname(path);
    if (packageFolders.includes(folder)) continue;
    const scraper = loadScraperFile(path);
    const isTopLevel = folder === root;
    packages.push({
      id: basename(path, ".yml"),
      name: nameOf(scraper),
      folder: isTopLevel ? undefined : folder,
      scrapers: [scraper],
      versionPath: isTopLevel ? path : folder,
      headers: scraper.headers,
    });
  }

  for (const folder of packageFolders) {
    const manifest = loadScraperFile(join(folder, PACKAGE_FILE));
    const scrapers = scraperPaths
      .filter((path) => dirname(path) === folder)
      .map(loadScraperFile);
    packages.push({
      id: basename(folder),
      name: nameOf(manifest),
      folder,
      scrapers,
      versionPath: folder,
      headers: {
        ...manifest.headers,
        scrapes: unique([
          ...manifest.headers.scrapes,
          ...scrapers.flatMap((scraper) => scraper.headers.scrapes),
        ]),
      },
    });
  }

  return packages.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}
