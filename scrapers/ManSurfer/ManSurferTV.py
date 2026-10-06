import json
import re
import sys

from bs4 import BeautifulSoup
import requests

from py_common.util import scraper_args
from py_common.types import ScrapedScene, ScrapedMovie
import py_common.log as log


BASE = "https://www.mansurfer.tv"
SEARCH_URL = (
    BASE
    + "/dispatcher/movieSearch?genreId=102&theaterId=35846"
    "&locale=en&max={max}&imageType=Small&isTextSearch=true&searchString={q}"
)

session = requests.Session()
session.cookies.set("ageGated", "true", domain="www.mansurfer.tv", path="/")
session.cookies.set("locale", "en", domain="www.mansurfer.tv", path="/")


def _get(url: str) -> BeautifulSoup:
    # Force locale=en in any mansurfer/aebn URL
    if "mansurfer.tv" in url or "aebn.com" in url:
        if "locale=" in url:
            url = re.sub(r"locale=\w+", "locale=en", url)
        elif "?" in url:
            url += "&locale=en"
        else:
            url += "?locale=en"
    res = session.get(url, timeout=15)
    return BeautifulSoup(res.text, "html.parser")


def _abs(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE + url
    return url


def _fix_canonical(url: str) -> str:
    """Convert AEBN canonical URLs to ManSurfer with locale=en."""
    m = re.search(r"movieId=(\d+)", url)
    if m:
        return (
            BASE
            + f"/dispatcher/movieDetail?genreId=102&theaterId=35846"
            f"&movieId={m.group(1)}&locale=en"
        )
    return url


# ---------------------------------------------------------------------------
# SEARCH
# ---------------------------------------------------------------------------
def search_scenes(query: str, max_results: int = 15) -> list[ScrapedScene]:
    url = SEARCH_URL.format(q=requests.utils.quote(query), max=max_results)
    soup = _get(url)
    results = []
    for container in soup.select("div.movieContainer, div[class*=movieContainer]"):
        a = container.select_one("a[title]")
        img = container.select_one("img")
        if not a:
            continue
        scene: ScrapedScene = {
            "title": a.get("title", "").strip(),
            "url": _abs(a.get("href", "")),
            "image": _abs(img["src"]) if img else "",
        }
        results.append(scene)
    return results


# ---------------------------------------------------------------------------
# MOVIE / GROUP from detail page
# ---------------------------------------------------------------------------
def movie_from_url(url: str) -> ScrapedMovie | None:
    soup = _get(url)
    movie: ScrapedMovie = {}

    # Name
    if h1 := soup.select_one("h1.md-movieTitle"):
        movie["name"] = h1.get_text(strip=True)

    # Director
    directors = soup.select("div.md-detailsDirector a")
    if directors:
        movie["director"] = ", ".join(d.get_text(strip=True) for d in directors)

    # Duration
    if rt := soup.select_one("span.runTime span"):
        mins = rt.get_text(strip=True)
        if mins.isdigit():
            movie["duration"] = f"{mins}:00"

    # Date
    if rel := soup.select_one("div.md-detailsRelease span.detailsLink"):
        raw = rel.get_text(strip=True)
        m = re.match(r"(\d{2})/(\d{4})", raw)
        if m:
            movie["date"] = f"{m.group(2)}-{m.group(1)}-01"

    # Studio (first link)
    if studio_a := soup.select_one("div.md-detailsStudio a"):
        movie["studio"] = {"name": studio_a.get_text(strip=True)}

    # Synopsis — try multiple sources
    synopsis = ""
    for div in soup.select("div.movieDetailDescriptionFull, div.movieDetailDescriptionOnly, div.movieDetailDescription"):
        for span in div.find_all("span"):
            if "detailsLabel" not in (span.get("class") or []):
                text = span.get_text(strip=True)
                if text and len(text) > len(synopsis):
                    synopsis = text
    if not synopsis:
        meta = soup.select_one("meta[name='description']")
        if meta:
            synopsis = meta.get("content", "").strip()
    if synopsis:
        movie["synopsis"] = synopsis

    # Front image (HD) — from the <a> wrapping #boxImage
    cover_a = soup.select_one("div#md-boxCover a[href]")
    if cover_a:
        href = _abs(cover_a.get("href", ""))
        if href:
            movie["front_image"] = href
            # Back image: _xlf → _xlb
            movie["back_image"] = href.replace("_xlf.", "_xlb.")

    # URL
    canonical = soup.select_one("link[rel='canonical']")
    if canonical:
        movie["url"] = _fix_canonical(canonical.get("href", ""))
    else:
        movie["url"] = url

    return movie


# ---------------------------------------------------------------------------
# Helpers for per-scene scraping
# ---------------------------------------------------------------------------
_SCENE_RE = re.compile(r"[,:\s]*\b(?:Scene|Cena)\s+(\d+)\s*$", re.IGNORECASE)


def _extract_scene_number(title: str) -> tuple[str, int | None]:
    """Return (base_title, scene_number) or (title, None) if no match."""
    m = _SCENE_RE.search(title)
    if m:
        base = title[: m.start()].strip()
        return base, int(m.group(1))
    return title, None


def _get_scene_block(soup: BeautifulSoup, scene_num: int) -> BeautifulSoup | None:
    """Find the extFunctSceneResult block for scene N (1-based)."""
    blocks = soup.select("div.extFunctSceneResult")
    if not blocks:
        return None

    # Strategy 1: match title text "...Scene N" in sceneResultHead .title
    for block in blocks:
        title_div = block.select_one("div.sceneResultHead div.title")
        if title_div:
            text = title_div.get_text(strip=True)
            # Match "Scene 3" at end of title
            m = re.search(r"\bScene\s+(\d+)\b", text, re.IGNORECASE)
            if m and int(m.group(1)) == scene_num:
                return block

    # Strategy 2: use 0-based index (scene_num 1 → index 0)
    idx = scene_num - 1
    if 0 <= idx < len(blocks):
        return blocks[idx]
    return None


def _scene_performers_from_block(block: BeautifulSoup) -> list[dict]:
    """Extract performers from a scene block (prefer expanded details)."""
    performers = []
    seen = set()

    # First try: expanded sceneDetailsTabRow → sceneStars
    detail_tab = block.select_one("div.sceneDetailsTabRow div.sceneStars")
    if detail_tab:
        for span in detail_tab.select("a span"):
            name = span.get_text(strip=True)
            if name and name not in seen:
                performers.append({"name": name})
                seen.add(name)

    # Fallback: limitedStars
    if not performers:
        limited = block.select_one("span.limitedStars span.detailsLink")
        if limited:
            for span in limited.select("a span"):
                name = span.get_text(strip=True)
                if name and name not in seen:
                    performers.append({"name": name})
                    seen.add(name)

    return performers


def _scene_tags_from_block(block: BeautifulSoup) -> list[dict]:
    """Extract sex acts as tags from a scene block's detail section."""
    tags = []
    seen = set()
    detail_tab = block.select_one("div.sceneDetailsTabRow")
    if not detail_tab:
        return tags
    # The first sceneDetails div with "Sex Acts" label
    for detail_div in detail_tab.select("div.sceneDetails"):
        label = detail_div.select_one("span.detailsLabel")
        if label and "Sex Acts" in label.get_text():
            for a in detail_div.select("span.detailsLink a"):
                name = a.get_text(strip=True)
                if name and name not in seen:
                    tags.append({"name": name})
                    seen.add(name)
            break
    return tags


def _scene_image_from_block(block: BeautifulSoup) -> str:
    """Get the first scene thumbnail as the scene image."""
    img = block.select_one("div.resultClipImages img.sceneThumbnail")
    if img:
        src = img.get("src") or img.get("data-img-src", "")
        if src:
            # Remove size constraint to get larger image (or keep as-is)
            return _abs(src)
    return ""


# ---------------------------------------------------------------------------
# SCENE from detail page (same page as movie, mapped to scene fields)
# ---------------------------------------------------------------------------
def scene_from_url(url: str, scene_num: int | None = None) -> ScrapedScene | None:
    soup = _get(url)
    scene: ScrapedScene = {}

    movie_title = ""
    if h1 := soup.select_one("h1.md-movieTitle"):
        movie_title = h1.get_text(strip=True)

    # If scene_num is set, we need per-scene data from the scene blocks
    scene_block = None
    if scene_num:
        scene_block = _get_scene_block(soup, scene_num)
        if scene_block:
            log.info(f"Found scene block for Scene {scene_num}")
        else:
            log.warning(f"Scene block {scene_num} not found, using movie-level data")

    # Title: "MovieTitle: Scene N" if per-scene, else movie title
    if scene_num and movie_title:
        scene["title"] = f"{movie_title}: Scene {scene_num}"
    elif movie_title:
        scene["title"] = movie_title

    # Director
    directors = soup.select("div.md-detailsDirector a")
    if directors:
        scene["director"] = ", ".join(d.get_text(strip=True) for d in directors)

    # Date
    if rel := soup.select_one("div.md-detailsRelease span.detailsLink"):
        raw = rel.get_text(strip=True)
        m = re.match(r"(\d{2})/(\d{4})", raw)
        if m:
            scene["date"] = f"{m.group(2)}-{m.group(1)}-01"

    # Studio
    if studio_a := soup.select_one("div.md-detailsStudio a"):
        scene["studio"] = {"name": studio_a.get_text(strip=True)}

    # Details (synopsis) — movie-level, always from the main description
    details = ""
    for div in soup.select("div.movieDetailDescriptionFull, div.movieDetailDescriptionOnly, div.movieDetailDescription"):
        for span in div.find_all("span"):
            if "detailsLabel" not in (span.get("class") or []):
                text = span.get_text(strip=True)
                if text and len(text) > len(details):
                    details = text
    if not details:
        meta = soup.select_one("meta[name='description']")
        if meta:
            details = meta.get("content", "").strip()
    if details:
        scene["details"] = details

    # Image: per-scene thumbnail or movie front cover
    if scene_block:
        img = _scene_image_from_block(scene_block)
        if img:
            scene["image"] = img
    if "image" not in scene:
        cover_a = soup.select_one("div#md-boxCover a[href]")
        if cover_a:
            scene["image"] = _abs(cover_a.get("href", ""))

    # Tags: per-scene sex acts if available, plus movie-level categories
    tags = []
    seen_tags = set()
    if scene_block:
        for t in _scene_tags_from_block(scene_block):
            if t["name"] not in seen_tags:
                tags.append(t)
                seen_tags.add(t["name"])
    # Always add movie-level categories
    for a in soup.select("div.md-detailsCategories a"):
        name = a.get_text(strip=True)
        if name and name not in seen_tags:
            tags.append({"name": name})
            seen_tags.add(name)
    if tags:
        scene["tags"] = tags

    # Performers: per-scene if available, else movie-level
    performers = []
    if scene_block:
        performers = _scene_performers_from_block(scene_block)
    if not performers:
        stars_full = soup.select_one("div.starsFull")
        if not stars_full:
            stars_full = soup.select_one("div.md-detailsStars")
        if stars_full:
            seen = set()
            for a in stars_full.select("a[href*='starDetail'] span"):
                name = a.get_text(strip=True)
                if name and name not in seen:
                    performers.append({"name": name})
                    seen.add(name)
    if performers:
        scene["performers"] = performers

    # Groups (link scene to movie/group) — always the movie
    if movie_title:
        canonical = soup.select_one("link[rel='canonical']")
        group_url = _fix_canonical(canonical.get("href", "")) if canonical else url
        scene["groups"] = [
            {"name": movie_title, "url": group_url}
        ]

    # URL
    canonical = soup.select_one("link[rel='canonical']")
    if canonical:
        scene["url"] = _fix_canonical(canonical.get("href", ""))
    else:
        scene["url"] = url

    return scene


# ---------------------------------------------------------------------------
# SCENE from fragment (Tagger / Scrape With...)
# ---------------------------------------------------------------------------
def scene_from_fragment(args: dict) -> ScrapedScene | None:
    title = args.get("title", "")
    url = args.get("url", "")

    # Always try to extract scene number from title first
    scene_num = None
    if title:
        _, scene_num = _extract_scene_number(title)

    # If URL is available, scrape directly (with scene_num if detected)
    if url and ("mansurfer.tv" in url or "aebn.com" in url):
        log.info(f"Scraping URL: {url}" +
                 (f" (Scene {scene_num})" if scene_num else ""))
        return scene_from_url(url, scene_num=scene_num)

    # Otherwise search by title
    if not title:
        log.error("No title or URL to scrape from")
        return None

    base_title, scene_num = _extract_scene_number(title)
    search_term = base_title if scene_num else title

    log.info(f"Searching ManSurfer for: {search_term}" +
             (f" (Scene {scene_num})" if scene_num else ""))
    results = search_scenes(search_term, max_results=5)
    if not results:
        log.error(f"No results found for: {search_term}")
        return None

    first_url = results[0].get("url", "")
    if not first_url:
        log.error("First search result has no URL")
        return None

    log.info(f"Scraping detail page: {first_url}")
    return scene_from_url(first_url, scene_num=scene_num)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    match op, args:
        case "scene-by-url", {"url": url} if url:
            # scene-by-url may also receive title — use it to detect scene number
            scene_num = None
            if title := args.get("title", ""):
                _, scene_num = _extract_scene_number(title)
            result = scene_from_url(url, scene_num=scene_num)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args)
        case "scene-by-name", {"name": name} if name:
            result = search_scenes(name, max_results=15)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
