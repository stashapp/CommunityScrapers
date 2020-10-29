# CommunityScrapers
This is a public repository containing scrapers created by the Stash Community.

To download the scrapers you can clone the git repo or download directly any of the scrapers.

When downloading directly click at the scraper.yml you want and then make sure to click the raw button:

![](https://user-images.githubusercontent.com/1358708/82524777-cd4cfe80-9afd-11ea-808d-5ea7bf26704f.jpg)

and then save page as file from the browser to preserve the correct format for the yml file.

Any scraper file has to be stored in the `~/.stash/scrapers` ( ~/.stash is where the config and database file are located) directory. If the `scrapers` directory is not there it needs to be created.

After updating the scrapers directory contents or editing a scraper file a restart of stash is needed and a refresh of the edit scene/performer page.(In recent stash builds instead of restarting __scrape with -> reload scrapers__ is enough)

Some sites block content if the user agent is not valid. If you get some kind of blocked or denied message make sure to configure the `Scraping ->
Scraper User Agent` setting in stash. Valid strings e.g. for firefox can be found here https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent/Firefox . Scrapers for those sites should have a comment mentioning this along with a tested and working user agent string

Scrapers with **useCDP** set to true require that you have properly configured the `Chrome CDP path` setting in Stash. If you decide to use a remote instance the headless chromium docker image from https://hub.docker.com/r/chromedp/headless-shell/ is highly recommended.

## Scene Scrapers
You can find a list of sites currently supported for by community scene scraping in [SCENE-SCRAPERS.md](https://github.com/stashapp/CommunityScrapers/blob/master/SCENE-SCRAPABLE.md)

For scene scrapers you have to edit the url of the scene. Once you populate that field with a specific url a button will appear.
![](https://user-images.githubusercontent.com/48220860/85202637-698e3f00-b310-11ea-9c06-b2cfe931474a.png)

Clicking on that button brings up the screne scrape popup that lets you select which fields to update.


Some scrapers like ThePornDB.yml support the scrape with function so you can you use that instead of adding a url.


## Movie Scrapers
This list is meant to keep track of which sites are already supported by existing community scrapers. And which scrapers support them. When introducing a new scraper, add the sites your scraper supports to this list in your PR. Please keep the site list in alphabetical order to keep the list tidy.

Supported Site|Scraper
------------- | -------------
adultdvdmarketplace.com|AdultDvdMarketPlace.yml
adultdvdempire.com|AdultEmpire.yml
aebn.com|AEBN.yml
digitalplayground.com|MindGeek.yml
evilangel.com|GammaEntertainment.yml
iafd.com|Iafd.yml
javlibrary.com (+mirror)|javlibrary.yml
julesjordan.com|JulesJordan.yml
newsensations.com|NewSensationsMain.yml
private.com|Private.yml
streaming.iafd.com|IafdStreaming.yml
transsensual.com|MindGeek.yml

## Performer Scrapers
This list is meant to keep track of which sites are already supported by existing community scrapers. And which scrapers support them. When introducing a new scraper, add the sites your scraper supports to this list in your PR. Please keep the site list in alphabetical order to keep the list tidy.

Supported Site|Scraper
------------- | -------------
assholefever.com|GammaEntertainment.yml
babepedia.com|Babepedia.yml
brazzers.com|Brazzers.yml
evilangel.com|GammaEntertainment.yml
freeones.com|FreeonesCommunity.yml
iafd.com|Iafd.yml
julesjordan.com|JulesJordan.yml
manyvids.com|ManyVids.yml
metadataapi.net|ThePornDB.yml
MindGeek (31 sites)|MindGeek.yml
modelhub.com|Modelhub.yml
pornhub.com|Pornhub.yml
realitykings.com|Brazzers.yml
sexvr.com|SexVR.yml
stasyq.com|StasyQ.yml
thenude.com|TheNude.yml
timtales.com|TimTales.yml
xslist.org|Xslist.yml

## Gallery Scrapers
This list is meant to keep track of which sites are already supported by existing community scrapers. And which scrapers support them. When introducing a new scraper, add the sites your scraper supports to this list in your PR. Please keep this site list in alphabetical order to keep the list tidy.

Supported Site|Scraper
------------- | -------------
anilos.com|Nubiles.yml
badteenspunished.com|Nubiles.yml
bountyhunterporn.com|Nubiles.yml
brattysis.com|Nubiles.yml
daddyslilangel.com|Nubiles.yml
deeplush.com|Nubiles.yml
detentiongirls.com|Nubiles.yml
driverxxx.com|Nubiles.yml
fitting-room.com|FittingRoom.yml
hentai2read.com|hentai2read.yml
karissa-diamond.com|Karissa-Diamond.yml
momsteachsex.com|Nubiles.yml
mplstudios.com|MPLStudios.yml
myfamilypies.com|Nubiles.yml
nfbusty.com|Nubiles.yml
nhentai.net|nhentai.yml
nubilefilms.com|Nubiles.yml
nubiles-casting.com|Nubiles.yml
nubiles-porn.com|Nubiles.yml
nubiles.net|Nubiles.yml
nubileset.com|Nubiles.yml
nubilesunscripted.com|Nubiles.yml
petiteballerinasfucked.com|Nubiles.yml
petitehdporn.com|Nubiles.yml
princesscum.com|Nubiles.yml
stepsiblingscaught.com|Nubiles.yml
teacherfucksteens.com|Nubiles.yml
thatsitcomshow.com|Nubiles.yml

## Contributing
Contributions are always welcome! Use the [Scraping Configuration](https://github.com/stashapp/stash/blob/develop/ui/v2.5/src/docs/en/Scraping.md) wiki entry to get started and stop by the [Discord](https://discord.gg/2TsNFKt) #the-scraping-initiative channel with any questions.
