from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
import re
import sys
from typing import Any

from py_common.deps import ensure_requirements
ensure_requirements("bs4:beautifulsoup4", "requests")
import py_common.log as log
from py_common.types import ScrapedGallery, ScrapedGroup, ScrapedPerformer, ScrapedScene
from py_common.util import guess_nationality, scraper_args

import requests
from bs4 import BeautifulSoup as bs
from AlgoliaAPI.AlgoliaAPI import sort_api_actors_by_match, sort_api_scenes_by_match

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
MODEL_URL_REGEX = re.compile(r"https?://(?:www\.)?([a-zA-Z0-9\-]+)\.com/(?:model|pornstars)/([a-zA-Z0-9\-]+)/?")
DEZYRED_GAME_URL_REGEX = re.compile(r"https?://(?:www\.)?dezyred\.com/games/([a-zA-Z0-9\-]+)/?")

# simple caches
DIGEST_CACHE: dict[str, dict] = {}
SCRAPED_SCENES_FILE_CACHE = "scraped_scenes_cache.json"

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
        "accept": "application/json",
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

def dezyred_api_scene_search(query: str) -> dict[str, dict[list[dict]]]:
    """
    Searches the Dezyred API for scenes matching the query
    """
    results: dict[str, dict[list[dict]]] = {}
    domains = ["dezyred"]

    def fetch(domain):
        headers = headers_for_domain(domain)
        api_url = f"https://{domain}.com/api/games"
        log.debug(f"Searching {api_url} with headers: {headers}")
        response = requests.get(api_url, headers=headers)
        if response.status_code != 200:
            log.error(f"Failed to search {domain}: HTTP {response.status_code}")
            return domain, None
        _json = response.json()
        # _json is a list of games, each game has a list of scenes
        scenes_count = sum(len(game.get("scenes", [])) for game in _json)
        log.debug(f"Found {len(_json)} games and {scenes_count} scenes on {domain}")
        return domain, _json

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch, domain): domain for domain in domains}
        for future in as_completed(futures):
            domain, result = future.result()
            if result is not None:
                # a result is a list of games, each with a list of scene dicts
                # we need to flatten this into a list of scenes where the
                # query matches the scene name or the game title
                scenes = []
                for game in result:
                    game_title = game.get("title", "").lower()
                    for scene in game.get("scenes", []):
                        scene_name = scene.get("name", "").lower()
                        if query.lower() in scene_name or query.lower() in game_title:
                            scenes.append({**scene, "_game": game, "title": scene.get("name", "")})
                results[domain] = scenes
    log.debug(f"Dezyred search found {len(results.get('dezyred', []))} matching scenes for query '{query}'")
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
    if performer.get("url"):
        performer["urls"] = [performer["url"]]
    else:
        performer["urls"] = []
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
        performer["urls"].extend(social_urls)
    return performer

def dezyred_to_scraped_performer(api_model: dict, domain: str) -> ScrapedPerformer:
    """
    Converts a Dezyred API model dictionary to a ScrapedPerformer
    """
    performer: ScrapedPerformer = {}
    if page_url := api_model.get("pageUrl"):
        performer["url"] = f"https://{domain}.com{page_url}"
    elif slug := api_model.get("slug"):
        performer["url"] = f"https://{domain}.com/pornstars/{slug}"
    if performer.get("url"):
        performer["urls"] = [performer["url"]]
    else:
        performer["urls"] = []
    if description := api_model.get("description"):
        performer["details"] = clean_text(description)
    if first_name := api_model.get("firstName"):
        if last_name := api_model.get("lastName"):
            performer["name"] = f"{first_name.strip()} {last_name.strip()}"
        else:
            performer["name"] = first_name.strip()
    if about := api_model.get("about"):
        if bio_stats := about.get("bioStats"):
            # this is a list of objects with "label" and "value" keys
            for info in bio_stats:
                name = info.get("name", "").lower()
                value = info.get("value", "")
                if name == "height":
                    if cm := re.search(r"(\d+)\s*cm", value.lower()):
                        # e.g. "5'4\" (or 162 cm)"
                        performer["height"] = cm.group(1)
                    else:
                        # assume value is in cm, e.g. "162"
                        performer["height"] = value
                elif name == "weight":
                    if kg:= re.search(r"(\d+)\s*kg", value.lower()):
                        # e.g. "97 lbs (or 44 kg)"
                        performer["weight"] = kg.group(1)
                    else:
                        # assume value is in kg, e.g. "44"
                        performer["weight"] = value
                elif name == "measurements":
                    # remove spaces and replace "/" with "-"
                    performer["measurements"] = value.replace(" ", "").replace("/", "-")
                elif name == "hair color":
                    performer["hair_color"] = value
                elif name == "eye color":
                    performer["eye_color"] = value
                elif name == "ethnicity":
                    performer["ethnicity"] = value
                elif name == "country of origin":
                    performer["country"] = guess_nationality(value)
                elif name == "place of birth" and "country" not in performer:
                    performer["country"] = guess_nationality(value)
        if biography_annotation := about.get("biography", {}).get("annotation"):
            # biography has full and annotation, the full is mostly VR blurb
            performer["details"] = clean_text(biography_annotation)
        if birth_date := about.get("birthDate"):
            # value is ISO date, e.g. "1990-05-15" or "1985-03-03 12:00:00"
            # just get first 10 characters
            performer["birthdate"] = birth_date[:10]
        if photo := about.get("photo"):
            performer["image"] = photo
    if socials := api_model.get("socials", []):
        social_urls = [ s["url"] for s in socials if s["url"] ]
        performer["urls"].extend(social_urls)
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

