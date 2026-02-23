import json
import re
import sys
import html
import urllib3
from urllib.parse import quote_plus

from py_common import log
from py_common.util import dig, scraper_args
from py_common.deps import ensure_requirements
from py_common.types import (
    ScrapedScene,
    ScrapedPerformer,
    ScrapedGallery,
    ScrapedTag,
)

ensure_requirements("requests")
import requests  # noqa: E402


# Had to set verify=False due to a certificate issue with their site
urllib3.disable_warnings()


def __raw_photoset_from_api(set_id: str, headers) -> dict | None:
    app_id = headers["X-Algolia-Application-Id"]
    api_URL = f"https://{app_id.lower()}-dsn.algolia.net/1/indexes/all_photosets/query"
    payload = {"params": f"query=&hitsPerPage=10&facetFilters=set_id:{set_id}"}
    log.debug(f"Asking the API... {api_URL}")
    res = requests.post(api_URL, headers=headers, json=payload).json()
    if not (_set := dig(res, "hits", 0)):
        log.warning(f"Unable to fetch photoset with ID {set_id}")
        return

    return _set


def __raw_clip_from_api(clip_id: str, headers) -> dict | None:
    app_id = headers["X-Algolia-Application-Id"]
    api_URL = f"https://{app_id.lower()}-dsn.algolia.net/1/indexes/all_scenes/query"
    payload = {"params": f"query=&hitsPerPage=10&facetFilters=clip_id:{clip_id}"}
    log.debug(f"Asking the API... {api_URL}")
    res = requests.post(api_URL, headers=headers, json=payload).json()
    if not (clip := dig(res, "hits", 0)):
        log.warning(f"Unable to fetch clip with ID {clip_id}")
        return

    return clip


def __raw_performer_from_api(actor_id: str, headers) -> dict | None:
    app_id = headers["X-Algolia-Application-Id"]
    api_URL = f"https://{app_id.lower()}-dsn.algolia.net/1/indexes/all_actors/query"
    payload = {
        "params": f"query=&hitsPerPage=10&page=0&facetFilters=actor_id:{actor_id}"
    }
    log.debug(f"Asking the API... {api_URL}")
    res = requests.post(api_URL, headers=headers, json=payload).json()
    if not (actor := dig(res, "hits", 0)):
        log.warning(f"Unable to fetch actor with ID {actor_id}")
        return

    return actor


def _create_headers() -> dict[str, str]:
    r = requests.get(
        "https://www.playboyplus.com",
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
            "Referer": "https://www.playboyplus.com",
            "Origin": "https://www.playboyplus.com",
        },
        verify=False,
    )
    if (script_tag := re.search(r"window.env\s+=\s(.+);", r.text, re.MULTILINE)) and (
        page_json := json.loads(script_tag.group(1))
    ):
        app_id = dig(page_json, "api", "algolia", "applicationID")
        api_key = dig(page_json, "api", "algolia", "apiKey")
    else:
        log.error(
            "Failed to get Algolia key from playboyplus.com, scraper needs updating"
        )
        return {}

    return {
        "X-Algolia-Application-Id": app_id,
        "X-Algolia-API-Key": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
        "Referer": "https://www.playboyplus.com",
        "Origin": "https://www.playboyplus.com",
    }


def clean_description(text: str) -> str:
    """Strip HTML tags and unescape entities from description fields.
    The PB+ API sometimes returns raw HTML (e.g. <p>...<br></p>),
    and sometimes plain text. This handles both cases safely.
    """
    if not text:
        return text
    # Replace <br> variants with a newline before stripping other tags
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    # Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities (e.g. &amp; -> &)
    text = html.unescape(text)
    return text.strip()


def to_scraped_tag(res: dict) -> ScrapedTag:
    return {
        "name": res["name"],
    }


