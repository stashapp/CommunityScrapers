import json
import re
import sys
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedGallery, ScrapedPerformer, ScrapedScene
from py_common.util import dig, scraper_args

ensure_requirements("requests", "lxml")
import requests
from lxml import html

session = requests.Session()
session.headers["User-Agent"] = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def get(url: str, **kwargs) -> requests.Response | None:
    log.debug(f"Request URL: {url}")
    try:
        response = session.get(url, timeout=10, **kwargs)
        response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Request to {url} failed: {e}")
        return None
    return response


def post_data(post_id: str) -> dict[str, Any] | None:
    "The API needs the CSRF token (and session cookie) the homepage hands out"
    if not (home := get("https://fantia.jp/")):
        return None
    if not (
        csrf := html.fromstring(home.text).xpath("//meta[@name='csrf-token']/@content")
    ):
        log.error("CSRF token not found on the homepage")
        return None
    headers = {"X-CSRF-Token": csrf[0], "X-Requested-With": "XMLHttpRequest"}
    if response := get(f"https://fantia.jp/api/v1/posts/{post_id}", headers=headers):
        return response.json().get("post")
    return None


def to_scraped_performer(fanclub: dict[str, Any]) -> ScrapedPerformer:
    performer: ScrapedPerformer = {"name": fanclub["creator_name"]}
    # Creators without an avatar get a relative default image, which isn't theirs
    if (image := dig(fanclub, "user", "image", "large")) and (
        "/images/fallback/" not in image
    ):
        performer["images"] = [urljoin("https://fantia.jp/", image)]
    return performer


def to_scraped_scene(post: dict[str, Any], url: str) -> ScrapedScene:
    fanclub = post["fanclub"]
    return {
        "title": post["title"].strip(),
        "details": post["comment"].strip(),
        "urls": [url],
        "image": post["thumb_micro"].replace("micro_", ""),
        "date": datetime.strptime(post["posted_at"], "%a, %d %b %Y %H:%M:%S %z")
        .date()
        .isoformat(),
        "performers": [to_scraped_performer(fanclub)],
        "tags": [{"name": tag["name"]} for tag in post["tags"]],
        "studio": {
            "name": fanclub["name"],
            "urls": [f"https://fantia.jp/fanclubs/{fanclub['id']}"],
            "parent": {"name": "Fantia"},
        },
    }


def post_from_url(url: str) -> ScrapedScene | None:
    if not (match := re.search(r"fantia\.jp/posts/(\d+)", url)):
        log.error(f"No post ID found in {url}")
        return None
    if not (post := post_data(match.group(1))):
        return None
    return to_scraped_scene(post, f"https://fantia.jp/posts/{match.group(1)}")


def gallery_from_url(url: str) -> ScrapedGallery | None:
    if not (scene := post_from_url(url)):
        return None
    return {
        "title": scene["title"],
        "details": scene["details"],
        "urls": scene["urls"],
        "date": scene["date"],
        "performers": scene["performers"],
        "tags": scene["tags"],
        "studio": scene["studio"],
    }


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = post_from_url(url)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
