import json
import re
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from py_common import log
from py_common.cache import cache_to_disk
from py_common.deps import ensure_requirements
from py_common.types import ScrapedImage, ScrapedPerformer, ScrapedScene
from py_common.util import scraper_args

ensure_requirements("requests")

import requests

session = requests.Session()


# Temporary tokens expire exactly 24 hours after they're issued
@cache_to_disk(ttl=23 * 60 * 60)
def auth_token() -> str:
    req = session.get("https://api.redgifs.com/v2/auth/temporary")
    req.raise_for_status()
    return req.json()["token"]


session.headers.update({"Authorization": "Bearer " + auth_token()})


def fetch_data(gif_id: str) -> dict[str, Any] | None:
    # The RedGIFs API only works with lowercased IDs, though other IDs are case-insensitive
    api_url = f"https://api.redgifs.com/v2/gifs/{gif_id.lower()}?users=yes"

    req = session.get(api_url)
    if req.status_code != 200:
        log.error(f"Failed to fetch {api_url}: {req.status_code} {req.reason}")
        return None

    return req.json()


def to_date(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=UTC).date().isoformat()


def to_performers(user: dict[str, Any]) -> list[ScrapedPerformer]:
    performers: list[ScrapedPerformer] = []
    if name := user.get("name"):
        performer: ScrapedPerformer = {"name": name}
        if urls := [
            url for key, url in user.items() if key.startswith("socialUrl") and url
        ]:
            performer["urls"] = urls
        performers.append(performer)
    if (username := user.get("username")) and username != name:
        performers.append({"name": username})
    return performers


def to_scraped_scene(data: dict[str, Any]) -> ScrapedScene:
    gif = data["gif"]
    user = data["user"]

    scene: ScrapedScene = {
        "date": to_date(gif["createDate"]),
        "urls": [f"https://www.redgifs.com/watch/{gif['id']}"],
    }
    if details := gif.get("description"):
        scene["details"] = details
    if tags := gif.get("tags"):
        scene["tags"] = [{"name": t} for t in tags]
    if duration := gif.get("duration"):
        scene["duration"] = round(duration)
    if poster := gif["urls"].get("poster"):
        scene["image"] = poster
    if name := user.get("name"):
        scene["studio"] = {"name": name, "urls": [user["url"]]}
    if performers := to_performers(user):
        scene["performers"] = performers

    return scene


def to_scraped_image(data: dict[str, Any]) -> ScrapedImage:
    gif = data["gif"]
    user = data["user"]

    image: ScrapedImage = {
        "date": to_date(gif["createDate"]),
        "urls": [f"https://www.redgifs.com/watch/{gif['id']}"],
    }
    if details := gif.get("description"):
        image["details"] = details
    if tags := gif.get("tags"):
        image["tags"] = [{"name": t} for t in tags]
    if name := user.get("name"):
        image["studio"] = {"name": name, "urls": [user["url"]]}
    if performers := to_performers(user):
        image["performers"] = performers

    return image


def extract_id(string: str) -> str | None:
    # Redgifs URLs are in the format https://www.redgifs.com/watch/identifier
    if match := re.search(r"redgifs.com/watch/(\w+)", string):
        return match.group(1)

    # Filenames are either 'Redgifs_identifier' or 'Title of Clip [identifier]'
    filename = Path(string).stem
    if (match := re.search(r"Redgifs_(\w+)", filename)) or (
        match := re.search(r"\[(\w+)\]", filename)
    ):
        return match.group(1)

    return None


def fragment_ids(fragment: dict[str, Any]) -> Iterator[str]:
    "Candidate IDs from a fragment, most reliable first"
    # Other sites' URLs (IAFD, StashDB, ...) can share the list
    for url in fragment.get("urls") or []:
        if identifier := extract_id(url):
            yield identifier
    paths = [f["path"] for f in fragment.get("files") or [] if f.get("path")]
    if title := fragment.get("title"):
        paths.append(title)
    for path in paths:
        if identifier := extract_id(path):
            yield identifier
    # Media downloaded as-is is named after the ID, e.g. 'ColorfulCapitalGermanspaniel-silent.mp4'
    for path in paths:
        if re.fullmatch(r"[A-Za-z]+", stem := Path(path).stem.split("-")[0]):
            yield stem


def data_from_fragment(fragment: dict[str, Any]) -> dict[str, Any] | None:
    for identifier in dict.fromkeys(i.lower() for i in fragment_ids(fragment)):
        if data := fetch_data(identifier):
            return data
    log.error("Could not find a Redgifs ID in the fragment's URLs, files or title")
    return None


def scene_by_url(url: str) -> ScrapedScene | None:
    if not (identifier := extract_id(url)):
        log.error(f"Could not extract ID from URL: {url}")
        return None
    if not (data := fetch_data(identifier)):
        return None
    return to_scraped_scene(data)


def scene_by_name(name: str) -> list[ScrapedScene]:
    "Searching only works by ID or URL"
    identifier = extract_id(name) or name.strip()
    if not (data := fetch_data(identifier)):
        return []
    return [to_scraped_scene(data)]


def scene_by_fragment(fragment: dict[str, Any]) -> ScrapedScene | None:
    if not (data := data_from_fragment(fragment)):
        return None
    return to_scraped_scene(data)


def image_by_url(url: str) -> ScrapedImage | None:
    if not (identifier := extract_id(url)):
        log.error(f"Could not extract ID from URL: {url}")
        return None
    if not (data := fetch_data(identifier)):
        log.error(f"Could not fetch data for '{identifier}', removed from site?")
        return None
    return to_scraped_image(data)


def image_by_fragment(fragment: dict[str, Any]) -> ScrapedImage | None:
    if not (data := data_from_fragment(fragment)):
        return None
    return to_scraped_image(data)


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_by_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_by_name(name)
        case "scene-by-fragment" | "scene-by-query-fragment", fragment:
            result = scene_by_fragment(fragment)
        case "image-by-url", {"url": url} if url:
            result = image_by_url(url)
        case "image-by-fragment", fragment:
            result = image_by_fragment(fragment)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
