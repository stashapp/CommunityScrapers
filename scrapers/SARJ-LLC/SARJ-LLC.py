import json
import re
import sys
from typing import Any
from urllib.parse import urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    ScrapedGallery,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedStudio,
    ScrapedTag,
)
from py_common.util import dig, is_own_url, is_valid_url, scraper_args

ensure_requirements("requests")

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0"
}

STUDIOS: dict[str, tuple[str, str]] = {
    "2163551D11D0439686AD9D291C8DFD71": ("ALS Scan", "alsscan.com"),
    "D0E7E33329311E3BB6E0800200C93255": ("Domai", "domai.com"),
    "FDA021004E3411DF98790800200C9A66": ("Erotic Beauty", "eroticbeauty.com"),
    "15A9FFA04E3511DF98790800200C9A66": ("Errotica Archives", "errotica-archives.com"),
    "706DF46B88884F7BB226097952427754": ("Eternal Desire", "eternaldesire.com"),
    "5592E33324211E3FF640800200C93111": ("Goddess Nudes", "goddessnudes.com"),
    "5A68E1D7B6E69E7401226779D559A10A": ("Love Hairy", "lovehairy.com"),
    "E6B595104E3411DF98790800200C9A66": ("MetArt", "metart.com"),
    "5C38C84F55841824817C19987F5447B0": ("MetArt Intimate", "metart.com"),
    "E7DFB70DF31C45B3B5E0BF10D733D349": ("MetArt X", "metartx.com"),
    "D99236C04DD011E1B86C0800200C9A66": ("Rylsky Art", "rylskyart.com"),
    "94DB3D0036FC11E1B86C0800200C9A66": ("SexArt", "sexart.com"),
    "3D345D1E156910B44DB5A80CDD746318": ("Straplez", "straplez.com"),
    "18A2E47EAEFD45F29033A5FCAF1F5B91": ("Stunning 18", "stunning18.com"),
    "FDAFDF209DC311E0AA820800200C9A66": ("The Life Erotic", "thelifeerotic.com"),
    "4F23028982B542FA9C6DAAA747E9B5B3": ("Viv Thomas", "vivthomas.com"),
}

NETWORK: ScrapedStudio = {"name": "MetArt Network"}

# These sites never list directors in the crew, so a "Still Photographer" there isn't one
DIRECTORS_NOT_IN_CREW = ("SexArt", "ALS Scan")

# Rylsky Art's releases aren't served by the network API
FRAGMENT_BASE_URLS = ("https://metartnetwork.com", "https://www.rylskyart.com")


def fetch(base_url: str, endpoint: str, **params: Any) -> Any:
    url = f"{base_url}/api/{endpoint}"
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=(3, 6))
    except requests.RequestException as e:
        log.error(f"Error fetching {url}: {e}")
        return None
    if response.status_code >= 400:
        log.info(f"Fetching {response.url} resulted in status {response.status_code}")
        return None
    return response.json()


def site_of(data: dict[str, Any]) -> tuple[str, str] | None:
    return STUDIOS.get(data.get("siteUUID") or dig(data, "media", "siteUUID") or "")


def directors(data: dict[str, Any], studio_name: str) -> str:
    "Directors are listed as photographers, and on most sites as crew too"
    names = [p["name"].strip() for p in data.get("photographers") or []]
    if studio_name not in DIRECTORS_NOT_IN_CREW:
        names += [
            name.strip()
            for crew in data.get("crew") or []
            if crew.get("role") == "Still Photographer"
            for name in crew.get("names") or []
        ]
    return ", ".join(dict.fromkeys(names))


def model_name_from_slug(slug: str) -> str:
    "angela-white -> Angela White, as the model endpoint looks models up by name"
    return " ".join(w.lower().capitalize() for w in re.split(r"[_-]+", slug) if w)


