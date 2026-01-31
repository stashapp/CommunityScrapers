"""
Stash scraper for Naughty America that uses the Naughty America API and direct
website scraping.
"""
import json
import re
import sys
import time
from typing import Any, Callable

from AlgoliaAPI.AlgoliaAPI import default_postprocess
from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedGallery, ScrapedPerformer, ScrapedScene
from py_common.util import scraper_args

ensure_requirements("bs4:beautifulsoup4", "cloudscraper")
from bs4 import BeautifulSoup as bs
import cloudscraper

IS_MEMBER = False

LOG_FILE = "NaughtyAmerica.log"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://www.naughtyamerica.com/",
}

GENDERS_MAP = {
    'female_trans': 'transgender_female',
    'shemale': 'transgender_female',
}

SITE_NAME_TO_STUDIO_NAME_MAP = {
    "Dorm Room": "The Dorm Room",
    "Dressing Room": "The Dressing Room",
    "Gym": "The Gym",
    "Office": "The Office",
    "Spa": "The Spa",
}

scraper = cloudscraper.create_scraper()

def mapped_gender(gender: str) -> str:
    "Gets corresponding value from map, else returns argument value"
    return GENDERS_MAP.get(gender, gender)

def mapped_studio(site_name: str) -> str:
    "Maps site name to studio name using SITE_NAME_TO_STUDIO_NAME_MAP"
    return SITE_NAME_TO_STUDIO_NAME_MAP.get(site_name, site_name)

def api_scene_performers_to_scraped_scene_performers(performers: dict[list[str]]) -> list[ScrapedPerformer]:
    "Converts API scene performers to list of ScrapedPerformer"
    return [
        { "gender": mapped_gender(gender), "name": name }
        for gender, names in performers.items()
        for name in names
    ]

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

def to_scraped_scene(scene_from_api: dict[str, Any]) -> ScrapedScene:
    "Helper function to convert from Naughty America's API to Stash's scraper return type"
    scene: ScrapedScene = {}
    # id
    if scene_id := scene_from_api.get("id"): # e.g. 123456
        log.debug(f"scene_id: {scene_id}")
        scene["code"] = str(scene_id) # Stash expects a string
    # title
    if title := scene_from_api.get("title"):
        log.debug(f"title: {title}")
        scene["title"] = title.strip()
    # published_date
    if published_date := scene_from_api.get("published_date"): # e.g. "2026-01-22 08:00:00"
        log.debug(f"published_date: {published_date}")
        scene["date"] = published_date[:10] # e.g. "2026-01-22"
    # scene_url
    if scene_url := scene_from_api.get("scene_url"):
        log.debug(f"scene_url: {scene_url}")
        scene["url"] = scene_url
    # synopsis
    if synopsis := scene_from_api.get("synopsis"):
        log.debug(f"synopsis: {synopsis}")
        scene["details"] = clean_text(synopsis)
    # tags
    if tags := scene_from_api.get("tags"):
        log.debug(f"tags: {tags}")
        # VR scenes can make use of pov and degrees as tags
        if "Virtual Reality" in tags or "VR Porn" in tags:
            if pov := scene_from_api.get("pov"):
                log.debug(f"pov: {pov}")
                tags.append(f"{pov} POV")
            if degrees := scene_from_api.get("degrees"):
                log.debug(f"degrees: {degrees}")
                tags.append(f"{degrees}°")
        scene["tags"] = [ { "name": t } for t in tags ]
    # performers
    if performers := scene_from_api.get("performers"):
        log.debug(f"performers: {performers}")
        scene["performers"] = api_scene_performers_to_scraped_scene_performers(performers)
    # site_name
    if site_name := scene_from_api.get("site_name"):
        log.debug(f"site_name: {site_name}")
        scene["studio"] = { "name": mapped_studio(site_name) }
    # image is determined indirectly from the trailer or promo video URL
    trailers = scene_from_api.get('trailers', {})
    log.debug(f"trailers: {trailers}")
    promo_video_data = scene_from_api.get('promo_video_data', {})
    log.debug(f"promo_video_data: {promo_video_data}")
    # check trailers or promo_video_data are dicts with at least one entry
    if (isinstance(trailers, dict) and len(trailers) > 0) or (isinstance(promo_video_data, dict) and len(promo_video_data) > 0):
        log.debug("trailers or promo_video_data contain entries")
        if trailer_or_promo_video := next(iter(trailers.values()), None) or next(iter(promo_video_data.values()), None):
            log.debug(f"trailer_or_promo_video: {trailer_or_promo_video}")
            # extract prefix and name
            match = re.match(r".+(?:promo|\.com)/(?:nonsecure/)?([^/]+)/(?:trailers(?:/vr)?/)?([^/_]+).*", trailer_or_promo_video)
            if match:
                prefix = match.group(1)
                name = match.group(2)
                if name.startswith(prefix):
                    name = name[len(prefix):]
                name = re.sub(r"(teaser|trailer)$", "", name)
                resolution = "1279x852"  # default resolution
                # studio-specific logic
                scene_url = scene.get('scene_url', '')
                if "www.naughtyamerica.com" in scene_url:
                    resolution = "1279x852"
                elif "www.naughtyamericavr.com" in scene_url:
                    resolution = "1000x563"
                elif "www.tonightsgirlfriend.com" in scene_url:
                    resolution = "1499x944"
                elif any(domain in scene_url for domain in [
                    "www.myfriendshotmom.com",
                    "www.mysistershotfriend.com",
                    "www.thundercock.com",
                    "www.tonightsts.com"
                ]):
                    resolution = "1279x719"
                scene["image"] = f"https://images4.naughtycdn.com/cms/nacmscontent/v1/scenes/{prefix}/{name}/scene/horizontal/{resolution}c.jpg"
    return scene

