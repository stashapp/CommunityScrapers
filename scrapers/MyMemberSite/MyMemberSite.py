import json
import sys
import re
from urllib.parse import urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.util import scraper_args, dig
from py_common.types import ScrapedGallery, ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag

ensure_requirements("requests", "bs4:beautifulsoup4")

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
    }
)


def _fetch_page(scrape_url: str) -> str:
    """
    Fetches the page at scrape_url and returns the HTML text.
    Exits if the request fails or if the response status is not 200.
    """
    log.debug(f"Fetching '{scrape_url}'")
    try:
        response = session.get(scrape_url, timeout=(3, 6))
    except requests.exceptions.RequestException as req_ex:
        log.error(f"Error fetching '{scrape_url}': {req_ex}")
        sys.exit(-1)

    if response.status_code != 200:
        log.error(f"Fetching '{scrape_url}' resulted in error status: {response.status_code}")
        sys.exit(-1)

    return response.text


def _extract_nextjs_video_data(html: str) -> dict | None:
    """
    Parse the Next.js __next_f RSC payload embedded in server-rendered HTML to
    extract scene/gallery data.
    """
    pattern = re.compile(
        r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', re.DOTALL
    )

    for m in pattern.finditer(html):
        raw = m.group(1)
        try:
            decoded = json.loads('"' + raw + '"')
        except Exception:
            continue

        if '"pageType":"video"' not in decoded and '"pageType":"photoset"' not in decoded:
            continue

        data_match = re.search(r'"data":(\{)', decoded)
        if not data_match:
            continue

        start = data_match.start(1)
        depth = 0
        for i, ch in enumerate(decoded[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(decoded[start : i + 1])
                    except Exception:
                        break

    return None


def _fetch_studio(html: str, scrape_url: str) -> ScrapedStudio:
    """
    Extract studio name and URL from __next_f payload.
    """
    pattern = re.compile(
        r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', re.DOTALL
    )
    for m in pattern.finditer(html):
        raw = m.group(1)
        try:
            decoded = json.loads('"' + raw + '"')
        except Exception:
            continue
        if '"site_long_name"' not in decoded:
            continue
        name_m = re.search(r'"site_long_name":"([^"]+)"', decoded)
        url_m = re.search(r'"site_url":"(https?://[^"]+)"', decoded)
        if name_m:
            parsed = urlparse(scrape_url)
            return ScrapedStudio(
                name=name_m.group(1),
                url=url_m.group(1) if url_m else f"{parsed.scheme}://{parsed.netloc}",
            )

    parsed = urlparse(scrape_url)
    return ScrapedStudio(
        name=parsed.netloc,
        url=f"{parsed.scheme}://{parsed.netloc}",
    )


def gallery_from_url(gallery_url: str) -> ScrapedGallery:
    """
    Scrapes a gallery from the given URL.

    Parameters
    ----------
    gallery_url : str
        The URL of the gallery to scrape.

    Returns
    -------
    ScrapedGallery
        The scraped gallery data.
    """
    html = _fetch_page(gallery_url)
    studio: ScrapedStudio = _fetch_studio(html, gallery_url)
    raw_gallery = _extract_nextjs_video_data(html)
    if not raw_gallery:
        log.error(f"Could not extract gallery data from Next.js payload at '{gallery_url}'")
        sys.exit(-1)

    scraped: ScrapedGallery = {}

    if title := raw_gallery.get("title"):
        scraped["title"] = title

    if _id := raw_gallery.get("id"):
        scraped["code"] = str(_id)

    if date := raw_gallery.get("publish_date"):
        scraped["date"] = date.split("T")[0]

    if details := raw_gallery.get("description"):
        scraped["details"] = BeautifulSoup(details, "html.parser").get_text()

    if tags := raw_gallery.get("tags"):
        scraped["tags"] = [ScrapedTag(name=t["name"]) for t in tags]

    if cast := raw_gallery.get("casts"):
        scraped["performers"] = [ScrapedPerformer(name=p["screen_name"]) for p in cast]

    scraped["studio"] = studio

    return scraped


def scene_from_url(scene_url: str) -> ScrapedScene:
    """
    Scrapes a scene from the given URL.

    Parameters
    ----------
    scene_url : str
        The URL of the scene to scrape.

    Returns
    -------
    ScrapedScene
        The scraped scene data.
    """
    html = _fetch_page(scene_url)
    studio: ScrapedStudio = _fetch_studio(html, scene_url)
    raw_scene = _extract_nextjs_video_data(html)
    if not raw_scene:
        log.error(f"Could not extract video data from Next.js payload at '{scene_url}'")
        sys.exit(-1)

    scraped: ScrapedScene = {}

    if title := raw_scene.get("title"):
        scraped["title"] = title

    if _id := raw_scene.get("id"):
        scraped["code"] = str(_id)

    if date := raw_scene.get("publish_date"):
        scraped["date"] = date.split("T")[0]

    if details := raw_scene.get("description"):
        scraped["details"] = BeautifulSoup(details, "html.parser").get_text()

    if tags := raw_scene.get("tags"):
        scraped["tags"] = [ScrapedTag(name=t["name"]) for t in tags]

    if cast := raw_scene.get("casts"):
        scraped["performers"] = [ScrapedPerformer(name=p["screen_name"]) for p in cast]

    if image := dig(raw_scene, ("poster_src", "cover_photo")):
        scraped["image"] = image

    scraped["studio"] = studio

    return scraped


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