def to_scraped_performer(base_url: str, model: dict[str, Any]) -> ScrapedPerformer:
    performer: ScrapedPerformer = {"name": (model.get("name") or "").strip()}
    if gender := model.get("gender"):
        performer["gender"] = gender.upper()
    if path := model.get("path"):
        performer["urls"] = [f"{base_url}{path}"]
    if ethnicity := model.get("ethnicity"):
        performer["ethnicity"] = ethnicity
    # Unknown is not parsable by Stash
    if (country := dig(model, "country", "name")) and country != "Unknown":
        performer["country"] = country
    # The API uses 0 for unknown measurements
    if height := model.get("height"):
        performer["height"] = str(height)
    if weight := model.get("weight"):
        performer["weight"] = str(weight)
    if (size := model.get("size")) and size != "0":
        performer["measurements"] = size
    if biography := model.get("biography"):
        performer["details"] = biography
    if hair := model.get("hair"):
        performer["hair_color"] = hair.capitalize()
    if eyes := model.get("eyes"):
        performer["eye_color"] = eyes.capitalize()
    if headshot := model.get("headshotImagePath"):
        performer["images"] = [
            f"https://cdn.metartnetwork.com/{model.get('siteUUID')}{headshot}"
        ]
    tags: list[ScrapedTag] = [{"name": t.strip()} for t in model.get("tags") or []]
    attribute_tags: list[ScrapedTag] = [
        {"name": template.format(value).strip()}
        for key, template in (
            ("hair", "{} hair"),
            ("pubicHair", "{} pussy"),
            ("eyes", "{} eyes"),
            ("breasts", "{} breasts"),
        )
        if (value := model.get(key))
    ]
    if tags := tags + attribute_tags:
        performer["tags"] = tags
    return performer


def to_scraped_scene(base_url: str, data: dict[str, Any]) -> ScrapedScene:
    site = site_of(data)
    scene: ScrapedScene = {
        "title": data["name"].strip(),
        "code": data["UUID"],
        "date": data["publishedAt"].split("T")[0],
    }
    if site:
        scene["studio"] = {"name": site[0], "parent": NETWORK}
        scene["urls"] = [f"https://www.{site[1]}{data['path']}"]
    if details := data.get("description") or data.get("descriptionSfw"):
        scene["details"] = details
    if director := directors(data, site[0] if site else ""):
        scene["director"] = director
    if runtime := data.get("runtime"):
        scene["duration"] = runtime
    if tags := data.get("tags"):
        scene["tags"] = [{"name": t.strip()} for t in tags]
    if performers := [to_scraped_performer(base_url, m) for m in data["models"]]:
        scene["performers"] = performers
    site_uuid = dig(data, "media", "siteUUID") or data.get("siteUUID")
    if image := next(
        (
            url
            for key in ("splashImagePath", "coverCleanImagePath", "coverImagePath")
            if (path := data.get(key))
            and is_valid_url(url := f"https://cdn.metartnetwork.com/{site_uuid}{path}")
        ),
        None,
    ):
        scene["image"] = image
    return scene


def to_scraped_gallery(base_url: str, data: dict[str, Any]) -> ScrapedGallery:
    site = site_of(data)
    gallery: ScrapedGallery = {
        "title": data["name"].strip(),
        "code": data["UUID"],
        "date": data["publishedAt"].split("T")[0],
    }
    if site:
        gallery["studio"] = {"name": site[0], "parent": NETWORK}
        gallery["urls"] = [f"https://www.{site[1]}{data['path']}"]
    if details := data.get("description") or data.get("descriptionSfw"):
        gallery["details"] = details
    if photographer := directors(data, site[0] if site else ""):
        gallery["photographer"] = photographer
    if tags := data.get("tags"):
        gallery["tags"] = [{"name": t.strip()} for t in tags]
    if performers := [to_scraped_performer(base_url, m) for m in data["models"]]:
        gallery["performers"] = performers
    return gallery


def split_url(url: str) -> tuple[str, list[str]]:
    "https://www.metart.com/model/x/movie/20250601/NAME -> base URL and path parts"
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}", parsed.path.strip("/").split("/")


def scene_from_release(base_url: str, date: str, name: str) -> ScrapedScene | None:
    log.info(f"Scraping movie '{name}' released on {date}")
    if not (data := fetch(base_url, "movie", name=name, date=date)):
        return None
    return to_scraped_scene(base_url, data)


def gallery_from_release(base_url: str, date: str, name: str) -> ScrapedGallery | None:
    log.info(f"Scraping gallery '{name}' released on {date}")
    # Movie URLs have a gallery of their own
    if not (
        data := fetch(base_url, "gallery", name=name, date=date)
        or fetch(base_url, "movie", name=name, date=date)
    ):
        log.error(f"Gallery '{name}' not found")
        return None
    return to_scraped_gallery(base_url, data)


