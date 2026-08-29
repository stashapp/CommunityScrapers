import json
import re
import sys
import time
from typing import Any

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    Gender,
    ScrapedGallery,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedTag,
)
from py_common.util import scraper_args

ensure_requirements("bs4:beautifulsoup4", "cloudscraper")
from bs4 import BeautifulSoup as bs  # noqa: E402
import cloudscraper  # noqa: E402

GENDERS_MAP: dict[str, Gender] = {
    "male": "MALE",
    "female": "FEMALE",
    "female_trans": "TRANSGENDER_FEMALE",
    "shemale": "TRANSGENDER_FEMALE",
}

SITE_NAME_TO_STUDIO_NAME_MAP = {
    "Dorm Room": "The Dorm Room",
    "Dressing Room": "The Dressing Room",
    "Gym": "The Gym",
    "Office": "The Office",
    "Spa": "The Spa",
}

scraper = cloudscraper.create_scraper()
scraper.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://www.naughtyamerica.com/",
    }
)


def mapped_gender(gender: str) -> Gender | None:
    return GENDERS_MAP.get(gender)


def mapped_studio(site_name: str) -> str:
    return SITE_NAME_TO_STUDIO_NAME_MAP.get(site_name, site_name)


def api_scene_performers_to_scraped_scene_performers(
    performers: dict[str, list[str]],
) -> list[ScrapedPerformer]:
    "Converts API scene performers to list of ScrapedPerformer"
    return [
        {"name": name, "gender": mapped}
        if (mapped := mapped_gender(gender))
        else {"name": name}
        for gender, names in performers.items()
        for name in names
    ]


def clean_text(details: str) -> str:
    "Remove escaped backslashes and html parse the details text, preserving newlines"
    details = details.replace("\\", "")
    details = re.sub(r"<\s*/?br\s*/?\s*>", "\n", details)
    return bs(details, features="html.parser").get_text("", strip=False)


RESOLUTION_BY_DOMAIN: list[tuple[tuple[str, ...], str]] = [
    (("www.naughtyamericavr.com",), "1000x563"),
    (("www.tonightsgirlfriend.com",), "1499x944"),
    (
        (
            "www.myfriendshotmom.com",
            "www.mysistershotfriend.com",
            "www.thundercock.com",
            "www.tonightsts.com",
        ),
        "1279x719",
    ),
]


def resolution_for(scene_url: str) -> str:
    return next(
        (
            res
            for site_domains, res in RESOLUTION_BY_DOMAIN
            if any(d in scene_url for d in site_domains)
        ),
        "1279x852",  # naughtyamerica.com's own resolution, also the default
    )


def scene_image_url(scene_from_api: dict[str, Any], scene_url: str) -> str | None:
    "Naughty America has no direct image field - derive one from a trailer/promo URL"
    combined = (scene_from_api.get("trailers") or {}) | (
        scene_from_api.get("promo_video_data") or {}
    )
    if not (trailer_or_promo := next(iter(combined.values()), None)):
        return None
    if not (
        match := re.match(
            r".+(?:promo|\.com)/(?:nonsecure/)?([^/]+)/(?:trailers(?:/vr)?/)?([^/_]+).*",
            trailer_or_promo,
        )
    ):
        return None
    prefix, name = match.group(1), match.group(2)
    if name.startswith(prefix):
        name = name[len(prefix) :]
    name = re.sub(r"(teaser|trailer)$", "", name)
    resolution = resolution_for(scene_url)
    return f"https://images4.naughtycdn.com/cms/nacmscontent/v1/scenes/{prefix}/{name}/scene/horizontal/{resolution}c.jpg"


def to_scraped_scene(scene_from_api: dict[str, Any]) -> ScrapedScene:
    "Converts Naughty America's API scene into Stash's scraper return type"
    scene_url = scene_from_api["scene_url"]
    published_date = scene_from_api["published_date"]  # "2026-01-22 08:00:00"
    scene: ScrapedScene = {
        "code": str(scene_from_api["id"]),
        "title": scene_from_api["title"].strip(),
        "date": published_date[:10],
        "urls": [scene_url],
        "performers": api_scene_performers_to_scraped_scene_performers(
            scene_from_api["performers"]
        ),
        "studio": {"name": mapped_studio(scene_from_api["site_name"])},
    }

    if synopsis := scene_from_api.get("synopsis"):
        scene["details"] = clean_text(synopsis)

    if tags := scene_from_api.get("tags"):
        # VR scenes can make use of pov and degrees as tags
        if "Virtual Reality" in tags or "VR Porn" in tags:
            if pov := scene_from_api.get("pov"):
                tags.append(f"{pov} POV")
            if degrees := scene_from_api.get("degrees"):
                tags.append(f"{degrees}°")
        scene["tags"] = [{"name": t} for t in tags]

    if image := scene_image_url(scene_from_api, scene_url):
        scene["image"] = image
    return scene


