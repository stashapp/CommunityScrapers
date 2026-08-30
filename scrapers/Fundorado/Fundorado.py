import atexit
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

from py_common import log
from py_common.types import ScrapedScene, ScrapedStudio
from py_common.util import scraper_args, dig

# studio_id and studio.name in the API are production houses or suppliers
# and not necessarily what we understand as studios in Stash
# NOTE: this part of the scraper is the most likely to need updating in the future
OWN_SITES: dict[str, tuple[str, str | None]] = {
    "taworship.com": ("TA Worship", "United Content"),
    "texasbukkake.com": ("Texas Bukkake", "United Content"),
    "tickleabuse.com": ("Tickle Abuse", "United Content"),
    "orgasmabuse.com": ("Orgasm Abuse", "United Content"),
    "rfmovies.com": ("RF Studio", "United Content"),
    "femdorado.com": ("FemDorado", None),
    "lezdorado.com": ("LezDorado", None),
    "sapphofilms.com": ("Sappho Films", None),
    "teencoreclub.com": ("Teen Core Club", None),
    "assteenmouth.com": ("Ass Teen Mouth", "Teen Core Club"),
    "brutalinvasion.com": ("Brutal Invasion", "Teen Core Club"),
    "defiled18.com": ("Defiled 18", "Teen Core Club"),
    "doubleteamedteens.com": ("Double Teamed Teens", "Teen Core Club"),
    "girlsgotcream.com": ("Girls Got Cream", "Teen Core Club"),
    "maketeengape.com": ("Make Teen Gape", "Teen Core Club"),
    "teachmyass.com": ("Teach My Ass", "Teen Core Club"),
    "teenanalcasting.com": ("Teen Anal Casting", "Teen Core Club"),
    "tryteens.com": ("Try Teens", "Teen Core Club"),
    "whiteteensblackcocks.com": ("White Teens Black Cocks", "Teen Core Club"),
    "youngthroats.com": ("Young Throats", "Teen Core Club"),
    "analcheckups.com": ("Anal Checkups", "Teen Core Club"),
    "analyzedgirls.com": ("Analyzed Girls", "Teen Core Club"),
    "bangteenpussy.com": ("Bang Teen Pussy", "Teen Core Club"),
    "cumaholicteens.com": ("Cumaholic Teens", "Teen Core Club"),
    "drilledchicks.com": ("Drilled Chicks", "Teen Core Club"),
    "fabsluts.com": ("Fab Sluts", "Teen Core Club"),
    "hardcoreyouth.com": ("Hardcore Youth", "Teen Core Club"),
    "littlehellcat.com": ("Little Hellcat", "Teen Core Club"),
    "nylonsweeties.com": ("Nylon Sweeties", "Teen Core Club"),
    "seductive18.com": ("Seductive 18", "Teen Core Club"),
    "shegotsix.com": ("She Got Six", "Teen Core Club"),
    "spearteenpussy.com": ("Spear Teen Pussy", "Teen Core Club"),
    "spermantino.com": ("Spermantino", "Teen Core Club"),
    "teendrillers.com": ("Teen Drillers", "Teen Core Club"),
    "teensnaturalway.com": ("Teens Natural Way", "Teen Core Club"),
    "teenstryblacks.com": ("Teens Try Blacks", "Teen Core Club"),
    "weneednewtalents.com": ("We Need New Talents", "Teen Core Club"),
    "nylonspunkjunkies.com": ("Nylon Spunk Junkies", "XCoreClub"),
    "xcoreclub.com": ("XCoreClub", None),
    "dreamteenshd.com": ("Dreamteens HD", "Teen Core Club"),
    "jerk-offpass.com": ("Jerk Off Pass", "Teen Core Club"),
    "teensgoporn.com": ("Teens Go Porn", "Teen Core Club"),
    "teencorezine.com": ("Teencore Zine", "Teen Core Club"),
}

SCENE_URL = re.compile(r"https?://(?:www\.)?([\w.-]+)/video/(\d+)")

# The API serialises publication dates as midnight in Europe/Amsterdam, which is
# always 22:00 or 23:00 UTC on the previous day depending on daylight saving
AMSTERDAM_MAX_OFFSET = timedelta(hours=2)

