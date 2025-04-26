# Aylo network paywalled URLs

1. Check if your site is on the Aylo network. AyloAPI is usually installed as a dependency and the easiest way to tell.
2. Scrape a publicly accessible member URL with the URL scraper, this will importantly populate `aylo_tokens.json` at `~/.stash/scrapers/AyloAPI/aylo_tokens.json` which should now look like this:

```~/.stash/scrapers/AyloAPI/aylo_tokens.json
{
  "example": {
    "token": "eyJ...."
    "date": "2025-04-26"
  }
}
```
3. Logging into your account on the site, go into `Debugging -> Network` and find a request to `https://site-api.project1service.com/v2/releases` or similar. Under `Headers -> Request Headers -> Instance`, grab the value for `Instance` and paste it into the `aylo_tokens.json` file, replacing the existing token.