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
from AlgoliaAPI.AlgoliaAPI import sort_api_actors_by_match

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
SOCIAL_BASE_URLS = {
    "facebook": "https://www.facebook.com/people",
    "instagram": "https://www.instagram.com",
    "twitter": "https://x.com",
}
TAG_MAPPER = {
    "STEREO_180_LR": "180°",
    "MONO_360": "360°",
    "FISHEYE_STEREO_180_LR": "Fisheye",
    "Compilations": "Compilation",
}
MODEL_URL_REGEX = re.compile(r"https?://(?:www\.)?([a-zA-Z0-9\-]+)\.com/model/([a-zA-Z0-9\-]+)/?")

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

def generate_social_url(label: str, value: str) -> str:
    """
    Generates a full social media URL based on the label and value
    """
    base_url = SOCIAL_BASE_URLS.get(label.lower(), f"https://{label}.com")
    return f"{base_url}/{value}"

def to_scraped_performer(api_model: dict, domain: str) -> ScrapedPerformer:
    """
    Converts an API model dictionary to a ScrapedPerformer
    """
    digest = get_digest(domain)
    performer: ScrapedPerformer = {}
    if slug := api_model.get("slug"):
        performer["url"] = f"https://{domain}.com/model/{slug}/"
    if description := api_model.get("description"):
        performer["details"] = clean_text(description)
    if title := api_model.get("title"):
        performer["name"] = title.strip()
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
                if cm := re.search(r"(\d+)\s*cm", value.lower()):
                    # e.g. "5'4\" (or 162 cm)"
                    performer["height"] = cm.group(1)
                else:
                    # assume value is in cm, e.g. "162"
                    performer["height"] = value
            elif label == "weight":
                if kg:= re.search(r"(\d+)\s*kg", value.lower()):
                    # e.g. "97 lbs (or 44 kg)"
                    performer["weight"] = kg.group(1)
                else:
                    # assume value is in kg, e.g. "44"
                    performer["weight"] = value
            elif label == "measurements":
                # remove spaces and replace "/" with "-"
                performer["measurements"] = value.replace(" ", "").replace("/", "-")
            elif label == "hair color":
                performer["hair_color"] = value
            elif label == "eye color":
                performer["eye_color"] = value
            elif label == "ethnicity":
                performer["ethnicity"] = value
            elif label == "country of origin":
                performer["country"] = guess_nationality(value)
    if featured_image_permalink := api_model.get("featuredImage", {}).get("permalink"):
        if featured_image_permalink:
            performer["image"] = f"https://content.{domain}.com{featured_image_permalink}"
    if social_items := api_model.get("socialItems", []):
        social_urls = [
            generate_social_url(digest_item.get("label"), item.get("value"))
            for digest_item in digest.get("socialItems", [])
            for item in social_items
            if item.get("id") == digest_item.get("id")
        ]
        performer["urls"] = social_urls
    return performer

def to_scraped_scene(api_scene: dict, domain: str) -> ScrapedScene:
    """
    Converts an API scene dictionary to a ScrapedScene
    """
    log.debug(f"Converting API scene: {api_scene} from domain: {domain}")
    digest = get_digest(domain)
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
    # add categories as tags
    if categories := api_scene.get("categories"):
        scene["tags"].extend([ { "name": TAG_MAPPER.get(c.get("name"), c.get("name")) } for c in categories ])
    def _extend_tags_from_ids(ids, digest_key, name_fmt=lambda n: n, tag_mapper=None):
        if not ids:
            return []
        items = digest.get(digest_key, [])
        return [
            {"name": name_fmt(tag_mapper(item.get("name", "")) if tag_mapper else item.get("name", ""))}
            for id_ in ids
            for item in items
            if item.get("id") == id_
        ]

    if video_tech_bar := api_scene.get("videoTechBar", {}):
        scene["tags"].extend(_extend_tags_from_ids(
            video_tech_bar.get("resolutions", []), "videoResolutions"
        ))
        scene["tags"].extend(_extend_tags_from_ids(
            video_tech_bar.get("formats", []), "videoFormats",
            tag_mapper=lambda n: TAG_MAPPER.get(n, n)
        ))
        scene["tags"].extend(_extend_tags_from_ids(
            video_tech_bar.get("positions", []), "videoPositions"
        ))
        scene["tags"].extend(_extend_tags_from_ids(
            video_tech_bar.get("degrees", []), "videoDegrees",
            name_fmt=lambda n: f"{n}°"
        ))
        scene["tags"].extend(_extend_tags_from_ids(
            video_tech_bar.get("fps", []), "videoFps",
            name_fmt=lambda n: f"{n} FPS"
        ))
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

