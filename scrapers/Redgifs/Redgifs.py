from base64 import b64encode
from datetime import datetime
from pathlib import Path
import json
import re
import sys
import requests

import py_common.log as log
from py_common.cache import cache_to_disk
from py_common.types import ScrapedScene
from py_common.util import dig, scraper_args

PROXIES = {}
TIMEOUT = 10

session = requests.Session()
session.proxies.update(PROXIES)


@cache_to_disk("token", 24 * 60 * 60)
def get_token():
    req = session.get("https://api.redgifs.com/v2/auth/temporary")
    req.raise_for_status()
    return req.json()["token"]


session.headers.update({"Authorization": "Bearer " + get_token()})


def scene_by_id(gif_id: str) -> ScrapedScene | None:
    api_url = f"https://api.redgifs.com/v2/gifs/{gif_id}?users=yes"

    req = session.get(api_url)
    if req.status_code != 200:
        log.error(f"Failed to fetch {api_url}: {req.status_code} {req.reason}")
        return

    data = req.json()
    gif = data["gif"]
    user = data["user"]

    scene: ScrapedScene = {
        "tags": [{"name": t} for t in gif.get("tags")],
        "date": datetime.fromtimestamp(gif["createDate"]).date().isoformat(),
        "url": f"https://www.redgifs.com/watch/{gif_id}",
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
    if identifier := extract_id(url):
        return scene_by_id(identifier)

    log.error(f"Could not extract ID from URL: {url}")


def scene_by_fragment(fragment: dict) -> ScrapedScene | None:
    if (url := dig(fragment, "url")) and (identifier := extract_id(url)):
        return scene_by_id(identifier)
    elif (filename := dig(fragment, "files", 0, "path")) and (
        identifier := extract_id(filename)
    ):
        return scene_by_id(identifier)
    log.error("Could not extract ID from fragment")
    log.error("Filename must match 'Redgifs_identifier' or 'whatever [identifier]'")


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url" | "scene-by-query-fragment", {"url": url}:
            result = scene_by_url(url)
        case "scene-by-name", {"name": identifier}:
            result = [s for s in [scene_by_id(identifier.strip())] if s]
        case "scene-by-fragment", fragment:
            result = scene_by_fragment(fragment)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
