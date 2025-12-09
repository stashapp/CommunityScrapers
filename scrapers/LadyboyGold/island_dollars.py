from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import re
import sys
from typing import Any

import requests

import py_common.log as log
from py_common.types import ScrapedPerformer, ScrapedScene
from py_common.util import guess_nationality, scraper_args

CACHE_RESULTS_FILE = "islanddollars-cache.json"
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
        "cms_area_id": "a1fbacce-2340-45ef-9576-129e766e63f9",
        "studio_name": "LadyboyGold",
        "sets": {
            "cms_block_id": "109727"
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
            "cms_block_id": "105792"
        }
    },
    "ladyboyvice": {
        "cms_area_id": "c594b28c-ab09-44da-9166-0a332d33469f",
        "studio_name": "Ladyboy Vice",
        "sets": {
            "cms_block_id": "106090"
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
GENDER_MAP = {
    "Trans": "TRANSGENDER_FEMALE",
}

REQUESTS_TIMEOUT = 10

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
        scene["url"] = f"https://members.{domain}.com/video/{slug}"

    if added_nice := cms_set.get("added_nice"):
        log.trace(f"date from cms_set['added_nice']: {added_nice}")
        scene["date"] = added_nice

    # get image
    if cms_set_image := last_value(cms_set["preview_formatted"]["thumb"])[0]:
        # get cdn url
        if cdn_url := cdn_url_for_server_id(cdn_servers, cms_set_image["cms_content_server_id"]):
            scene["image"] = f"{cdn_url}{cms_set_image["fileuri"]}?{cms_set_image["signature"]}"

    if main_website := extract_names(cms_set, "MainWebsite"):
        # url
        scene["url"] = f"https://members.{main_website[0].lower()}/video/{cms_set['slug']}"

        # studio
        # use first value, remove .com or whatever suffix if present, and lowercase
        main_website_name = re.sub(r'\..*$', '', main_website[0], flags=re.IGNORECASE).lower()
        if main_website_name in CONFIG:
            scene["studio"] = {"name": CONFIG[main_website_name]["studio_name"]}
        else:
            scene["studio"] = {"name": main_website}

    categories = extract_names(cms_set, "Category")
    tags = extract_names(cms_set, "Tags")
    categories_and_tags = categories + tags
    performers = extract_names(cms_set, "Models")

    scene["tags"] = [ {"name": ct } for ct in categories_and_tags ]
    scene["performers"] = [ {"name": p } for p in performers ]
    scene["code"] = cms_set["cms_set_id"]

    return scene

def infer_birthday_from_age_and_born(age: int, born_str: str, added: datetime) -> str | None:
    try:
        born_date = datetime.strptime(born_str, "%B %d")
        current_year = datetime.now().year
        born_date = born_date.replace(year=current_year)
        added_date = datetime(current_year, added.month, added.day)
        if born_date > added_date:
            born_date = born_date.replace(year=current_year - 1)
        birth_year = born_date.year - age - (current_year - added.year)
        birth_date = born_date.replace(year=birth_year)
        return birth_date.strftime("%Y-%m-%d")
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
    performer: ScrapedPerformer = {}
    log.trace(f"cms_data: {cms_data}")
    performer["name"] = cms_data["name"]
    performer["details"] = cms_data["description"]
    performer["url"] = f"https://www.{domain}.com/model/{cms_data['slug']}"

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
            if first_cms_set_id := next(iter(cms_data.get("cms_set_ids", [])), None):
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

            # object containing "value": "value": "May 25", extract born date
            if inferred_birthday := infer_birthday_from_age_and_born(int(age["value"]), born["value"], added):
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
        performer["gender"] = GENDER_MAP.get(gender["value"], gender["value"])

    log.debug(f"(parsed) performer: {performer}")
    return performer

def extract_names(cms_set, data_type_name):
    return [
        value['name']
        for data_type in cms_set["data_types"]
        if data_type['data_type'] == data_type_name
        for value in data_type['data_values']
    ]

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

def get_sets(
        domain: str,
        content_type: str | None,
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


def get_all_video_sets(domain: str):
    cms_sets = []
    _result = get_sets(domain, content_type="video")
    if _result is not None and "total_count" in _result:
        total_count = _result["total_count"]
        log.debug(f"Total count: {total_count}")
        cms_sets.extend(_result["sets"])
    return cms_sets


def scene_search(
    query: str | None = None,
    slug: str | None = None,
    search_domains: list[str] | None = None,
) -> list[ScrapedScene]:
    if not search_domains:
        log.error("No search_domains provided")
        return None

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
                log.debug(e.with_traceback())

    # cache results
    log.debug(f"writing {len(parsed_scenes)} parsed scenes to {CACHE_RESULTS_FILE}")
    with open(CACHE_RESULTS_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(parsed_scenes))

    return parsed_scenes


def performer_search(
    name: str | None = None,
    slug: str | None = None,
    search_domains: list[str] | None = None,
) -> list[ScrapedPerformer]:
    if not search_domains:
        log.error("No search_domains provided")
        return None

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

    # cache results
    log.debug(f"writing {len(parsed_performers)} parsed performers to {CACHE_RESULTS_FILE}")
    with open(CACHE_RESULTS_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(parsed_performers))

    return parsed_performers


def scene_from_fragment(
    fragment,
    search_domains: list[str] | None = None,
) -> ScrapedScene:
    if not fragment:
        log.error("No fragment provided")
        return None
    log.debug(f"fragment: {fragment}")

    # attempt to get from cached results first
    search_results = None
    try:
        log.debug(f"Attempting to get result from {CACHE_RESULTS_FILE}")
        with open(CACHE_RESULTS_FILE, 'r', encoding='utf-8') as f:
            log.debug(f"Opened cache file {CACHE_RESULTS_FILE}")
            cached_scenes = json.load(f)
            log.debug(f"cached_scenes: {cached_scenes}")
            search_results = cached_scenes
    except FileNotFoundError:
        log.error(f"Cache file {CACHE_RESULTS_FILE} not found")
    except json.JSONDecodeError:
        log.error(f"Error decoding JSON from {CACHE_RESULTS_FILE}")
    except (OSError, IOError) as e:
        log.error(f"An I/O error occurred: {e}")
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")

    # if no scenes retrieved from cached file, do an API search
    if search_results is None:
        search_results = scene_search(fragment["title"], search_domains=search_domains)
    first_match = next(
        (
            r for r in search_results
            if r["title"] == fragment["title"]
            and r["date"] == fragment["date"]
        ),
        None
    )

    return first_match

def performer_by_url(
    url: str,
    search_domains: list[str] | None = None,
) -> ScrapedPerformer:
    # extract slug from url
    match = re.search(r'/model/([^/]+)', url)
    if not match:
        log.error(f"Could not extract slug from url: {url}")
        return None
    slug = match.group(1)

    search_results = performer_search(slug=slug, search_domains=search_domains)
    first_match = next(
        (
            r for r in search_results
            if r["url"].endswith(f"/model/{slug}")
        ),
        None
    )
    return first_match

def scene_by_url(
    url: str,
    search_domains: list[str] | None = None,
) -> ScrapedScene:
    # extract slug from url
    match = re.search(r'/video/([^/]+)', url)
    if not match:
        log.error(f"Could not extract slug from url: {url}")
        return None
    slug = match.group(1)

    search_results = scene_search(slug=slug, search_domains=search_domains)
    first_match = next(
        (
            r for r in search_results
            if r["url"].endswith(f"/video/{slug}")
        ),
        None
    )
    return first_match

def performer_by_fragment(
    fragment,
    search_domains: list[str] | None = None,
) -> ScrapedPerformer:
    search_results = performer_search(fragment["name"], search_domains=search_domains)
    log.debug(f"search_results: {search_results}")
    first_match = next(
        (
            r for r in search_results
            if r["name"] == fragment["name"]
        ),
        {}
    )

    return first_match

if __name__ == "__main__":
    domains = list(CONFIG.keys())
    op, args = scraper_args()

    result = None
    match op, args:
        case "performer-by-fragment", args:
            log.debug(f"performer-by-fragment, args: {args}, domains: {domains}")
            result = performer_by_fragment(args, search_domains=domains)
        case "performer-by-name", {"name": name} if name:
            log.debug(f"performer-by-name, name: {name}, domains: {domains}")
            result = performer_search(name, search_domains=domains)
        case "performer-by-url", {"url": url} if url:
            log.debug(f"performer-by-url, url: {url}, domains: {domains}")
            result = performer_by_url(url, search_domains=domains)
        case "scene-by-name", {"name": name} if name:
            log.debug(f"scene-by-name, name: {name}, domains: {domains}")
            result = scene_search(name, search_domains=domains)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            log.debug(f"scene-by-fragment, args: {args}, domains: {domains}")
            result = scene_from_fragment(args, search_domains=domains)
        case "scene-by-url", {"url": url} if url:
            log.debug(f"scene-by-url, url: {url}, domains: {domains}")
            result = scene_by_url(url, search_domains=domains)
        case _:
            log.error(f"Invalid operation: {op}")
            sys.exit(1)

    print(json.dumps(result))
