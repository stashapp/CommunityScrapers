from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import re
import sys
import traceback
from typing import Any

import requests

import py_common.log as log
from py_common.cache import cache_to_disk
from py_common.types import Gender, ScrapedGallery, ScrapedPerformer, ScrapedScene, ScrapedStudio
from py_common.util import guess_nationality, scraper_args

CONFIG = {
    "ladyboycrush": {
        "cms_area_id": "74175374-c756-4ae9-97b2-e011512a1521",
        "studio_name": "Ladyboy Crush",
        "sets": {
            "cms_block_id": "106093"
        }
    },
    "ladyboyglamour": {
        "cms_area_id": "60f34ef8-3a0e-44ae-8afc-5795ee75eeff",
        "studio_name": "Ladyboy Glamour",
        "sets": {
            "cms_block_id": "109727"
        }
    },
    "ladyboygold": {
        "cms_area_id": "cd9a5600-5cda-4ed0-b356-f62af1887d96", # from homepage call to /config.json
        "studio_name": "LadyboyGold",
        "sets": {
            "cms_block_id": "114793" # from scene page call to /sets, query param
        }
    },
    "ladyboypussy": {
        "cms_area_id": "3b74725d-ad01-45a1-8186-ac6be1bc1661",
        "studio_name": "Ladyboy Pussy",
        "sets": {
            "cms_block_id": "112975"
        }
    },
    "ladyboysfuckedbareback": {
        "cms_area_id": "126f96ec-ffdc-4f4b-a459-c9a2e78b9b67",
        "studio_name": "Ladyboys Fucked Bareback",
        "sets": {
            "cms_block_id": "105724"
        }
    },
    "ladyboyvice": {
        "cms_area_id": "c594b28c-ab09-44da-9166-0a332d33469f",
        "studio_name": "Ladyboy Vice",
        "sets": {
            "cms_block_id": "101951"
        }
    },
    "tsraw": {
        "cms_area_id": "cc6bd0ac-a417-47d1-9868-7855b25986e5",
        "studio_name": "TSRaw",
        "sets": {
            "cms_block_id": "102013"
        }
    },
}
GENDER_MAP: dict[str, Gender] = {
    "Trans": "TRANSGENDER_FEMALE",
}

REQUESTS_TIMEOUT = 10

def domain_from_url(url: str) -> str | None:
    url_lower = url.lower()
    return next((d for d in CONFIG if f"{d}.com" in url_lower), None)

def urls_match(url_a: str, url_b: str, path_segment: str) -> bool:
    pattern = re.compile(rf'/{path_segment}/([^/]+)')
    match_a = pattern.search(url_a)
    match_b = pattern.search(url_b)
    if not match_a or not match_b:
        return False
    return domain_from_url(url_a) == domain_from_url(url_b) and match_a.group(1) == match_b.group(1)

WORKING_SUBDOMAINS: dict[str, tuple[str, ...]] = {
    "ladyboycrush": ("www",),
    "ladyboyglamour": (),
    "ladyboygold": ("www", "members"),
    "ladyboypussy": ("www", "members"),
    "ladyboysfuckedbareback": ("www", "members"),
    "ladyboyvice": ("www",),
    "tsraw": ("www", "members"),
}

def known_urls(original_url: str, domain: str, slug: str, path_segment: str) -> list[str]:
    urls = [
        f"https://{prefix}.{domain}.com/{path_segment}/{slug}"
        for prefix in WORKING_SUBDOMAINS.get(domain, ())
    ]
    return urls or [original_url]

def headers_for_domain(domain: str) -> dict[str, str]:
    return {
        "origin": f"https://www.{domain}.com",
        "referer": f"https://www.{domain}.com",
        "priority": "u=1, i",
        "sec-ch-ua": '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "Windows",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "x-nats-cms-area-id": f"{CONFIG[domain]['cms_area_id']}",
        "x-nats-entity-decode": f"{1}",
        "x-nats-natscode": "MC4wLjAuMC4wLjAuMC4wLjA"
    }

def get_cdn_servers(domain: str) -> dict[str, Any]:
    search_params = {
        "cms_area_id": CONFIG[domain]["cms_area_id"]
    }
    headers = {
        "x-nats-cms-area-id": f"{CONFIG[domain]['cms_area_id']}",
        "x-nats-entity-decode": f"{1}",
        "x-nats-natscode": "MC4wLjAuMC4wLjAuMC4wLjA"
    }
    url = "https://nats.islanddollars.com/tour_api.php/content/config"
    res = requests.get(url, params=search_params, headers=headers, timeout=REQUESTS_TIMEOUT)
    _result = res.json()
    return _result['servers']

