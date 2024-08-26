from base64 import b64encode
from datetime import datetime
from pathlib import Path
import json
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


def scrape_id(gif_id: str):
    api_url = f"https://api.redgifs.com/v2/gifs/{gif_id}?users=yes"

    req = session.get(api_url)
    if req.status_code != 200:
        log.error(f"Failed to fetch {api_url}: {req.status_code} {req.reason}")
        return

    data = req.json()
    gif = data["gif"]
    user = data["user"]

    scene = {
        "title": gif.get("description"),
        "tags": [{"name": t} for t in gif.get("tags")],
        "date": datetime.fromtimestamp(gif["createDate"]).date().strftime("%Y-%m-%d"),
        "performers": [],
    }

    # We cannot return the image URL because you need the token to access it
    # and Stash does not have our token: base64 encoding the image instead
    if img := dig(gif, "urls", ("poster", "hd", "sd")):
        image_data = session.get(img).content
        base64_encoded = b64encode(image_data).decode("utf-8")
        scene["image"] = f"data:image/jpeg;base64,{base64_encoded}"

    if name := user.get("name"):
        scene["studio"] = {"name": name, "url": user["url"]}
        scene["performers"] = [{"name": name}]

    if (username := user.get("username")) and username != name:
        scene["performers"].append({"name": username})

    return scene


def extract_id(string: str):
    # Redgifs URLs are in the format https://www.redgifs.com/watch/unique-name
    if "redgifs.com/watch" in string:
        return string.split("/")[-1].split("#")[0].split("?")[0]

    # Filenames are assumed to have the format "Redgifs_{id}.mp4"
    return Path(string).stem.split("_")[-1]


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url" | "scene-by-query-fragment", {"url": identifier}:
            gif_id = extract_id(identifier)
        case "scene-by-name", {"name": identifier}:
            gif_id = extract_id(identifier)
        case "scene-by-fragment", {"title": title, "url": url}:
            identifier = title or url
            gif_id = extract_id(identifier)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    if gif_id:
        log.debug(f"Fetching scene with ID '{gif_id}'")
        result = scrape_id(gif_id)
    else:
        log.error(f"Unable to find valid GIF identifier in '{identifier}'")
        result = None

    print(json.dumps(result))
