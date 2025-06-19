import re
import json
import requests
import sys
from datetime import datetime
import py_common.log as log
from py_common.cache import cache_to_disk
from py_common.util import dig, scraper_args
from py_common.config import get_config

config = get_config(
    default="""
username = 
password = ""
"""
)

has_login = config.username and config.password


@cache_to_disk(ttl=60 * 60 * 24)
def auth_token():
    login_url = "https://api.iwara.tv/user/login"
    payload = {"email": config.username, "password": config.password}
    response = requests.post(login_url, json=payload)
    if response.status_code != 200:
        log.error(
            "Failed to log in to Iwara, check password/username in Iwara/config.ini"
        )
        sys.exit(1)
    return response.json().get("token")


def api_request(query):
    headers = {}
    if has_login:
        token = auth_token()
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(query, headers=headers)
    if response.status_code == 404 and not has_login:
        log.error(
            "Login required: please fill in your username and password in Iwara/config.ini"
        )
        sys.exit(1)
    elif not response.ok:
        log.error(f"Failed to fetch video data: {response.reason}")
        # Cached login might be invalid, nuke it before next attempt
        auth_token.clear_cache()
        sys.exit(1)

    return response.json()


def to_scraped_scene(json_from_api: dict):
    # Some videos have custom thumbnails
    # Example: https://www.iwara.tv/video/J7W7n4VdKtohQ7/
    if custom := dig(json_from_api, "customThumbnail", "id"):
        image = f"https://i.iwara.tv/image/original/{custom}/{custom}.jpg"
    # Normal thumbnails must have their index padded to two digits: 1 -> thumbnail-01.jpg
    # Example: https://www.iwara.tv/video/2DORyCe5fVqXz6/
    elif (file_id := dig(json_from_api, "file", "id")) and (
        idx := dig(json_from_api, "thumbnail")
    ) is not None:
        image = f"https://i.iwara.tv/image/original/{file_id}/thumbnail-{idx:02}.jpg"
    else:
        image = "https://placehold.co/600x400?text=Scraper+broken"

    return {
        "title": json_from_api["title"],
        "url": f"https://www.iwara.tv/video/{json_from_api["id"]}",
        "image": image,
        "date": datetime.strptime(json_from_api["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ")
        .date()
        .isoformat(),
        "details": json_from_api["body"],
        "studio": {
            "Name": dig(json_from_api, "user", "name"),
            "URL": f"https://www.iwara.tv/profile/{dig(json_from_api, "user", "username")}",
        },
        "tags": [{"name": tag["id"]} for tag in json_from_api.get("tags", [])],
    }


def get_video_details(video_id):
    scene = api_request(f"https://api.iwara.tv/video/{video_id}")
    return to_scraped_scene(scene)


def scene_by_url(url):
    if not (match := re.search(r"/video/([^/]+)/?", url)):
        log.error(f"Invalid video URL: {url}")
        exit(1)
    video_id = match.group(1)
    return get_video_details(video_id)


def scene_by_filename(file):
    # Filename must contain video ID in brackets
    # Example: Robin - Queencard [2DORyCe5fVqXz6].mp4
    if match := re.search(r"\[([0-9a-zA-Z]{13,})\]", file):
        return get_video_details(match.group(1))
    log.error(f"Unable to extract video ID from filename '{file}'")
    return None


def scene_search(query):
    search_results = api_request(
        f"https://api.iwara.tv/search?type=video&page=0&query={query}"
    )["results"]

    return [to_scraped_scene(r) for r in search_results]


if __name__ == "__main__":
    op, args = scraper_args()

    result = None
    match op, args:
        case "scene-by-url", {"url": url}:
            result = scene_by_url(url)
        case "scene-by-fragment", args:
            file = dig(args, "files", 0, "path")
            result = scene_by_filename(file)
        case "scene-by-name", {"name": query}:
            result = scene_search(query)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
