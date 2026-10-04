import json
import re
import sys
from html import unescape
from typing import Any
from urllib.parse import urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag
from py_common.util import dig, scraper_args

ensure_requirements("requests", "lxml")
import requests  # noqa: E402
from lxml import html  # noqa: E402

session = requests.Session()

TAG_TAXONOMIES = ("video-category", "video-categories")

PARENTS = {
    "milfuckd.com": "Dirty Cinema",
    "mypovfam.com": "Peter's Kingdom",
    "passionsonly.com": "Peter's Kingdom",
    "pervertedpov.com": "Peter's Kingdom",
    "rawwhitemeat.com": "Peter's Kingdom",
    "slutsaroundtown.com": "Peter's Kingdom",
}

# Elementor pages put the name in the anchor, Bricks pages in the list item's tooltip
PERFORMERS_XPATH = (
    "//span[contains(.,'Starring')]/a"
    " | //a[contains(@href,'performers') and @class='jet-listing-dynamic-terms__link']"
    " | //li[contains(@class,'single-video__cast-list-item')]//a[contains(@href,'/performers/')]"
)


def scrape_performers(page: str) -> list[ScrapedPerformer]:
    tree = html.fromstring(page)
    return [
        {"name": name, "urls": [a.get("href")]}
        for a in tree.xpath(PERFORMERS_XPATH)
        if (
            name := a.text_content().strip()
            or a.xpath("string(ancestor::li[1]/@data-balloon)").strip()
        )
    ]


def to_scraped_studio(host: str, site_name: str) -> ScrapedStudio:
    studio: ScrapedStudio = {"name": unescape(site_name)}
    if parent := PARENTS.get(host.removeprefix("www.")):
        studio["parent"] = {"name": parent}
    return studio


def to_scraped_scene(
    video: dict[str, Any], studio: ScrapedStudio, page: str
) -> ScrapedScene:
    scene: ScrapedScene = {
        "title": unescape(video["title"]["rendered"]),
        "urls": [video["link"]],
        "date": video["date"].split("T")[0],
        "studio": studio,
    }
    if details := re.sub(r"</?[^>]+>", "", video["content"]["rendered"]).strip():
        scene["details"] = unescape(details)
    if image := dig(video, "_embedded", "wp:featuredmedia", 0, "source_url"):
        scene["image"] = image
    if tags := [
        ScrapedTag(name=unescape(term["name"]))
        for terms in dig(video, "_embedded", "wp:term", default=[])
        for term in terms
        if term.get("taxonomy") in TAG_TAXONOMIES
    ]:
        scene["tags"] = tags
    if performers := scrape_performers(page):
        scene["performers"] = performers
    return scene


def scene_by_url(url: str) -> ScrapedScene | None:
    page = session.get(url)
    if page.status_code != 200:
        log.error(f"Error fetching {url}: {page.status_code}")
        return None

    pattern = r'type="application\/json" href="(.+?\/wp-json\/wp\/v2\/videos\/\d+)"'
    if not (api_url := re.search(pattern, page.text)):
        log.error(f"No wp-json URL found in {url}, site is probably incompatible")
        return None

    host = urlparse(api_url[1]).netloc
    video = session.get(api_url[1], params={"_embed": 1}).json()
    site = session.get(f"https://{host}/wp-json").json()
    return to_scraped_scene(video, to_scraped_studio(host, site["name"]), page.text)


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url}:
            result = scene_by_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