def last_value(d: dict[str, Any]) -> Any:
    """Get the last value in a dictionary."""
    if not d:
        return None
    last_key = list(d.keys())[-1]
    return d[last_key]

def parse_set_as_scene(domain: str, cms_set: Any, cdn_servers: dict[str, Any]) -> ScrapedScene:
    scene: ScrapedScene = {}
    log.trace(f"cms_set: {cms_set}")
    if title := cms_set.get("title"):
        log.trace(f"title from cms_set['title']: {title}")
        scene["title"] = title.rstrip(" 4K")
    elif name := cms_set.get("name"):
        log.trace(f"title from cms_set['name']: {name}")
        scene["title"] = name.rstrip(" 4K")
    else:
        log.error("No title or name found in cms_set")

    if description := cms_set.get("description"):
        log.trace(f"description from cms_set['description']: {description}")
        scene["details"] = description.strip()

    if slug := cms_set.get("slug"):
        log.trace(f"slug from cms_set['slug']: {slug}")
        scene["urls"] = [f"https://members.{domain}.com/video/{slug}"]

    if added_nice := cms_set.get("added_nice"):
        log.trace(f"date from cms_set['added_nice']: {added_nice}")
        scene["date"] = added_nice

    # get image
    if cms_set_image := last_value(cms_set["preview_formatted"]["thumb"])[0]:
        # get cdn url
        if cdn_url := cdn_url_for_server_id(cdn_servers, cms_set_image["cms_content_server_id"]):
            scene["image"] = f"{cdn_url}{cms_set_image["fileuri"]}?{cms_set_image["signature"]}"

    if main_website := extract_names(cms_set, "MainWebsite"):
        scene["urls"] = [f"https://members.{main_website[0].lower()}/video/{cms_set['slug']}"]

    if studio := resolve_studio(cms_set):
        scene["studio"] = studio

    categories = extract_names(cms_set, "Category")
    tags = extract_names(cms_set, "Tags")
    categories_and_tags = categories + tags
    performers = extract_names(cms_set, "Models")

    scene["tags"] = [ {"name": ct } for ct in categories_and_tags ]
    scene["performers"] = [ {"name": p } for p in performers ]
    scene["code"] = cms_set["cms_set_id"]

    return scene


def parse_set_as_gallery(domain: str, cms_set: Any, cdn_servers: dict[str, Any]) -> ScrapedGallery:
    gallery: ScrapedGallery = {}
    log.trace(f"cms_set: {cms_set}")
    if title := cms_set.get("title"):
        log.trace(f"title from cms_set['title']: {title}")
        gallery["title"] = title.rstrip(" 4K")
    elif name := cms_set.get("name"):
        log.trace(f"title from cms_set['name']: {name}")
        gallery["title"] = name.rstrip(" 4K")
    else:
        log.error("No title or name found in cms_set")

    if description := cms_set.get("description"):
        log.trace(f"description from cms_set['description']: {description}")
        gallery["details"] = description.strip()

    if slug := cms_set.get("slug"):
        log.trace(f"slug from cms_set['slug']: {slug}")
        gallery["urls"] = [f"https://members.{domain}.com/photo/{slug}"]

    if added_nice := cms_set.get("added_nice"):
        log.trace(f"date from cms_set['added_nice']: {added_nice}")
        gallery["date"] = added_nice

    # get image
    if cms_set_image := last_value(cms_set["preview_formatted"]["thumb"])[0]:
        # get cdn url
        if cdn_url := cdn_url_for_server_id(cdn_servers, cms_set_image["cms_content_server_id"]):
            # gallery doesn't have an image or cover field, but it is useful to know which is
            # the cover image for the gallery, so we will log it out here
            cover_image_url = f"{cdn_url}{cms_set_image["fileuri"]}?{cms_set_image["signature"]}"
            log.debug(f"Cover image URL for gallery '{gallery.get('title')}': {cover_image_url}")

    if main_website := extract_names(cms_set, "MainWebsite"):
        gallery["urls"] = [f"https://members.{main_website[0].lower()}/photo/{cms_set['slug']}"]

    if studio := resolve_studio(cms_set):
        gallery["studio"] = studio

    categories = extract_names(cms_set, "Category")
    tags = extract_names(cms_set, "Tags")
    categories_and_tags = categories + tags
    performers = extract_names(cms_set, "Models")

    gallery["tags"] = [ {"name": ct } for ct in categories_and_tags ]
    gallery["performers"] = [ {"name": p } for p in performers ]
    gallery["code"] = cms_set["cms_set_id"]

    return gallery