def scene_from_url(url: str) -> ScrapedScene:
    """
    Scrapes a scene from a URL at the corresponding site API
    """
    # extract domain and slug from url in one regex
    match = re.match(r"https?://(?:www\.)?([a-zA-Z0-9\-]+)\.com/video/([a-zA-Z0-9\-]+)/?", url)
    if not match:
        log.error(f"Invalid scene URL format: {url}")
        return {}
    domain = match.group(1)
    if domain not in CONFIG.keys():
        log.error(f"Domain {domain} not in sites: {CONFIG.keys()}")
        return {}
    slug = match.group(2)

    headers = headers_for_domain(domain)
    api_url = f"https://content.{domain}.com/api/content/v1/videos/{slug}"
    params = { "limit": 1 }
    log.debug(f"Fetching scene from {api_url} with params: {params} and headers: {headers}")
    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code != 200:
        log.error(f"Failed to fetch scene from {domain}: HTTP {response.status_code}")
        return {}
    api_scene = response.json().get("data", {}).get("item", {})
    return to_scraped_scene(api_scene, domain)

def performer_from_url(url: str) -> ScrapedPerformer:
    """
    Scrapes a performer from a URL at the corresponding site API
    """
    # extract domain and slug from url in one regex
    match = MODEL_URL_REGEX.match(url)
    if not match:
        log.error(f"Invalid performer URL format: {url}")
        return {}
    domain = match.group(1)
    if domain not in CONFIG.keys():
        log.error(f"Domain {domain} not in sites: {CONFIG.keys()}")
        return {}
    slug = match.group(2)

    headers = headers_for_domain(domain)
    api_url = f"https://content.{domain}.com/api/content/v1/models/{slug}"
    log.debug(f"Fetching performer from {api_url} with headers: {headers}")
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        log.error(f"Failed to fetch performer from {domain}: HTTP {response.status_code}")
        return {}
    api_model = response.json().get("data", {}).get("item", {})
    return to_scraped_performer(api_model, domain)

def performer_search(query: str, sites: list[str]) -> list[ScrapedPerformer]:
    """
    Searches for performers matching the query across the specified sites
    """
    api_search_results = api_search(query, sites)
    all_models = [
        {**model, "_domain": domain, "name": model.get("title", "")}
        for domain, data in api_search_results.items()
        for model in data.get("models", [])
    ]
    return [
        to_scraped_performer(model, model["_domain"])
        for model in sort_api_actors_by_match(all_models, {"name": query})
    ]

def performer_from_fragment(fragment: dict[str, Any], sites: list[str]) -> ScrapedPerformer:
    """
    Scrapes a performer from a fragment across the specified sites

    This receives:
    - sites
    from the scraper YAML (array items), and fragment containing:
    - url
    - name
    - disambiguation
    - gender
    - urls
    - twitter
    - instagram
    - birthdate
    - ethnicity
    - country
    - eye_color
    - height
    - measurements
    - fake_tits
    - penis_length
    - circumcised
    - career_length
    - tattoos
    - piercings
    - aliases
    - details
    - death_date
    - hair_color
    - weight
    """
    # if there are any studio performer profile URLs, use the first match
    for _url in fragment.get("urls", []):
        if MODEL_URL_REGEX.match(_url):
            return performer_from_url(_url)
    # search by name
    if name := fragment.get("name"):
        performers = performer_search(name, sites)
        if len(performers) > 0:
            # return best match (the first one)
            return performers[0]
    return {}

def get_digest(site: str) -> dict | None:
    """
    Gets a site's set of lookup values
    
    :param site: The domain (without TLD)
    :type site: str
    :return: The "digest" of the site
    :rtype: dict | None
    """
    headers = headers_for_domain(site)
    api_url = f"https://content.{site}.com/api/content/v1/digest"
    log.debug(f"Searching {api_url} with headers: {headers}")
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        log.error(f"Failed to search {site}: HTTP {response.status_code}")
        return None
    _json = response.json()
    return _json.get("data", {}).get("digest", {})

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
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = scene_search(name, sites)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            sites = args.pop("extra")
            result = scene_from_fragment(args, sites)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            sites = args.pop("extra")
            result = performer_from_fragment(args, sites)
        case "performer-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = performer_search(name, sites)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
