import {
  ymlScraper,
  isUrlScraper,
  byUrlScraperDefn,
  anyScraper,
  isScriptScraper,
} from "./types";
import { git } from "./git";
import { lstat } from "fs/promises";

interface searchTypes {
  scene: {
    name: boolean;
    fragment: boolean;
    queryFragment: boolean;
    url: boolean;
  };
  performer: {
    name: boolean;
    url: boolean;
  };
  group: {
    url: boolean;
  };
  gallery: {
    url: boolean;
    fragment: boolean;
  };
  image: {
    url: boolean;
    fragment: boolean;
  };
}

export interface scraperExport {
  filename: string;
  name: string;
  sites: string[];
  hosts?: string[]; // for fuse searching
  scrapes?: string[];
  searchTypes: searchTypes;
  requires: {
    cdp: boolean;
    python: boolean;
  };
  lastUpdate: Date;
}

const getSearchTypes = (scraper: ymlScraper): searchTypes => ({
  scene: {
    name: scraper.sceneByName !== undefined,
    fragment: scraper.sceneByFragment !== undefined,
    queryFragment: scraper.sceneByQueryFragment !== undefined,
    url: scraper.sceneByURL !== undefined,
  },
  performer: {
    name: scraper.performerByName !== undefined,
    url: scraper.performerByURL !== undefined,
  },
  group: {
    url: scraper.groupByURL !== undefined,
  },
  gallery: {
    fragment: scraper.galleryByFragment !== undefined,
    url: scraper.galleryByURL !== undefined,
  },
  image: {
    url: scraper.imageByURL !== undefined,
    fragment: scraper.imageByFragment !== undefined,
  },
});

function collectURLSites(scraper: ymlScraper): string[] {
  // collect URL sites
  const urlActions = [
    "sceneByURL",
    "performerByURL",
    "groupByURL",
    "galleryByURL",
    "imageByURL",
  ];
  let urlSites: string[] = [];
  for (const action of urlActions) {
    const scrapers: byUrlScraperDefn[] = scraper[action];
    if (scrapers === undefined) continue;
    for (const scraper of scrapers) {
      if (isUrlScraper(scraper)) {
        urlSites = urlSites.concat(scraper.url);
      }
    }
  }
  // remove duplicates
  return Array.from(new Set(urlSites)).sort();
}

const checkScraperPython = (scraper: anyScraper): boolean =>
  isScriptScraper(scraper) &&
  scraper.script.some((script) => script.includes("python"));

function hasPython(scraper: ymlScraper): boolean {
  const actions = [
    "performerByName",
    "performerByFragment",
    "performerByURL",
    "sceneByName",
    "sceneByQueryFragment",
    "sceneByFragment",
    "sceneByURL",
    "groupByURL",
    "galleryByFragment",
    "galleryByURL",
    "imageByURL",
    "imageByFragment",
  ];
  return actions.some((action) => {
    const scrapers = scraper[action];
    if (scrapers === undefined) return false;
    // check if is array
    return Array.isArray(scrapers)
      ? scrapers.some(checkScraperPython)
      : checkScraperPython(scrapers);
  });
}

const getRequires = (
  scraper: ymlScraper,
): { cdp: boolean; python: boolean } => ({
  cdp: scraper.driver?.useCDP ?? false,
  python: hasPython(scraper),
});

async function getLastUpdate(scraper: ymlScraper): Promise<Date | false> {
  // if script we have to take all files into account, or take the folder
  // check if scraper has a parent folder
  const filename = scraper.filename.replace(/^\.\.\/scrapers\//, "");
  const folder = filename.split("/").slice(0, -1).join("/");
  const isFolder = await lstat(folder)
    .then((stat) => stat.isDirectory())
    .catch((err) => false);
  const chosenPath = isFolder ? folder : filename;
  const latestUpdate = await git
    .log({ file: "../scrapers/"+chosenPath, maxCount: 1 })
    .then((gitLog) => gitLog?.latest);
  return latestUpdate ? new Date(latestUpdate.date) : false;
}

// fix return type
export async function exportScraper(
  scraper: ymlScraper,
): Promise<scraperExport> {
  // collect URL sites
  const sites = collectURLSites(scraper);
  const hosts = sites.map(
    (url) => new URL(url.startsWith("http") ? url : `https://${url}`).hostname,
  );
  const searchTypes = getSearchTypes(scraper);
  const requires = getRequires(scraper);
  const lastUpdate = (await getLastUpdate(scraper)) || new Date(0);
  // if debug, warn and error
  if (scraper?.debug?.printHTML) new Error("Debug is enabled");
  return {
    filename: scraper.filename,
    name: scraper.name,
    sites,
    hosts: [...new Set(hosts)],
    scrapes: scraper.scrapes,
    searchTypes: searchTypes,
    requires: requires,
    lastUpdate: lastUpdate,
  };
}
