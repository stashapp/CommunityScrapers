from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote
import json
import re
import sys
import traceback
from typing import Any

import requests

import py_common.log as log
from py_common.cache import cache_to_disk
from py_common.types import ScrapedGallery, ScrapedPerformer, ScrapedScene, ScrapedStudio
from py_common.util import scraper_args

NATS_URL = "https://nats.mygaycash.com"

# TODO: Same structure as LadyboyGold, we might be able to consolidate
CONFIG = {
    "barebackcumpigs": {
        "cms_area_id": "1fa10fa0-ddb8-418a-8ed1-f621f19f621c",
        "studio_name": "Bareback Cum Pigs",
    },
    "barebackthathole": {
        "cms_area_id": "b1f1d230-6030-4efd-bcfb-f30650c7675c",
        "studio_name": "Bareback That Hole",
    },
    "bearfilms": {
        "cms_area_id": "30e1a84e-91f7-436c-bb1b-d51a8bb521c6",
        "studio_name": "Bear Films",
    },
    "breedmeraw": {
        "cms_area_id": "e87b32a4-3edf-4c4b-97ee-4fefc2a88a34",
        "studio_name": "Breed Me Raw",
    },
    "bringmeaboy": {
        "cms_area_id": "6b3ea9d2-0364-4d1b-99f4-9949cca65a59",
        "studio_name": "Bring Me A Boy",
    },
    "bulldogpit": {
        "cms_area_id": "b3981bf3-f23d-44ee-9b9e-5552618d460e",
        "studio_name": "Bulldog Pit",
    },
    "hairyandraw": {
        "cms_area_id": "34e58e83-da78-43d7-9606-7fbf34ad08fa",
        "studio_name": "Hairy And Raw",
    },
    "hardbritlads": {
        "cms_area_id": "9baa305b-f3f6-4854-b7e6-b9e0cbabaaad",
        "studio_name": "HardBritLads",
    },
    "southernstrokes": {
        "cms_area_id": "c78e6e09-7276-4c13-9c2e-8f5cf51e8bed",
        "studio_name": "Southern Strokes",
    },
    "touchthatboy": {
        "cms_area_id": "e6132199-686e-44b0-a624-a6724c817a35",
        "studio_name": "Touch That Boy",
    },
    "twinksinshorts": {
        "cms_area_id": "e78aca5e-111c-44d8-aba5-64994846f223",
        "studio_name": "Twinks In Shorts",
    },
}

REQUESTS_TIMEOUT = 10


def domain_from_url(url: str) -> str | None:
    url_lower = url.lower()
    return next((d for d in CONFIG if f"{d}.com" in url_lower), None)


def headers_for_domain(domain: str) -> dict[str, str]:
    return {
        "x-nats-cms-area-id": CONFIG[domain]["cms_area_id"],
        "x-nats-entity-decode": "1",
        "x-nats-natscode": "MC4wLjAuMC4wLjAuMC4wLjA",
    }


def last_value(d: dict[str, Any]) -> Any:
    if not d:
        return None
    last_key = list(d.keys())[-1]
    return d[last_key]


def extract_names(cms_set, data_type_name: str) -> list[str]:
    return [
        value["name"]
        for data_type in cms_set.get("data_types", [])
        if data_type["data_type"] == data_type_name
        for value in data_type.get("data_values", [])
    ]


def resolve_studio(domain: str, cms_set: Any) -> ScrapedStudio:
    if names := extract_names(cms_set, "Studio"):
        return {"name": names[0]}
    return {"name": CONFIG[domain]["studio_name"]}


