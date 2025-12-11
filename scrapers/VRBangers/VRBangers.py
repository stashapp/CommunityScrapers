from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import re
import sys
from typing import Any

from py_common.deps import ensure_requirements
ensure_requirements("bs4:beautifulsoup4", "requests")
import py_common.log as log
from py_common.types import ScrapedPerformer, ScrapedScene
from py_common.util import guess_nationality, scraper_args

import requests
from bs4 import BeautifulSoup as bs

CONFIG = {
    "arporn": {
        "studio_name": "AR Porn",
    },
    "blowvr": {
        "studio_name": "Blow VR",
    },
    "dezyred": {
        "studio_name": "Dezyred",
    },
    "vrbangers": {
        "studio_name": "VR Bangers",
    },
    "vrconk": {
        "studio_name": "VR Conk",
    },
    "vrbgay": {
        "studio_name": "VRB Gay",
    },
    "vrbtrans": {
        "studio_name": "VRB Trans",
    },
}

def studio_name_for_domain(domain: str) -> str:
    return CONFIG.get(domain, {}).get("studio_name", domain)

def clean_text(details: str) -> str:
    "Remove escaped backslashes and html parse the details text."
    if details:
        details = details.replace("\\", "")
        # replace breaks with newlines
        details = re.sub(r"<\s*\/?br\s*\/?\s*>", "\n", details)
        # don't strip to preserve newlines
        # don't add additional newlines
        details = bs(details, features='html.parser').get_text("", strip=False)
    return details

def headers_for_domain(domain: str) -> dict[str, str]:
    return {
        "origin": f"https://{domain}.com",
        "referer": f"https://{domain}.com/",
        "priority": "u=1, i",
        "sec-ch-ua": '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "Windows",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-GB,en;q=0.6",
    }

def api_search(query: str, domains: list[str]) -> dict[str, dict[list[dict]]]:
    """
    Searches the API for models and videos matching the query across the specified sites
    """
    results: dict[str, dict[list[dict]]] = {}

    def fetch(domain):
        headers = headers_for_domain(domain)
        api_url = f"https://content.{domain}.com/api/content/v1/search/{query}"
        log.debug(f"Searching {api_url} with headers: {headers}")
        response = requests.get(api_url, headers=headers)
        if response.status_code != 200:
            log.error(f"Failed to search {domain}: HTTP {response.status_code}")
            return domain, None
        _json = response.json()
        log.debug(f"Found {len(_json.get('data', {}).get('models', []))} models and {len(_json.get('data', {}).get('videos', []))} videos on {domain}")
        return domain, {
            "models": _json.get("data", {}).get("models", []),
            "videos": _json.get("data", {}).get("videos", []),
        }

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch, domain): domain for domain in domains}
        for future in as_completed(futures):
            domain, result = future.result()
            if result is not None:
                results[domain] = result

    return results

def to_scraped_performer(api_model: dict, domain: str) -> ScrapedPerformer:
    """
    Converts an API model dictionary to a ScrapedPerformer
    """
    performer: ScrapedPerformer = {}
    if slug := api_model.get("slug"):
        performer["url"] = f"https://{domain}.com/model/{slug}/"
    if description := api_model.get("description"):
        performer["details"] = clean_text(description)
    if title := api_model.get("title"):
        performer["name"] = title
    if model_information := api_model.get("modelInformation"):
        # this is a list of objects with "label" and "value" keys
        for info in model_information:
            label = info.get("label", "").lower()
            value = info.get("value", "")
            if label == "birthday":
                # value is in epoch seconds, convert to "YYYY-MM-DD"
                try:
                    birth_date = datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d")
                    performer["birthdate"] = birth_date
                except ValueError:
                    log.warning(f"Invalid birthdate format for performer {performer.get('name')}: {value}")
            elif label == "height":
                performer["height"] = value
            elif label == "weight":
                performer["weight"] = value
            elif label == "measurements":
                performer["measurements"] = value
            elif label == "hair color":
                performer["hair_color"] = value
            elif label == "eye color":
                performer["eye_color"] = value
            elif label == "ethnicity":
                performer["ethnicity"] = value
            elif label == "country of origin":
                performer["country"] = guess_nationality(value)
    if featured_image := api_model.get("featuredImage"):
        permalink = featured_image.get("permalink")
        if permalink:
            performer["image"] = f"https://content.{domain}.com{permalink}"
    return performer

