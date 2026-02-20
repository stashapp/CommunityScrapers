import json
import re
import sys
import os
import time

scrapers_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, scrapers_dir)
sys.path.insert(0, os.path.join(scrapers_dir, "community"))
from py_common.deps import ensure_requirements
from py_common import log

ensure_requirements("requests", "bs4:beautifulsoup4")

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://twinktop.com"
SITEMAP_URL = "https://twinktop.com/sitemap.xml"
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code_cache.json")
CACHE_MAX_AGE = 7 * 24 * 3600  # Refresh cache weekly

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
}


# ---------------------------------------------------------------------------
# Code cache - maps scene codes (rfb0018) to page URLs
# ---------------------------------------------------------------------------

def load_cache():
    """Load the code-to-URL cache from disk."""
    if not os.path.isfile(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_cache(cache):
    """Save the code-to-URL cache to disk."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
    except IOError as e:
        log.error(f"Failed to save cache: {e}")


def cache_is_stale():
    """Check if cache file is older than CACHE_MAX_AGE."""
    if not os.path.isfile(CACHE_FILE):
        return True
    age = time.time() - os.path.getmtime(CACHE_FILE)
    return age > CACHE_MAX_AGE


def rebuild_cache():
    """Rebuild the cache by fetching the sitemap and scraping og:image from each page."""
    log.info("Rebuilding scene code cache from sitemap...")

    try:
        resp = requests.get(SITEMAP_URL, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            log.error(f"Sitemap returned HTTP {resp.status_code}")
            return {}
    except Exception as e:
        log.error(f"Failed to fetch sitemap: {e}")
        return {}

    urls = re.findall(r'<loc>(https://rawfuckboys\.com/videos/[^<]+)</loc>', resp.text)
    log.info(f"Found {len(urls)} video URLs in sitemap")

    cache = {}
    for url in urls:
        try:
            page_resp = requests.get(url, headers=HEADERS, timeout=15)
            if page_resp.status_code != 200:
                continue
            match = re.search(r'content/(ttp\d+)/', page_resp.text)
            if match:
                cache[match.group(1)] = url
        except Exception:
            continue

    log.info(f"Built cache with {len(cache)} entries")
    save_cache(cache)
    return cache


def get_cache():
    """Get the code cache, rebuilding if stale."""
    if cache_is_stale():
        cache = rebuild_cache()
        if cache:
            return cache
    return load_cache()


def lookup_code(code):
    """Look up a scene code in the cache, return URL or None."""
    cache = load_cache()
    url = cache.get(code)
    if url:
        return url

    # Code not found - maybe cache is outdated, try rebuilding
    if not cache_is_stale():
        log.info(f"Code {code} not in cache, forcing rebuild")
        cache = rebuild_cache()
        return cache.get(code)

    return None


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch_page(url):
    """Fetch a page and return BeautifulSoup object."""
    log.info(f"Fetching: {url}")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        log.error(f"HTTP {resp.status_code} fetching {url}")
        return None
    return BeautifulSoup(resp.text, "html.parser")


# ---------------------------------------------------------------------------
# Scene scraping
# ---------------------------------------------------------------------------

def scrape_scene(url):
    """Scrape a scene from a TwinkTop URL."""
    soup = fetch_page(url)
    if not soup:
        return {}

    result = {"url": url}

    # Title from og:title - "Scott & Logan - Chapter 1 | Raw Fuck Boys"
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = re.sub(r'\s*\|\s*Raw Fuck Boys\s*$', '', og_title["content"]).strip()
        if title:
            result["title"] = title

    # Description from og:description
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        result["details"] = og_desc["content"].strip()

    # Cover image from video poster
    video = soup.find("video")
    if video and video.get("poster"):
        result["image"] = video["poster"]

    # Scene code from og:image
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        code_match = re.search(r'content/(ttp\d+)/', og_image["content"])
        if code_match:
            result["code"] = code_match.group(1)

    # Studio
    result["studio"] = {"name": "Twink Top"}

    # Performers from modelProfile divs (each performer has their own)
    performers = []
    for profile in soup.find_all("div", class_="modelProfile"):
        name_tag = None
        for h2 in profile.find_all("h2"):
            text = h2.get_text(strip=True)
            if text and text != "TALENT":
                name_tag = text
                break

        link = profile.find("a", href=re.compile(r"/models/"))
        href = link["href"] if link else ""
        if href and not href.startswith("http"):
            href = BASE_URL + href

        # TwinkTop uses src directly, not data-src (no lazy loading)
        img = profile.find("img", src=True)
        img_url = ""
        if img and img.get("src"):
            # Skip button images (seeprofile.svg, etc.)
            src = img["src"]
            if "contentthumbs" in src:
                img_url = src

        if name_tag:
            # Normalize all-caps names to title case
            normalized_name = name_tag.title() if name_tag.isupper() else name_tag
            perf = {"name": normalized_name, "gender": "Male"}
            if href:
                perf["url"] = href
            if img_url:
                perf["image"] = img_url
                perf["images"] = [img_url]
            performers.append(perf)

    if performers:
        result["performers"] = performers

    return result


# ---------------------------------------------------------------------------
# Performer scraping
# ---------------------------------------------------------------------------

def scrape_performer(url):
    """Scrape a performer from a TwinkTop model URL."""
    soup = fetch_page(url)
    if not soup:
        return {}

    result = {"url": url, "gender": "Male"}

    # Name from first non-generic h2
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True)
        if text and text not in ("TALENT", "VIDEOS", "PHOTOS", "Explore", "Get Help",
                                  "Join Us", "Newsletter"):
            # Strip "Talent" suffix if present (e.g., "Logan CarterTalent")
            text = re.sub(r'Talent$', '', text).strip()
            if text:
                # Normalize all-caps names to title case
                result["name"] = text.title() if text.isupper() else text
                break

    # Image - TwinkTop uses src directly (not lazy-loaded)
    for section in soup.find_all("div", class_="modelProfile"):
        img = section.find("img", src=True)
        if img and img.get("src") and "contentthumbs" in img["src"]:
            result["image"] = img["src"]
            result["images"] = [img["src"]]
            break

    log.info(f"Scraped performer: {result.get('name', 'unknown')}")
    return result


# ---------------------------------------------------------------------------
# Scene code extraction from filenames
# ---------------------------------------------------------------------------

def extract_scene_code(text):
    """Extract a TwinkTop scene code (e.g. ttp0004) from a filename or string."""
    m = re.search(r'(?i)(?:^|[_\-\s])(ttp\d{3,5})(?:$|[_\-\s.])', text)
    if m:
        return m.group(1).lower()
    return None


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

    # If scene has a RawFuckBoys URL, scrape it
    scene_url = fragment.get("url", "")
    if scene_url and "twinktop.com/videos/" in scene_url:
        result = scrape_scene(scene_url)
        print(json.dumps(result))
        return

    # Try to extract a scene code from filename or title
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
        log.info(f"No TwinkTop scene code found in '{source}'")
        print(json.dumps({}))
        return

    log.info(f"Extracted code '{code}' from '{source}'")
    url = lookup_code(code)
    if not url:
        log.info(f"Code '{code}' not found in cache")
        print(json.dumps({}))
        return

    log.info(f"Resolved {code} -> {url}")
    result = scrape_scene(url)
    print(json.dumps(result))


def scene_by_name():
    """Search scenes by title using the sitemap and cache."""
    fragment = json.loads(sys.stdin.read())
    name = fragment.get("name", "")
    if not name:
        log.error("No search query provided")
        print(json.dumps([]))
        return

    log.info(f"Searching for scene: {name}")

    # Fetch sitemap and search URLs by slug matching
    try:
        resp = requests.get(SITEMAP_URL, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            log.error(f"Sitemap returned HTTP {resp.status_code}")
            print(json.dumps([]))
            return

        urls = re.findall(r'<loc>(https://twinktop\.com/videos/[^<]+)</loc>', resp.text)

        # Convert search query to slug-like terms for matching
        terms = re.sub(r'[^a-z0-9\s]', '', name.lower()).split()
        matches = []
        for url in urls:
            slug = url.split("/")[-1].replace(".html", "")
            if all(t in slug for t in terms):
                matches.append(url)

        results = []
        for url in matches[:10]:
            result = scrape_scene(url)
            if result:
                results.append(result)

        log.info(f"Found {len(results)} scene(s) matching '{name}'")
        print(json.dumps(results))

    except Exception as e:
        log.error(f"Search error: {e}")
        print(json.dumps([]))


def scene_by_query_fragment():
    """Handle sceneByQueryFragment - scrape by URL or match by code/title."""
    fragment = json.loads(sys.stdin.read())

    scene_url = fragment.get("url", "")
    if scene_url and "twinktop.com/videos/" in scene_url:
        result = scrape_scene(scene_url)
        print(json.dumps(result))
        return

    # Try code from title
    title = fragment.get("title", "")
    if title:
        code = extract_scene_code(title)
        if code:
            url = lookup_code(code)
            if url:
                result = scrape_scene(url)
                print(json.dumps(result))
                return

    print(json.dumps({}))


def performer_by_url():
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url", "")
    if not url:
        log.error("No URL provided")
        print(json.dumps({}))
        return
    result = scrape_performer(url)
    print(json.dumps(result))


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
    elif mode == "rebuildCache":
        cache = rebuild_cache()
        print(f"Cache rebuilt with {len(cache)} entries")
    else:
        log.error(f"Unknown mode: {mode}")
        print(json.dumps({}))
