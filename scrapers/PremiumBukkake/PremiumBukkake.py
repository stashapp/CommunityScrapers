import json
import re
import sys
import time
from typing import Any
from urllib.parse import urljoin

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedTag
from py_common.util import scraper_args

ensure_requirements("requests", "lxml")
import requests  # noqa: E402
from lxml import html  # noqa: E402

BASE = "https://premiumbukkake.com"

session = requests.Session()
session.headers["User-Agent"] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)


def fetch(url: str) -> html.HtmlElement | None:
    try:
        res = session.get(url, timeout=10, allow_redirects=False)
    except requests.RequestException as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None
    # Paywalled and missing pages redirect to the homepage
    if res.status_code != 200:
        log.debug(f"{url} returned {res.status_code}")
        return None
    return html.fromstring(res.text, base_url=url)


def site_urls(url: str) -> tuple[str, str, str] | None:
    "The tour, members and free URLs for a scene, from any one of them"
    if "members.premiumbukkake.com" in url:
        m = re.search(r"/([^/]+)_vids\.html", url)
    else:
        m = re.search(r"/([^/]+)\.html", url)
    if not m:
        return None
    page = m[1]
    # The free site has one page for both camera angles
    free_page = re.sub(r"-(first|second)-camera", "", page, flags=re.IGNORECASE)
    return (
        f"{BASE}/tour2/updates/{page}.html",
        f"https://members.premiumbukkake.com/scenes/{page}_vids.html",
        f"https://free.premiumbukkake.com/updates/{free_page}.html",
    )


def text(element: html.HtmlElement, xpath: str) -> str:
    return " ".join(element.xpath(f"string({xpath})").split())


def info_row(section: html.HtmlElement, label: str) -> html.HtmlElement | None:
    return next(
        (
            row
            for row in section.xpath('.//div[@class="slide_info_row"]')
            if label in row.text_content()
        ),
        None,
    )


def parse_date(posted: str) -> str | None:
    try:
        return time.strftime("%Y-%m-%d", time.strptime(posted, "%B %d, %Y"))
    except ValueError:
        return None


def to_scraped_performer(name: str, url: str) -> ScrapedPerformer:
    performer: ScrapedPerformer = {"name": name, "gender": "FEMALE", "urls": [url]}
    if (page := fetch(url)) is None:
        return performer
    stats = {
        dt.text_content().strip(): dd.text_content().strip()
        for dt, dd in zip(
            page.xpath('//div[contains(@class,"block-bio-stats")]//dt'),
            page.xpath('//div[contains(@class,"block-bio-stats")]//dd'),
            strict=False,
        )
    }
    if height := stats.get("Height:"):
        performer["height"] = height
    # "88-63-91  (cup: 2)"
    if body := stats.get("Body:"):
        performer["measurements"] = body.split()[0]
    # Lines are separated by <br>, so join the text nodes rather than the paragraphs
    if details := "\n".join(
        s
        for t in page.xpath('//div[contains(@class,"block-bio-text")]//p//text()')
        if (s := t.strip())
    ):
        performer["details"] = details
    if image := page.xpath(
        'string(//div[contains(@class,"block-bio-img")]//img/@data-src)'
    ):
        performer["images"] = [urljoin(BASE, image)]
    return performer


def tour_scene(tour_url: str) -> ScrapedScene:
    "The tour page is the most accurate source, and the only one for some scenes"
    if (page := fetch(tour_url)) is None:
        log.warning(f"Unable to scrape tags/performers from {tour_url}")
        return {}
    # The first tour section is this scene, the rest are related scenes
    if not (sections := page.xpath('//div[@class="section tour"]')):
        return {}
    section = sections[0]

    scene: ScrapedScene = {}
    if title := text(section, './/h2[contains(@class,"slide_title")]'):
        scene["title"] = title
    if details := section.xpath('string(.//p[contains(@class,"slide_text")])').strip():
        scene["details"] = details
    # The studio code is part of the image path: /tour2/content/002/PB_462_.../12.jpg
    if image := section.xpath(
        'string(.//div[contains(@class,"slide_avatar")]//img/@data-src)'
    ):
        folder = image.rsplit("/", 1)[0]
        scene["image"] = urljoin(BASE, f"{folder}/0.jpg")
        if code := re.search(r"PB_\d+", folder):
            scene["code"] = code[0]
    if (row := info_row(section, "Posted")) is not None and (
        date := parse_date(text(row, ".").removeprefix("Posted "))
    ):
        scene["date"] = date
    if (row := info_row(section, "Categories:")) is not None and (
        tags := [
            ScrapedTag(name=s)
            for a in row.xpath(".//a")
            if (s := a.text_content().strip())
        ]
    ):
        scene["tags"] = tags
    if (row := info_row(section, "Pornstars:")) is not None and (
        performers := [
            to_scraped_performer(name, urljoin(BASE, a.get("href")))
            for a in row.xpath(".//a")
            if (name := a.text_content().strip())
        ]
    ):
        scene["performers"] = performers
    return scene


def free_scene(free_url: str) -> dict[str, Any] | None:
    "The free site's JSON-LD: a longer description, plus fallbacks"
    if (page := fetch(free_url)) is None:
        log.debug(f"No free site page at {free_url}")
        return None
    if not (scripts := page.xpath('//script[@type="application/ld+json"]/text()')):
        return None
    # The description contains raw newlines, which strict JSON rejects
    return json.loads(scripts[0], strict=False)


def clean_description(description: str) -> str:
    return "\n".join(" ".join(line.split()) for line in description.split("\n")).strip()


def scene_from_url(url: str) -> ScrapedScene | None:
    if not (urls := site_urls(url)):
        log.error(f"Could not extract the scene name from {url}")
        return None
    tour_url, members_url, free_url = urls

    scene = tour_scene(tour_url)
    scene["studio"] = {"name": "Premium Bukkake"}
    scene["urls"] = [tour_url, members_url]

    if not (ld := free_scene(free_url)):
        return scene

    scene["urls"].append(free_url)
    if description := ld.get("description"):
        scene["details"] = clean_description(description)
    # The free site's upload date can be a few days off the tour's
    if "date" not in scene and (date := ld.get("uploadDate")):
        scene["date"] = date
    if "image" not in scene and (image := ld.get("thumbnailUrl")):
        scene["image"] = image
    # "Performer A, Performer B, Scene type"
    *names, scene_type = (s.strip() for s in ld.get("actor", "").split(","))
    if "performers" not in scene and (
        performers := [ScrapedPerformer(name=n) for n in names if n]
    ):
        scene["performers"] = performers
    if "tags" not in scene and scene_type:
        scene["tags"] = [ScrapedTag(name=scene_type)]

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