def to_scraped_scene(api_scene: dict, domain: str) -> ScrapedScene:
    """
    Converts an API scene dictionary to a ScrapedScene
    """
    scene: ScrapedScene = {}
    if title := api_scene.get("title"):
        scene["title"] = title
    elif name := api_scene.get("name"):
        scene["title"] = name
    if slug := api_scene.get("slug"):
        scene["url"] = f"https://{domain}.com/video/{slug}/"
    if published_at := api_scene.get("publishedAt"):
        # date is epoch seconds, e.g. 1688108460, convert to YYYY-MM-DD
        published_at = datetime.fromtimestamp(published_at, timezone.utc).strftime("%Y-%m-%d")
        scene["date"] = published_at

    if description := api_scene.get("description"):
        scene["details"] = clean_text(description)
    scene["tags"] = []
    if categories := api_scene.get("categories"):
        scene["tags"].extend([ { "name": c.get("name") } for c in categories ])
    # add fixed tag for VR
    if "Virtual Reality" not in [tag["name"] for tag in scene["tags"]]:
        scene["tags"].append({ "name": "Virtual Reality" })
    if models := api_scene.get("models"):
        scene["performers"] = [to_scraped_performer(model, domain) for model in models]
    scene["studio"] = { "name": studio_name_for_domain(domain) }
    if poster := api_scene.get("poster"):
        if permalink := poster.get("permalink"):
            scene["image"] = f"https://content.{domain}.com{permalink}"
    return scene

def scene_search(query: str, sites: list[str]) -> list[ScrapedScene]:
    """
    Searches for scenes matching the query across the specified sites
    """
    api_scenes = api_search(query, sites)
    return [
        to_scraped_scene(scene, domain)
        for domain, data in api_scenes.items()
        for scene in data.get("videos", [])
    ]

def scene_from_fragment(fragment: dict[str, Any], sites: list[str]) -> ScrapedScene:
    """
    Scrapes a scene from a fragment across the specified sites
    """
    """
    This receives:
    - sites
    from the scraper YAML (array items)
    - url
    - title
    - code
    - details
    - director
    - date
    - urls
    from the result of the scene-by-name search
    """
    # if urls := fragment.get("urls"): # the first URL should be usable for a full search
    #     return scene_from_url(urls[0], sites, fragment, postprocess)
    # if code := fragment.get("code"): # if the (studio) code is present, search by clip_id
    #     return scene_from_id(code, sites, fragment, postprocess)
    # if title := fragment.get("title"): # if a title is present, search by text
    #     if len(scenes := scene_search(title, sites, fragment, postprocess)) > 0:
    #         return scenes[0] # best match is sorted at the top
    return {}

if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        # case "gallery-by-url", {"url": url, "extra": extra} if url and extra:
        #     sites = extra
        #     result = gallery_from_url(url, sites)
        # case "gallery-by-fragment", args:
        #     sites = args.pop("extra")
        #     result = gallery_from_fragment(args, sites)
        # case "scene-by-url", {"url": url, "extra": extra} if url and extra:
        #     sites = extra
        #     result = scene_from_url(url, sites)
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = scene_search(name, sites)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            sites = args.pop("extra")
            result = scene_from_fragment(args, sites)
        # case "performer-by-url", {"url": url}:
        #     result = performer_from_url(url)
        # case "performer-by-fragment", args:
        #     result = performer_from_fragment(args)
        # case "performer-by-name", {"name": name, "extra": extra} if name and extra:
        #     sites = extra
        #     result = performer_search(name, sites)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
