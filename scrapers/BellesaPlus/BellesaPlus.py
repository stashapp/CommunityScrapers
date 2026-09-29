import json
import re
import sys
from datetime import UTC, datetime
from typing import Any

import requests

from py_common import log
from py_common.types import ScrapedScene, ScrapedTag
from py_common.util import scraper_args

# Only Bellesa's own series: the API also carries redistributed studios
BELLESA_STUDIO_HANDLES = {
    "bellesa-house",
    "bellesa-films",
    "bellesa-blind-date",
    "belle-says",
    "bellesa-house-party",
    "zero-to-hero",
}

# Replace bellesa tags with stash tags (make sure hyphen is preserved)
TAG_REPLACEMENTS = {
    "penetration": "Vaginal Penetration",
    "dick-riding": "Riding",
    "porn for women": "Erotica",
    "sex": "Hardcore",
    "lesbian-rough": "Rough",
    "unscripted": "Gonzo",
    "partner-swapping": "Swapping",
    "masturbating": "Masturbation",
    "brunnette": "Brown Hair",
    "real couples": "Real Couple",
    "threesome fmf": "Threesome (BGG)",
    "sweaty sex": "Sweaty",
    "hot guy tattoos": "Tattoos",
    "tattos": "Tattoos",
    "girl girl": "Twosome (Lesbian)",
    "sidefuck": "Side Fuck",
    "hairpulling": "Hair Pulling",
    "gbg": "Threesome (BGG)",
    "gameshow": "Game Show",
    "male anal fingering": "Anal Fingering",
    "snowball": "Cum Swapping",
    "cumkiss": "Cum Kissing",
    "girl eats guys ass": "Rimming Him",
    "male rimjob": "Rimming Him",
    "sloppy": "Sloppy Blowjob",
    "bi": "Bisexual",
    "lesbian ass eating": "Rimming (Lesbian)",
    "fake breasts": "Fake Tits",
    "girl rims guy": "Rimming Him",
    "titty suck": "Breast Sucking",
    "light choking": "Choking",
    "nipple suck": "Nipple Play",
    "tall guy": "Tall Man",
}

# Tags with no stash equivalent (make sure hyphens are preserved)
BAD_TAGS = {
    "original",
    "hot guy",
    "hot girls",
    "bellesa",
    "bellesa houses",
    "bs",  # belle says
    "bellesa original",
    "bh",  # bellesa house
    "special",
    "zth",  # zero to hero
    "z2h",  # zero 2 hero
    "euro house",  # bellesa euro house
}


def to_tags(raw: str, not_tags: set[str]) -> list[ScrapedTag]:
    "The API mixes the scene's studio and performers into its tags"
    return [
        {"name": TAG_REPLACEMENTS.get(lower, tag).replace("-", " ")}
        for tag in raw.split(",")
        if (lower := tag.lower()) not in not_tags
    ]


def to_scraped_scene(video: dict[str, Any], url: str) -> ScrapedScene:
    studio_name = video["content_provider"][0]["name"]
    performers = [p["name"] for p in video["performers"]]
    scene: ScrapedScene = {
        "title": video["title"],
        "code": str(video["id"]),
        "urls": [url],
        "studio": {"name": studio_name, "parent": {"name": "Bellesa"}},
        "performers": [{"name": name} for name in performers],
        # Released at 08:00 Pacific, so UTC gives the site's own date anywhere
        "date": datetime.fromtimestamp(video["posted_on"], UTC).date().isoformat(),
    }
    if details := video.get("description"):
        scene["details"] = details
    if image := video.get("image"):
        scene["image"] = image
    if duration := video.get("duration"):
        scene["duration"] = duration
    not_tags = BAD_TAGS | {studio_name.lower()} | {p.lower() for p in performers}
    if tags := to_tags(video.get("tags") or "", not_tags):
        scene["tags"] = tags
    return scene


def scene_from_url(url: str) -> ScrapedScene | None:
    if not (match := re.search(r"/videos?/(\d+)", url)):
        log.error(f"No video ID found in {url}")
        return None
    api_url = f"https://www.bellesa.co/api/rest/v1/videos/{match.group(1)}"
    try:
        res = requests.get(api_url, timeout=30)
    except requests.RequestException as e:
        log.error(f"Failed to fetch {api_url}: {e}")
        return None
    # Premium videos answer 402 Payment Required, but the body still has the metadata
    if res.status_code not in (200, 402):
        log.error(f"HTTP {res.status_code} for {api_url}")
        return None
    data = res.json()
    video = data.get("value") or data

    # bellesa.co also carries free redistributions and delayed scenes
    if video["access"]["plus"] != 1 or video["access"]["bellesa"] == 1:
        log.error("This video is from bellesa.co (free), not bellesaplus.co (premium)")
        return None
    if video["content_provider"][0]["handle"] not in BELLESA_STUDIO_HANDLES:
        log.error("This video is not from a Bellesa original series/studio")
        return None
    return to_scraped_scene(video, url)


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