def calculate_dob(age: int, born_str: str, added: datetime) -> str | None:
    try:
        birth_year = added.year - age
        birthday = datetime.strptime(born_str, "%B %d")

        # check if birthday has occurred yet in added year
        birthday_in_added_year = datetime(added.year, birthday.month, birthday.day)

        if added < birthday_in_added_year:
            birth_year -= 1

        date_of_birth = birthday.replace(year=birth_year)
        return date_of_birth.strftime("%Y-%m-%d")
    except ValueError as e:
        log.error(f"Error parsing born date: {e}")
        return None

def cdn_url_for_server_id(cdn_servers: dict[str, Any], server_id: str) -> str | None:
    server_info = cdn_servers.get(server_id, None)
    if server_info is None:
        return None
    cdn_url = server_info["settings"]["url"]
    return cdn_url.rstrip("/")

def parse_model_as_performer(domain: str, cms_data: Any, cdn_servers: dict[str, Any]) -> ScrapedPerformer:
    performer: ScrapedPerformer = {"name": cms_data["name"]}
    log.trace(f"cms_data: {cms_data}")
    performer["details"] = cms_data["description"]
    performer["urls"] = [f"https://www.{domain}.com/model/{cms_data['slug']}"]

    data_detail_values = cms_data.get("data_detail_values", {})

    # get image
    if cms_set_image := last_value(data_detail_values["preview"]["11"])[0]:
        # get cdn url
        if cdn_url := cdn_url_for_server_id(cdn_servers, cms_set_image["cms_content_server_id"]):
            performer["image"] = f"{cdn_url}{cms_set_image["fileuri"]}?{cms_set_image["signature"]}"

    if weight := data_detail_values.get("4"):
        # object containing "value": "140lbs (63kg)", extract numeric weight in kg
        weight_value = weight["value"]
        if match := re.search(r'(\d[\.\d+]*)\s*kg', weight_value):
            performer["weight"] = match.group(1)

    if age := data_detail_values.get("2"):
        # object containing "value": "23", extract numeric age
        if born := data_detail_values.get("1"):
            # get first cms_set_id from data_detail_values
            if first_cms_set_id := next(iter(cms_data.get("cms_set_id", [])), None):
                log.debug(f"first_cms_set_id: {first_cms_set_id}")
                # get added date from cms_set
                cms_sets = get_sets(domain, cms_set_id=first_cms_set_id)
                if cms_sets and "added_nice" in cms_sets[0]:
                    added_nice = cms_sets[0]["added_nice"]
                    added = datetime.strptime(added_nice, "%Y-%m-%d")
                else:
                    added = datetime.now()
            else:
                added = datetime.now()
            log.debug(f"added: {added}")

            # object containing "value": "value": "May 25", extract born date
            if inferred_birthday := calculate_dob(int(age["value"]), born["value"], added):
                performer["birthdate"] = inferred_birthday

    if measurements := data_detail_values.get("6"):
        # object containing "value": "38C-32-40"
        performer["measurements"] = measurements["value"]

    if height := data_detail_values.get("3"):
        # object containing "value": "5'5\" (165cm)", extract numeric height in cm
        height_value = height["value"]
        if match := re.search(r'(\d[\.\d+]*)\s*cm', height_value):
            performer["height"] = match.group(1)

    if country := data_detail_values.get("8"):
        # object containing "value": "Brazil"
        performer["country"] = guess_nationality(country["value"])

    if hair_color := data_detail_values.get("13"):
        # object containing "value": "Brown"
        performer["hair_color"] = hair_color["value"]

    if eye_color := data_detail_values.get("14"):
        # object containing "value": "Brown"
        performer["eye_color"] = eye_color["value"]

    if ethnicity := data_detail_values.get("7"):
        # object containing "value": "Latina"
        performer["ethnicity"] = ethnicity["value"]

    if gender := data_detail_values.get("5"):
        # object containing "value": "Trans"
        if mapped_gender := GENDER_MAP.get(gender["value"]):
            performer["gender"] = mapped_gender
        else:
            log.debug(f"Unmapped gender value: {gender['value']}")

    log.debug(f"(parsed) performer: {performer}")
    return performer

