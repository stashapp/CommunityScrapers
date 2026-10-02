import json
import re
import sys

from py_common import log
from py_common.cache import cache_to_disk
from py_common.config import get_config
from py_common.deps import ensure_requirements
from py_common.types import ScrapedScene
from py_common.util import dig, scraper_args

ensure_requirements("cloudscraper")

import cloudscraper  # noqa: E402

config = get_config(
    default="""
username = 
password =
"""
)
scraper = cloudscraper.create_scraper()


@cache_to_disk(ttl=60 * 60 * 24)
def auth_token(username: str, password: str):
    login_url = "https://api.iwara.tv/user/login"
    payload = {"email": username, "password": password}
    response = scraper.post(
        login_url,
        headers={
            "Host": "api.iwara.tv",
            "Origin": "https://www.iwara.tv",
            "Referer": "https://www.iwara.tv",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
        },
        json=payload,
    )
    if response.status_code != 200:
        log.error(f"{response.status_code} {response.reason} - {response.text}")
        sys.exit(1)
    return response.json().get("token")


has_login = config.username and config.password
if has_login:
    token = auth_token(config.username, config.password)
    scraper.headers["Authorization"] = f"Bearer {token}"


def api_request(query: str, params: dict | None = None) -> dict:
    response = scraper.get(query, params=params)
    if response.status_code == 404 and not has_login:
        log.error(
            "Login required for this video: please fill in your username and password in Iwara/config.ini"
        )
        sys.exit(1)
    elif not response.ok:
        log.error(f"Failed to fetch video: {response.status_code} {response.reason}")
        sys.exit(1)

    return response.json()


def youtube_thumbnail(embed_url: str) -> str | None:
    if not (
        match := re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([\w-]{11})", embed_url)
    ):
        return None
    # maxresdefault only exists for HD uploads, hqdefault always does
    maxres = f"https://i.ytimg.com/vi/{match[1]}/maxresdefault.jpg"
    if scraper.head(maxres).ok:
        return maxres
    return f"https://i.ytimg.com/vi/{match[1]}/hqdefault.jpg"


def thumbnail(json_from_api: dict) -> str | None:
    # Some videos have custom thumbnails
    # Example: https://www.iwara.tv/video/J7W7n4VdKtohQ7/
    if custom := dig(json_from_api, "customThumbnail", "id"):
        return f"https://i.iwara.tv/image/original/{custom}/{custom}.jpg"
    # Normal thumbnails must have their index padded to two digits: 1 -> thumbnail-01.jpg
    # Example: https://www.iwara.tv/video/2DORyCe5fVqXz6/
    if (file_id := dig(json_from_api, "file", "id")) and (
        idx := json_from_api.get("thumbnail")
    ) is not None:
        return f"https://i.iwara.tv/image/original/{file_id}/thumbnail-{idx:02}.jpg"
    # Embedded YouTube videos have no file of their own
    # Example: https://www.iwara.tv/video/LcJWjXgoz8aY6D
    if embed_url := json_from_api.get("embedUrl"):
        return youtube_thumbnail(embed_url)
    return None


def to_scraped_scene(json_from_api: dict) -> ScrapedScene:
    scene: ScrapedScene = {
        "title": json_from_api["title"],
        "urls": [f"https://www.iwara.tv/video/{json_from_api['id']}"],
        "date": json_from_api["createdAt"][:10],
        "studio": {
            "name": dig(json_from_api, "user", "name"),
            "urls": [
                f"https://www.iwara.tv/profile/{dig(json_from_api, 'user', 'username')}"
            ],
        },
    }
    if image := thumbnail(json_from_api):
        scene["image"] = image
    if details := json_from_api.get("body"):
        scene["details"] = details
    if duration := dig(json_from_api, "file", "duration"):
        scene["duration"] = duration
    if tags := json_from_api.get("tags"):
        scene["tags"] = [{"name": tag["id"]} for tag in tags]
    return scene


def get_video_details(video_id: str) -> ScrapedScene:
    scene = api_request(f"https://api.iwara.tv/video/{video_id}")
    return to_scraped_scene(scene)


def scene_by_url(url: str) -> ScrapedScene | None:
    if not (match := re.search(r"/video/([^/?#]+)", url)):
        log.error(f"Invalid video URL: {url}")
        return None
    return get_video_details(match.group(1))


def scene_by_fragment(args: dict) -> ScrapedScene | None:
    urls = [args.get("url"), *(args.get("urls") or [])]
    if url := next((u for u in urls if u and "iwara.tv/video/" in u), None):
        return scene_by_url(url)

    # Filename must contain video ID in brackets
    # Example: Robin - Queencard [2DORyCe5fVqXz6].mp4
    names = [f["path"] for f in args.get("files") or []] + [args.get("title") or ""]
    if match := next(
        (m for name in names if (m := re.search(r"\[([0-9a-zA-Z]{13,})\]", name))),
        None,
    ):
        return get_video_details(match.group(1))
    log.error(f"Unable to extract video ID from {names}")
    return None


def scene_search(query: str) -> list[ScrapedScene]:
    search_results = api_request(
        "https://api.iwara.tv/search",
        params={"type": "videos", "page": 0, "query": query},
    )["results"]
    return [to_scraped_scene(r) for r in search_results]


if __name__ == "__main__":
    op, args = scraper_args()

    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_by_url(url)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_by_fragment(args)
        case "scene-by-name", {"name": query} if query:
            result = scene_search(query)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