def api_scene_from_id(
    scene_id: int | str,
) -> dict[str, Any] | None:
    "Searches a scene from its id and returns the API result as-is"
    api_url = f"https://api.naughtyapi.com/tools/scenes/scenes?id={scene_id}"
    log.debug(f"API URL: {api_url}")
    # the API sometimes returns 405 errors, so implement retries with exponential backoff
    max_retries = 8
    backoff = 0.5
    for attempt in range(1, max_retries + 1):
        try:
            r = scraper.get(api_url, headers=HEADERS, timeout=(3, 5))
            if r.status_code == 405:
                log.warning(f"Received 405 response (attempt {attempt}/{max_retries}), retrying after {backoff}s...")
                time.sleep(backoff)
                backoff *= 1.2
                continue
            break
        except Exception as e:
            log.error("An error has occurred with the page request")
            log.error(e)
            log.error(f"Check your {LOG_FILE} for more details")
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write(f"Scene ID: {scene_id}\n")
                f.write(f"Request:\n{e}")
            return None
    else:
        log.error(f"Failed to get a valid response after {max_retries} attempts (last status: {r.status_code if 'r' in locals() else 'N/A'})")
        return None
    try:
        _json = r.json()
        if data := _json.get("data"):
            if len(data) == 0:
                log.error("Scene not found (Wrong ID?)")
                log.debug(json.dumps(_json, indent=2))
            elif len(data) == 1:
                return data[0]
            else:
                log.error("Multiple scenes found for ID?")
                log.debug(json.dumps(_json, indent=2))
        else:
            log.error("Scene not found (Wrong ID?)")
            log.trace(json.dumps(_json, indent=2))
    except Exception as e:
        log.error(e)
        log.debug(r.status_code)
        if r.status_code == 401 and IS_MEMBER:
            log.error("It's likely that your member access token needs to be replaced")
        if "Just a moment..." in r.text:
            log.error("Protected by Cloudflare. Retry later...")
        else:
            log.error("Invalid page content")
            log.debug(r.text)
    return None

