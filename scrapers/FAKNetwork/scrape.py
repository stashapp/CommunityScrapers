import json
import pathlib
import re
import sys
from html import unescape
from urllib.parse import quote

import requests

from FAKNetwork.sites import to_scraped_studio
from py_common import log
from py_common.cache import cache_to_disk
from py_common.config import get_config
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedTag
from py_common.util import dig, scraper_args

config = get_config(
    default="""
# Flattens the studio / series hierarchy to just output the studio
# for example
# - when True: studio is FaKings
# - when False: studio is MILF Club, parent is FaKings
flatten_hierarchy = False
"""
)


scraper = requests.Session()

tag_map = {}

IMAGE_URL = "https://almacen-faknetworks.b-cdn.net/videos"


def clean_text(text):
    return re.sub(r"<[^>]+>", "", unescape(text))


@cache_to_disk(ttl=60 * 60 * 24)
def tag_mappings(site, lang="en"):
    categories_url = f"https://api.faknetworks.com/v1/categories?product={site}&lang={lang}&page=1&take=1000"
    data = scraper.get(categories_url)
    if data.status_code != 200:
        log.error(f"Unable to get tag mappings from API: {data.status_code}")
        return {}
    data = data.json()["results"]
    return {category["id"]: category["title"] for category in data}


def to_scraped_tag(api_obj: dict) -> ScrapedTag:
    return {"name": tag_map.get(str(api_obj["id"]), api_obj["title"])}


def to_scraped_performer(api_obj: dict) -> ScrapedPerformer:
    performer: ScrapedPerformer = {
        "name": api_obj["name"],
        "images": [
            f"https://almacen.fakings.com/almacen/actrices/{api_obj['profilePhoto']}"
        ],
        "urls": [],
    }
    if site_name := dig(api_obj, "product"):
        performer["urls"].append(
            f"https://{site_name}.com/actrices-porno/{api_obj['slug']}"
        )

    if loverfans := dig(api_obj, "loverfansUrl"):
        performer["urls"].append(loverfans)

    return performer


def cover_image(data: dict) -> str | None:
    """
    The screenshot is the full-size version of the cover the site shows
    (portada_<profile>), but older scenes only have the small cover left
    """
    candidates = [
        f"{IMAGE_URL}/{quote(screenshot)}"
        if (screenshot := dig(data, "screenshot"))
        else None,
        f"{IMAGE_URL}/portada_{quote(profile)}"
        if (profile := dig(data, "profile"))
        else None,
        f"https://player.faknetworks.com/almacen/videos/listado_horizontal_{image}"
        if (image := dig(data, "horizontalProfile"))
        else None,
    ]
    urls = [url for url in candidates if url]
    for url in urls[:-1]:
        try:
            if scraper.head(url, timeout=15).status_code == 200:
                return url
        except requests.RequestException:
            continue
    return urls[-1] if urls else None


def to_scraped_scene(data: dict, lang="en") -> ScrapedScene:
    global tag_map
    site_name = data["product"]
    tag_map = tag_mappings(site=site_name, lang=lang)
    # Search results are partial: they lack the filename, description, tags and performers
    scene: ScrapedScene = {
        "title": data["title"],
        "date": data["date"],
        "tags": [to_scraped_tag(c) for c in data.get("categories", [])],
        "performers": [to_scraped_performer(p) for p in data.get("performers", [])],
        "urls": [
            f"https://{site_name}.com/{lang}/video/{data['slug']}",
        ],
    }
    if code := data.get("filename"):
        scene["code"] = code
    if description := data.get("description"):
        scene["details"] = clean_text(description)

    if image := cover_image(data):
        scene["image"] = image

    studio = to_scraped_studio(data["serie"], site_name, lang)
    if config.flatten_hierarchy:
        studio = studio["parent"]

    scene["studio"] = studio

    return scene


def scene_by_url(url: str) -> ScrapedScene | None:
    url_pattern = r".+?(?:/(?P<lang>\w{2}))?/video/(?P<slug>[-\w]+)"
    if not (match := re.search(url_pattern, url)):
        log.error(f"Unable to parse URL: {url}")
        return None

    # default to english
    lang = match.group("lang") or "en"
    slug = match.group("slug")
    api_url = f"https://api.faknetworks.com/v1/public/videos/{slug}?lang={lang}"

    log.debug(f"Asking API... {api_url}")
    response = scraper.get(api_url)
    if response.status_code == 404 and (new_slug := renamed_slug(url, slug)):
        log.debug(f"Scene slug was renamed to {new_slug}")
        api_url = f"https://api.faknetworks.com/v1/public/videos/{new_slug}?lang={lang}"
        response = scraper.get(api_url)
    if response.status_code != 200:
        log.error(f"Failed to fetch data for {slug}: {response.status_code}")
        return None
    data = response.json()

    return to_scraped_scene(data, lang=lang)


def renamed_slug(url: str, slug: str) -> str | None:
    "The sites redirect old scene slugs to renamed ones, but the API only knows the new one"
    if not url.startswith("http"):
        return None
    try:
        response = scraper.get(url, allow_redirects=False, timeout=30)
    except requests.RequestException:
        return None
    # Either a plain Location header, or a Next.js digest in the body of a 308 without one
    target = response.headers.get("Location") or next(
        iter(re.findall(r"NEXT_REDIRECT;\w+;([^;\\\"]+);30\d", response.text)), ""
    )
    new_slug = target.rstrip("/").rsplit("/", 1)[-1]
    return new_slug if re.fullmatch(r"[-\w]+", new_slug) and new_slug != slug else None


# Placeholder until we can figure out how to map filenames back to scenes
def scene_by_id(id: str) -> ScrapedScene | None: ...


def scene_search(query: str, site, lang="en") -> list[ScrapedScene]:
    api_url = f"https://api.faknetworks.com/v1/search?query={quote(query)}&product={site}&lang={lang}&limit=10"
    log.debug(f"Asking API... {api_url}")
    response = scraper.get(api_url)
    if response.status_code != 200:
        log.error(f"Failed to fetch data for {query}: {response.status_code}")
        return []
    data = response.json()

    return [to_scraped_scene(s) for s in data.get("videos", ())]


def scene_by_fragment(fragment: dict) -> ScrapedScene | None:
    for url in fragment["urls"]:
        if scene := scene_by_url(url):
            log.debug(f"Successfully scraped from URL: {url}")
            return scene
    # TODO: figure out if we can map the filename back to the scene: it's in the API but might not be queryable
    # 7-130-tania -> https://fakings.com/en/video/we-go-into-a-bar-full-of-people-only-the-manager-knows-tania-does-what-she-does-best-and
    if path := dig(fragment, "files", 0, "path"):
        filename = pathlib.Path(path).stem
        if scene := scene_by_id(filename):
            log.debug(f"Successfully scraped from filename: {filename}")
            return None
    # Studio code returned by this scraper is currently the filename, but TPDB use the URL slug so this could work for some
    if (code := dig(fragment, "code")) and (scene := scene_by_url(f"/video/{code}")):
        log.debug(f"Successfully scraped from code: {code}")
        return scene

    log.debug("Unable to scrape this fragment")
    return None


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url" | "scene-by-query-fragment", {"url": url} if url:
            result = scene_by_url(url)
        case "scene-by-name", {"name": query, "extra": sites}:
            site = dig(sites, 0, default="fakings")
            result = scene_search(query, site=site)
        case "scene-by-fragment", fragment:
            result = scene_by_fragment(fragment)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
