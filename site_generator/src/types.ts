// driver configuration
interface driverConfig {
  useCDP?: boolean;
  sleep?: number;
  clicks?: {
    xpath: string;
    sleep?: number;
  }[];
  cookies?: {
    CookieURL?: string;
    Cookies?: Cookie[];
  }[];
  headers?: {
    Key: string;
    Value: string;
  }[];
}
type Cookie = {
  Name: string;
  Domain: string;
  ValueRandom?: number;
  Value?: string;
  Path?: string;
};
// URL-based scraper actions
type urlScrapeActions = "scrapeXPath" | "scrapeJson" | "stash";
export type singleActions =
  | "performerByName"
  | "performerByFragment"
  | "sceneByName"
  | "sceneByQueryFragment"
  | "sceneByFragment"
  | "galleryByFragment"
  | "imageByFragment";
export type arrayActions =
  | "performerByURL"
  | "sceneByURL"
  | "groupByURL"
  | "galleryByURL"
  | "imageByURL";
interface baseUrlScraper {
  action: urlScrapeActions;
  scraper: string;
  queryURLReplace?: Record<string, replaceRegex[]>;
}
export interface byUrlScraper extends baseUrlScraper {
  url: string[];
  queryURL?: string;
}
interface byFragmentScraper extends baseUrlScraper {
  queryURL: string;
}
interface byNameScraper extends byFragmentScraper {} // clone
// script scraper
export interface scriptScraper {
  action: "script";
  script: string[];
}
export type anyScraper =
  | byNameScraper
  | byFragmentScraper
  | byUrlScraper
  | scriptScraper;
// xPath scrapers definitions
type xPathScraper = Record<
  string,
  {
    fixed?: string;
    selector?: string;
    postProcess?: {
      replace?: replaceRegex[];
      parseDate: string;
    }[];
    concat?: string;
  }
>;
// post processing
type replaceRegex = {
  regex: string;
  with: string | null;
};
//
export type byNameScraperDefn = scriptScraper | byNameScraper;
export type byFragmentScraperDefn = scriptScraper | byFragmentScraper;
export type byUrlScraperDefn = scriptScraper | byUrlScraper;

export interface ymlScraper {
  [key: string]: any;
  filename: string;
  name: string;
  scrapes?: string[];
  driver?: driverConfig;
  xPathScrapers?: xPathScraper | xPathScraper[];
  debug?: {
    printHTML?: boolean;
  };
  performerByName?: byNameScraperDefn;
  performerByFragment?: byFragmentScraperDefn;
  performerByURL?: byUrlScraperDefn[];
  sceneByName?: byNameScraperDefn;
  sceneByQueryFragment?: byFragmentScraperDefn;
  sceneByFragment?: byFragmentScraperDefn;
  sceneByURL?: byUrlScraperDefn[];
  groupByURL?: byUrlScraperDefn[];
  galleryByFragment?: byFragmentScraperDefn;
  galleryByURL?: byUrlScraperDefn[];
  imageByURL?: byUrlScraperDefn[];
  imageByFragment?: byFragmentScraperDefn;
}

export const isUrlScraper = (
  scraper: byUrlScraperDefn,
): scraper is byUrlScraper => (scraper as byUrlScraper).url !== undefined;
export const isScriptScraper = (
  scraper: anyScraper,
): scraper is scriptScraper => scraper.action === "script";
