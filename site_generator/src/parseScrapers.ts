import { parse } from "yaml";
import { readFileSync, writeFileSync } from "fs";
import { ymlScraper } from "./types";
import { glob } from "glob";
import * as z from "zod";
import { ymlScraperSchema } from "./zodType";
import { git } from "./git";
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

async function parseScrapers(scraperFiles: string[]): Promise<ymlScraper[]> {
  const scrapers: ymlScraper[] = [];
  scraperFiles.forEach((file: string) => {
    const scraper = parseFile(file);
    if (scraper.scrapes?.length === 0) delete scraper.scrapes;
    scrapers.push(scraper);
  });
  return scrapers;
}

async function parseRepository(
  pathName: string = "../scrapers",
): Promise<ymlScraper[]> {
  const ymlFolderFiles = await glob(`${pathName}/**/*.yml`);
  const ymlFiles = await glob(`${pathName}/*.yml`);
  const allYmlFiles = [...new Set([...ymlFolderFiles, ...ymlFiles])];
  return parseScrapers(allYmlFiles);
}

const mergeScraperArr = (
  oldScrapers: scraperExport[],
  newScrapers: scraperExport[],
) => {
  // iterate through newScrapers and delete from old if exists
  const cleanOldScrapers = oldScrapers.filter(
    (oldScraper) =>
      !newScrapers.some(
        (newScraper) => newScraper.filename === oldScraper.filename,
      ),
  );
  return [...cleanOldScrapers, ...newScrapers];
};

function validate(scraper: ymlScraper) {
  ymlScraperSchema.parse(scraper);
  type validated = z.infer<typeof ymlScraperSchema>;
  return scraper as validated;
}

// get all scrapers
export async function validateAllScrapers(): Promise<void> {
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

export async function validateNewScrapers(): Promise<void> {
  // check for presence of scrapers-debug.json
  try {
    readFileSync("scrapers-debug.json", "utf8");
  } catch {
    console.log(
      "no scrapers-debug.json found, cowardly refusing to do partial updates",
    );
    // run full validation
    return validateAllScrapers();
  }
  // get modified files
  const newScrapers = await git
    .diff(["--name-only", "HEAD^1", "HEAD"])
    // skip empty lines
    .then((files) => files.split("\n").filter((file) => file.length))
    // skip files not in scrapers
    .then((files) => files.filter((file) => file.startsWith("scrapers/")))
    // map to full path
    .then((files) => files.map((file) => `../${file}`));
  // check if only yml files
  const nonYml = newScrapers.some((file) => !file.endsWith(".yml"));
  if (nonYml) {
    console.log(
      "non-yml files detected, cowardly refusing to do partial updates",
    );
    // run full validation
    return validateAllScrapers();
  }
  if (!newScrapers.length) {
    console.log("no new scrapers detected, recycling old mdscrapers");
    const oldScrapers = JSON.parse(
      readFileSync("scrapers-debug.json", "utf8"),
    ) as scraperExport[];
    writeFileSync("site/assets/scrapers.json", JSON.stringify(oldScrapers));
    return;
  }
  console.log("only validating new scrapers");
  const newValidScrapers = await parseScrapers(newScrapers)
    .then((undefScrapers) => undefScrapers.map(validate))
    .then((scrapers) => scrapers.map((s) => exportScraper(s as ymlScraper)));
  let newMdScrapers: scraperExport[] = await Promise.all(newValidScrapers);
  // merge with old scrapers
  const oldScrapers = JSON.parse(
    readFileSync("scrapers-debug.json", "utf8"),
  ) as scraperExport[];
  let newScraperArr = mergeScraperArr(oldScrapers, newMdScrapers);
  newScraperArr = newScraperArr.sort((a, b) => (a.name > b.name ? 1 : -1));
  // export to files
  writeFileSync("scrapers-debug.json", JSON.stringify(newScraperArr, null, 2));
  writeFileSync("site/assets/scrapers.json", JSON.stringify(newScraperArr));
  console.log("PARTIAL VALIDATED");
}