@cache_to_disk(ttl=86400)
def get_block_id(domain: str, page_slug: str) -> str | None:
    """
    Discovers a usable cms_block_id for a domain by fetching one of its own pages:
    any block ID a page returns works for querying that content type, so no manual
    per-domain reverse-engineering is needed (unlike island_dollars.py's CONFIG)
    """
    params = {"cms_area_id": CONFIG[domain]["cms_area_id"], "slug": page_slug}
    headers = headers_for_domain(domain)
    url = f"{NATS_URL}/tour_api.php/content/page"
    res = requests.get(url, params=params, headers=headers, timeout=REQUESTS_TIMEOUT)
    try:
        result = res.json()
    except Exception as e:
        log.error(f"Error parsing JSON response for {domain} page {page_slug}: {e}")
        return None
    if not (blocks := result.get("blocks")):
        log.error(f"No blocks found for {domain} page {page_slug}")
        return None
    return blocks[0]["cms_block_id"]


@cache_to_disk(ttl=600)
def get_cdn_servers(domain: str) -> dict[str, Any]:
    params = {"cms_area_id": CONFIG[domain]["cms_area_id"]}
    headers = headers_for_domain(domain)
    url = f"{NATS_URL}/tour_api.php/content/config"
    res = requests.get(url, params=params, headers=headers, timeout=REQUESTS_TIMEOUT)
    return res.json()["servers"]


def cdn_url_for_server_id(cdn_servers: dict[str, Any], server_id: str) -> str | None:
    server_info = cdn_servers.get(server_id)
    if server_info is None:
        return None
    return server_info["settings"]["url"].rstrip("/")


@cache_to_disk(ttl=600)
def get_sets(
    domain: str,
    content_type: str | None = None,
    cms_set_id: str | None = None,
    slug: str | None = None,
    text_search: str | None = None,
    start: int = 0,
) -> list[Any]:
    if not (block_id := get_block_id(domain, "/videos")):
        return []

    search_params = {
        "data_types": "1",
        "content_count": "1",
        "count": "5",
        "start": f"{start}",
        "cms_block_id": block_id,
        "orderby": "published_desc",
        "status": "enabled",
        "cms_area_id": CONFIG[domain]["cms_area_id"],
    }
    if cms_set_id is not None:
        search_params["cms_set_ids"] = f"[{cms_set_id}]"
    if content_type is not None:
        search_params["content_type"] = content_type
    if slug is not None:
        search_params["slug"] = slug
    if text_search is not None:
        search_params["text_search"] = text_search
    headers = headers_for_domain(domain)
    url = f"{NATS_URL}/tour_api.php/content/sets"
    log.debug(f"Searching domain {domain} with params: {search_params}")
    res = requests.get(url, params=search_params, headers=headers, timeout=REQUESTS_TIMEOUT)
    try:
        result = res.json()
    except Exception as e:
        log.error(f"Error parsing JSON response: {e}")
        return []
    if result is not None and "total_count" in result:
        log.debug(f"Search hits for domain {domain}: {result['total_count']}")
        return result["sets"]
    log.debug(f"No results found for domain {domain}: {res.text}")
    return []


@cache_to_disk(ttl=600)
def get_models(
    domain: str, start: int = 0, name: str | None = None, slug: str | None = None
) -> list[Any]:
    if not (block_id := get_block_id(domain, "/models")):
        return []

    search_params = {
        "cms_data_type_id": "4",
        "start": f"{start}",
        "count": "10",
        "orderby": "published_desc",
        "cms_block_id": block_id,
        "cms_area_id": CONFIG[domain]["cms_area_id"],
        "name": name,
        "slug": slug,
    }
    headers = headers_for_domain(domain)
    url = f"{NATS_URL}/tour_api.php/content/data-values"
    res = requests.get(url, params=search_params, headers=headers, timeout=REQUESTS_TIMEOUT)
    try:
        result = res.json()
    except Exception as e:
        log.error(f"Error parsing JSON response: {e}")
        return []
    if result is not None and "total_count" in result:
        return result["data_values"]
    return []