# Map PlayboyPlus "home" field values to ISO 3166-1 alpha-2 country codes.
# The API returns full country names; extend this dict as new values are
# discovered via the warning log below.
COUNTRY_MAP = {
    "United States": "US",
    "United Kingdom": "GB",
    "Canada": "CA",
    "Australia": "AU",
    "Germany": "DE",
    "France": "FR",
    "Brazil": "BR",
    "Czech Republic": "CZ",
    "Hungary": "HU",
    "Sweden": "SE",
    "Denmark": "DK",
    "Netherlands": "NL",
    "Italy": "IT",
    "Spain": "ES",
    "Russia": "RU",
    "Mexico": "MX",
    "Japan": "JP",
    "South Africa": "ZA",
    "New Zealand": "NZ",
    "Poland": "PL",
    "Romania": "RO",
}

# Map PlayboyPlus hair_color values to StashDB internal values.
# StashDB stores "Brunette" internally but displays it as "Brown" in the UI —
# always use the internal value here.
HAIR_COLOR_MAP = {
    "Brown": "Brunette",
    "Brunette": "Brunette",
    "Blonde": "Blonde",
    "Black": "Black",
    "Red": "Red",
    "Auburn": "Auburn",
    "Grey": "Grey",
    "White": "White",
    "Bald": "Bald",
    "Other": "Other",
}


def sanitize_hair_color(value: str) -> str | None:
    return HAIR_COLOR_MAP.get(value.strip()) if value else None


def to_scraped_performer(res: dict) -> ScrapedPerformer:
    performer: ScrapedPerformer = {
        "name": res["name"],
        "gender": res["gender"],
    }

    if (actor_id := dig(res, "actor_id")) and (url_name := dig(res, "url_name")):
        performer["urls"] = [
            f"https://www.playboyplus.com/en/model/view/{url_name}/{actor_id}",
            f"https://members.playboyplus.com/en/model/view/{url_name}/{actor_id}",
        ]

    if details := dig(res, "description"):
        performer["details"] = clean_description(details)

    # PB+ uses /media/ as the CDN path prefix, not /actors/ like other Gamma sites.
    # multicontent_data.nsfw is the primary image source despite pictures also existing,
    # because pictures can contain broken legacy URLs (e.g. 119840/119840_500x750.jpg)
    # while multicontent_data consistently points to the current CDN-hosted hero images.
    # modelHeroMobile (1000x1600 portrait) is the correct variant for performer images —
    # modelHero is a wide banner crop (1920x810) not suitable as a performer thumbnail.
    # Fallback to pictures only if multicontent_data is absent.
    if nsfw := dig(res, "multicontent_data", "nsfw"):
        if img := next(
            (e["file"] for e in nsfw if e.get("name") == "modelHeroMobile"), None
        ):
            performer["images"] = [f"https://transform.gammacdn.com/media/{img}"]
    elif pictures := dig(res, "pictures"):
        if main_pic := list(pictures.values())[-1]:
            performer["images"] = [f"https://transform.gammacdn.com/media{main_pic}"]

    if eye_color := dig(res, "attributes", "eye_color"):
        performer["eye_color"] = eye_color

    if hair_color := sanitize_hair_color(dig(res, "attributes", "hair_color") or ""):
        performer["hair_color"] = hair_color

    if height := dig(res, "attributes", "height"):
        performer["height"] = height

    if (weight := dig(res, "attributes", "weight")) and (weight := float(weight)):
        # Weight is in lbs
        performer["weight"] = str(round(float(weight) * 0.453))

    if home := dig(res, "attributes", "home"):
        home = home.strip()
        if home and home != "N/A":
            # "home" is a full location string, e.g. "Burlington DC United States"
            # or "London United Kingdom" — match by checking which country name it ends with
            matched = next(
                (code for name, code in COUNTRY_MAP.items() if home.endswith(name)),
                None,
            )
            if matched:
                performer["country"] = matched
            else:
                log.warning(f"Unknown country value: {home!r} — add to COUNTRY_MAP if valid")

    return performer


def to_scraped_gallery(res: dict) -> ScrapedGallery:
    gallery: ScrapedGallery = {
        "title": res["title"],
        "code": str(res["set_id"]),
        "date": res["date_online"],
    }
    if studio_name := res.get("studio_name", "").strip():
        gallery["studio"] = {"name": studio_name}
    if description := dig(res, "description"):
        gallery["details"] = clean_description(description)

    if performers := dig(res, "actors"):
        gallery["performers"] = [to_scraped_performer(p) for p in performers]

    if tags := dig(res, "categories"):
        gallery["tags"] = [to_scraped_tag(t) for t in tags]

    if directors := dig(res, "directors"):
        gallery["photographer"] = ", ".join(d["name"] for d in directors)

    return gallery


