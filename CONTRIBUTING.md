## Contributing

Contributions are always welcome! Use the [Scraping Configuration](https://github.com/stashapp/stash/blob/develop/ui/v2.5/src/docs/en/Manual/ScraperDevelopment.md) help section to get started and stop by the [Discord](https://discord.gg/2TsNFKt) #scrapers channel with any questions.

### Language
If possible, XPath or JSON based yml scrapers are always preferred over python scrapers unless explicitly required

### Validation

The scrapers in this repository can be validated against a schema and checked for common errors.

[Deno](https://deno.com/) is used as a drop-in, sandboxed NodeJS alternative

```sh
# check all scrapers
deno task validate
# check specific scraper
deno task validate scrapers/foo.yml scrapers/bar.yml
```
The Deno version used in CI is pinned in `.dvmrc`

#### Docker option

Instead of Deno, [Docker](https://docs.docker.com/engine/install/) can be used to run the validator

```sh
docker run --rm -v .:/app denoland/deno:distroless run -R=/app/ -E /app/validate.js --ci
```
