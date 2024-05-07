# CommunityScrapers

This is a public repository containing scrapers created by the Stash Community.

**:exclamation: Make sure to read ALL of the instructions here before requesting any help in the Discord channel. For a more user friendly step-by-step guide you can check out the [Guide to Scraping](https://docs.stashapp.cc/beginner-guides/guide-to-scraping/) :exclamation:**

When asking for help do not forget to mention what version of Stash you are using, the scraper that is failing, the URL you are attempting to scrape, and your current Python version (but only if the scraper requires Python)

Note that some scrapers (notably [ThePornDB for Movies](./scrapers/ThePornDBMovies.yml) and [ThePornDB for JAV](./scrapers/ThePornDBJAV.yml)) require extra configuration. As of v0.24.0 this is not possible through the web interface so you will need to open these in a text editor and read the instructions to add the necessary fields, usually an API key or a cookie.

## Installing scrapers

With the [v0.24.0 release of Stash](https://github.com/stashapp/stash/releases/tag/v0.24.0) you no longer need to install scrapers manually: if you go to `Settings > Metadata Providers` you can find the scrapers from this repository in the `Community (stable)` feed and install them without ever needing to copy any files manually. Note that some scrapers still require [manual configuration](#manually-configured-scrapers)

If you still prefer to manage your scrapers manually that is still supported as well, using the same steps as before. Manually installed scrapers and ones installed through Stash can both be used at the same time.

## Installing scrapers (manually)

To download all of the scrapers at once you can clone the git repository. If you only need some of the scrapers they can be downloaded individually.

When downloading directly click at the `.yml` you want and then make sure to click the raw button:

![](https://user-images.githubusercontent.com/1358708/82524777-cd4cfe80-9afd-11ea-808d-5ea7bf26704f.jpg)

and then save page as file from the browser to preserve the correct format for the `.yml` file.

Any scraper file has to be stored in the path you've configured as your `Scrapers Path` in `Settings > System > Application Paths`, which is `~/.stash/scrapers` by default. You may recognize `~/.stash` as the folder where the config and database file are located.

After manually updating the scrapers folder contents or editing a scraper file a reload of the scrapers is needed and a refresh of the edit scene/performer page. (**Scrape with... -> Reload scrapers**)

Some sites block content if the user agent is not valid. If you get some kind of blocked or denied message make sure to configure the `Scraping ->
Scraper User Agent` setting in stash. Valid strings e.g. for firefox can be found here https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent/Firefox . Scrapers for those sites should have a comment mentioning this along with a tested and working user agent string

Scrapers with **useCDP** set to true require that you have properly configured the `Chrome CDP path` setting in Stash. If you decide to use a remote instance the headless chromium docker image from https://hub.docker.com/r/chromedp/headless-shell/ is highly recommended.

## Python scrapers

Some scrapers require external programs to function, usually [Python](https://www.python.org/). All scrapers are tested with the newest stable release of Python, currently 3.12.2.

Depending on your operating system you may need to install both Python and the scrapers' dependencies before they will work. For Windows users we strongly recommend installing Python using the [installers from python.org](https://www.python.org/downloads/) instead of through the Windows Store, and also installing it outside of the Users folder so it is accessible to the entire system: a commonly used option is `C:\Python312`.

After installing Python you should install the most commonly used dependencies by running the following command in a terminal window:

```cmd
python -m pip install stashapp-tools requests cloudscraper beautifulsoup4 lxml
```

You may need to replace `python` with `py` in the command if you are running on Windows.

If Stash does not detect your Python installation you can set the `Python executable path` in `Settings > System > Application Paths`. Note that this needs to point to the executable itself and not just the folder it is in.

## Manually configured scrapers

Some scrapers need extra configuration before they will work. This is unfortunate if you install them through the web interface as any updates will overwrite your changes.

- [ThePornDBMovies](./scrapers/ThePornDBMovies.yml) and [ThePornDBJAV](./scrapers/ThePornDBJAV.yml) need to be edited to have your API key in them. Make sure you do not remove the `Bearer` part when you add your key.
- Python scrapers that need to communicate with your Stash (to create markers, for example, or to search your file system) _might_ need to be configured to talk to your local Stash: by default they will use `http://localhost:9999/graphql` with no authentication to make their queries, but if your setup requires otherwise then you can find `py_common/config.ini` and set your own values.
- Python scrapers that can be configured will (usually) create a default configuration file called `config.ini` in their respective directories the first time you run them.

## Scrapers

You can find a list of sites that currently have a scraper in [SCRAPERS-LIST.md](https://github.com/stashapp/CommunityScrapers/blob/master/SCRAPERS-LIST.md)

:boom: For **most scrapers** you have to provide the scene/performer URL

|                                             Stable build (>=v0.11.0)                                             |
| :--------------------------------------------------------------------------------------------------------------: |
|         Once you populate the `URL` field with an appropriate url, the scrape URL button will be active.         |
| ![stable](https://user-images.githubusercontent.com/23707269/139529970-d2966ae0-ae51-4e73-8f7c-d14844b90691.png) |

Clicking on that button brings up a popup that lets you select which fields to update.

Some scrapers support the `Scrape with...` function so you can you use that instead of adding a url. `Scrape with...` usually works with either the `Title` field or the filename so make sure that they provide enough data for the scraper to work with.

A `Query` button is also available for scrapers that support that. Clicking the button allows you to edit the text that the scraper will use for your queries.

In case of errors/no results during scraping make sure to check stash's log section (Settings->Logs->Log Level Debug) for more info.

For more info please check the scraping help [section](https://github.com/stashapp/stash/blob/develop/ui/v2.5/src/docs/en/Manual/Scraping.md)

## Contributing

Contributions are always welcome! Use the [Scraping Configuration](https://github.com/stashapp/stash/blob/develop/ui/v2.5/src/docs/en/Manual/ScraperDevelopment.md) help section to get started and stop by the [Discord](https://discord.gg/2TsNFKt) #scrapers channel with any questions.

The last line of a scraper definition (`.yml` file) must be the last updated date, in the following format:  
`# Last Updated Month Day, Year`  
Month = Full month name (`October`)  
Day = Day of month, with leading zero (`04`, `16`)  
Year = Full year (`2020`)  
Example: `# Last Updated October 04, 2020`

### Validation

The scrapers in this repository can be validated against a schema and checked for common errors.

First, install the validator's dependencies - inside the [`./validator`](./validator) folder, run: `yarn`.

Then, to run the validator, use `node validate.js` in the root of the repository.  
Specific scrapers can be checked using: `node validate.js scrapers/foo.yml scrapers/bar.yml`
