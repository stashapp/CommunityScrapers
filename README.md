# CommunityScrapers
This is a public repository containing scrapers created by the Stash Community.

**:exclamation: Make sure to read ALL of the instructions here before requesting any help in the discord channel  :exclamation:**

To download the scrapers you can clone the git repo or download directly any of the scrapers.

When downloading directly click at the scraper.yml you want and then make sure to click the raw button:

![](https://user-images.githubusercontent.com/1358708/82524777-cd4cfe80-9afd-11ea-808d-5ea7bf26704f.jpg)

and then save page as file from the browser to preserve the correct format for the yml file.


Any scraper file has to be stored in the `~/.stash/scrapers` ( ~/.stash is where the config and database file are located) directory. If the `scrapers` directory is not there it needs to be created.

After updating the scrapers directory contents or editing a scraper file a restart of stash is needed and a refresh of the edit scene/performer page.(In recent stash builds instead of restarting __scrape with -> reload scrapers__ is enough)

Some sites block content if the user agent is not valid. If you get some kind of blocked or denied message make sure to configure the `Scraping ->
Scraper User Agent` setting in stash. Valid strings e.g. for firefox can be found here https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent/Firefox . Scrapers for those sites should have a comment mentioning this along with a tested and working user agent string

Scrapers with **useCDP** set to true require that you have properly configured the `Chrome CDP path` setting in Stash. If you decide to use a remote instance the headless chromium docker image from https://hub.docker.com/r/chromedp/headless-shell/ is highly recommended.

## Scrapers
You can find a list of sites currently supported for by community scraping in [SCRAPERS-LIST.md](https://github.com/stashapp/CommunityScrapers/blob/master/SCRAPERS-LIST.md)

:boom: For **most scrapers** you have to provide the scene/performer url.

|-| Stable (<=v0.10.0) | Development build |
|:-:|:--:|:--:|
|Once you populate the `URL` field with an appropriate url| The scrape URL button will appear.| The scrape URL button will be active.|
|Image|![stable](https://user-images.githubusercontent.com/23707269/139531203-e63b3587-ba37-4927-9956-ef9373256a50.png)|![dev](https://user-images.githubusercontent.com/23707269/139529970-d2966ae0-ae51-4e73-8f7c-d14844b90691.png)|

Clicking on that button brings up a popup that lets you select which fields to update.

Some scrapers support the `Scrape with...` function so you can you use that instead of adding a url. `Scrape with...` usually works with either the `Title` field or the filename so make sure that they provide enough data for the scraper to work with.

On newer stash versions there is a `Query` button for scrapers that support that. Clicking the button allows you to edit the text that the scraper will use for your queries.

In case of errors/no results during scraping make sure to check stash's log section (Settings->Logs->Log Level Debug) for more info.

## Contributing
Contributions are always welcome! Use the [Scraping Configuration](https://github.com/stashapp/stash/blob/develop/ui/v2.5/src/docs/en/ScraperDevelopment.md) wiki entry to get started and stop by the [Discord](https://discord.gg/2TsNFKt) #the-scraping-initiative channel with any questions.

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
