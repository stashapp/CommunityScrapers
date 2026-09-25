# Dynamically generated CommunityScrapers index

A static page listing every scraper, searchable by name, site and the studios
in each scraper's `# scrapes:` comment. It reads scraper packages through the
same `lib/` as the index build and the validator.

```sh
deno task site _site   # then serve _site/ with any static file server
```

## site dependencies
- `ago.js`
  - https://github.com/sebastiansandqvist/s-ago
  - modified to remove future dates
- `fuse-keys.js`
  - search keys and weights, shared by the page and the generator
- `fuse-index.json` (generated)
  - pre-generated fuse index for faster searching
- `scrapers.json` (generated)
  - generated list of scrapers
