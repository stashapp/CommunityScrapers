from base64 import b64encode
from datetime import datetime
from pathlib import Path
import json
import re
import sys
import requests

import py_common.log as log
from py_common.cache import cache_to_disk
from py_common.types import ScrapedImage, ScrapedScene
from py_common.util import dig, scraper_args

PROXIES = {}
TIMEOUT = 10

session = requests.Session()
session.proxies.update(PROXIES)


@cache_to_disk(ttl=24 * 60 * 60)
def auth_token():
    req = session.get("https://api.redgifs.com/v2/auth/temporary")
    req.raise_for_status()
    return req.json()["token"]


session.headers.update({"Authorization": "Bearer " + auth_token()})


def fetch_data(gif_id: str) -> dict | None:
    # The RedGIFs API only works with lowercased IDs, though other IDs are case-insensitive
    api_url = f"https://api.redgifs.com/v2/gifs/{gif_id.lower()}?users=yes"

    req = session.get(api_url)
    if req.status_code != 200:
        log.error(f"Failed to fetch {api_url}: {req.status_code} {req.reason}")
        return None

    return req.json()


def to_scraped_scene(data: dict) -> ScrapedScene | None:
    gif = data["gif"]
    user = data["user"]

    scene: ScrapedScene = {
        "tags": [{"name": t} for t in gif.get("tags")],
        "date": datetime.fromtimestamp(gif["createDate"]).date().isoformat(),
        "url": f"https://www.redgifs.com/watch/{gif['id']}",
        "performers": [],
    }

    if title := gif.get("title"):
        scene["title"] = title
    # We cannot return the image URL because you need the token to access it
    # and Stash does not have our token: base64 encoding the image instead
    if img := dig(gif, "urls", ("poster", "hd", "sd")):
        image_data = session.get(img).content
        base64_encoded = b64encode(image_data).decode("utf-8")
        scene["image"] = f"data:image/jpeg;base64,{base64_encoded}"

    if name := user.get("name"):
        scene["studio"] = {"name": name, "url": user["url"]}
        urls = [
            url for url in [dig(user, f"socialUrl{i}") for i in range(1, 16)] if url
        ]
        scene["performers"] = [{"name": name, "urls": urls}]

    if (username := user.get("username")) and username != name:
        scene["performers"].append({"name": username})

    return scene


def to_scraped_image(data: dict) -> ScrapedImage | None:
    gif = data["gif"]
    user = data["user"]

    image: ScrapedImage = {
        "tags": [{"name": t} for t in gif.get("tags")],
        "date": datetime.fromtimestamp(gif["createDate"]).date().isoformat(),
        "urls": [f"https://www.redgifs.com/watch/{gif['id']}"],
        "performers": [],
    }

    if title := gif.get("title"):
        image["title"] = title

    if name := user.get("name"):
        image["studio"] = {"name": name, "url": user["url"]}
        urls = [
            url for url in [dig(user, f"socialUrl{i}") for i in range(1, 16)] if url
        ]
        image["performers"] = [{"name": name, "urls": urls}]

    if (username := user.get("username")) and username != name:
        image["performers"].append({"name": username})

    return image


def extract_id(string: str):
    # Redgifs URLs are in the format https://www.redgifs.com/watch/identifier
    if match := re.search(r"redgifs.com/watch/(\w+)", string):
        return match.group(1)

    # Filenames are either 'Redgifs_identifier' or 'Title of Clip [identifier]'
    filename = Path(string).stem
    if match := re.search(r"Redgifs_(\w+)", filename):
        return match.group(1)
    elif match := re.search(r"\[(\w+)\]", filename):
        return match.group(1)

    return None


def scene_by_url(url: str) -> ScrapedScene | None:
    if not (identifier := extract_id(url)):
        log.error(f"Could not extract ID from URL: {url}")
        return

    if not (data := fetch_data(identifier)):
        return

    return to_scraped_scene(data)


def scene_by_fragment(fragment: dict) -> ScrapedScene | None:
    if (
        (url := dig(fragment, "url"))
        and (identifier := extract_id(url))
        and (data := fetch_data(identifier))
    ):
        return to_scraped_scene(data)
    if not (filename := dig(fragment, "files", 0, "path")):
        log.error(
            "Could not extract ID from fragment: need to have a file or a Redgifs URL"
        )
        return None
    if (identifier := extract_id(filename)) and (data := fetch_data(identifier)):
        return to_scraped_scene(data)
    if data := fetch_data(Path(filename).stem):
        return to_scraped_scene(data)
    log.debug("Unable to scrape this fragment from Redgifs")


def image_by_url(url: str) -> ScrapedImage | None:
    if not (identifier := extract_id(url)):
        log.error(f"Could not extract ID from URL: {url}")
        return
    if not (data := fetch_data(identifier)):
        log.error(f"Could not fetch data for '{identifier}', removed from site?")
        return
    return to_scraped_image(data)


def image_by_fragment(fragment: dict) -> ScrapedImage | None:
    if (
        (url := dig(fragment, "url"))
        and (identifier := extract_id(url))
        and (data := fetch_data(identifier))
    ):
        return to_scraped_image(data)
    if (identifier := extract_id(fragment["title"])) and (
        data := fetch_data(identifier)
    ):
        return to_scraped_image(data)

    if data := fetch_data(Path(fragment["title"]).stem):
        return to_scraped_image(data)
    log.debug("Unable to scrape this fragment from Redgifs")


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url" | "scene-by-query-fragment", {"url": url}:
            result = scene_by_url(url)
        case "scene-by-name", {"name": identifier}:
            result = [s for s in [to_scraped_scene(identifier.strip())] if s]
        case "scene-by-fragment", fragment:
            result = scene_by_fragment(fragment)
        case "image-by-url", {"url": url}:
            result = image_by_url(url)
        case "image-by-fragment", fragment:
            result = image_by_fragment(fragment)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