def scene_from_id(
    scene_id,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedScene | None:
    "Scrapes a scene from a clip_id, running an optional postprocess function on the result"
    api_scene = api_scene_from_id(scene_id)
    log.trace(f"type(api_scene): {type(api_scene)}")
    if api_scene:
        return postprocess(to_scraped_scene(api_scene), api_scene)
    return None

def id_from_url(_url: str) -> str | None:
    "Get the ID from a URL"
    if match := re.search(r"/.*?(\d+)(?:\?|#|$)$", _url):
        return match.group(1)
    log.error("Are you sure that URL is from a site that uses the Naughty America API?")
    return None

def scene_from_webpage(_url: str) -> ScrapedScene | None:
    "Scrapes a scene directly from the webpage, running an optional postprocess function on the result"
    scene: ScrapedScene = {}
    if scene_id := id_from_url(_url):
        scene["code"] = str(scene_id)
    try:
        r = scraper.get(_url, headers=HEADERS, timeout=(3, 5))
    except Exception as e:
        log.error("An error has occurred with the page request")
        log.error(e)
        log.error(f"Check your {LOG_FILE} for more details")
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"URL: {_url}\n")
            f.write(f"Request:\n{e}")
        return None
    if r.status_code != 200:
        log.error(f"Failed to retrieve webpage, status code: {r.status_code}")
        return None
    log.debug(f"Webpage retrieved successfully: {_url}")
    log.trace(f"Webpage content: {r.text}")
    soup = bs(r.text, features='html.parser')
    # get title from //div[@class="scenepage-info"]/h1
    if title_elem := soup.select_one("div.scenepage-info > h1"):
        log.debug(f"title_elem: {title_elem}")
        scene["title"] = title_elem.get_text(strip=True)
    else:
        log.warning("Title element not found on webpage")
    # get date from //span[@class="scenepage-date"]/text()
    if date_elem := soup.select_one("span.scenepage-date"):
        log.debug(f"date_elem: {date_elem}")
        # parse MM-DD-YY as YYYY-MM-DD
        date_text = date_elem.get_text(strip=True)
        if match := re.match(r"(\d{2})-(\d{2})-(\d{2})", date_text):
            month = match.group(1)
            day = match.group(2)
            year = int(match.group(3))
            year += 2000 if year < 70 else 1900
            scene["date"] = f"{year:04d}-{month}-{day}"
    else:
        log.warning("Date element not found on webpage")
    # get image from //img[@class="playcard"]/@src
    if image_elem := soup.select_one("img.playcard"):
        log.debug(f"image_elem: {image_elem}")
        img_src = image_elem.get("src")
        # add protocol if missing
        if img_src and img_src.startswith("//"):
            img_src = f"https:{img_src}"
        scene["image"] = img_src
    else:
        log.warning("Image element not found on webpage")
    # get details from //div[@class="scenepage-description"]
    if description_elem := soup.select_one("div.scenepage-description"):
        log.debug(f"description_elem: {description_elem}")
        scene["details"] = description_elem.get_text(strip=True)
    else:
        log.warning("Description element not found on webpage")
    # get tags from //div[@class="scenepage-categories"]/a/text()
    scene_tags: list[dict[str, Any]] = []
    for tag_elem in soup.select("div.scenepage-categories > a"):
        tag_name = tag_elem.get_text(strip=True)
        scene_tags.append({ "name": tag_name })
    scene["tags"] = scene_tags
    # get URL from //link[@rel="canonical"]/@href
    if url_elem := soup.select_one('link[rel="canonical"]'):
        log.debug(f"url_elem: {url_elem}")
        scene["url"] = url_elem.get("href")
    else:
        log.warning("Canonical URL element not found on webpage")
    # get performers from //div[@class="scenepage-info"]/p
    performers: list[dict[str, Any]] = []
    for performer_elem in soup.select("div.scenepage-info > p > a"):
        # remove "Added:.*" at end if present
        performer_names = re.sub(r"Added:.*$", "", performer_elem.get_text(strip=True)).strip()
        performers.extend(
            [{"name": name.strip()} for name in performer_names.split(",") if name.strip()]
        )
        scene["performers"] = performers
    return scene

def scene_by_url(
    _url: str,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedScene | None:
    "Scrapes a scene from a URL, running an optional postprocess function on the result"
    log.debug("Attempting to scrape scene from API")
    if scene_id := id_from_url(_url):
        log.debug(f"Scene ID: {scene_id}")
        if scene := scene_from_id(scene_id, postprocess):
            log.trace(f"scraped scene via API: {json.dumps(scene, indent=2)}")
            return scene
    # scene not found in API, scrape website directly
    log.debug("Falling back to webpage scraping")
    if scene := scene_from_webpage(_url):
        return scene
    return None

def gallery_by_url(
    _url: str,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedGallery | None:
    if scene := scene_by_url(_url, postprocess):
        gallery: ScrapedGallery = {
            "title": scene.get("title", ""),
            "url": scene.get("url", ""),
            "details": scene.get("details", ""),
            "studio": scene.get("studio", {}),
            "tags": scene.get("tags", []),
            "performers": scene.get("performers", []),
            "date": scene.get("date", ""),
            "code": scene.get("code", ""),
        }
        return gallery
    return None

if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_by_url(url)
        case "scene-by-url", {"url": url} if url:
            result = scene_by_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
