import json
import re
import sys
import os

scrapers_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, scrapers_dir)
sys.path.insert(0, os.path.join(scrapers_dir, "community"))
from py_common.deps import ensure_requirements
from py_common import log

ensure_requirements("requests")

import requests

BASE_URL = "https://www.sayuncle.com"
SEARCH_URL = "https://tours-store.psmcdn.net/sau_network/_search"


def fetch_initial_state(url):
    """Fetch a SayUncle page and extract the __INITIAL_STATE__ JSON."""
    log.info(f"Fetching: {url}")
    resp = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    })
    if resp.status_code != 200:
        log.error(f"HTTP {resp.status_code} fetching {url}")
        return None

    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});\s*\n', resp.text, re.DOTALL)
    if not match:
        log.error("Could not find __INITIAL_STATE__ in page")
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse __INITIAL_STATE__ JSON: {e}")
        return None


def strip_html(text):
    """Remove HTML tags from a string."""
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text).strip()


# ---------------------------------------------------------------------------
# Scene scraping
# ---------------------------------------------------------------------------

def parse_scene(scene, url=None):
    """Parse a scene JSON object (from page or API) into Stash format."""
    result = {}

    if url:
        result["url"] = url
    elif scene.get("id"):
        result["url"] = f"{BASE_URL}/movies/{scene['id']}"

    # Title
    title = scene.get("videoTitle") or scene.get("title")
    if title:
        result["title"] = title

    # Description
    if scene.get("description"):
        result["details"] = scene["description"]

    # Date
    if scene.get("publishedDate"):
        result["date"] = scene["publishedDate"][:10]

    # Cover image
    if scene.get("img"):
        result["image"] = scene["img"]

    # Studio (sub-site within SayUncle network)
    site = scene.get("site", {})
    if site.get("name"):
        result["studio"] = {"name": site["name"]}

    # Code - extract from image URL (e.g. fdk0487 from .../fdk/fdk0487/...)
    if scene.get("img"):
        code_match = re.search(r'/([a-z]{2,4}\d{3,5})/', scene["img"])
        if code_match:
            result["code"] = code_match.group(1)

    # Performers - return full details so they auto-populate on creation
    models = scene.get("models", [])
    if models:
        performers = []
        for model in models:
            perf = parse_performer(model)
            if perf.get("name"):
                performers.append(perf)
        if performers:
            result["performers"] = performers

    # Tags
    tags = scene.get("tags", [])
    if tags:
        result["tags"] = [{"name": t} for t in tags]

    return result


def scrape_scene(url):
    """Scrape a scene from a SayUncle URL."""
    slug = url.rstrip("/").split("/")[-1]
    if not slug:
        log.error("Could not extract slug from URL")
        return {}

    state = fetch_initial_state(url)
    if not state:
        return {}

    videos = state.get("content", {}).get("videosContent", {})
    scene = videos.get(slug)
    if not scene:
        log.error(f"Scene '{slug}' not found in page data")
        return {}

    return parse_scene(scene, url)


# SayUncle network site code prefixes
SITE_PREFIXES = [
    "fdk", "mbz", "brc", "yps", "lle", "bgz", "yfr", "dcp", "bmg",
    "shb", "slb", "twk", "bac", "dct", "byh", "suc", "mtd", "sas",
    "tdk", "vgp", "pig", "drs", "rub", "suf", "fut", "ano", "bvs",
    "sco", "eur",
]

# Quality suffixes to strip from filenames
QUALITY_SUFFIXES = [
    "_3g", "_iphone", "_mobile", "_sd", "_hd",
    "_720p", "_1080p", "_4k", "_FULLHD", "_full",
    "_high", "_medium", "_low",
    "_720", "_1080", "_2160",
]