def dezyred_to_scraped_scene(api_scene: dict, domain: str) -> ScrapedScene:
    """
    Converts an Dezyred API scene dictionary to a ScrapedScene
    """
    log.debug(f"Converting Dezyred API scene: {api_scene} from domain: {domain}")
    scene: ScrapedScene = {}
    if name := api_scene.get("name"):
        scene["title"] = name
    scene["studio"] = { "name": studio_name_for_domain(domain) }
    if image := api_scene.get("image"):
        scene["image"] = image
    # models is a list of model IDs, we need to fetch each model
    # if models := api_scene.get("models"):
    #     scene["performers"] = [to_scraped_performer(model, domain) for model in models]
    # there is not much information for a scene, so we can get it from the _game
    # which is the parent of the scene
    if game := api_scene.get("_game", {}):
        if game_page_url := game.get("pageUrl"):
            scene["url"] = f"https://{domain}.com{game_page_url}"
        if game_created_at := game.get("createdAt"):
            # date is ISO, e.g. "2023-06-30T12:34:56Z", get first 10 characters
            scene["date"] = game_created_at[:10]
        if description := game.get("description"):
            scene["details"] = clean_text(description)

        scene["tags"] = []
        # add categories as tags
        if categories := game.get("categories"):
            scene["tags"].extend([ { "name": TAG_MAPPER.get(c.get("title"), c.get("title")) } for c in categories ])
        # add fixed tag for VR
        if "Virtual Reality" not in [tag["name"] for tag in scene["tags"]]:
            scene["tags"].append({ "name": "Virtual Reality" })
    return scene

