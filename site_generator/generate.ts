/**
 * Generates the static scraper list site into <outdir>: the pages from site/
 * plus the scraper list and its pre-built search index
 */
import { copy } from "@std/fs";
import { fromFileUrl, join, relative } from "@std/path";
import Fuse from "fuse.js";
import { mapConcurrent } from "../lib/concurrent.ts";
import { lastCommit } from "../lib/git.ts";
import { contentTypes, urlPatterns } from "../lib/metadata.ts";
import {
  discoverPackages,
  SCRAPERS_DIR,
  type ScraperFile,
} from "../lib/package.ts";
import { keys } from "./site/assets/fuse-keys.js";

interface SiteEntry {
  filename: string;
  name: string;
  sites: string[];
  hosts: string[];
  scrapes?: string[];
  searchTypes: Record<string, Record<string, boolean>>;
  requires: { cdp: boolean; python: boolean };
  lastUpdate: string;
}

const has = (data: ScraperFile["data"], key: string) => data[key] !== undefined;

function searchTypes({ data }: ScraperFile): SiteEntry["searchTypes"] {
  return {
    scene: {
      name: has(data, "sceneByName"),
      fragment: has(data, "sceneByFragment"),
      queryFragment: has(data, "sceneByQueryFragment"),
      url: has(data, "sceneByURL"),
    },
    performer: {
      name: has(data, "performerByName"),
      url: has(data, "performerByURL"),
    },
    group: { url: has(data, "groupByURL") },
    gallery: {
      url: has(data, "galleryByURL"),
      fragment: has(data, "galleryByFragment"),
    },
    image: {
      url: has(data, "imageByURL"),
      fragment: has(data, "imageByFragment"),
    },
  };
}

const actionPattern = /^[a-z]+By(Name|Fragment|QueryFragment|URL)$/;

function usesPython({ data }: ScraperFile): boolean {
  return Object.entries(data)
    .filter(([key]) => actionPattern.test(key))
    .flatMap(([, value]) => (Array.isArray(value) ? value : [value]))
    .some(
      (definition) =>
        definition?.action === "script" &&
        Array.isArray(definition.script) &&
        definition.script.some(
          (arg: unknown) => typeof arg === "string" && arg.includes("python"),
        ),
    );
}

function hostname(pattern: string): string {
  const url = pattern.startsWith("http") ? pattern : `https://${pattern}`;
  return new URL(url).hostname;
}

function siteEntry(scraper: ScraperFile, lastUpdate: string): SiteEntry {
  const sites = [
    ...new Set(contentTypes.flatMap((type) => urlPatterns([scraper], type))),
  ].sort();
  const driver = scraper.data.driver as { useCDP?: boolean } | undefined;
  return {
    // a shared "scrapers/" prefix fuzzy-matches queries like "brazzers"
    filename: relative(SCRAPERS_DIR, scraper.path),
    name: scraper.data.name as string,
    sites,
    hosts: [...new Set(sites.map(hostname))],
    ...(scraper.headers.scrapes.length
      ? { scrapes: scraper.headers.scrapes }
      : {}),
    searchTypes: searchTypes(scraper),
    requires: { cdp: driver?.useCDP ?? false, python: usesPython(scraper) },
    lastUpdate,
  };
}

const outdir = Deno.args[0] ?? "_site";
const pages = fromFileUrl(new URL("./site", import.meta.url));
await Deno.mkdir(outdir, { recursive: true });
for await (const entry of Deno.readDir(pages)) {
  await copy(join(pages, entry.name), join(outdir, entry.name), {
    overwrite: true,
  });
}

// dated by the package, so "last updated" matches what Stash offers as an update
const entries = (
  await mapConcurrent(discoverPackages(), async (pkg) => {
    const { date } = await lastCommit(pkg.versionPath);
    const lastUpdate = new Date(`${date.replace(" ", "T")}Z`).toISOString();
    return pkg.scrapers.map((scraper) => siteEntry(scraper, lastUpdate));
  })
)
  .flat()
  .sort((a, b) => (a.name > b.name ? 1 : -1));

const assets = join(outdir, "assets");
await Deno.writeTextFile(
  join(assets, "scrapers.json"),
  JSON.stringify(entries),
);
await Deno.writeTextFile(
  join(assets, "fuse-index.json"),
  JSON.stringify(Fuse.createIndex(keys, entries).toJSON()),
);
console.log(`Generated site for ${entries.length} scrapers into ${outdir}`);
