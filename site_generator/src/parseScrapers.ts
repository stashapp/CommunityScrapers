import { parse } from "yaml";
import { readFileSync, writeFileSync } from "fs";
import { ymlScraper } from "./types";
import { glob } from "glob";
import { z } from "zod";
import { ymlScraperSchema } from "./zodType";
import { exportScraper, scraperExport } from "./scraper";

function parseFile(file: string): ymlScraper {
  const fileData = readFileSync(file, "utf8");
  // extract scrapes: comment
  let scrapes = fileData.match(/^# scrapes: (.*)/gm)?.[0];
  let scrapeList: string[] = [];
  if (scrapes) {
    scrapeList = scrapes
      .replace("# scrapes:", "")
      .split(",")
      .map((scrape) => scrape.trim());
  }
  const parsed: ymlScraper = parse(fileData) as unknown as ymlScraper;
  return {
    ...parsed,
    filename: file,
    scrapes: scrapeList,
  };
}
async function parseRepository(
  pathName: string = "../scrapers",
): Promise<ymlScraper[]> {
  const ymlFolderFiles = await glob(`${pathName}/**/*.yml`);
  const ymlFiles = await glob(`${pathName}/*.yml`);
  const allYmlFiles = [...new Set([...ymlFolderFiles, ...ymlFiles])];
  const scrapers: ymlScraper[] = [];
  allYmlFiles.forEach((file: string) => {
    const scraper = parseFile(file);
    if (scraper.scrapes?.length === 0) delete scraper.scrapes;
    scrapers.push(scraper);
  });
  return scrapers;
}
function validate(scraper: ymlScraper) {
  ymlScraperSchema.parse(scraper);
  type validated = z.infer<typeof ymlScraperSchema>;
  return scraper as validated;
}

// get all scrapers
async function main(): Promise<void> {
  const validatedScrapers = await parseRepository()
    .then((scrapers) => scrapers.map(validate) as ymlScraper[])
    .then((scrapers) => scrapers.map(exportScraper));
  let mdScrapers: scraperExport[] = await Promise.all(validatedScrapers);
  // sort
  mdScrapers = mdScrapers.sort((a, b) => (a.name > b.name ? 1 : -1));
  // export to files
  writeFileSync("scrapers-debug.json", JSON.stringify(mdScrapers, null, 2));
  writeFileSync("site/assets/scrapers.json", JSON.stringify(mdScrapers));
  console.log("VALIDATED");
}
main();
