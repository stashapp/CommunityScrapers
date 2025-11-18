import Fuse from "https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/dist/fuse.basic.min.mjs";
import ago from "./ago.js";
// constant elements
const searchInput = document.querySelector("#search");
const table = document.getElementById("scraper-list");
const searchTypes = {
  name: { tooltip: "Search:", emoji: "🔍" },
  url: { tooltip: "URL:", emoji: "🔗" },
  fragment: { tooltip: "Smart:", emoji: "🧠" },
};

// helper functions
const emojiBool = (value) => (value ? "✅" : "❌");
const noMatch = "—";
const returnMatch = (bool, value) => (bool ? value : noMatch);
const anyTrue = (obj) => Object.values(obj).some((v) => v);
// https://stackoverflow.com/a/54265129
function debounce(f, interval) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    return new Promise((resolve) => {
      timer = setTimeout(() => resolve(f(...args)), interval);
    });
  };
}

// tooltip helper
const createToolTip = (target, stypeObj) => {
  // if false, don't add tooltip
  if (!anyTrue(stypeObj)) return (target.textContent = noMatch);
  // generate tooltip text dynamically
  let tooltipArray = [];
  let typeText = "";
  // add all applicable tooltips
  for (const [key, value] of Object.entries(searchTypes)) {
    const check = stypeObj[key];
    if (check !== undefined) {
      tooltipArray.push(`${value.tooltip} ${emojiBool(check)}`);
      if (check) typeText += value.emoji;
    }
  }
  // create tooltip text
  const tooltipElement = document.createElement("span");
  tooltipElement.textContent = tooltipArray.join(" | ");
  target.textContent = typeText;
  target.classList.add("tooltip");
  target.appendChild(tooltipElement);
};

const createDetails = (values, fallback, searchValue, expand = false) => {
  const preContainer = document.createElement("div");
  if (!values?.length) preContainer.textContent = fallback;
  else {
    // search
    values = values.map((value) =>
      searchValue && value.toLowerCase().includes(searchValue.toLowerCase())
        ? `<mark>${value}</mark>`
        : value,
    );
    const summary = document.createElement("summary");
    summary.textContent = fallback;
    const p = document.createElement("p");
    p.innerHTML = values.join("\n");
    const detailsBox = document.createElement("details");
    detailsBox.appendChild(p);
    detailsBox.appendChild(summary);
    preContainer.appendChild(detailsBox);
    if (expand && searchValue) detailsBox.open = true;
  }
  return preContainer;
};

const siteDetails = (sites, searchValue, expand = false) => {
  const preContainer = createDetails(
    sites.slice(1),
    sites[0],
    searchValue,
    expand,
  );
  preContainer.classList.add("pre");
  return preContainer;
};

const scrapes = (name, scrapes, searchValue, expand = false) =>
  createDetails(scrapes, name, searchValue, expand);

const setTable = (scrapers, searchValue = "") => {
  if (table.rows.length) table.innerHTML = "";
  scrapers.forEach((scp, idx) => {
    const sType = scp.searchTypes;
    const row = table.insertRow();
    // name
    row
      .insertCell(0)
      .appendChild(scrapes(scp.name, scp.scrapes, searchValue, idx <= 5));
    // supported sites
    row
      .insertCell(1)
      .appendChild(siteDetails(scp.sites, searchValue, idx <= 5));
    // scene scraping
    createToolTip(row.insertCell(2), sType.scene);
    // gallery scraping
    createToolTip(row.insertCell(3), sType.gallery);
    // image scraping
    createToolTip(row.insertCell(4), sType.image);
    // group scraping
    row.insertCell(5).textContent = returnMatch(sType.group.url, "🔗");
    // performer scraping
    createToolTip(row.insertCell(6), sType.performer);
    // requires
    row.insertCell(7).textContent = returnMatch(scp.requires.python, "🐍");
    row.insertCell(8).textContent = returnMatch(scp.requires.cdp, "🌐");
    row.insertCell(9).textContent = ago(new Date(scp.lastUpdate));
  });
};

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

// fuse config
const fuseConfig = {
  keys,
  threshold: 0.4,
  shouldSort: true,
  includeScore: true, // debugging
  minMatchCharLength: 3,
};

// init fuse
let fuse;

// fuse search
async function search(searchValue) {
  if (searchValue.length < 3) return setTable(rawScraperList);
  const results = fuse.search(searchValue, {
    limit: 20,
  });
  console.debug(searchValue, results);
  const filterTable = results.map((result) => result.item);
  setTable(filterTable, searchValue);
  window.location.hash = searchValue;
}

// parse scrapers.json
const rawScraperList = await fetch("assets/scrapers.json").then((response) =>
  response.json(),
);
setTable(rawScraperList);
const fuseIndex = await fetch("assets/fuse-index.json")
  .then((response) => response.json())
  .then((data) => Fuse.parseIndex(data));
fuse = new Fuse(rawScraperList, fuseConfig, fuseIndex);
// if query in URL, jump automatically
const query = window.location.hash.slice(1);
if (query) {
  searchInput.value = query;
  search(query);
}
searchInput.addEventListener("input", (event) =>
  debounce(search(event.target.value), 300),
);
