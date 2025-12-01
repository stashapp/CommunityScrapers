from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import sys
from typing import Any

import requests

import py_common.log as log
from py_common.types import ScrapedScene
from py_common.util import scraper_args

CACHE_RESULTS_FILE = "islanddollars-cache.json"
CONFIG = {
    "ladyboycrush": {
        "cms_area_id": "74175374-c756-4ae9-97b2-e011512a1521",
        "studio_name": "Ladyboy Crush",
        "sets": {
            "cms_block_id": "106093",
            "data_type_search": '{"100001":"184"}'
        }
    },
    "ladyboyglamour": {
        "cms_area_id": "60f34ef8-3a0e-44ae-8afc-5795ee75eeff",
        "studio_name": "Ladyboy Glamour",
        "sets": {
            "cms_block_id": "109727",
            "data_type_search": '{"100001":"190"}'
        }
    },
    "ladyboypussy": {
        "cms_area_id": "3b74725d-ad01-45a1-8186-ac6be1bc1661",
        "studio_name": "Ladyboy Pussy",
        "sets": {
            "cms_block_id": "112975",
            "data_type_search": '{"100001":"183"}'
        }
    },
    "ladyboysfuckedbareback": {
        "cms_area_id": "126f96ec-ffdc-4f4b-a459-c9a2e78b9b67",
        "studio_name": "Ladyboys Fucked Bareback",
        "sets": {
            "cms_block_id": "105792",
            "data_type_search": '{"100001":"182"}'
        }
    },
    "ladyboyvice": {
        "cms_area_id": "c594b28c-ab09-44da-9166-0a332d33469f",
        "studio_name": "Ladyboy Vice",
        "sets": {
            "cms_block_id": "106090",
            "data_type_search": '{"100001":"185"}'
        }
    },
    "tsraw": {
        "cms_area_id": "cc6bd0ac-a417-47d1-9868-7855b25986e5",
        "studio_name": "TSRaw",
        "sets": {
            "cms_block_id": "102013",
            "data_type_search": '{"100001":"164"}'
        }
    },
}

REQUESTS_TIMEOUT = 10

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


def parse_set_as_scene(domain: str, cms_set: Any, cdn_servers: dict[str, Any]) -> ScrapedScene:
    scene: ScrapedScene = {}
    log.debug(f"cms_set: {cms_set}")
    scene["title"] = cms_set["name"].rstrip(" 4K")
    scene["details"] = cms_set["description"].strip()
    scene["url"] = f"https://members.{domain}.com/video/{cms_set['slug']}"
    scene["date"] = cms_set["added_nice"]

    # get image
    # Get the last item
    last_key = list(cms_set["preview_formatted"]["thumb"].keys())[-1]
    last_value = cms_set["preview_formatted"]["thumb"][last_key]
    cms_set_image = last_value[0]
    cms_content_server_id = cms_set_image["cms_content_server_id"]
    # get cdn url
    cdn_url = cdn_servers[cms_content_server_id]["settings"]["url"]
    cdn_url = cdn_url.rstrip("/")

    scene["image"] = f"{cdn_url}{cms_set_image["fileuri"]}?{cms_set_image["signature"]}"
    scene["studio"] = {"name": CONFIG[domain]["studio_name"]}

    categories = extract_names(cms_set, "Category")
    tags = extract_names(cms_set, "Tags")
    categories_and_tags = categories + tags
    performers = extract_names(cms_set, "Models")

    scene["tags"] = [ {"name": ct } for ct in categories_and_tags ]
    scene["performers"] = [ {"name": p } for p in performers ]
    # scene["code"] = cms_set["cms_set_id"]

    return scene

def extract_names(cms_set, data_type_name):
    return [
        value['name']
        for data_type in cms_set["data_types"]
        if data_type['data_type'] == data_type_name
        for value in data_type['data_values']
    ]

def get_sets(domain: str, start: int = 0, text_search = ""):
    search_params = {
        "cms_set_ids": "",
        "data_types": "1",
        "content_count": "1",
        "count": "12",
        "start": f"{start}",
        "cms_block_id": CONFIG[domain]["sets"]["cms_block_id"],
        "orderby": "published_desc",
        "content_type": "video",
        "status": "enabled",
        "text_search": text_search,
        "data_type_search": CONFIG[domain]["sets"]["data_type_search"],
        "cms_area_id": CONFIG[domain]["cms_area_id"]
    }
    headers = {
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
    url = "https://nats.islanddollars.com/tour_api.php/content/sets"
    res = requests.get(url, params=search_params, headers=headers, timeout=REQUESTS_TIMEOUT)
    _result = res.json()
    return _result


def get_all_video_sets(domain: str):
    cms_sets = []
    _result = get_sets(domain)
    if _result is not None and "total_count" in _result:
        total_count = _result["total_count"]
        log.debug(f"Total count: {total_count}")
        cms_sets.extend(_result["sets"])
    return cms_sets


def scene_search(
    query: str,
    search_domains: list[str] | None = None,
) -> list[ScrapedScene]:
    if not query:
        log.error("No query provided")
        return None

    if not search_domains:
        log.error("No search_domains provided")
        return None

    log.debug(f"Matching '{query}' against {len(search_domains)} sites")

    parsed_scenes: list[ScrapedScene] = []

    def fetch_domain(domain):
        cdn_servers = get_cdn_servers(domain)
        log.debug(f"CDN servers: {cdn_servers}")
        log.debug(f"Searching domain: {domain} for query: {query}")
        video_sets = get_sets(domain, text_search=query)["sets"]
        return [parse_set_as_scene(domain, cms_set, cdn_servers) for cms_set in video_sets]

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_domain, domain): domain for domain in search_domains}
        for future in as_completed(futures):
            try:
                domain_parsed_scenes = future.result()
                parsed_scenes.extend(domain_parsed_scenes)
            except Exception as e:
                log.error(f"Error processing domain {futures[future]}: {e}")

    # cache results
    log.debug(f"writing {len(parsed_scenes)} parsed scenes to {CACHE_RESULTS_FILE}")
    with open(CACHE_RESULTS_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(parsed_scenes))

    return parsed_scenes


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
    # try:
    #     log.debug(f"Attempting to get result from {CACHE_RESULTS_FILE}")
    #     with open(CACHE_RESULTS_FILE, 'r', encoding='utf-8') as f:
    #         log.debug(f"Opened cache file {CACHE_RESULTS_FILE}")
    #         cached_scenes = json.load(f)
    #         log.debug(f"cached_scenes: {cached_scenes}")
    #         search_results = cached_scenes
    # except FileNotFoundError:
    #     log.error(f"Cache file {CACHE_RESULTS_FILE} not found")
    # except json.JSONDecodeError:
    #     log.error(f"Error decoding JSON from {CACHE_RESULTS_FILE}")
    # except (OSError, IOError) as e:
    #     log.error(f"An I/O error occurred: {e}")
    # except Exception as e:
    #     log.error(f"An unexpected error occurred: {e}")

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

if __name__ == "__main__":
    domains = list(CONFIG.keys())
    op, args = scraper_args()

    result = None
    match op, args:
        case "scene-by-name", {"name": name, "extra": extra} if name:
            log.debug(f"scene-by-name, name: {name}, domains: {domains}")
            result = scene_search(name, search_domains=domains)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            log.debug(f"scene-by-fragment, args: {args}, domains: {domains}")
            result = scene_from_fragment(args, search_domains=domains)            
        case _:
            log.error(f"Invalid operation: {op}")
            sys.exit(1)

    print(json.dumps(result))