__STUDIO_CACHE_FILE = Path(__file__).parent / "studio_cache.json"
try:
    __STUDIO_CACHE: dict[str, str] = json.load(
        __STUDIO_CACHE_FILE.open(encoding="utf-8")
    )
except (FileNotFoundError, json.JSONDecodeError):
    __STUDIO_CACHE = {}


@atexit.register
def __save_studio_cache():
    sorted_cache = dict(sorted(__STUDIO_CACHE.items(), key=lambda x: int(x[0])))
    json.dump(sorted_cache, __STUDIO_CACHE_FILE.open("w", encoding="utf-8"), indent=2)


def studio_name_from_id(studio_id: int) -> str | None:
    key = str(studio_id)
    if key in __STUDIO_CACHE:
        return __STUDIO_CACHE[key]

    try:
        response = requests.get(
            "https://api.fundorado.com/api/meta/studiobyids",
            params={"ss": key},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json()
    except requests.RequestException as e:
        log.warning(f"Failed to look up studio_id {studio_id}: {e}")
        return None
    if not results:
        log.warning(f"Unknown studio_id: {studio_id}")
        return None

    name = results[0]["name"]
    __STUDIO_CACHE[key] = name
    return name


def localized(field: dict | None) -> str:
    if not field:
        return ""
    return field.get("en") or next(iter(field.values()), "")


def release_date(timestamp: str | None) -> str | None:
    if not timestamp:
        return None
    published = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if published.year < 1970:
        return None
    return (published + AMSTERDAM_MAX_OFFSET).date().isoformat()


def cover_image(video: dict) -> str | None:
    if url := dig(video, ("artwork", "artwork_f16", "cover"), "large"):
        return url if url.startswith("http") else f"https://s01.uni73d.net/{url}"
    return None


def studio_for(hostname: str, video: dict) -> ScrapedStudio | None:
    if own := OWN_SITES.get(hostname):
        name, parent = own
        studio: ScrapedStudio = {"name": name}
        if parent:
            studio["parent"] = {"name": parent}
        return studio

    if (studio_id := video.get("studio_id")) and (
        name := studio_name_from_id(studio_id)
    ):
        return {"name": name}
    return None


def is_bulk_migrated(hostname: str, video: dict) -> bool:
    # These sites have been bought out and have misleading dates from
    # the bulk import process into Fundorado
    if not (own := OWN_SITES.get(hostname)):
        return False
    return (raw_name := dig(video, "studio", "name")) and (
        raw_name.casefold() != own[0].casefold()
    )


def scene_from_url(url: str) -> ScrapedScene | None:
    match = SCENE_URL.match(url)
    if not match:
        log.error(f"Not a supported scene URL: {url}")
        return None

    hostname, video_id = match.group(1).lower(), match.group(2)

    try:
        response = requests.get(f"https://api.fundorado.com/api/videodetail/{video_id}")
        response.raise_for_status()
    except requests.HTTPError as e:
        log.info(f"No scene found with id {video_id}: {e}")
        return None
    except requests.RequestException as e:
        log.error(f"Request failed for video {video_id}: {e}")
        return None

    if not (video := response.json().get("video")):
        log.error(f"No scene found with id {video_id}")
        return None

    scene: ScrapedScene = {
        "title": localized(video.get("title")),
        "details": localized(video.get("description")),
        "code": str(video["id"]),
        "urls": [f"https://{hostname}/video/{video['id']}/{video['slug']}"],
        "performers": [{"name": actor["name"]} for actor in video.get("actors", [])],
        "tags": [
            {"name": localized(genre.get("title"))} for genre in video.get("genres", [])
        ],
    }

    if studio := studio_for(hostname, video):
        scene["studio"] = studio

    # Bulk migrated videos have messed up their original release date
    # but they might still remember the original year of release
    if is_bulk_migrated(hostname, video):
        if year := dig(video, "meta", "year"):
            scene["date"] = str(year)
    elif date := release_date(video.get("publication_date")):
        scene["date"] = date
    if image := cover_image(video):
        scene["image"] = image
    # if duration := dig(video, "meta", "duration_seconds"):
    #     scene["duration"] = duration

    return scene


if __name__ == "__main__":
    op, args = scraper_args()

    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(
                f"Not implemented: Operation: {op}, arguments: {json.dumps(args)}"
            )
            sys.exit(1)

    print(json.dumps(result))