def extract_scene_code(text):
    """Extract a SayUncle scene code (e.g. brc0199) from a filename or string."""
    # Match known prefix + digits pattern (use [_\-\s] or start as boundary since \b doesn't work across underscores)
    prefixes = "|".join(SITE_PREFIXES)
    m = re.search(rf'(?i)(?:^|[_\-\s])({prefixes})(\d{{3,5}})(?:$|[_\-\s.])', text)
    if m:
        return m.group(1).lower() + m.group(2)
    return None


def search_scene_by_code(code):
    """Search for a scene by its code via the Elasticsearch API."""
    log.info(f"Searching for scene by code: {code}")
    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"_doc_type": "tour_movie"}},
                    {"match_phrase": {"img": code}}
                ]
            }
        },
        "size": 1
    }

    try:
        resp = requests.post(SEARCH_URL, json=query, headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        })
        if resp.status_code != 200:
            log.error(f"Search API returned HTTP {resp.status_code}")
            return {}

        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        if not hits:
            log.info(f"No scene found for code '{code}'")
            return {}

        scene = hits[0].get("_source", {})
        log.info(f"Found scene: {scene.get('title', 'unknown')}")
        return parse_scene(scene)

    except Exception as e:
        log.error(f"Search API error: {e}")
        return {}


# ---------------------------------------------------------------------------
# Performer scraping
# ---------------------------------------------------------------------------

def parse_performer(model):
    """Convert a SayUncle model JSON object to a Stash performer dict."""
    result = {}

    if model.get("name"):
        result["name"] = model["name"]

    if model.get("id"):
        result["url"] = f"{BASE_URL}/models/{model['id']}"

    # Profile image (include both singular and array for Stash compatibility)
    if model.get("img"):
        result["image"] = model["img"]
        result["images"] = [model["img"]]

    # Gender
    if model.get("gender"):
        g = model["gender"].lower()
        if g == "male":
            result["gender"] = "Male"
        elif g == "female":
            result["gender"] = "Female"
        elif g in ("trans", "transgender"):
            result["gender"] = "Transgender Male"

    # Ethnicity
    if model.get("ethnicity"):
        result["ethnicity"] = model["ethnicity"]

    # Hair color
    if model.get("hairColor"):
        result["hair_color"] = model["hairColor"]

    # Bio text
    bio_text = model.get("modelBio") or model.get("seo", {}).get("description", "")
    if bio_text:
        result["details"] = strip_html(bio_text)

    # Structured bio fields
    bio = model.get("bio", {})
    if bio:
        # Height (feet/inches to cm)
        if bio.get("heightFeet") is not None and bio.get("heightInches") is not None:
            try:
                inches = int(bio["heightFeet"]) * 12 + int(bio["heightInches"])
                result["height"] = str(round(inches * 2.54))
            except (ValueError, TypeError):
                pass

        # Weight (lbs to kg)
        if bio.get("weight") is not None:
            try:
                result["weight"] = str(round(float(bio["weight"]) * 0.453592))
            except (ValueError, TypeError):
                pass

        # Birthdate
        if bio.get("birthdate"):
            result["birthdate"] = bio["birthdate"][:10]

    return result


def scrape_performer(url):
    """Scrape a performer from a SayUncle model URL."""
    slug = url.rstrip("/").split("/")[-1]
    if not slug:
        log.error("Could not extract slug from URL")
        return {}

    state = fetch_initial_state(url)
    if not state:
        return {}

    models = state.get("content", {}).get("modelsContent", {})
    model = models.get(slug)
    if not model:
        log.error(f"Model '{slug}' not found in page data")
        return {}

    result = parse_performer(model)
    result["url"] = url
    log.info(f"Scraped performer: {result.get('name', 'unknown')}")
    return result