def extract_names(cms_set, data_type_name):
    return [
        value['name']
        for data_type in cms_set["data_types"]
        if data_type['data_type'] == data_type_name
        for value in data_type['data_values']
    ]

def extract_slugs(cms_set, data_type_name):
    return [
        value['slug']
        for data_type in cms_set["data_types"]
        if data_type['data_type'] == data_type_name
        for value in data_type['data_values']
    ]

def resolve_studio(cms_set: Any) -> ScrapedStudio | None:
    for tag, values in (("Section", extract_slugs(cms_set, "Section")), ("MainWebsite", extract_names(cms_set, "MainWebsite"))):
        if not values:
            continue
        key = re.sub(r'\..*$', '', values[0], flags=re.IGNORECASE).lower()
        if key in CONFIG:
            return {"name": CONFIG[key]["studio_name"]}
        # not one of our configured studios, fall back to its own display name
        names = extract_names(cms_set, tag)
        return {"name": names[0] if names else values[0]}
    return None

@cache_to_disk(ttl=600)
def get_models(domain: str, start: int = 0, name: str | None = None, slug: str | None = None):
    search_params = {
        "cms_data_type_id": "4",
        "start": f"{start}",
        "count": "10",
        "orderby": "published_desc",
        "cms_block_id": CONFIG[domain]["sets"]["cms_block_id"],
        "name": name,
        "slug": slug
    }
    headers = headers_for_domain(domain)
    url = "https://nats.islanddollars.com/tour_api.php/content/data-values"
    res = requests.get(url, params=search_params, headers=headers, timeout=REQUESTS_TIMEOUT)
    data_values = []
    try:
        _result = res.json()
    except Exception as e:
        log.error(f"Error parsing JSON response: {e}")
        _result = {"data_values": []}
    else:
        if _result is not None and "total_count" in _result:
            log.debug(f"Total count at domain: {domain}: {_result['total_count']}")
            data_values.extend(_result["data_values"])
    log.trace(f"get_models result: {data_values}")
    return data_values

@cache_to_disk(ttl=600)
def get_sets(
        domain: str,
        content_type: str | None = None,
        cms_set_id: str | None = None,
        start: int = 0,
        text_search: str | None = None,
        slug : str | None = None
    ) -> list[Any]:

    search_params = {
        "data_types": "1",
        "content_count": "1",
        "count": "5",
        "start": f"{start}",
        "cms_block_id": CONFIG[domain]["sets"]["cms_block_id"],
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
    log.debug(f"Searching domain {domain} with params: {search_params} and headers: {headers}")
    url = "https://nats.islanddollars.com/tour_api.php/content/sets"
    res = requests.get(url, params=search_params, headers=headers, timeout=REQUESTS_TIMEOUT)
    log.trace(f"Content-Length: {res.headers.get('Content-Length')}")
    log.trace(f"Content-Type: {res.headers.get('Content-Type')}")
    cms_sets = []
    try:
        _result = res.json()
    except Exception as e:
        log.error(f"Error parsing JSON response: {e}")
        _result = {"sets": []}
    else:
        if _result is not None and "total_count" in _result:
            log.debug(f"Search hits for domain {domain}: {_result['total_count']}")
            cms_sets.extend(_result["sets"])
        else:
            log.debug(f"No results found for domain {domain}")
            log.debug(f"Response content: {res.text}")
    log.trace(f"get_sets result: {cms_sets}")
    return cms_sets


def scene_search(
    query: str | None = None,
    slug: str | None = None,
    search_domains: list[str] | None = None,
) -> list[ScrapedScene]:
    if not search_domains:
        log.error("No search_domains provided")
        return []

    log.debug(f"Matching query: {query} and slug: {slug} against {len(search_domains)} sites")

    parsed_scenes: list[ScrapedScene] = []

    def fetch_domain(domain):
        cdn_servers = get_cdn_servers(domain)
        log.trace(f"CDN servers: {cdn_servers}")
        log.trace(f"Searching domain: {domain} for query: {query}")
        video_sets = get_sets(domain, content_type="video", text_search=query, slug=slug)
        return [parse_set_as_scene(domain, cms_set, cdn_servers) for cms_set in video_sets]

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_domain, domain): domain for domain in search_domains}
        for future in as_completed(futures):
            try:
                domain_parsed_scenes = future.result()
                parsed_scenes.extend(domain_parsed_scenes)
            except Exception as e:
                log.error(f"Error processing domain {futures[future]}: {e}")
                log.debug(traceback.format_exc())

    return parsed_scenes


