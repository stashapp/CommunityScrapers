# CommunityScrapers repository

This repository contains scrapers created by the Stash community.

**:exclamation: Make sure to read ALL of the instructions here before requesting help from the community**. :exclamation: 

> [!TIP] 
For a more user friendly step-by-step guide you can check out the [Guide to Scraping](https://docs.stashapp.cc/beginner-guides/guide-to-scraping/).

## Installing scrapers via manager

> [!TIP] 
Guide: [How to install a scraper?](https://discourse.stashapp.cc/t/how-to-install-a-scraper/2307)

Scrapers can be installed and managed from the **Settings** > **Metadata Providers** page.

Scrapers are installed using the **Available Scrapers** section. The `Community (stable)` source is configured by default.

Some scrapers may require [manual configuration](#manually-configured-scrapers) before they will work, so make sure to check the scraper file for any instructions after installing it.

## Installing scrapers manually

> [!TIP] 
Guide: [How to install a scraper?](https://discourse.stashapp.cc/t/how-to-install-a-scraper/2307)

To download all scrapers at once, clone this git repository. If you only need specific scrapers, download those `.yml` files individually.

When downloading individual files:

1. Open the `.yml` file you want.
2. Click the **Download raw file** button.
3. Save the page as a `.yml` file to preserve the correct format.

![](https://github.com/user-attachments/assets/112f525a-34b4-4996-a962-e3ae5979c18e)

Move scraper files to your configured `Scrapers Path` under `Settings > System > Application Paths` (default: `~/.stash/scrapers`). You may recognize `~/.stash` as the folder where the config and database files are located.

After manually updating the scrapers folder or editing a scraper file, reload scrapers and refresh the edit scene/performer page. (**Scrape with... -> Reload scrapers**)

Some sites block content if the user agent is not valid. If you get a blocked or denied message, configure the `Scraping -> Scraper User Agent` setting in Stash. Valid Firefox user agent strings can be found [here](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent/Firefox). Scrapers for those sites should include a comment with a tested and working user agent string.

Scrapers with **useCDP** set to true require that you have properly configured the `Chrome CDP path` setting in Stash. If you decide to use a remote instance, the headless Chromium Docker image from [chromedp/headless-shell](https://hub.docker.com/r/chromedp/headless-shell/) is highly recommended. `browserless/chrome` is not CDP-compatible and is not supported.

## Python scrapers

Some scrapers require external programs to function, usually [Python](https://www.python.org/). All scrapers are tested with the newest stable release of Python, currently 3.14.x

Depending on your operating system you may need to install both Python and the scrapers' dependencies before they will work. For Windows users we strongly recommend installing Python using the [installers from python.org](https://www.python.org/downloads/) instead of through the Windows Store, and also installing it outside of the Users folder so it is accessible to the entire system: a commonly used option is `C:\Python314`.

After installing Python you should install the most commonly used dependencies by running the following command in a terminal window:

```cmd
python -m pip install stashapp-tools requests cloudscraper beautifulsoup4 lxml
```

You may need to replace `python` with `py` in the command if you are running on Windows.

If Stash does not detect your Python installation you can set the `Python executable path` in `Settings > System > Application Paths`. Note that this needs to point to the executable itself and not just the folder it is in.

## Manually configured scrapers

Some scrapers need extra configuration before they will work. This is unfortunate if you install them through the web interface as any updates will overwrite your changes.

- Python scrapers that need to communicate with your Stash (to create markers, for example, or to search your file system) _might_ need to be configured to talk to your local Stash: by default they will use `http://localhost:9999/graphql` with no authentication to make their queries, but if your setup requires otherwise then you can find `py_common/config.ini` and set your own values.
- Python scrapers that can be configured will (usually) create a default configuration file called `config.ini` in their respective directories the first time you run them.
- Some scrapers require an API key or a cookie to work. If that is the case there will be instructions in the scraper file itself mentioning that and telling you how to add those fields.

## How to use scrapers?

You can find a list of sites that currently have a scraper at https://stashapp.github.io/CommunityScrapers/

:boom: For **most scrapers** you have to provide the object URL.

|                                             Stable build (>=v0.11.0)                                             |
| :--------------------------------------------------------------------------------------------------------------: |
|         Once you populate the `URL` field with an appropriate url, the scrape URL button will be active.         |
| ![stable](https://user-images.githubusercontent.com/23707269/139529970-d2966ae0-ae51-4e73-8f7c-d14844b90691.png) |

Clicking on that button brings up a popup that lets you select which fields to update.

Some scrapers support the `Scrape with...` function so you can use that instead of adding a url. `Scrape with...` usually works with either the `Title` field or the filename so make sure that they provide enough data for the scraper to work with.

A `Query` button is also available for scrapers that support that. Clicking the button allows you to edit the text that the scraper will use for your queries.

In case of errors/no results during scraping make sure to check stash's log section (**Settings** > **Logs** > set **Log Level** to **Debug**) for more info.

For more info please check the scraping help [section](https://docs.stashapp.cc/in-app-manual/scraping/) or ask help from the community.

## Host your own scrapers

We have a GitHub template available for those that prefer hosting on their own with step-by-step instructions to get started.

Repository: https://github.com/stashapp/scrapers-repo-template

## Community support

- **Forum:** [discourse.stashapp.cc](https://discourse.stashapp.cc) - Primary place for community support, feature requests, and discussions.
- **Discord:** [discord.gg/2TsNFKt](https://discord.gg/2TsNFKt) - Real-time chat and community support.
- **Lemmy:** [discuss.online/c/stashapp](https://discuss.online/c/stashapp) - Community discussions.

## Contributing

Contributions are always welcome! Use the [Scraping Configuration](https://github.com/stashapp/stash/blob/develop/ui/v2.5/src/docs/en/Manual/ScraperDevelopment.md) help section to get started and stop by the [Discord](https://discord.gg/2TsNFKt) #scrapers channel with any questions.

### Validation

The scrapers in this repository can be validated against a schema and checked for common errors.

[Deno](https://deno.com/) is used as a drop-in, sandboxed NodeJS alternative

```sh
# check all scrapers
deno run -R=scrapers -R="validator\scraper.schema.json" validate.js
# check specific scraper
deno run -R=scrapers -R="validator\scraper.schema.json" validate.js scrapers/foo.yml scrapers/bar.yml
```
Deno asks for env and sys permissions from [chalk](https://www.npmjs.com/package/chalk)

#### Docker option

Instead of Deno, [Docker](https://docs.docker.com/engine/install/) can be used to run the validator

```sh
docker run --rm -v .:/app denoland/deno:distroless run -R=/app/ -E /app/validate.js --ci
```
