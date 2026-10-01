import json
import re
import sys
import time
from typing import Any

import requests

from py_common import log
from py_common.types import ScrapedScene
from py_common.util import scraper_args


def fetch_post(url: str) -> dict[str, Any] | None:
    try:
        response = requests.get(
            url, headers={"User-Agent": "stash-scraper/1.0"}, timeout=(3, 10)
        )
        response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None

    if not (
        match := re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
            response.text,
        )
    ):
        log.error(f"No __NEXT_DATA__ found on {url}")
        return None

    return json.loads(match.group(1))["props"]["pageProps"].get("post")


def to_iso_date(date: str) -> str:
    return time.strftime("%Y-%m-%d", time.strptime(date, "%b %d, %Y"))


def to_scraped_scene(post: dict[str, Any]) -> ScrapedScene:
    scene: ScrapedScene = {
        "title": post["title"].replace("_", " "),
        "urls": [f"https://fetishkitsch.com/post/{post['_id']}"],
        "date": to_iso_date(post["publishDate"]),
        "studio": {"name": "FetishKitsch", "urls": ["https://fetishkitsch.com/"]},
    }
    if shoot_date := post.get("shootDate"):
        scene["production_date"] = to_iso_date(shoot_date)
    if code := post.get("shootCode"):
        scene["code"] = str(code)
    if duration := post.get("videoLength"):
        scene["duration"] = int(duration)
    if image := post.get("videoThumbnail"):
        scene["image"] = image
    if tags := post.get("tags"):
        scene["tags"] = [{"name": t.replace("_", " ")} for t in tags]
    if people := post.get("people"):
        scene["performers"] = [{"name": p.replace("_", " ")} for p in people]
    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = (post := fetch_post(url)) and to_scraped_scene(post)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