def scene_search(query: str, sites: list[str], fragment: dict[str, Any] | None = None) -> list[ScrapedScene]:
    """
    Searches for scenes matching the query across the specified sites
    """
    api_scenes = api_search(query, [ s for s in sites if s != "dezyred" ])
    all_scenes = [
        {**scene, "_domain": domain}
        for domain, data in api_scenes.items()
        for scene in data.get("videos", [])
    ]
    # log the number of scenes found per domain
    domain_counts = {}
    for scene in all_scenes:
        domain = scene["_domain"]
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    log.debug(f"Number of scenes found per domain: {domain_counts}")
    scraped_scenes = [
        to_scraped_scene(scene, scene["_domain"])
        for scene in sort_api_scenes_by_match(all_scenes, fragment if fragment is not None else {"title": query})[:40]  # limit to first 40 best-matching scenes
    ]
    if "dezyred" in sites:
        dezyred_api_scenes = dezyred_api_scene_search(query)
        dezyred_all_scenes = [
            {**scene, "_domain": "dezyred"}
            for scene in dezyred_api_scenes.get("dezyred", [])
        ]
        log.debug(f"Number of Dezyred scenes found: {len(dezyred_all_scenes)}")
        dezyred_scraped_scenes = [
            dezyred_to_scraped_scene(scene, scene["_domain"])
            for scene in dezyred_all_scenes
        ]
        scraped_scenes.extend(dezyred_scraped_scenes)
    # write scraped_scenes as JSON to file cache
    with open(SCRAPED_SCENES_FILE_CACHE, "w", encoding="utf-8") as f:
        f.write(json.dumps(scraped_scenes, ensure_ascii=False, indent=2))
        f.write("\n")
    return scraped_scenes

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
    # attempt to get the scene from the cache first
    if os.path.exists(SCRAPED_SCENES_FILE_CACHE):
        with open(SCRAPED_SCENES_FILE_CACHE, "r", encoding="utf-8") as f:
            try:
                scraped_scenes_cache = json.load(f)
            except json.JSONDecodeError:
                log.error(f"Failed to decode JSON from cache file: {SCRAPED_SCENES_FILE_CACHE}")
                scraped_scenes_cache = []
        for cached_scene in scraped_scenes_cache:
            log.debug(f"Checking cached scene: {cached_scene.get('title')}")
            if (
                fragment.get("url") and cached_scene.get("url") == fragment.get("url")
                and cached_scene.get("title", "").lower() == fragment.get("title", "").lower()
            ):
                log.debug(f"Found scene in cache for URL: {fragment.get('url')} and title: {fragment.get('title')}")
                return cached_scene
    if urls := fragment.get("urls"): # the first URL should be usable for a full search
        return scene_from_url(urls[0])
    if title := fragment.get("title"): # if a title is present, search by text
        if match := re.match(r"^(vrbangers|vrbgay|vrbtrans|vrconk)_(.+)_(?:oculus|\dk)_.+$", title.strip(), re.IGNORECASE):
            domain = match.group(1).lower()
            # convert the 2nd part to a slug (underscores to hyphens, lowercase)
            slug = match.group(2).replace("_", "-").lower()
            return scene_from_url(f"https://{domain}.com/video/{slug}/")
        if len(scenes := scene_search(title, sites, fragment)) > 0:
            return scenes[0] # best match is sorted at the top
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
    log.debug(f"Fetching scene from {api_url} with headers: {headers}")
    try:
        log.trace(f"Making request to URL: {api_url}")
        response = requests.get(api_url, headers=headers, timeout=10)
        log.trace(f"API response: {response.text}")
        if response.status_code != 200:
            log.error(f"Failed to fetch scene from {domain}: HTTP {response.status_code}")
            return {}
        api_scene = response.json().get("data", {}).get("item", {})
    except requests.RequestException as e:
        log.error(f"Request exception while fetching scene from {domain}: {e}")
        return {}
    except BaseException as e:
        log.error(f"Unexpected exception while fetching scene from {domain}: {e}")
        return {}
    log.debug(f"Fetched API scene: {api_scene}")
    return to_scraped_scene(api_scene, domain)

def gallery_from_url(url: str) -> ScrapedGallery:
    """
    Scrapes a gallery from a URL at the corresponding site API
    """
    # the "gallery" is just the scene, so scrape the scene and then convert to gallery
    scene = scene_from_url(url)
    if not scene:
        return {}
    gallery: ScrapedGallery = {}
    if title := scene.get("title"):
        gallery["title"] = title
    if url := scene.get("url"):
        gallery["url"] = url
    if date := scene.get("date"):
        gallery["date"] = date
    if details := scene.get("details"):
        gallery["details"] = details
    if tags := scene.get("tags"):
        gallery["tags"] = tags
    if performers := scene.get("performers"):
        gallery["performers"] = performers
    if studio := scene.get("studio"):
        gallery["studio"] = studio
    return gallery

def get_api_model(domain: str, api_url: str) -> dict[str, Any]:
    headers = headers_for_domain(domain)
    log.debug(f"Fetching model from {api_url} with headers: {headers}")
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        log.error(f"Failed to fetch model from {domain}: HTTP {response.status_code}")
        return {}
    response_json = response.json()
    data_item = response_json.get("data", {}).get("item", {})
    api_model = data_item if data_item else response_json
    return api_model

