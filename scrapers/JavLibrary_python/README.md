# JAVLibrary python scraper

## Requirements

JAVLibrary is protected by CloudFlare. This scraper uses Flaresolverr (default: `http://localhost:8191/v1`) to bypass it. Set the `FLARESOLVERR_URL` environment variable to override.

To avoid overloading the site, the scraper applies a rate limit of **1 request per second** (burst up to 40 per minute).

## Configuration file

[config.ini](https://github.com/stashapp/CommunityScrapers#manually-configured-scrapers) in the scraper directory can be used to customize the scraper operation. The first call to the scraper creates a default  `.ini` file.

### Options

**language**

Site (and scrape) language: `en`, `ja`, `tw`, `cn`

**title_template**

`str.format()` template for the scene title. Variables from [ScrapedScene](https://github.com/stashapp/CommunityScrapers/blob/master/scrapers/py_common/types.py) are available with an additional `label` variable.

**details_template** 

Same as above, but for the scene details. JAVLibrary has no dedicated details field, but you can use the template to assign label and title to the details for example.

**import_performer_aliases**

`True` to extract aliases (shown in parentheses on the release page).

**tag_separators**

A string of characters on which to split tags. For example, `"·,"` splits tags containing either `·` or `,`. Set to `False` to disable splitting.

**Example `config.ini`:**

```ini
language = en
title_template = {code} - {title}
details_template = Label: {label}\n{title}
import_performer_aliases = False
tag_separators = ·,

```

## Customizing scrape results

Scrape data is modified using data from [base_config.py](base_config.py). You can add and override these rules by creating a new file `local_config.py` and giving your own rules there. If you want to ignore the rules in `base_config.py`, add `REPLACE_ALL = True` to your local file.

Without REPLACE_ALL, your local lists are merged with the base ones (duplicates removed), and your dict updates the base dict (your keys override).

Example `local_config.py` (full override):

```python
REPLACE_ALL = True
FIXED_TAGS = ["own_tag1", "own_tag2"]
IGNORE_TAGS = ["ignore_me"]
REPLACE_TITLE = {"old": "new", "clean": ""}
```

**FIXED_TAGS**

Tags added to every scraped scene.

**IGNORE_TAGS**

Tags that are removed from the scraped result.

**REPLACE_TITLE**

String replacements applied to search query (scene-by-name) and title search.

## Troubleshooting

Check "Settings" -> "Logs" in Stash for detailed debug information.

### Flaresolverr not found after configuring the environment variable

Flaresolverr status is cached to disc. If you first ran the scraper without a valid Flaresolverr, that negative status persists even after you add or change `FLARESOLVERR_URL`. To clear the cache, delete `scrapers/community/py_common/cache.json`. For implementation details, see [proxy.py](https://github.com/stashapp/CommunityScrapers/blob/master/scrapers/py_common/proxy.py).