def parse_set_as_scene(domain: str, cms_set: Any, cdn_servers: dict[str, Any]) -> ScrapedScene:
    scene: ScrapedScene = {}
    if title := cms_set.get("name"):
        scene["title"] = title

    if description := cms_set.get("description"):
        scene["details"] = description.strip()

    if slug := cms_set.get("slug"):
        scene["urls"] = [f"https://tour.{domain}.com/video/{slug}"]

    if added_nice := cms_set.get("added_nice"):
        scene["date"] = added_nice

    if cms_set_image := last_value(cms_set.get("preview_formatted", {}).get("thumb", {})):
        if cdn_url := cdn_url_for_server_id(cdn_servers, cms_set_image[0]["cms_content_server_id"]):
            scene["image"] = f"{cdn_url}{cms_set_image[0]['fileuri']}?{cms_set_image[0]['signature']}"

    scene["studio"] = resolve_studio(domain, cms_set)

    categories = extract_names(cms_set, "Category")
    tags = extract_names(cms_set, "Tags")
    scene["tags"] = [{"name": t} for t in categories + tags]
    scene["performers"] = [{"name": p} for p in extract_names(cms_set, "Models")]
    scene["code"] = cms_set["cms_set_id"]

    return scene


def parse_set_as_gallery(domain: str, cms_set: Any, cdn_servers: dict[str, Any]) -> ScrapedGallery:
    gallery: ScrapedGallery = {}
    if title := cms_set.get("name"):
        gallery["title"] = title

    if description := cms_set.get("description"):
        gallery["details"] = description.strip()

    if slug := cms_set.get("slug"):
        gallery["urls"] = [f"https://tour.{domain}.com/photo/{slug}"]

    if added_nice := cms_set.get("added_nice"):
        gallery["date"] = added_nice

    # ScrapedGallery has no image/cover field, but it's useful to know which
    # one this set's cover would be, so just log it rather than dropping it
    if (
        (cms_set_image := last_value(cms_set.get("preview_formatted", {}).get("thumb", {})))
        and (cdn_url := cdn_url_for_server_id(cdn_servers, cms_set_image[0]["cms_content_server_id"]))
    ):
        cover_image_url = f"{cdn_url}{cms_set_image[0]['fileuri']}?{cms_set_image[0]['signature']}"
        log.debug(f"Cover image URL for gallery '{gallery.get('title')}': {cover_image_url}")

    gallery["studio"] = resolve_studio(domain, cms_set)

    categories = extract_names(cms_set, "Category")
    tags = extract_names(cms_set, "Tags")
    gallery["tags"] = [{"name": t} for t in categories + tags]
    gallery["performers"] = [{"name": p} for p in extract_names(cms_set, "Models")]
    gallery["code"] = cms_set["cms_set_id"]

    return gallery


def parse_model_as_performer(domain: str, cms_data: Any, cdn_servers: dict[str, Any]) -> ScrapedPerformer:
    performer: ScrapedPerformer = {"name": cms_data["name"]}
    performer["urls"] = [f"https://tour.{domain}.com/model/{cms_data['slug']}"]

    data_detail_values = cms_data.get("data_detail_values", {})
    if cms_set_image := last_value(data_detail_values.get("preview", {}).get("11", {})):
        if cdn_url := cdn_url_for_server_id(cdn_servers, cms_set_image[0]["cms_content_server_id"]):
            performer["image"] = f"{cdn_url}{cms_set_image[0]['fileuri']}?{cms_set_image[0]['signature']}"

    return performer


def strip_studio_prefix(domain: str, title: str) -> str:
    # Some legacy update URLs redundantly repeat the studio's own slug as a prefix
    # on the title like southernstrokes.com/updates/southern-strokes-Carson-and-Matthew.html
    # so we strip it text_search isn't polluted by it
    prefix = domain.replace("-", " ")
    if title.lower().startswith(prefix.lower()):
        return title[len(prefix):].strip(" -")
    return title


