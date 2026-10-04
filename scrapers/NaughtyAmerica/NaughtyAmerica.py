import json
import re
import sys
import time
from datetime import datetime
from typing import Any

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    Gender,
    ScrapedGallery,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedStudio,
)
from py_common.util import scraper_args

ensure_requirements("bs4:beautifulsoup4", "cloudscraper")
import cloudscraper  # noqa: E402
import requests  # noqa: E402
from bs4 import BeautifulSoup as bs  # noqa: E402
from cloudscraper.exceptions import CloudflareException  # noqa: E402

REQUEST_ERRORS = (requests.RequestException, CloudflareException)

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

# Tonight's Girlfriend belongs to La Touraine, not the Naughty America network
STUDIO_PARENTS = {
    "Naughty America": None,
    "Tonight's Girlfriend": "La Touraine",
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


def to_scraped_studio(site_name: str) -> ScrapedStudio:
    name = SITE_NAME_TO_STUDIO_NAME_MAP.get(site_name, site_name)
    if parent := STUDIO_PARENTS.get(name, "Naughty America"):
        return {"name": name, "parent": {"name": parent}}
    return {"name": name}


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
    # Pretty bad crops at this resolution so we grab the default from `resolution_for` instead
    # (("www.tonightsgirlfriend.com",), "1499x944"),
    (
        (
            "www.myfriendshotmom.com",
            "www.mysistershotfriend.com",
            "www.thundercock.com",
            "www.tonightsts.com",
        ),
        "1279x852",
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
    "The API has no direct image field so we derive one from a trailer/promo URL"
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
    name = re.sub(r"(teaser|trailer)$", "", name.removeprefix(prefix))
    resolution = resolution_for(scene_url)
    return f"https://images4.naughtycdn.com/cms/nacmscontent/v1/scenes/{prefix}/{name}/scene/horizontal/{resolution}c.jpg"


def to_scraped_scene(scene_from_api: dict[str, Any]) -> ScrapedScene:
    "Converts Naughty America's API scene into Stash's scraper return type"
    scene_url = scene_from_api["scene_url"]
    published_date = scene_from_api["published_date"]  # "2026-01-22 08:00:00"
    scene: ScrapedScene = {
        "title": scene_from_api["title"].strip(),
        "date": published_date[:10],
        "urls": [scene_url],
        "performers": api_scene_performers_to_scraped_scene_performers(
            scene_from_api["performers"]
        ),
        "studio": to_scraped_studio(scene_from_api["site_name"]),
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

    # older scenes have a length of 0
    if (length := scene_from_api.get("length")) and length >= 10:
        scene["duration"] = length

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
        except REQUEST_ERRORS as e:
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
    except ValueError as e:
        log.error(f"Invalid page content: {e}")
        if "Just a moment..." in r.text:
            log.error("Protected by Cloudflare. Retry later...")
        return None

    if len(data) == 1:
        return data[0]
    log.warning(f"Scene not found in the API for ID {scene_id}")
    return None


def id_from_url(_url: str) -> str | None:
    "Get the API ID from a URL"
    # Naughty America 3D numbers its scenes separately from the API
    if "/vr-porn-3d/" in _url:
        return None
    if match := re.search(r"/.*?(\d+)(?:\?|#|$)$", _url):
        return match.group(1)
    return None


def fetch_page(_url: str) -> bs | None:
    try:
        r = scraper.get(_url, timeout=(3, 5))
    except REQUEST_ERRORS as e:
        log.error(f"An error has occurred with the page request: {e}")
        return None
    if r.status_code != 200:
        log.error(f"Failed to retrieve webpage, status code: {r.status_code}")
        return None
    return bs(r.text, features="html.parser")


def image_from_page(soup: bs, _url: str) -> str | None:
    "The cover from the scene page's player or og:image, skipping lazy-load placeholders"
    candidates = [
        img.get(attr)
        for img in soup.select("img.start-card, img.playcard")
        for attr in ("data-srcset", "srcset", "src")
    ] + [meta.get("content") for meta in soup.select('meta[property="og:image"]')]
    src = next(
        (c for c in candidates if isinstance(c, str) and c.startswith(("//", "http"))),
        None,
    )
    if not src:
        return None
    return re.sub(
        r"(/nacmscontent/.+/horizontal/)\d+x\d+c\.jpg$",
        rf"\g<1>{resolution_for(_url)}c.jpg",
        f"https:{src}" if src.startswith("//") else src,
    )


def scene_from_tour_page(soup: bs, _url: str) -> ScrapedScene | None:
    "naughtyamerica.com's scene pages"
    if not (info := soup.select_one("div.scene-info")):
        return None
    scene: ScrapedScene = {
        "urls": [_url],
        "performers": [
            {"name": a.get_text(strip=True)}
            for a in info.select("div.performer-list a")
        ],
        "tags": [
            {"name": name}
            for name in dict.fromkeys(
                a.get_text(strip=True) for a in info.select("div.categories a.cat-tag")
            )
        ],
    }
    if title := info.select_one("h1.scene-title"):
        scene["title"] = title.get_text(strip=True)
    if date := info.select_one("span.entry-date"):
        # Apr 8, 2016
        scene["date"] = datetime.strptime(  # noqa: DTZ007
            date.get_text(strip=True), "%b %d, %Y"
        ).strftime("%Y-%m-%d")
    if synopsis := soup.select_one("div.synopsis"):
        if label := synopsis.select_one("h2"):
            label.decompose()
        if details := synopsis.get_text().strip():
            scene["details"] = details
    if site := info.select_one("a.site-title"):
        scene["studio"] = to_scraped_studio(site.get_text(strip=True))
    if image := image_from_page(soup, _url):
        scene["image"] = image
    return scene


def scene_from_suite_page(soup: bs, _url: str) -> ScrapedScene | None:
    "The older template that tonightsts.com still uses"
    if not (info := soup.select_one("div.scenepage-info")):
        return None
    scene: ScrapedScene = {
        "urls": [_url],
        "tags": [
            {"name": a.get_text(strip=True)}
            for a in soup.select("div.scenepage-categories a")
        ],
    }
    if title := info.select_one("h1"):
        scene["title"] = title.get_text(strip=True)
    if cast := info.select_one("p"):
        # only some performers are links, so split the whole line instead
        if added := cast.select_one("span.scenepage-date"):
            # Added: 05-03-19
            if match := re.search(r"\d\d-\d\d-\d\d", added.get_text()):
                scene["date"] = datetime.strptime(  # noqa: DTZ007
                    match[0], "%m-%d-%y"
                ).strftime("%Y-%m-%d")
            added.decompose()
        scene["performers"] = [
            {"name": name}
            for name in (n.strip() for n in cast.get_text().split(","))
            if name
        ]
    if (description := soup.select_one("div.scenepage-description")) and (
        details := description.get_text().strip()
    ):
        scene["details"] = details
    # <title> ends with the site's name: "... | Tonight's TS"
    if (page_title := soup.select_one("title")) and " | " in (
        text := page_title.get_text(strip=True)
    ):
        scene["studio"] = to_scraped_studio(text.rsplit(" | ", 1)[1])
    if image := image_from_page(soup, _url):
        scene["image"] = image
    return scene


def scene_from_webpage(_url: str) -> ScrapedScene | None:
    "Scrapes the live page for scenes the API doesn't have"
    if not (soup := fetch_page(_url)):
        return None
    if scene := scene_from_tour_page(soup, _url) or scene_from_suite_page(soup, _url):
        return scene
    log.error(f"Unrecognised page layout at '{_url}'")
    return None


def api_scene_by_url(_url: str) -> ScrapedScene | None:
    if (scene_id := id_from_url(_url)) and (api_scene := api_scene_from_id(scene_id)):
        return to_scraped_scene(api_scene)
    return None


def scene_by_url(_url: str) -> ScrapedScene | None:
    "Scrapes a scene from the API, falling back to the live page if the API doesn't have it"
    if not (scene := api_scene_by_url(_url)):
        return scene_from_webpage(_url)
    if "image" in scene:
        return scene
    # scenes without trailers still show their cover on the page
    if (soup := fetch_page(_url)) and (image := image_from_page(soup, _url)):
        return {**scene, "image": image}
    return scene


def to_scraped_gallery(scene: ScrapedScene) -> ScrapedGallery:
    "A scene and its gallery are the same thing here - just drop scene-only fields"
    gallery: ScrapedGallery = {}
    if title := scene.get("title"):
        gallery["title"] = title
    if urls := scene.get("urls"):
        gallery["urls"] = urls
    if date := scene.get("date"):
        gallery["date"] = date
    if details := scene.get("details"):
        gallery["details"] = details
    if studio := scene.get("studio"):
        gallery["studio"] = studio
    if tags := scene.get("tags"):
        gallery["tags"] = tags
    if performers := scene.get("performers"):
        gallery["performers"] = performers
    return gallery


def gallery_by_url(_url: str) -> ScrapedGallery | None:
    if scene := api_scene_by_url(_url) or scene_from_webpage(_url):
        return to_scraped_gallery(scene)
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