def performer_from_url(url: str) -> ScrapedPerformer:
    match = MODEL_URL_REGEX.match(url)
    if not match:
        log.error(f"Invalid performer URL format: {url}")
        return {}
    domain = match.group(1)
    if domain not in CONFIG.keys():
        log.error(f"Domain {domain} not in sites: {CONFIG.keys()}")
        return {}
    slug = match.group(2)
    if domain == "dezyred":
        api_url = f"https://{domain}.com/api/models/{slug}"
        return dezyred_to_scraped_performer(get_api_model(domain, api_url), domain)
    else:
        api_url = f"https://content.{domain}.com/api/content/v1/models/{slug}"
        return to_scraped_performer(get_api_model(domain, api_url), domain)

def dezyred_performer_from_id(model_id: str) -> ScrapedPerformer:
    domain = "dezyred"
    api_url = f"https://{domain}.com/api/models/{model_id}"
    return dezyred_to_scraped_performer(get_api_model(domain, api_url), domain)

def performer_search(query: str, sites: list[str]) -> list[ScrapedPerformer]:
    """
    Searches for performers matching the query across the specified sites
    """
    api_search_results = api_search(query, sites)
    all_models = [
        {**model, "_domain": domain, "name": model.get("title", "")}
        for domain, data in api_search_results.items()
        for model in data.get("models", [])[:10]    # limit to first 10 models per site
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
    if site in DIGEST_CACHE:
        return DIGEST_CACHE[site]
    headers = headers_for_domain(site)
    api_url = f"https://content.{site}.com/api/content/v1/digest"
    log.debug(f"Fetching {api_url} with headers: {headers}")
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        log.error(f"Failed to search {site}: HTTP {response.status_code}")
        return None
    digest = response.json().get("data", {}).get("digest", {})
    DIGEST_CACHE[site] = digest
    return digest

def to_scraped_group(api_group: dict, domain: str) -> ScrapedGroup:
    """
    Converts an API group dictionary to a ScrapedGroup
    """
    group: ScrapedGroup = {}
    group["studio"] = { "name": studio_name_for_domain(domain) }
    if title := api_group.get("title"):
        group["name"] = title
    if description := api_group.get("description"):
        group["synopsis"] = clean_text(description)
    if page_url := api_group.get("pageUrl"):
        group["url"] = f"https://{domain}.com{page_url}"
    if posters_list_item := api_group.get("posters", {}).get("listItem"):
        group["front_image"] = posters_list_item
    if categories := api_group.get("categories", []):
        group["tags"] = [ { "name": c.get("title") } for c in categories ]
    if created_at := api_group.get("createdAt"):
        # date is ISO date, e.g. "2023-06-15T12:34:56Z", just get first 10 characters
        group["date"] = created_at[:10]

    # performers are in "models" key, which is a list of model IDs
    # this is not a property of the group, but we can log them out for some
    # useful info for the associated scenes, as the scenes do not include
    # performer details
    if model_ids := api_group.get("models", []):
        # use futures to fetch all performers concurrently
        performers: list[ScrapedPerformer] = []
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(dezyred_performer_from_id, model_id): model_id
                for model_id in model_ids
            }
            for future in as_completed(futures):
                performer = future.result()
                if performer:
                    performers.append(performer)
        log.debug(f"Group performers: {[p.get('name') for p in performers]}")

    # the scene titles can be logged out
    if scenes := api_group.get("scenes", []):
        scene_titles = [ scene.get("name") for scene in scenes ]
        log.debug(f"Group scenes: {scene_titles}")
    
    return group

def group_from_url(url: str) -> ScrapedGroup:
    """
    Dezyred "games" are really groups of scenes
    
    :param url: URL of the "game", e.g. https://dezyred.com/games/white-iris/
    :type url: str
    :return: ScrapedGroup representing the game
    :rtype: ScrapedGroup
    """
    match = DEZYRED_GAME_URL_REGEX.match(url)
    if not match:
        log.error(f"Invalid group URL format: {url}")
        return {}
    slug = match.group(1)
    domain = "dezyred"
    headers = headers_for_domain(domain)
    api_url = f"https://{domain}.com/api/games/{slug}"
    log.debug(f"Fetching group from {api_url} with headers: {headers}")
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        log.error(f"Failed to fetch group from {domain}: HTTP {response.status_code}")
        return {}
    api_group = response.json()
    return to_scraped_group(api_group, domain)

if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url)
        # case "gallery-by-fragment", args:
        #     sites = args.pop("extra")
        #     result = gallery_from_fragment(args, sites)
        case "group-by-url", {"url": url} if url:
            result = group_from_url(url)
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