def video_identifier_from_url(url: str, domain: str) -> tuple[str, str] | None:
    # Oldest legacy scheme: a bare numeric ID in a query param
    # like index.php?VidID=4013
    if match := re.search(r"[?&]VidID=(\d+)", url):
        return ("id", match.group(1))

    if match := re.search(r"/video/([^/?]+)", url):
        value = match.group(1)
        return ("id", value) if value.isdigit() else ("slug", value)

    if match := re.search(r"/(?:tour/)?(?:updates|trailers)/([^/?]+)\.html", url):
        title = unquote(match.group(1)).replace("-", " ").replace("_", " ")
        return ("search", strip_studio_prefix(domain, title))

    return None


def gallery_identifier_from_url(url: str) -> tuple[str, str] | None:
    if match := re.search(r"/photo/([^/?]+)", url):
        value = match.group(1)
        return ("id", value) if value.isdigit() else ("slug", value)
    return None


def best_match(candidates: list, url: str) -> Any | None:
    if not candidates:
        return None
    if url_domain := domain_from_url(url):
        for candidate in candidates:
            if any(domain_from_url(u) == url_domain for u in candidate.get("urls", [])):
                return candidate
    return candidates[0]


def scene_search(
    query: str | None = None,
    slug: str | None = None,
    cms_set_id: str | None = None,
    search_domains: list[str] | None = None,
) -> list[ScrapedScene]:
    if not search_domains:
        log.error("No search_domains provided")
        return []

    parsed_scenes: list[ScrapedScene] = []

    def fetch_domain(domain):
        cdn_servers = get_cdn_servers(domain)
        video_sets = get_sets(
            domain, content_type="video", text_search=query, slug=slug, cms_set_id=cms_set_id
        )
        return [parse_set_as_scene(domain, cms_set, cdn_servers) for cms_set in video_sets]

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_domain, domain): domain for domain in search_domains}
        for future in as_completed(futures):
            try:
                parsed_scenes.extend(future.result())
            except Exception as e:
                log.error(f"Error processing domain {futures[future]}: {e}")
                log.debug(traceback.format_exc())

    return parsed_scenes


def gallery_search(
    query: str | None = None,
    slug: str | None = None,
    cms_set_id: str | None = None,
    search_domains: list[str] | None = None,
) -> list[ScrapedGallery]:
    if not search_domains:
        log.error("No search_domains provided")
        return []

    parsed_galleries: list[ScrapedGallery] = []

    def fetch_domain(domain):
        cdn_servers = get_cdn_servers(domain)
        photo_sets = get_sets(
            domain, content_type="image", text_search=query, slug=slug, cms_set_id=cms_set_id
        )
        return [parse_set_as_gallery(domain, cms_set, cdn_servers) for cms_set in photo_sets]

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_domain, domain): domain for domain in search_domains}
        for future in as_completed(futures):
            try:
                parsed_galleries.extend(future.result())
            except Exception as e:
                log.error(f"Error processing domain {futures[future]}: {e}")
                log.debug(traceback.format_exc())

    return parsed_galleries


def performer_search(
    name: str | None = None,
    slug: str | None = None,
    search_domains: list[str] | None = None,
) -> list[ScrapedPerformer]:
    if not search_domains:
        log.error("No search_domains provided")
        return []

    parsed_performers: list[ScrapedPerformer] = []

    def fetch_domain(domain):
        cdn_servers = get_cdn_servers(domain)
        models = get_models(domain, name=name, slug=slug)
        return [parse_model_as_performer(domain, cms_data, cdn_servers) for cms_data in models]

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_domain, domain): domain for domain in search_domains}
        for future in as_completed(futures):
            try:
                parsed_performers.extend(future.result())
            except Exception as e:
                log.error(f"Error processing domain {futures[future]}: {e}")
                log.debug(traceback.format_exc())

    return parsed_performers