def search_performers(name):
    """Search for performers by name via the Elasticsearch API."""
    log.info(f"Searching for performer: {name}")
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"name": name}},
                    {"term": {"_doc_type": "tour_model"}}
                ]
            }
        },
        "size": 10
    }

    try:
        resp = requests.post(SEARCH_URL, json=query, headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        })
        if resp.status_code != 200:
            log.error(f"Search API returned HTTP {resp.status_code}")
            return []

        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        results = []
        for hit in hits:
            model = hit.get("_source", {})
            perf = parse_performer(model)
            if perf.get("name"):
                results.append(perf)

        log.info(f"Found {len(results)} performer(s) matching '{name}'")
        return results

    except Exception as e:
        log.error(f"Search API error: {e}")
        return []


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def scene_by_url():
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url", "")
    if not url:
        log.error("No URL provided")
        print(json.dumps({}))
        return
    result = scrape_scene(url)
    print(json.dumps(result))


def scene_by_fragment():
    fragment = json.loads(sys.stdin.read())

    # If scene already has a SayUncle URL, use that
    scene_url = fragment.get("url", "")
    if scene_url and "sayuncle.com/movies/" in scene_url:
        log.info(f"Using existing URL: {scene_url}")
        result = scrape_scene(scene_url)
        print(json.dumps(result))
        return

    # Try to extract a scene code from the filename
    file_info = fragment.get("file")
    filename = ""
    if isinstance(file_info, dict):
        filename = file_info.get("path", "")

    source = os.path.basename(filename) if filename else fragment.get("title", "")
    if not source:
        log.info("No URL, filename, or title to scrape from")
        print(json.dumps({}))
        return

    code = extract_scene_code(source)
    if not code:
        log.info(f"No SayUncle scene code found in '{source}'")
        print(json.dumps({}))
        return

    log.info(f"Extracted code '{code}' from '{source}'")
    result = search_scene_by_code(code)
    print(json.dumps(result))


def scene_by_name():
    fragment = json.loads(sys.stdin.read())
    name = fragment.get("name", "")
    if not name:
        log.error("No search query provided")
        print(json.dumps([]))
        return

    log.info(f"Searching for scene: {name}")
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"title": name}},
                    {"term": {"_doc_type": "tour_movie"}}
                ]
            }
        },
        "size": 20
    }

    try:
        resp = requests.post(SEARCH_URL, json=query, headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        })
        if resp.status_code != 200:
            log.error(f"Search API returned HTTP {resp.status_code}")
            print(json.dumps([]))
            return

        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        results = []
        for hit in hits:
            scene = hit.get("_source", {})
            results.append(parse_scene(scene))

        log.info(f"Found {len(results)} scene(s) matching '{name}'")
        print(json.dumps(results))

    except Exception as e:
        log.error(f"Search error: {e}")
        print(json.dumps([]))


def performer_by_url():
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url", "")
    if not url:
        log.error("No URL provided")
        print(json.dumps({}))
        return
    result = scrape_performer(url)
    print(json.dumps(result))


def performer_by_name():
    fragment = json.loads(sys.stdin.read())
    name = fragment.get("name", "")
    if not name:
        log.error("No name provided")
        print(json.dumps([]))
        return
    results = search_performers(name)
    print(json.dumps(results))


def scene_by_query_fragment():
    """Handle sceneByQueryFragment - same logic as sceneByFragment."""
    fragment = json.loads(sys.stdin.read())

    # If scene has a SayUncle URL, scrape it
    scene_url = fragment.get("url", "")
    if scene_url and "sayuncle.com/movies/" in scene_url:
        result = scrape_scene(scene_url)
        print(json.dumps(result))
        return

    # Try to extract a scene code from title or filename
    title = fragment.get("title", "")
    if title:
        code = extract_scene_code(title)
        if code:
            result = search_scene_by_code(code)
            print(json.dumps(result))
            return

    # No match
    print(json.dumps({}))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "sceneByURL":
        scene_by_url()
    elif mode == "sceneByFragment":
        scene_by_fragment()
    elif mode == "sceneByName":
        scene_by_name()
    elif mode == "sceneByQueryFragment":
        scene_by_query_fragment()
    elif mode == "performerByURL":
        performer_by_url()
    elif mode == "performerByName":
        performer_by_name()
    else:
        log.error(f"Unknown mode: {mode}")
        print(json.dumps({}))