def gallery_search(
    query: str | None = None,
    slug: str | None = None,
    search_domains: list[str] | None = None,
) -> list[ScrapedGallery]:
    if not search_domains:
        log.error("No search_domains provided")
        return []

    log.debug(f"Matching query: {query} and slug: {slug} against {len(search_domains)} sites")

    parsed_galleries: list[ScrapedGallery] = []

    def fetch_domain(domain):
        cdn_servers = get_cdn_servers(domain)
        log.trace(f"CDN servers: {cdn_servers}")
        log.trace(f"Searching domain: {domain} for query: {query}")
        photo_sets = get_sets(domain, content_type="image", text_search=query, slug=slug)
        return [parse_set_as_gallery(domain, cms_set, cdn_servers) for cms_set in photo_sets]

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_domain, domain): domain for domain in search_domains}
        for future in as_completed(futures):
            try:
                domain_parsed_galleries = future.result()
                parsed_galleries.extend(domain_parsed_galleries)
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

    log.debug(f"Matching name: {name} and slug: {slug} against {len(search_domains)} sites")

    parsed_performers: list[ScrapedPerformer] = []

    def fetch_domain(domain):
        cdn_servers = get_cdn_servers(domain)
        log.trace(f"CDN servers: {cdn_servers}")
        log.trace(f"Searching domain: {domain} for query: {name}")
        models = get_models(domain, name=name, slug=slug)
        return [parse_model_as_performer(domain, cms_data, cdn_servers) for cms_data in models]

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_domain, domain): domain for domain in search_domains}
        for future in as_completed(futures):
            try:
                domain_parsed_performers = future.result()
                parsed_performers.extend(domain_parsed_performers)
            except Exception as e:
                log.error(f"Error processing domain {futures[future]}: {e}")

    return parsed_performers


def scene_from_fragment(
    fragment,
    search_domains: list[str] | None = None,
) -> ScrapedScene | None:
    if not fragment:
        log.error("No fragment provided")
        return None
    log.debug(f"fragment: {fragment}")

    search_results = scene_search(fragment["title"], search_domains=search_domains)
    match = get_matching_scene(fragment, search_results)

    if match and (url_domain := domain_from_url(fragment.get("url", ""))):
        if slug_match := re.search(r'/video/([^/]+)', fragment.get("url", "")):
            match["urls"] = known_urls(fragment["url"], url_domain, slug_match.group(1), "video")
        if not match.get("studio"):
            match["studio"] = {"name": CONFIG[url_domain]["studio_name"]}

    return match

def get_matching_scene(fragment, search_results: list[ScrapedScene]) -> ScrapedScene | None:
    fragment_url = fragment.get("url", "")
    first_match = next(
        (
            r for r in search_results
            if r.get("title") == fragment["title"]
            and r.get("date") == fragment["date"]
            and any(urls_match(fragment_url, u, "video") for u in r.get("urls", []))
        ),
        None
    )
    return first_match


def gallery_from_fragment(
    fragment,
    search_domains: list[str] | None = None,
) -> ScrapedGallery | None:
    if not fragment:
        log.error("No fragment provided")
        return None
    log.debug(f"fragment: {fragment}")

    search_results = gallery_search(fragment["title"], search_domains=search_domains)
    match = get_matching_gallery(fragment, search_results)

    if match and (url_domain := domain_from_url(fragment.get("url", ""))):
        if slug_match := re.search(r'/photo/([^/]+)', fragment.get("url", "")):
            match["urls"] = known_urls(fragment["url"], url_domain, slug_match.group(1), "photo")
        if not match.get("studio"):
            match["studio"] = {"name": CONFIG[url_domain]["studio_name"]}

    return match

def get_matching_gallery(fragment, search_results: list[ScrapedGallery]) -> ScrapedGallery | None:
    first_match = next(
        (
            r for r in search_results
            if r.get("title") == fragment["title"]
        ),
        None
    )
    return first_match