def scene_by_url(url: str, search_domains: list[str] | None = None) -> ScrapedScene | None:
    url_domain = domain_from_url(url)
    if not url_domain:
        log.error(f"Could not determine domain from url: {url}")
        return None

    match video_identifier_from_url(url, url_domain):
        case None:
            log.error(f"Could not extract a video identifier from url: {url}")
            return None

        case "id", value:
            results = scene_search(cms_set_id=value, search_domains=[url_domain])
        case "slug", value:
            results = scene_search(slug=value, search_domains=[url_domain])
        case _, value:
            # Legacy title-based URL: try the domain the link was on first,
            # then search the rest of the network if that domain has no match
            results = scene_search(query=value, search_domains=[url_domain])
            if not results and search_domains:
                results = scene_search(query=value, search_domains=search_domains)
            if len(results) > 1:
                log.error(f"Ambiguous title match ({len(results)} results) for '{value}' from {url}")
                return None

    return best_match(results, url)


def gallery_by_url(url: str, search_domains: list[str] | None = None) -> ScrapedGallery | None:
    if not (url_domain := domain_from_url(url)):
        log.error(f"Could not determine domain from url: {url}")
        return None

    match gallery_identifier_from_url(url):
        case None:
            log.error(f"Could not extract a slug from url: {url}")
            return None
        case "id", value:
            kwargs = {"cms_set_id": value}
        case _, value:
            kwargs = {"slug": value}

    results = gallery_search(**kwargs, search_domains=[url_domain])
    if not results and search_domains:
        results = gallery_search(**kwargs, search_domains=search_domains)
    return best_match(results, url)


def performer_by_url(url: str, search_domains: list[str] | None = None) -> ScrapedPerformer | None:
    if not (url_domain := domain_from_url(url)):
        log.error(f"Could not determine domain from url: {url}")
        return None
    if not (match := re.search(r"/model/([^/?]+)$", url)):
        log.error(f"Could not extract slug from url: {url}")
        return None
    slug = match.group(1)

    results = performer_search(slug=slug, search_domains=[url_domain])
    if not results and search_domains:
        results = performer_search(slug=slug, search_domains=search_domains)
    return best_match(results, url)


def get_matching_scene(fragment, search_results: list[ScrapedScene]) -> ScrapedScene | None:
    return next(
        (
            r
            for r in search_results
            if r.get("title") == fragment.get("title")
            and r.get("date") == fragment.get("date")
        ),
        None,
    )


def scene_from_fragment(
    fragment, search_domains: list[str] | None = None
) -> ScrapedScene | None:
    if not fragment:
        log.error("No fragment provided")
        return None
    search_results = scene_search(fragment.get("title"), search_domains=search_domains)
    match = get_matching_scene(fragment, search_results)

    if match and (url_domain := domain_from_url(fragment.get("url", ""))):
        if slug_match := re.search(r"/video/([^/?]+)", fragment.get("url", "")):
            match["urls"] = [f"https://tour.{url_domain}.com/video/{slug_match.group(1)}"]

    return match


def get_matching_performer(fragment, search_results: list[ScrapedPerformer]) -> ScrapedPerformer | None:
    return next((r for r in search_results if r["name"] == fragment["name"]), None)


def performer_from_fragment(
    fragment, search_domains: list[str] | None = None
) -> ScrapedPerformer | None:
    if not fragment:
        log.error("No fragment provided")
        return None
    search_results = performer_search(fragment.get("name"), search_domains=search_domains)
    return get_matching_performer(fragment, search_results)


if __name__ == "__main__":
    domains = list(CONFIG.keys())
    op, args = scraper_args()

    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_by_url(url, search_domains=domains)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_by_url(url, search_domains=domains)
        case "performer-by-url", {"url": url} if url:
            result = performer_by_url(url, search_domains=domains)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, search_domains=domains)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, search_domains=domains)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, search_domains=domains)
        case _:
            log.error(f"Invalid operation: {op}")
            sys.exit(1)

    print(json.dumps(result))
