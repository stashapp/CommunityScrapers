import json
import re
import requests
import sys
import time

from pathlib import Path
from py_common import log
from py_common.types import ScrapedScene, ScrapedPerformer
from py_common.util import scraper_args, dig
from py_common.config import get_config
from py_common.cache import cache_to_disk
from py_common.ratelimit import get_limiter_session

HOSTNAME = "fc2cmadb.com"
BASE_URL = f"https://{HOSTNAME}"

config = get_config(
    default="""
fc2cmadb_session =
scrape_scene_image = True
unique_performer_name = False
disambiguation_prefix = fc2cmadb-
"""
)

def get_valid_image_url(url: str) -> str:
    return url if (url and url.startswith(('http://', 'https://')) and not url.endswith("no-image.jpg")) else ""

def get_fresh_inertia_version() -> str:
    # hacky - we can't force refresh get_inertia_version() or
    # have access to the filename, so just hope this is the file
    cache_file = Path(__file__).parent / "cache.json"
    if cache_file.exists():
        cache_file.unlink()
    return get_inertia_version()

@cache_to_disk(ttl=86400)
def get_inertia_version() -> str:
    session = requests.Session()
    response = session.get(BASE_URL)
    # get inertia version from the app script
    pattern = r'<script[^>]*data-page="app"[^>]*>(.*?)</script>'
    match = re.search(pattern, response.text, re.DOTALL)
    if not match:
        log.error("Can't extract app data.")
        print("{}")
        sys.exit(1)
    json_content = match.group(1)
    return json.loads(json_content).get("version")

def get_payload(session, url: str, headers=None):
    log.debug(f"Fetching {url}")
    # fill inertia headers to get json instead of html
    session.headers.update({
        "X-Inertia": "true",
        "X-Inertia-Version": get_inertia_version(),
        "X-Requested-With": "XMLHttpRequest",
        "Referer": url,
        "Cache-Control": "no-cache"
    } | headers or {})
    resp = session.get(url)
    if resp.status_code == 409:
        session.headers.update({ "X-Inertia-Version": get_fresh_inertia_version() })
        resp = session.get(url)
        log.debug("Refreshed inertia version")

    try:
        resp_json = resp.json()
        user = resp_json.get("props", {}).get("auth", {}).get("user")
        if user is None or user.get("id") is None:
            log.error("Not logged in, please provide fresh fc2cmadb_session cookie")
            sys.exit(1)
        else:
            log.debug(f"Logged in with ID: {user.get('id')}")
    except json.JSONDecodeError:
        log.error("Invalid JSON response.")
        log.debug(resp.text)
        print("{}")
        sys.exit(1)

    if resp_json.get("component", "") == "Error":
        log.error("API returned error with status: " + str(resp_json.get("props").get("status")))
        log.debug(resp.text)
        print("{}")
        sys.exit(1)
    return resp_json

def scene_from_url(session, url: str) -> ScrapedScene:
    resp_json = get_payload(session, url, {
        "X-Inertia-Partial-Component": "Articles/Show",
        "X-Inertia-Partial-Data": "article,actresses,auth"
    })
    article = resp_json.get("props").get('article')
    # actresses may be returned as list or dict
    actresses_data = resp_json.get("props", {}).get('actresses', [])
    if isinstance(actresses_data, dict):
        actresses = list(actresses_data.values())
    else:
        actresses = actresses_data

    if not article:
        log.error(f"Can't get article data from {url}")
        log.debug(resp_json)
        print("{}")
        sys.exit(1)

    scene: ScrapedScene = {}
    scene["title"] = article.get("title", "").strip()
    scene["code"] = "FC2-PPV-" + str(article.get("video_id", ""))
    scene["date"] = article.get("release_date", "")
    scene["studio"] = { "name": dig(article, "writer", "name") }
    scene["tags"] = [{ "name": tag.get("name", "").strip() } for tag in article.get("tags", [])]
    scene["urls"] = [url]
    if config['scrape_scene_image']:
        scene["image"] = get_valid_image_url(article.get("image_url", ""))

    scene["performers"] = []
    for actress in actresses:
        scene["performers"].append(get_performer_from_actress(actress))

    return scene

def get_performer_from_actress(actress) -> ScrapedPerformer:
    performer_name = actress.get("name", "").strip()
    if config['unique_performer_name']:
        performer_name = f"{performer_name}_{actress['id']}"

    if config['disambiguation_prefix']:
        disambiguation = f"{config['disambiguation_prefix']}{actress['id']}"
    else:
        disambiguation = ""

    performer: ScrapedPerformer = {
        "name": performer_name,
        "disambiguation": disambiguation,
        "urls": [ f"{BASE_URL}/actresses/" + str(actress.get("id")) ],
        "gender": "female",
        "image": get_valid_image_url(actress.get("image_url", ""))
    }
    return performer

def performer_from_url(session, url: str) -> ScrapedPerformer:
    resp_json = get_payload(session, url, {
        "X-Inertia-Partial-Component": "Actresses/Show",
        "X-Inertia-Partial-Data": "actress,auth"
    })

    actress = resp_json.get("props").get('actress')

    if not actress:
        log.error(f"Can't get actress data from {url}")
        log.debug(resp_json)
        print("{}")
        sys.exit(1)

    return get_performer_from_actress(actress)

def url_from_frag(files) -> str:
    filename = Path(files[0].get("path", ""))
    code = re.search(r"(\d{5,})", filename.name)
    match = code.group(1) if code else None
    if match:
        return f"{BASE_URL}/articles/{match}"
    log.debug(f"No 5+ digit ID found in filename {filename}")
    return None

if __name__ == "__main__":
    op, args = scraper_args()

    # if no config, throw error
    if not config["fc2cmadb_session"]:
        log.error("Missing required cookie in config. Please update config and try again.")
        log.debug(f"fc2cmadb_session cookie: {config['fc2cmadb_session']}")
        print("{}")
        sys.exit(1)

    session = get_limiter_session(per_second = 1, per_minute = 30, per_hour = 250)
    session.cookies.set( "ageVerified", "true", domain=HOSTNAME, path="/" )
    session.cookies.set( "fc2cmadb-session", config["fc2cmadb_session"], domain=f".{HOSTNAME}", path="/" )

    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(session, url)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            files = args.get("files", [])
            url = url_from_frag(files)
            if url:
                result = scene_from_url(session, url)
            else:
                log.error("Could not extract article ID from filename")
                print("{}")
                sys.exit(1)
        case "performer-by-url", {"url": url} if url:
             result = performer_from_url(session, url)

        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            print("{}")
            sys.exit(1)

    print(json.dumps(result))
