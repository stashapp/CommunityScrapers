import json
import re
import sys
from typing import Any

from py_common import log
from py_common.deps import ensure_requirements
from py_common.rsc import Flight
from py_common.types import (
    ScrapedGallery,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedStudio,
    ScrapedTag,
)
from py_common.util import dig, scraper_args

ensure_requirements("requests", "bs4:beautifulsoup4")

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
    }
)


def _fetch_page(scrape_url: str) -> str:
    log.debug(f"Fetching '{scrape_url}'")
    try:
        response = session.get(scrape_url, timeout=(3, 6))
    except requests.exceptions.RequestException as req_ex:
        log.error(f"Error fetching '{scrape_url}': {req_ex}")
        sys.exit(-1)

    if response.status_code != 200:
        log.error(
            f"Fetching '{scrape_url}' resulted in error status: {response.status_code}"
        )
        sys.exit(-1)

    return response.text


def _details(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    lines = soup.find_all(
        ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "pre"]
    )
    text = (
        "\n".join(line.get_text().strip() for line in lines)
        if lines
        else soup.get_text()
    )
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _page(scrape_url: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """
    The page's video/photoset data and its site settings
    """
    flight = Flight.from_html(_fetch_page(scrape_url))
    page = flight.first(lambda d: d.get("pageType") in ("video", "photoset")) or {}
    if not isinstance(data := page.get("data"), dict):
        log.error(
            f"Could not extract content data from Next.js payload at '{scrape_url}'"
        )
        sys.exit(-1)
    return data, flight.first(lambda d: "site_long_name" in d)


def to_scraped_studio(site: dict[str, Any]) -> ScrapedStudio:
    studio = ScrapedStudio(name=site["site_long_name"])
    if url := site.get("site_url"):
        studio["urls"] = [url]
    return studio


def to_scraped_scene(data: dict[str, Any], site: dict[str, Any] | None) -> ScrapedScene:
    scene: ScrapedScene = {}
    if title := data.get("title"):
        scene["title"] = title
    if date := data.get("publish_date"):
        scene["date"] = date.split("T")[0]
    if (details := data.get("description")) and (text := _details(details)):
        scene["details"] = text
    if tags := data.get("tags"):
        scene["tags"] = [ScrapedTag(name=t["name"]) for t in tags]
    if performers := data.get("casts"):
        scene["performers"] = [
            ScrapedPerformer(name=p["screen_name"]) for p in performers
        ]
    if site:
        scene["studio"] = to_scraped_studio(site)
    if image := dig(data, ("poster_src", "cover_photo")):
        scene["image"] = image
    if duration := data.get("duration"):
        scene["duration"] = duration

    return scene


def to_scraped_gallery(
    data: dict[str, Any], site: dict[str, Any] | None
) -> ScrapedGallery:
    gallery: ScrapedGallery = {}
    if title := data.get("title"):
        gallery["title"] = title
    if date := data.get("publish_date"):
        gallery["date"] = date.split("T")[0]
    if (details := data.get("description")) and (text := _details(details)):
        gallery["details"] = text
    if tags := data.get("tags"):
        gallery["tags"] = [ScrapedTag(name=t["name"]) for t in tags]
    if performers := data.get("casts"):
        gallery["performers"] = [ScrapedPerformer(name=p["screen_name"]) for p in performers]
    if site:
        gallery["studio"] = to_scraped_studio(site)

    return gallery


def scene_from_url(scene_url: str) -> ScrapedScene:
    return to_scraped_scene(*_page(scene_url))


def gallery_from_url(gallery_url: str) -> ScrapedGallery:
    return to_scraped_gallery(*_page(gallery_url))


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
