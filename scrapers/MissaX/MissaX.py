import json
import re
import sys
import urllib.parse

import cloudscraper
from lxml import html

import py_common.log as log
from py_common.util import scraper_args
from py_common.types import ScrapedScene

"This scraper scrapes title and uses it to search the site and grab a cover from the search results, among other things"

STUDIO_MAP = {
    "missax.com": "MissaX",
    "allherluv.com": "All Her Luv",
}

scraper = cloudscraper.create_scraper()


def scraped_content(url):
    try:
        scraped = scraper.get(url)
        scraped.raise_for_status()
        return scraped.content
    except Exception as e:
        log.error(f"Unable to fetch '{url}': {e}")
        exit(1)


def scrape_cover(domain, title):
    # loop throught search result pages until img found
    for p in range(1, 6):
        log.debug(f"Searching page {p} for cover")
        url = f"https://{domain}/tour/search.php?st=advanced&qall=&qany=&qex={urllib.parse.quote(title)}&none=&tadded=0&cat%5B%5D=5&page={p}"
        body = scraped_content(url)
        tree = html.fromstring(body)
        if image := tree.xpath(f'//img[@alt="{title}"]/@src0_4x'):
            return image[0]
        if not tree.xpath(
            '//li[@class="active"]/following-sibling::li'
        ):  # if there is a next page
            break

    log.warning(f"Unable to find better cover for {title}")


def scene_from_url(url) -> ScrapedScene:
    domain = urllib.parse.urlparse(url).netloc.removeprefix("www.")
    studio = STUDIO_MAP.get(domain, domain)
    body = scraped_content(url)
    tree = html.fromstring(body)

    scene: ScrapedScene = {}

    if title := tree.xpath('//p[@class="raiting-section__title"]'):
        title = title[0].text.strip()
        log.debug(f"Title: {title}")
        scene["title"] = title
    else:
        log.warning("Title not found, bailing")
        exit(1)

    if (
        subheader := tree.xpath(
            '//p[@class="dvd-scenes__data" and contains(., " Added:")]'
        )
    ) and (
        date := re.match(
            r".*Added:\s(?P<month>\d\d)/(?P<day>\d\d)/(?P<year>\d{4}).*",
            subheader[0].text_content(),
            re.DOTALL | re.MULTILINE,
        )
    ):
        date = f"{date.group('year')}-{date.group('month')}-{date.group('day')}"
        log.debug(f"Date: {date}")
        scene["date"] = date
    else:
        log.warning("Date not found")

    if performers := tree.xpath(
        '//p[@class="dvd-scenes__data"]//a[contains(@href, "models")]'
    ):
        scene["performers"] = [
            {"name": x.text.strip(), "url": x.get("href")} for x in performers
        ]
        performers = ", ".join(p["name"] for p in scene["performers"])
        log.debug(f"Performers: {performers}")
    else:
        log.warning("Performers not found")

    if tags := tree.xpath(
        '//p[@class="dvd-scenes__data"]//a[contains(@href, "categories")]'
    ):
        scene["tags"] = [{"name": x.text.strip()} for x in tags]     
        tags = ", ".join(t["name"] for t in scene["tags"])
        log.debug(f"Tags: {tags}")
    else:
        log.warning("Tags not found")

    if details := tree.xpath(
        '//p[@class="dvd-scenes__title"]/following-sibling::p//text()'
    ):
        details = "".join(details)
        # Get rid of double spaces
        details = "\n".join(" ".join(line.split()) for line in details.split("\n"))
        # get rid of double newlines
        details = re.sub(r"\r?\n\n?", r"\n", details).strip()
        scene["details"] = details
    else:
        log.warning("Details not found")

    scene["studio"] = {"name": studio, "url": f"https://{domain}"}

    # cover from scene's page if better one is not found (it will be)
    bad_cover_url = tree.xpath("//img[@src0_4x]/@src0_4x")
    scene["image"] = scrape_cover(domain, title) or bad_cover_url
    log.debug(f"Image: {scene['image']}")
    return scene


# FRAGNEMT = {"url": "https://allherluv.com/tour/trailers/Like-I-Do.html"}

if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