def best_match(candidates: list, url: str) -> Any | None:
    # tries to find the candidate that best fits the URL used to scrape
    if not candidates:
        return None
    if url_domain := domain_from_url(url):
        for candidate in candidates:
            if any(domain_from_url(u) == url_domain for u in candidate.get("urls", [])):
                return candidate
    return candidates[0]

def gallery_by_url(
    url: str,
    search_domains: list[str] | None = None,
) -> ScrapedGallery | None:
    # extract slug from url
    match = re.search(r'/photo/([^/]+)', url)
    if not match:
        log.error(f"Could not extract slug from url: {url}")
        return None
    slug = match.group(1)

    search_results = gallery_search(slug=slug, search_domains=search_domains)
    candidates = [r for r in search_results if any(u.endswith(f"/photo/{slug}") for u in r.get("urls", []))]
    first_match = best_match(candidates, url)
    if first_match:
        # report both the members-area and public URL for the domain that was
        # actually requested, not whichever domain's search happened to find
        # the match (see scene_by_url)
        url_domain = domain_from_url(url)
        first_match["urls"] = known_urls(url, url_domain, slug, "photo") if url_domain else [url]
        if not first_match.get("studio") and url_domain:
            first_match["studio"] = {"name": CONFIG[url_domain]["studio_name"]}
    return first_match

def performer_by_url(
    url: str,
    search_domains: list[str] | None = None,
) -> ScrapedPerformer | None:
    # extract slug from url
    match = re.search(r'/model/([^/]+)', url)
    if not match:
        log.error(f"Could not extract slug from url: {url}")
        return None
    slug = match.group(1)

    search_results = performer_search(slug=slug, search_domains=search_domains)
    candidates = [r for r in search_results if any(u.endswith(f"/model/{slug}") for u in r.get("urls", []))]
    first_match = best_match(candidates, url)
    if first_match:
        # report both the members-area and public URL for the domain that was
        # actually requested (see scene_by_url)
        url_domain = domain_from_url(url)
        first_match["urls"] = known_urls(url, url_domain, slug, "model") if url_domain else [url]
    return first_match

def scene_by_url(
    url: str,
    search_domains: list[str] | None = None,
) -> ScrapedScene | None:
    # extract slug from url
    match = re.search(r'/video/([^/]+)', url)
    if not match:
        log.error(f"Could not extract slug from url: {url}")
        return None
    slug = match.group(1)

    search_results = scene_search(slug=slug, search_domains=search_domains)
    candidates = [r for r in search_results if any(u.endswith(f"/video/{slug}") for u in r.get("urls", []))]
    first_match = best_match(candidates, url)

    if first_match:
        # A scene can show up in the search from any domain but the final URL
        # can reliably determine the studio name. Report both the members-area
        # and public URL for that domain, not just whichever one was pasted.
        url_domain = domain_from_url(url)
        first_match["urls"] = known_urls(url, url_domain, slug, "video") if url_domain else [url]
        if not first_match.get("studio") and url_domain:
            first_match["studio"] = {"name": CONFIG[url_domain]["studio_name"]}

    return first_match

def performer_by_fragment(
    fragment,
    search_domains: list[str] | None = None,
) -> ScrapedPerformer | None:
    if not fragment:
        log.error("No fragment provided")
        return None
    log.debug(f"fragment: {fragment}")

    search_results = performer_search(fragment["name"], search_domains=search_domains)
    return get_matching_performer(fragment, search_results)

def get_matching_performer(fragment, search_results: list[ScrapedPerformer]) -> ScrapedPerformer | None:
    first_match = next(
        (
            r for r in search_results
            if r["name"] == fragment["name"]
        ),
        None
    )
    return first_match

if __name__ == "__main__":
    domains = list(CONFIG.keys())
    op, args = scraper_args()

    result = None
    match op, args:
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, search_domains=domains)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_by_url(url, search_domains=domains)
        case "performer-by-fragment", args:
            result = performer_by_fragment(args, search_domains=domains)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, search_domains=domains)
        case "performer-by-url", {"url": url} if url:
            result = performer_by_url(url, search_domains=domains)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, search_domains=domains)
        case "scene-by-url", {"url": url} if url:
            result = scene_by_url(url, search_domains=domains)
        case _:
            log.error(f"Invalid operation: {op}")
            sys.exit(1)

    print(json.dumps(result))
