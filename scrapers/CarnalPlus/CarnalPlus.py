import json
import re
import sys
import os

scrapers_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, scrapers_dir)
sys.path.insert(0, os.path.join(scrapers_dir, "community"))
from py_common.deps import ensure_requirements
from py_common import log

ensure_requirements("requests", "bs4:beautifulsoup4")

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://carnalplus.com"
SEARCH_URL = "https://carnalplus.com/process_searchAjax.php"

# Map logo alt text to proper studio names
STUDIO_NAMES = {
    "gaycest": "Gaycest",
    "funsizeboys": "Fun Size Boys",
    "scoutboys": "Scout Boys",
    "masonicboys": "Masonic Boys",
    "baptistboys": "Baptist Boys",
    "catholicboys": "Catholic Boys",
    "boyforsale": "Boy For Sale",
    "twinktop": "Twink Top",
    "twinks": "Twinks",
    "staghomme": "Stag Homme",
    "barebackplus": "Bareback Plus",
    "bangbangboys": "Bang Bang Boys",
    "carnaloriginals": "Carnal Originals",
    "americanmusclehunks": "American Muscle Hunks",
    "jalifstudio": "Jalif Studio",
    "nextdoorstudios": "Next Door Studios",
    "teensandtwinks": "Teens And Twinks",
}


def fetch_page(url):
    """Fetch a page and return BeautifulSoup object."""
    log.info(f"Fetching: {url}")
    resp = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    })
    if resp.status_code != 200:
        log.error(f"HTTP {resp.status_code} fetching {url}")
        return None
    return BeautifulSoup(resp.text, "html.parser")


def strip_html(text):
    """Remove HTML tags from a string."""
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text).strip()


def clean_title(raw_title):
    """Clean up a CarnalPlus title from the search API.
    API returns: ' troop time  | Chapter 9: Hands-On Scouting '
    We want:    'Hands-On Scouting - Troop Time - Chapter 9'
    """
    raw_title = raw_title.strip()
    if not raw_title:
        return ""

    # Format: "series_name | Chapter N: Scene Title" or just a plain title
    if "|" in raw_title:
        parts = raw_title.split("|", 1)
        series = parts[0].strip().title()
        chapter_and_title = parts[1].strip()
        # "Chapter 9: Hands-On Scouting" -> separate chapter and title
        ch_match = re.match(r'(Chapter\s+\d+):\s*(.*)', chapter_and_title, re.I)
        if ch_match:
            chapter = ch_match.group(1)
            title = ch_match.group(2).strip().title()
            return f"{title} - {series} - {chapter}"
        # "Vol. 1" or other format without chapter prefix
        vol_match = re.match(r'(Vol\.\s*\d+):\s*(.*)', chapter_and_title, re.I)
        if vol_match:
            vol = vol_match.group(1)
            title = vol_match.group(2).strip().title()
            return f"{title} - {series} {vol}"
        return f"{chapter_and_title.title()} - {series}"

    return raw_title.title()


# ---------------------------------------------------------------------------
# Scene scraping
# ---------------------------------------------------------------------------

def scrape_scene(url):
    """Scrape a scene from a CarnalPlus URL."""
    soup = fetch_page(url)
    if not soup:
        return {}

    result = {"url": url}

    # Title - use <title> tag which is well-formatted, e.g.:
    # "Hands-On Scouting - TROOP TIME - Chapter 9 | Carnal Plus"
    title_tag = soup.find("title")
    if title_tag:
        page_title = title_tag.get_text(strip=True)
        # Strip "| Carnal Plus" or "| Site Name" suffix
        page_title = re.sub(r'\s*\|\s*[^|]+$', '', page_title).strip()
        if page_title:
            result["title"] = page_title

    # Description
    desc_div = soup.find("div", class_="textDescription")
    if desc_div:
        paragraphs = desc_div.find_all("p")
        if paragraphs:
            text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            if text:
                result["details"] = text

    # Date - "February 14, 2026 | Full Length Video : 18min 34sec"
    date_div = soup.find("div", class_="releasedate")
    if date_div:
        date_text = date_div.get_text(strip=True)
        date_part = date_text.split("|")[0].strip()
        try:
            from datetime import datetime
            # Handle ordinal suffixes if present
            date_clean = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_part)
            dt = datetime.strptime(date_clean, "%B %d, %Y")
            result["date"] = dt.strftime("%Y-%m-%d")
        except ValueError:
            log.debug(f"Could not parse date: {date_part}")

    # Cover image from video poster
    video = soup.find("video")
    if video and video.get("poster"):
        result["image"] = video["poster"]

    # Studio - from the title-updates-logo section
    logo_div = soup.find("div", class_="title-updates-logo")
    if logo_div:
        img = logo_div.find("img")
        if img and img.get("alt"):
            # alt is like "logo gaycest"
            alt = img["alt"].replace("logo ", "").strip()
            studio_name = STUDIO_NAMES.get(alt, alt.title())
            result["studio"] = {"name": studio_name}

    # Performers - fetch full details so they auto-populate on creation
    models_div = soup.find("div", class_="update-models")
    if models_div:
        performers = []
        for a in models_div.find_all("a", href=True):
            if "/models/" in a["href"]:
                name = a.get_text(strip=True)
                href = a["href"]
                if not href.startswith("http"):
                    href = BASE_URL + href
                if name:
                    log.info(f"Fetching performer details: {name}")
                    perf = scrape_performer(href)
                    if not perf:
                        perf = {"name": name, "url": href}
                    performers.append(perf)
        if performers:
            result["performers"] = performers

    # Tags
    tag_elements = soup.find_all(class_="txt-tags")
    if tag_elements:
        tags = []
        for el in tag_elements:
            name = el.get_text(strip=True)
            if name:
                tags.append({"name": name})
        if tags:
            result["tags"] = tags

    return result


