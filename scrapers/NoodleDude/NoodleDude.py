import datetime
import json
import re
import sys

import requests
from py_common.deps import ensure_requirements
from py_common.util import scraper_args
from py_common import log


ensure_requirements("lxml")
from lxml import html  # noqa: E402

scraper = requests.Session()


def xpath_string(tree, selector):
    raw = tree.xpath(selector)
    if not raw or len(raw) < 1:
        return ""
    return raw[0].strip()


def scrape(url: str, retries=0):
    if retries > 2:
        log.error(f"Giving up on '{url}' after 3 retries")
    try:
        scraped = scraper.get(url, timeout=(3, 7))
    except requests.exceptions.Timeout as exc_time:
        log.debug(f"Timeout: {exc_time}")
        return scrape(url, retries + 1)
    except Exception as e:
        log.error(f"scrape error {e}")
        sys.exit(1)
    if scraped.status_code >= 400:
        log.error(f"HTTP Error: {scraped.status_code}")
        sys.exit(1)
    return html.fromstring(scraped.content)


def scene_title(tree):
    return (
        xpath_string(tree, "//meta[@property='og:title']/@content")
        .split("|")[0]
        .strip()
    )


def scene_date(tree):
    stash_date = "%Y-%m-%d"
    date_format = "%B %d, %Y"
    raw = tree.xpath(
        "//div[contains(@class, 'video_info_wrapper')]//span[@id='release_date']/@title"
    )[0]
    raw = re.sub(r"(\d)(st|nd|rd|th)", r"\1", raw)
    return datetime.datetime.strptime(raw, date_format).strftime(stash_date)


def scene_details(tree):
    rawDescription = tree.xpath("//*[contains(@class, 'video_description')]")
    details = rawDescription[0].text_content()

    songs = ""
    rawSong = tree.xpath("//a[contains(@class, 'song_link')]//span/text()")
    rawSongs = zip(rawSong[::2], rawSong[1::2])
    for songTitle, songAuthor in rawSongs:
        songs += "\n" + songAuthor + " - " + songTitle

    if songs != "":
        details = details + "\n\nSongs:" + songs
    return details


def scene_tags(tree):
    # Tags do not appear anymore on the site
    return []


def parse_performer_card(tree):
    performer = {}
    imgUrl = tree.xpath("img/@src")
    if imgUrl and len(imgUrl) == 1 and imgUrl[0] != "/static/images/placeholder.svg":
        performer["images"] = [imgUrl[0]]
    performer["name"] = tree.xpath("div/span[1]/text()")[0]

    performer["urls"] = ["https://www.noodledude.io" + tree.xpath("@href")[0]]
    return performer


def get_performers(tree):
    detailsUrl = tree.xpath(
        "//*[@id='current-video']//button[contains(@class, 'btn-plus')]/@hx-get"
    )
    if not detailsUrl or len(detailsUrl) < 1:
        return []

    scrapedPerformers = scrape("https://www.noodledude.io" + detailsUrl[0])
    performerNodes = scrapedPerformers.xpath("//a[contains(@class, 'performer_card')]")
    return [parse_performer_card(p) for p in performerNodes]


def scene_image(tree):
    return tree.xpath("//video[@id='player']/@poster")[0]


def performer_name(tree):
    return xpath_string(tree, "h1/text()")


def performer_birthdate(tree):
    return xpath_string(tree, "span[not(@class)]/span[@class='fc2']/@title")


def performer_aliases(tree):
    raw = tree.xpath("span[@class='fs-s']/text()")
    if not raw or len(raw) == 0:
        return ""
    return ",".join(raw)


def performer_urls(tree):
    raw = tree.xpath("div[@class='performer-links']/a/@href")
    if not raw or len(raw) == 0:
        return []
    return raw


def scene_from_tree(tree):
    return {
        "title": scene_title(tree),
        "date": scene_date(tree),
        "details": scene_details(tree),
        "tags": scene_tags(tree),
        "image": scene_image(tree),
        "studio": {"name": "NoodleDudePMV"},
        "performers": get_performers(tree),
    }


def performer_from_tree(tree):
    performerTree = tree.xpath("//div[contains(@class, 'performer-main-info')]")[0]
    return {
        "name": performer_name(tree),
        "urls": performer_urls(performerTree),
        "birthdate": performer_birthdate(performerTree),
        "aliases": performer_aliases(performerTree),
        "images": tree.xpath("//img[@class='performer-image']/@src"),
    }


if __name__ == "__main__":
    op, args = scraper_args(prog="NoodleDude scraper")

    result = None

    match op, args:
        case "scene-by-url", {"url": url}:
            result = scene_from_tree(scrape(url))
        case "performer-by-url", {"url": url}:
            result = performer_from_tree(scrape(url))
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