def scene_from_url(url: str) -> ScrapedScene | None:
    base_url, (*_, date, name) = split_url(url)
    return scene_from_release(base_url, date, name)


def gallery_from_url(url: str) -> ScrapedGallery | None:
    base_url, (*_, date, name) = split_url(url)
    return gallery_from_release(base_url, date, name)


def performer_from_url(url: str) -> ScrapedPerformer | None:
    base_url, (*_, slug) = split_url(url)
    name = model_name_from_slug(slug)
    log.info(f"Scraping model '{slug}' as '{name}'")
    if not (
        data := fetch(base_url, "model", name=name, order="DATE", direction="DESC")
    ):
        return None
    return to_scraped_performer(base_url, data)


def release_key(fragment: dict[str, Any]) -> tuple[str, str] | None:
    "The API looks releases up by date and their uppercased, underscored title"
    if not (title := fragment.get("title")) or not (date := fragment.get("date")):
        log.error("Title and date are required when scraping without a URL")
        return None
    return date.replace("-", ""), re.sub(r"\W", "_", title).upper()


def scene_from_fragment(fragment: dict[str, Any]) -> ScrapedScene | None:
    for url in fragment.get("urls") or []:
        if is_own_url(url) and (scene := scene_from_url(url)):
            return scene
    if not (key := release_key(fragment)):
        return None
    return next(
        (s for b in FRAGMENT_BASE_URLS if (s := scene_from_release(b, *key))), None
    )


def gallery_from_fragment(fragment: dict[str, Any]) -> ScrapedGallery | None:
    for url in fragment.get("urls") or []:
        if is_own_url(url) and (gallery := gallery_from_url(url)):
            return gallery
    if not (key := release_key(fragment)):
        return None
    return next(
        (g for b in FRAGMENT_BASE_URLS if (g := gallery_from_release(b, *key))), None
    )


def performer_from_fragment(fragment: dict[str, Any]) -> ScrapedPerformer | None:
    for url in fragment.get("urls") or []:
        if is_own_url(url) and (performer := performer_from_url(url)):
            return performer
    return None


def search(query: str, item_type: str) -> list[dict[str, Any]]:
    "Every result of one type, across all pages"
    items: dict[str, dict[str, Any]] = {}
    page, page_size = 1, 30
    log.info(f"Searching for {item_type} '{query}'")
    while response := fetch(
        "https://metartnetwork.com",
        "search-results",
        searchPhrase=query,
        pageSize=page_size,
        sortBy="relevance",
        page=page,
    ):
        for result in response["items"]:
            if result["type"] == item_type:
                # The same release can appear more than once
                items.setdefault(result["item"]["path"], result["item"])
        if page * page_size > response["total"] or not response["items"]:
            break
        page += 1
    return list(items.values())


def scene_search(query: str) -> list[ScrapedScene]:
    scenes: list[ScrapedScene] = []
    for item in search(query, "MOVIE"):
        scene: ScrapedScene = {
            "title": item["name"],
            "urls": [f"https://www.metartnetwork.com{item['path']}"],
            "date": item["publishedAt"].split("T")[0],
        }
        performers: list[ScrapedPerformer] = [
            {"name": m["name"].strip()} for m in item["models"]
        ]
        if performers:
            scene["performers"] = performers
        if site := site_of(item):
            scene["image"] = f"https://www.{site[1]}{item['thumbnailCoverPath']}"
        scenes.append(scene)
    return scenes


def performer_search(query: str) -> list[ScrapedPerformer]:
    return [
        {
            "name": item["name"].strip(),
            "urls": [f"https://www.metartnetwork.com{item['path']}"],
        }
        for item in search(query, "model")
    ]


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name)
        case "scene-by-fragment" | "scene-by-query-fragment", fragment:
            result = scene_from_fragment(fragment)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url)
        case "gallery-by-fragment", fragment:
            result = gallery_from_fragment(fragment)
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name)
        case "performer-by-fragment", fragment:
            result = performer_from_fragment(fragment)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