# ---------------------------------------------------------------------------
# Performer scraping
# ---------------------------------------------------------------------------

def scrape_performer(url):
    """Scrape a performer from a CarnalPlus model URL."""
    soup = fetch_page(url)
    if not soup:
        return {}

    result = {"url": url, "gender": "Male"}

    # Name
    h1 = soup.find("h1", class_="modelbio-title")
    if not h1:
        h1 = soup.find("h2", class_="modelbio-title")
    if h1:
        result["name"] = h1.get_text(strip=True).title()

    # Image
    thumb = soup.find("div", class_="control_thumb_model")
    if thumb:
        img = thumb.find("img")
        if img and img.get("src"):
            result["image"] = img["src"]
            result["images"] = [img["src"]]

    # Bio
    bio_div = soup.find("div", class_="modelExtraValue")
    if bio_div:
        text = bio_div.get_text(strip=True)
        if text:
            result["details"] = text

    log.info(f"Scraped performer: {result.get('name', 'unknown')}")
    return result


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


def performer_by_url():
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url", "")
    if not url:
        log.error("No URL provided")
        print(json.dumps({}))
        return
    result = scrape_performer(url)
    print(json.dumps(result))


def scene_by_name():
    fragment = json.loads(sys.stdin.read())
    name = fragment.get("name", "")
    if not name:
        log.error("No search query provided")
        print(json.dumps([]))
        return

    log.info(f"Searching for scene: {name}")
    try:
        resp = requests.post(SEARCH_URL, data={"input": name}, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Referer": "https://carnalplus.com/search",
        })
        if resp.status_code != 200:
            log.error(f"Search returned HTTP {resp.status_code}")
            print(json.dumps([]))
            return

        data = resp.json()
        results = []
        for item in data:
            scene_url = f"{BASE_URL}/videos/{item.get('SEOname', '')}.html"
            studio_key = item.get("sitename", "")
            studio_name = STUDIO_NAMES.get(studio_key, studio_key.title())

            result = {
                "title": clean_title(item.get("Title", "")),
                "url": scene_url,
                "image": item.get("movieplayer", ""),
                "studio": {"name": studio_name},
            }
            results.append(result)

        log.info(f"Found {len(results)} scene(s) matching '{name}'")
        print(json.dumps(results))

    except Exception as e:
        log.error(f"Search error: {e}")
        print(json.dumps([]))


def scene_by_query_fragment():
    """Handle sceneByQueryFragment - scrape by URL or search by title."""
    fragment = json.loads(sys.stdin.read())

    # If scene has a CarnalPlus URL, scrape it
    scene_url = fragment.get("url", "")
    if scene_url and "carnalplus.com/videos/" in scene_url:
        result = scrape_scene(scene_url)
        print(json.dumps(result))
        return

    # Try searching by title
    title = fragment.get("title", "")
    if title:
        try:
            resp = requests.post(SEARCH_URL, data={"input": title}, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
                "Referer": "https://carnalplus.com/search",
            })
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    item = data[0]
                    scene_url = f"{BASE_URL}/videos/{item.get('SEOname', '')}.html"
                    result = scrape_scene(scene_url)
                    print(json.dumps(result))
                    return
        except Exception as e:
            log.error(f"Search error: {e}")

    print(json.dumps({}))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "sceneByURL":
        scene_by_url()
    elif mode == "sceneByName":
        scene_by_name()
    elif mode == "sceneByQueryFragment":
        scene_by_query_fragment()
    elif mode == "performerByURL":
        performer_by_url()
    else:
        log.error(f"Unknown mode: {mode}")
        print(json.dumps({}))