def to_scraped_scene(res: dict) -> ScrapedScene:
    scene: ScrapedScene = {
        "title": res["title"],
        "date": res["release_date"],
    }
    if studio_name := res.get("studio_name", "").strip():
        scene["studio"] = {"name": studio_name}
    if description := dig(res, "description"):
        scene["details"] = clean_description(description)

    if performers := dig(res, "actors"):
        scene["performers"] = [to_scraped_performer(p) for p in performers]

    if tags := dig(res, "categories"):
        scene["tags"] = [to_scraped_tag(t) for t in tags]

    if directors := dig(res, "directors"):
        scene["director"] = ", ".join(d["name"] for d in directors)

    return scene


def scene_from_url(url: str) -> ScrapedScene | None:
    # All of their public URLs are for photosets so we need to scrape that
    # first in order to get access to the clip_id we need to scrape the scene
    if not (match := re.search(r"/(\d+)$", url)):
        log.error(
            "Can't get the ID of the Scene. "
            "Are you sure that URL is from a site that uses Algolia?"
        )
        return None
    set_id = match.group(1)

    log.debug(f"Scraping set ID {set_id}")

    if not (api_headers := _create_headers()):
        return None

    if not (photoset := __raw_photoset_from_api(set_id, api_headers)):
        return

    if not (clip_id := dig(photoset, "clip_id")):
        log.error("Unable to scrape: this photoset has no associated video")
        return

    if not (clip := __raw_clip_from_api(clip_id, api_headers)):
        return

    scene = to_scraped_scene(clip)

    # Image workaround: the scene image covers in the API aren't actually shown
    # on their site so we fall back to using the hero image from the photoset
    if image := dig(photoset, "multicontent_data", "nsfw", 0, "file"):  # type: ignore
        scene["image"] = f"https://transform.gammacdn.com/media/{image}"

    # Using the clip_id is pointless here since those URLs do not resolve
    scene["code"] = set_id
    if not dig(scene, "details") and (description := dig(photoset, "description")):
        scene["details"] = clean_description(description)

    return scene


def gallery_from_url(url: str) -> ScrapedGallery | None:
    if not (match := re.search(r"/(\d+)$", url)):
        log.error(
            "Can't get the ID of the gallery. "
            "Are you sure that URL is from a site that uses Algolia?"
        )
        return None
    set_id = match.group(1)

    log.debug(f"Scraping set ID {set_id}")

    if not (api_headers := _create_headers()):
        return None

    if not (photoset := __raw_photoset_from_api(set_id, api_headers)):
        return

    return to_scraped_gallery(photoset)


def performer_from_url(url: str) -> ScrapedPerformer | None:
    if not (match := re.search(r"/(\d+)$", url)):
        log.error(
            "Can't get the ID of the performer. "
            "Are you sure that URL is from a site that uses Algolia?"
        )
        return None
    actor_id = match.group(1)

    log.debug(f"Performer ID: {actor_id}")

    if not (api_headers := _create_headers()):
        return None
    if not (actor := __raw_performer_from_api(actor_id, api_headers)):
        return

    return to_scraped_performer(actor)


def performer_search(query: str) -> list[ScrapedPerformer]:
    if not (api_headers := _create_headers()):
        return []
    app_id = api_headers["X-Algolia-Application-Id"]
    api_URL = f"https://{app_id.lower()}-dsn.algolia.net/1/indexes/all_actors/query"
    payload = {"params": f"query={quote_plus(query)}&hitsPerPage=20"}
    log.debug(f"Searching performers for '{query}'... {api_URL}")
    res = requests.post(api_URL, headers=api_headers, json=payload).json()
    hits = res.get("hits") or []
    if not hits:
        log.warning(f"No performers found for query: {query}")
        return []
    return [to_scraped_performer(hit) for hit in hits]


def main_scraper():
    """
    Takes arguments from stdin or from the command line and dumps output as JSON to stdout
    """
    op, args = scraper_args()
    result = None
    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main_scraper()