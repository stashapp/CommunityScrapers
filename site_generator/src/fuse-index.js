const Fuse = require("fuse.js");
const fs = require("fs");

const data = require("../site/assets/scrapers.json");
// filename - contains path, not super helpful
// name - primary key
// sites - scraping URLs, mostly for exact matching
// scrapes - manual comment for sites supported
// hosts - sites but reduced to URL hosts (reduce false positives)
const keys = [
  {
    name: "filename",
    weight: 2,
  },
  {
    name: "name",
    weight: 20,
  },
  {
    name: "sites",
    weight: 2,
  },
  {
    name: "scrapes",
    weight: 10,
  },
  {
    name: "hosts",
    weight: 10,
  },
];
const fuseIndex = Fuse.createIndex(keys, data);

fs.writeFileSync(
  "site/assets/fuse-index.json",
  JSON.stringify(fuseIndex.toJSON()),
);
