# CommunityScrapers
This is a public repository containing scrapers created by the Stash Community.

To download the scrapers you can clone the git repo or download directly any of the scrapers.

When downloading directly click at the scraper.yml you want and then make sure to click the raw button:

![](https://user-images.githubusercontent.com/1358708/82524777-cd4cfe80-9afd-11ea-808d-5ea7bf26704f.jpg)

and then save page as file from the browser to preserve the correct format for the yml file.

Any scraper file has to be stored in the `~/.stash/scrapers` ( ~/.stash is where the config and database file are located) directory. If the `scrapers` directory is not there it needs to be created.

After updating the scrapers directory contents or editing a scraper file a restart of stash is needed and a refresh of the edit scene/performer page.(In recent stash builds instead of restarting __scrape with -> reload scrapers__ is enough)

Scrapers with **useCDP** set to true require that you have properly configured the `Chrome CDP path` setting in Stash. If you decide to use a remote instance the headless chromium docker image from https://hub.docker.com/r/chromedp/headless-shell/ is highly recommended.

## Scene Scrapers
You can find a list of sites currently supported for by community scene scraping in [SCENE-SCRAPERS.md](https://github.com/stashapp/CommunityScrapers/blob/master/SCENE-SCRAPABLE.md)

For scene scrapers you have to edit the url of the scene. Once you populate that field with a specific url a button will appear.
![](https://user-images.githubusercontent.com/48220860/85202637-698e3f00-b310-11ea-9c06-b2cfe931474a.png)

Clicking on that button brings up the screne scrape popup that lets you select which fields to update.

## Performer Scrapers
This list is meant to keep track of which sites are already supported by existing community scrapers. And which scrapers support them. When introducing a new scraper, add the sites your scraper supports to this list in your PR. Please keep the site list in alphabetical order to keep the list tidy.

Supported Site|Scraper
------------- | -------------
babepedia.com|Babepedia.yml
freeones.xxx|FreeonesCommunity.yml
iafd.com|Iafd.yml
manyvids.com|ManyVids.yml
pornhub.com|Pornhub.yml
sexvr.com|SexVR.yml

## Contributing
Contributions are always welcome! Use the [Scraping Configuration](https://github.com/stashapp/stash/wiki/Scraping-configuration) wiki entry to get started and stop by the [Discord](https://discord.gg/2TsNFKt) #the-scraping-initiative channel with any questions.
