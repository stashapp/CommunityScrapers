import json
import requests
import sys
from typing import Any

import py_common.log as log
from py_common.types import ScrapedScene
from py_common.util import scraper_args

cdn_servers = {}
cache_results_file = "tsraw-cache.json"

def get_cdn_servers() -> str:
    global cdn_servers
    cms_area_id = 8
    search_params = {
        "cms_area_id": cms_area_id
    }
    headers = {
        "x-nats-cms-area-id": f"{cms_area_id}",
        "x-nats-entity-decode": f"{1}",
        "x-nats-natscode": "MC4wLjAuMC4wLjAuMC4wLjA"
    }
    url = "https://nats.islanddollars.com/tour_api.php/content/config"
    res = requests.get(url, params=search_params, headers=headers)
    result = res.json()
    cdn_servers = result['servers']


def parse_set_as_scene(cms_set: Any) -> ScrapedScene:
    scene: ScrapedScene = {}
    log.debug(f"cms_set: {cms_set}")
    scene["title"] = cms_set["name"].rstrip(" 4K")
    scene["details"] = cms_set["description"]
    scene["url"] = f"https://members.tsraw.com/video/{cms_set['slug']}"
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
    scene["studio"] = {"name": "TSRaw"}

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
    cms_area_id = 8
    search_params = {
        "cms_set_ids": "",
        "data_types": "1",
        "content_count": "1",
        "count": "12",
        "start": f"{start}",
        "cms_block_id": "102013",
        "orderby": "published_desc",
        "content_type": "video",
        "status": "enabled",
        "text_search": text_search,
        "data_type_search": '{"100001":"164"}',
        "cms_area_id": cms_area_id
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
        "x-nats-cms-area-id": f"{cms_area_id}",
        "x-nats-entity-decode": f"{1}",
        "x-nats-natscode": "MC4wLjAuMC4wLjAuMC4wLjA"
    }
    url = "https://nats.islanddollars.com/tour_api.php/content/sets"
    res = requests.get(url, params=search_params, headers=headers)
    result = res.json()
    return result


def get_all_video_sets(domain: str):
    cms_sets = []
    result = get_sets(domain)
    if result is not None and "total_count" in result:
        total_count = result["total_count"]
        cms_sets.extend(result["sets"])
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

    # get CDN servers to prepend to image URLs
    get_cdn_servers()
    log.debug(f"CDN servers: {cdn_servers}")

    video_sets = get_sets(search_domains[0], text_search=query)["sets"]
    parsed_scenes = [ parse_set_as_scene(cms_set) for cms_set in video_sets ]

    # cache results
    log.debug(f"writing {len(parsed_scenes)} parsed scenes to {cache_results_file}")
    with open(cache_results_file, 'w') as f:
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
    try:
        log.debug(f"Attempting to get result from {cache_results_file}")
        with open(cache_results_file, 'r') as f:
            cached_scenes = json.load(f)
            log.debug(f"cached_scenes: {cached_scenes}")
            search_results = cached_scenes
    except:
        pass
    
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
    domains = ["tsraw"]
    op, args = scraper_args()

    result = None
    match op, args:
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, search_domains=domains)            
        case _:
            log.error(f"Invalid operation: {op}")
            sys.exit(1)

    print(json.dumps(result))
