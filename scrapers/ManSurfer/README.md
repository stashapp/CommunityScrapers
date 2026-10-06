# ManSurferTV Scraper

Stash scraper for [ManSurferTV](https://www.mansurfer.tv/), supporting both **Scenes** and **Groups**.

## Supported Features

### Scenes

The scraper can retrieve scene metadata using a ManSurferTV movie URL.

Using a URL is the **recommended method**, as it provides the most reliable match and allows the scraper to retrieve the metadata directly from the correct ManSurferTV page.

Scenes can also be scraped **without providing a URL**. In this case, the scraper searches ManSurferTV using the scene title and attempts to match the corresponding movie.

Search-based scraping is less reliable than URL-based scraping and may occasionally return an incorrect or less satisfactory result, particularly when titles are similar or ambiguous.

Supported scene operations:

- Scrape by URL
- Scrape by name
- Scrape from a Stash scene fragment
- Scrape from a query fragment

When a scene title contains a scene number, such as `Movie Title: Scene 2`, the scraper attempts to identify the corresponding scene within the ManSurferTV movie page and retrieve scene-specific performers, tags and image data.

### Groups

The scraper also supports Stash **Groups**, using ManSurferTV movie pages as the metadata source.

Groups are currently scraped **by URL**.

Example:

```text
https://www.mansurfer.tv/dispatcher/movieDetail?...&movieId=12345&locale=en
```

The scraper can retrieve available movie-level metadata such as:

- Title
- Director
- Release date
- Duration
- Studio
- Synopsis
- Front cover
- Back cover
- Source URL

## Recommended Usage

For the best results, add the corresponding ManSurferTV URL to the Scene or Group in Stash and scrape using that URL.

For Scenes without a known URL, the scraper can search ManSurferTV automatically using the existing scene title, but the resulting match should be reviewed before applying the metadata.

## Requirements

This scraper requires:

- `py_common`
- `requests`
- `beautifulsoup4`

## Source

Metadata is retrieved from:

https://www.mansurfer.tv/