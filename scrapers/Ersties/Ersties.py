import json
import re
import sys
from datetime import UTC, datetime
from functools import cache
from typing import Any

from py_common import log
from py_common.config import get_config
from py_common.deps import ensure_requirements
from py_common.types import ScrapedGroup, ScrapedPerformer, ScrapedScene
from py_common.util import guess_nationality, scraper_args

ensure_requirements("requests", "bs4:beautifulsoup4")
import requests
from bs4 import BeautifulSoup

config = get_config(
    default="""
# Ersties auth configuration: while logged in, copy the "authorization" header of any
# request to api.ersties.com from your browser's developer tools (or the value of the
# "access_token" cookie, which holds the same token)
AUTHORIZATION =
"""
)

API_URL = "https://api.ersties.com"
IMAGE_URL = "https://thumb.ersties.com/format=jpeg/plain/https://ersties.com/content/images_mysql"
PERFORMER_IMAGE_URL = "https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/Model_Cover_Image/backup"


def bearer_token(value: str) -> str:
    "Accepts the header value, the bare token, or a whole cookie string"
    value = (value or "").strip()
    if match := re.search(r"access_token=([^;\s]+)", value):
        value = match.group(1)
    return value if value.lower().startswith("bearer ") else f"Bearer {value}"


session = requests.Session()
session.headers["authorization"] = bearer_token(config.AUTHORIZATION)


@cache
def api(path: str) -> Any:
    try:
        res = session.get(f"{API_URL}/{path}", timeout=30)
    except requests.RequestException as e:
        log.error(f"Failed to fetch {path}: {e}")
        return None
    if res.status_code != 200:
        log.error(
            f"HTTP {res.status_code} for {path}: check the auth values in config.ini"
        )
        return None
    return res.json()


def clean_text(details: str | None) -> str:
    "Strips escaped backslashes and HTML, keeping line breaks"
    if not details:
        return ""
    details = details.replace("\\", "")
    details = re.sub(r"<\s*/?br\s*/?\s*>", "\n", details)
    details = re.sub(r"</?p>", "\n", details)
    details = BeautifulSoup(details, features="html.parser").get_text()
    lines = (
        " ".join(w for w in line.strip(" ").split(" ") if w)
        for line in details.split("\n")
    )
    return "\n".join(lines).strip()


def to_date(epoch: Any) -> str | None:
    # Midnight-ish UTC releases would shift a day in far-east local timezones
    try:
        return datetime.fromtimestamp(int(epoch), UTC).date().isoformat()
    except (TypeError, ValueError):
        return None


def to_group(gallery: dict[str, Any]) -> ScrapedGroup:
    group: ScrapedGroup = {
        "name": gallery.get("title_en", ""),
        "studio": {"name": "Ersties"},
        "urls": [f"https://ersties.com/shoot/{gallery.get('id', '')}"],
    }
    if synopsis := clean_text(gallery.get("description_en")):
        group["synopsis"] = synopsis
    if image := gallery.get("image"):
        group["front_image"] = f"{IMAGE_URL}/Shoot_Cover/{image}"
    if date := to_date(gallery.get("available_since")):
        group["date"] = date
    return group


def to_performers(models: list[dict[str, Any]]) -> list[ScrapedPerformer]:
    return [
        {
            "name": model.get("name_en", ""),
            "details": model.get("description_en", ""),
            "urls": [f"https://ersties.com/profile/{model.get('id')}"],
            "images": [
                f"{IMAGE_URL}/Model_Cover_Image/backup/{model.get('thumbnail', '')}"
            ],
        }
        for model in models
    ]


def shoot_scene(gallery: dict[str, Any], url: str) -> ScrapedScene:
    "What every video in a shoot has in common"
    scene: ScrapedScene = {
        "urls": [url],
        "studio": {"name": "Ersties"},
        "performers": to_performers(gallery.get("participated_models", [])),
        "groups": [to_group(gallery)],
    }
    if title := gallery.get("title_en") or gallery.get("title"):
        scene["title"] = title
    if details := clean_text(gallery.get("description_en")):
        scene["details"] = details
    if image := gallery.get("image"):
        scene["image"] = f"{IMAGE_URL}/Shoot_Cover/{image}"
    if date := to_date(gallery.get("available_since")):
        scene["date"] = date
    return scene


def chapter_date(gallery_id: str, chapter_id: Any) -> str | None:
    "Trailers are released in their own chapter, days before the rest of the shoot"
    chapters = api(f"galleries/{gallery_id}/chapters") or []
    return next(
        (
            to_date(c.get("available_since"))
            for c in chapters
            if str(c.get("id")) == str(chapter_id)
        ),
        None,
    )


def video_scene(video_id: str) -> ScrapedScene | None:
    if not (video := api(f"videos/{video_id}")):
        return None
    # The video only carries the gallery's id and titles, the rest is on the gallery
    gallery = {**(video.get("gallery") or {})}
    gallery_id = str(gallery.get("id", ""))
    if gallery_id and (full := api(f"galleries/{gallery_id}")):
        gallery |= full

    url = f"https://ersties.com/shoot/{gallery_id}#play-{video_id}"
    scene = shoot_scene(gallery, url)
    scene["code"] = str(video.get("id", ""))
    scene["tags"] = [{"name": t.get("name_en", "")} for t in video.get("tags", [])]
    scene["performers"] = to_performers(video.get("participated_models", []))
    gallery_title = gallery.get("title_en") or gallery.get("title")
    if (scene_title := video.get("title_en") or video.get("title")) and gallery_title:
        scene["title"] = f"{gallery_title}: {scene_title}"
    if main := next((t for t in video.get("thumbnails", []) if t.get("is_main")), None):
        scene["image"] = (
            f"{IMAGE_URL}/images_videothumbnails/backup/{main.get('file_name', '')}"
        )
    if date := chapter_date(gallery_id, video.get("gallery_chapter_id")):
        scene["date"] = date
    if (duration := video.get("duration")) and str(duration).isdigit():
        scene["duration"] = int(duration)
    return scene


def scene_from_url(url: str) -> ScrapedScene | None:
    if match := re.search(r"#play-(\d+)", url):
        return video_scene(match.group(1))
    # A shoot page doesn't say which of its videos is playing
    if (match := re.search(r"/shoot/(\d+)", url)) and (
        gallery := api(f"galleries/{match.group(1)}")
    ):
        return shoot_scene(gallery, url)
    log.error('No shoot or scene ID in URL: expected "/shoot/<id>" or "#play-<id>"')
    return None


def group_from_url(url: str) -> ScrapedGroup | None:
    if not (match := re.search(r"/shoot/(\d+)", url)):
        log.error("No shoot ID found in URL")
        return None
    if not (gallery := api(f"galleries/{match.group(1)}")):
        return None
    return to_group(gallery)


def performer_from_url(url: str) -> ScrapedPerformer | None:
    if not (match := re.search(r"/profile/(\d+)", url)):
        log.error('No performer ID found in URL: it should end with "profile/<id>"')
        return None
    if not (model := api(f"models/{match.group(1)}")):
        return None

    performer: ScrapedPerformer = {"name": model["name_en"], "urls": [url]}
    if details := model.get("description_en"):
        performer["details"] = details
    if thumbnail := model.get("thumbnail"):
        performer["images"] = [f"{PERFORMER_IMAGE_URL}/{thumbnail}"]
    if location := model.get("location_en"):
        performer["country"] = guess_nationality(location)
    return performer


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "group-by-url", {"url": url} if url:
            result = group_from_url(url)
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
