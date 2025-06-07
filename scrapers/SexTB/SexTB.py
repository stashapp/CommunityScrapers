"""
Stash scraper for SexTB
"""
import json
import re
import sys
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from datetime import datetime
import base64
from py_common import log
from py_common.types import  ScrapedScene
from py_common.util import scraper_args






def get_html(url):
    try:
        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Referer": "https://sextb.net/",
        })
        with urlopen(req) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.error(f"Request failed: {e}")
        return None

def fetch_image_base64(image_url: str, referer: str) -> str:
    try:
        req = Request(
            image_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Referer": referer,
            }
        )
        with urlopen(req) as response:
            content_type = response.headers.get("Content-Type", "image/jpeg")
            img_data = response.read()
            base64_data = base64.b64encode(img_data).decode("utf-8")
            return f"data:{content_type};base64,{base64_data}"
    except Exception as e:
        log.error(f"Image download failed: {e}")
        return None
    
def scene_from_fragment(fragment: dict[str, str]) -> ScrapedScene | list[dict]:
    # 1️⃣  build candidate search terms (remove None / "")
    terms = [fragment.get("code"), fragment.get("title")]
    terms = [t for t in terms if t]

    for term in terms:
        hits = scene_search(term, limit=10)
        if hits:
            if len(hits) == 1:
                return scene_from_url(hits[0]["url"])
            return hits

    # No search term worked — return empty list so Stash shows “no results”.
    return []

# ──────────────────────────────────────────────────────────────────────────────
#  query_fragment just forwards to scene_from_fragment; Stash usually sends a
#  "query" key that already combines pieces (e.g. "NPJS‑051 Nampa").
# ──────────────────────────────────────────────────────────────────────────────
def scene_from_query_fragment(fragment: dict[str, str]):
    """
    Called when the user highlights text / right‑clicks → Scrape With…
    Stash may include:
        • url   – direct scene link
        • query – free‑text the user highlighted
    """
    if fragment.get("url"):            # already handled in match block
        return scene_from_url(fragment["url"])

    # fall back to text search
    combined = {"title": fragment.get("query")}
    return scene_from_fragment(combined)




def scrape_poster_url(soup, url):
    """
    Return the best‐guess poster URL or None.
    """
    for img in soup.find_all("img"):
        cand = img.get("data-src") or img.get("src")
        if cand and re.compile(r"/poster/").search(cand):
            # make absolute if site uses relative paths
            return urljoin(url, cand)
    log.debug("poster image NOT found")
    return None

def _description_by_icon(soup: BeautifulSoup, icon_class: str):
    for div in soup.select("div.description"):
        i_tag = div.find("i")
        if i_tag and icon_class in i_tag.get("class", []):
            return div
    return None


 
def scene_search(term: str, limit: int = 20) -> list[dict[str, str]]:
    search_url = f"https://sextb.net/search/{term}"
    html       = get_html(search_url)
    if not html:
        return []

    soup    = BeautifulSoup(html, "html.parser")
    results = []

    for item in soup.select("div.tray-item")[:limit]:
        a_tag = item.find("a")
        if not a_tag:
            continue

        # -- title / scene code ------------------------------------------
        code_tag   = a_tag.select_one("div.tray-item-code")
        title_tag  = a_tag.select_one("div.tray-item-title")
        title      = (
            code_tag.get_text(strip=True) if code_tag
            else title_tag.get_text(strip=True) if title_tag
            else "Unknown Title"
        )

        # -- image -------------------------------------------------------
        img_tag = a_tag.find("img")
        poster  = img_tag.get("data-src") or img_tag.get("src") if img_tag else None

        # -- absolute scene URL -----------------------------------------
        url = urljoin(search_url, a_tag["href"])

        results.append({
            "title": title,     # e.g. 200GANA‑3203‑RM
            "url":   url,
            "image": poster,
        })

    log.debug(f"Found {len(results)} results for '{term}'")
    return results


    
def scene_from_url(url: str) -> ScrapedScene | None:
    html = get_html(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # ── title ────────────────────────────────────────────────────────────────

    # 1 ️⃣  new – “film‑info” block
    title = soup.select_one("div.film-info h1.film-info-title strong")
    if title:
        first_a = title.find("a")
        title   = first_a.get_text(strip=True) if first_a else title.get_text(" ", strip=True)

    # ── cover / poster image ────────────────────────────────────────────────
    image_url = scrape_poster_url(soup, url)
    if image_url:
        image_url = fetch_image_base64(image_url, referer=url)
    log.debug(f"IMAGE_URL: {image_url}")

    # ── release date (convert to ISO‑8601 if you like) ───────────────────────
    date_div  = _description_by_icon(soup, "fa-calendar")
    date_str  = None
    if date_div:
        strong = date_div.find("strong")
        if strong:
            # e.g.  "Jul. 02, 2024"  →  2024‑07‑02
            try:
                date_str = datetime.strptime(strong.get_text(strip=True), "%b. %d, %Y").date().isoformat()
            except ValueError:
                date_str = strong.get_text(strip=True)

    # ── studio ───────────────────────────────────────────────────────────────
    studio_div = _description_by_icon(soup, "fa-camera")
    studio     = None
    if studio_div:
        studio_link = studio_div.find("a")
        studio      = studio_link.get_text(strip=True) if studio_link else None

    # ── synopsis / description (may be hidden via CSS) ───────────────────────
    synopsis_tag = soup.select_one("span.full-text-desc")
    synopsis     = synopsis_tag.get_text(strip=True) if synopsis_tag else None

    # ── tags / genres ────────────────────────────────────────────────────────
    genre_div = _description_by_icon(soup, "fa-list")
    tags      = []
    if genre_div:
        tags = [a.get_text(strip=True) for a in genre_div.select("a")]
    cast_div   = _description_by_icon(soup, "fa-users")
    performers = [
        {"name": a.get_text(strip=True)}
        for a in cast_div.select("a")
    ] if cast_div else []

    # ── assemble ScrapedScene dict (fields required by Stash) ────────────────
    scene: ScrapedScene = {
        "title"   : title,
        "url"     : url,
        "date"    : date_str,            # None if not found
        "studio"  : {"name": studio} if studio else None,
        "details" : synopsis,
        "performers":performers,
        "tags"    : [{"name": t} for t in tags],
        "image"   : image_url,           # Stash calls this "cover" or "poster"
        "urls"    : [url],               # original page as a reference
    }

    # Any extra post‑processing you already have
    scene = postprocess_scene(scene)

    return scene
    




def postprocess_scene(scene: ScrapedScene) -> ScrapedScene:
    """
    Applies post-processing to the scene
    """

    return scene


if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url :
            result = scene_from_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name)
        case ("scene-by-fragment" | "scene-by-query-fragment"), fragment:
            if url := fragment.get("url"):
                result = scene_from_url(url)
            else:
                result = scene_from_query_fragment(fragment)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))