def api_scene_from_id(scene_id: int | str) -> dict[str, Any] | None:
    api_url = f"https://api.naughtyapi.com/tools/scenes/scenes?id={scene_id}"
    # the API sometimes returns 405 errors, so retry with exponential backoff
    max_retries = 8
    backoff = 0.5
    for attempt in range(1, max_retries + 1):
        try:
            r = scraper.get(api_url, timeout=(3, 5))
        except Exception as e:
            log.error(f"An error has occurred with the API request: {e}")
            return None
        if r.status_code != 405:
            break
        log.warning(
            f"Received 405 response (attempt {attempt}/{max_retries}), "
            f"retrying after {backoff}s..."
        )
        time.sleep(backoff)
        backoff *= 1.2
    else:
        log.error(f"Failed to get a valid response after {max_retries} attempts")
        return None

    try:
        data = r.json().get("data", [])
    except Exception as e:
        log.error(f"Invalid page content: {e}")
        if "Just a moment..." in r.text:
            log.error("Protected by Cloudflare. Retry later...")
        return None

    if len(data) == 1:
        return data[0]
    log.error(f"Scene not found for ID {scene_id} (got {len(data)} results)")
    return None


def scene_from_id(scene_id: int | str) -> ScrapedScene | None:
    if api_scene := api_scene_from_id(scene_id):
        return to_scraped_scene(api_scene)
    return None


def id_from_url(_url: str) -> str | None:
    "Get the ID from a URL"
    if match := re.search(r"/.*?(\d+)(?:\?|#|$)$", _url):
        return match.group(1)
    log.error("Are you sure that URL is from a site that uses the Naughty America API?")
    return None


def video_json_ld(soup: bs) -> dict[str, Any]:
    "The site's own schema.org VideoObject block - far more stable than its CSS classes"
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        if data.get("@type") == "VideoObject":
            return data
    return {}


def scene_performers_from_json_ld(video: dict[str, Any]) -> list[ScrapedPerformer]:
    result: list[ScrapedPerformer] = []
    for actor in video.get("actor", []):
        if not (name := actor.get("name")):
            continue
        performer: ScrapedPerformer = {"name": name}
        if mapped := mapped_gender((actor.get("gender") or "").lower()):
            performer["gender"] = mapped
        result.append(performer)
    return result


def scene_tags_from_webpage(soup: bs) -> list[ScrapedTag]:
    if not (scene_div := soup.select_one("div.scene")):
        return []
    names = dict.fromkeys(
        tag_elem.get_text(strip=True) for tag_elem in scene_div.select("a.cat-tag")
    )
    return [{"name": name} for name in names]


def scene_from_webpage(_url: str) -> ScrapedScene | None:
    "Falls back to scraping the live page directly when the API doesn't have the scene"
    try:
        r = scraper.get(_url, timeout=(3, 5))
    except Exception as e:
        log.error(f"An error has occurred with the page request: {e}")
        return None
    if r.status_code != 200:
        log.error(f"Failed to retrieve webpage, status code: {r.status_code}")
        return None

    soup = bs(r.text, features="html.parser")
    video = video_json_ld(soup)
    scene: ScrapedScene = {
        "urls": [video.get("contentUrl") or _url],
        "tags": scene_tags_from_webpage(soup),
        "performers": scene_performers_from_json_ld(video),
    }
    if scene_id := id_from_url(_url):
        scene["code"] = str(scene_id)
    # the JSON-LD "name" is "{performers} in {site}"
    # the page's has the actual title in a <h1>
    if title_elem := soup.select_one("h1.grey-title"):
        scene["title"] = title_elem.get_text(strip=True)
    if upload_date := video.get("uploadDate"):
        # 2010-10-29T15:00:00.000000Z
        scene["date"] = upload_date[:10]
    if description := video.get("description"):
        scene["details"] = description
    if image := video.get("thumbnailUrl"):
        scene["image"] = image
    return scene


def scene_by_url(_url: str) -> ScrapedScene | None:
    "Scrapes a scene from a URL, falling back to the live page if the API doesn't have it"
    if (scene_id := id_from_url(_url)) and (scene := scene_from_id(scene_id)):
        return scene
    return scene_from_webpage(_url)


def gallery_by_url(_url: str) -> ScrapedGallery | None:
    "A scene and its gallery are the same thing here - just drop scene-only fields"
    if not (scene := scene_by_url(_url)):
        return None
    gallery_keys = ScrapedGallery.__required_keys__ | ScrapedGallery.__optional_keys__
    return {k: v for k, v in scene.items() if k in gallery_keys}  # type: ignore


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
