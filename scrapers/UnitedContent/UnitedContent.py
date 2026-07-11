import json
import re
import sys
from datetime import datetime, timedelta

import requests

from py_common import log
from py_common.types import ScrapedScene
from py_common.util import scraper_args

API_URL = "https://api.fundorado.com/api/videodetail/{}"
IMAGE_CDN = "https://s01.uni73d.net"
PARENT_STUDIO = "United Content"

STUDIOS = {
    "orgasmabuse.com": "Orgasm Abuse",
    "rfmovies.com": "RF studio",
    "taworship.com": "TA Worship",
    "texasbukkake.com": "Texas Bukkake",
    "tickleabuse.com": "Tickle Abuse",
}

SCENE_URL = re.compile(r"https?://(?:www\.)?([\w.-]+)/video/(\d+)")

# The API serialises publication dates as midnight in Europe/Amsterdam, which is
# always 22:00 or 23:00 UTC on the previous day depending on daylight saving.
AMSTERDAM_MAX_OFFSET = timedelta(hours=2)


def localized(field: dict | None) -> str:
    if not field:
        return ""
    return field.get("en") or next(iter(field.values()), "")


def release_date(timestamp: str | None) -> str | None:
    if not timestamp:
        return None
    published = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if published.year < 1970:
        return None
    return (published + AMSTERDAM_MAX_OFFSET).date().isoformat()


def cover_image(video: dict) -> str | None:
    for key in ("artwork", "artwork_f16", "cover"):
        url = (video.get(key) or {}).get("large")
        if url:
            return url if url.startswith("http") else IMAGE_CDN + url
    return None


def scene_from_url(url: str) -> ScrapedScene | None:
    match = SCENE_URL.match(url)
    if not match:
        log.error(f"Not a supported scene URL: {url}")
        return None

    hostname, video_id = match.group(1).lower(), match.group(2)
    studio = STUDIOS.get(hostname)
    if not studio:
        log.error(f"Unknown United Content site: {hostname}")
        return None

    response = requests.get(API_URL.format(video_id), timeout=10)
    response.raise_for_status()
    video = response.json().get("video")
    if not video:
        log.error(f"No scene found with id {video_id}")
        return None

    scene: ScrapedScene = {
        "title": localized(video.get("title")),
        "details": localized(video.get("description")),
        "code": str(video["id"]),
        "urls": [f"https://{hostname}/video/{video['id']}/{video['slug']}"],
        "studio": {"name": studio, "parent": {"name": PARENT_STUDIO}},
        "performers": [{"name": actor["name"]} for actor in video.get("actors", [])],
        "tags": [{"name": localized(genre.get("title"))} for genre in video.get("genres", [])],
    }

    if date := release_date(video.get("publication_date")):
        scene["date"] = date
    if image := cover_image(video):
        scene["image"] = image
    if duration := (video.get("meta") or {}).get("duration_seconds"):
        scene["duration"] = duration

    return scene


if __name__ == "__main__":
    op, args = scraper_args()

    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Not implemented: Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
