import json
import re
import struct
import sys
import urllib.parse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedScene
from py_common.util import scraper_args

ensure_requirements("cloudscraper", "lxml")
import cloudscraper  # noqa: E402
import requests  # noqa: E402
from lxml import html  # noqa: E402

"This scraper scrapes title and uses it to search the site and grab a cover from the search results, among other things"

STUDIO_MAP = {
    "missax.com": "MissaX",
    "allherluv.com": "All Her Luv",
}

scraper = cloudscraper.create_scraper()


def scraped_content(url: str) -> bytes:
    try:
        scraped = scraper.get(url)
        scraped.raise_for_status()
        return scraped.content
    except requests.RequestException as e:
        log.error(f"Unable to fetch '{url}': {e}")
        sys.exit(1)


def scrape_cover(domain: str, title: str) -> str | None:
    # loop throught search result pages until img found
    for p in range(1, 6):
        log.debug(f"Searching page {p} for cover")
        url = f"https://{domain}/tour/search.php?st=advanced&qall=&qany=&qex={urllib.parse.quote(title)}&none=&tadded=0&cat%5B%5D=5&page={p}"
        body = scraped_content(url)
        tree = html.fromstring(body)
        if image := tree.xpath("//img[@alt=$title]/@src0_4x", title=title):
            return image[0]
        if not tree.xpath(
            '//li[@class="active"]/following-sibling::li'
        ):  # if there is a next page
            break

    log.warning(f"Unable to find better cover for {title}")


def jpeg_size(buffer: bytes) -> tuple[int, int] | None:
    i = 2
    while i + 9 <= len(buffer) and buffer[i] == 0xFF:
        marker = buffer[i + 1]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", buffer[i + 5 : i + 9])
            return width, height
        i += 2 + struct.unpack(">H", buffer[i + 2 : i + 4])[0]
    return None


def image_size(url: str) -> tuple[int, int] | None:
    # The frame header sits behind up to ~100KB of embedded metadata,
    # so stream until it has been read instead of downloading the whole image
    try:
        with scraper.get(url, stream=True, timeout=15) as res:
            if not res.ok:
                return None
            buffer = b""
            for chunk in res.iter_content(16384):
                buffer += chunk
                if size := jpeg_size(buffer):
                    return size
                if len(buffer) > 512 * 1024:
                    return None
    except requests.RequestException as e:
        log.debug(f"Unable to read size of '{url}': {e}")
    return None


def best_tier(url: str) -> str:
    # -full is the original, -4x is a recompressed (sometimes upscaled) copy;
    # on the oldest titles -full is a different picture, which shows as a different aspect ratio
    full = url.replace("-4x.jpg", "-full.jpg")
    if (
        full != url
        and (cover := image_size(url))
        and (original := image_size(full))
        and abs(original[0] / original[1] - cover[0] / cover[1]) < 0.01
    ):
        return full
    return url


def scene_from_url(url: str) -> ScrapedScene:
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
        sys.exit(1)

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

    if runtime := re.search(
        r"Runtime:\s*((?:\d+:)?\d+:\d\d)",
        tree.xpath(
            'string(//p[@class="dvd-scenes__data" and contains(., "Runtime:")])'
        ),
    ):
        scene["duration"] = sum(
            int(part) * 60**i for i, part in enumerate(reversed(runtime[1].split(":")))
        )

    if performers := tree.xpath(
        '//p[@class="dvd-scenes__data"]//a[contains(@href, "models")]'
    ):
        scene["performers"] = [
            {"name": x.text_content().strip(), "urls": [x.get("href")]}
            for x in performers
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

    if details := "\n\n".join(
        text
        for p in tree.xpath('//p[@class="dvd-scenes__title"]/following-sibling::p')
        if (text := " ".join(p.text_content().split()))
    ):
        scene["details"] = details
    else:
        log.warning("Details not found")

    scene["studio"] = {"name": studio, "urls": [f"https://{domain}"]}

    # cover from scene's page if better one is not found (it will be)
    bad_cover_url = tree.xpath("string(//img[@src0_4x]/@src0_4x)")
    if image := scrape_cover(domain, title) or bad_cover_url:
        # The CDN URLs carry expiring tokens; the site itself serves the same path without one
        scene["image"] = best_tier(
            f"https://{domain}{urllib.parse.urlparse(image).path}"
        )
        log.debug(f"Image: {scene['image']}")
    return scene


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
