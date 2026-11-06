import base64
import importlib
import json
import re
import sys
import time
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from py_common import log
from py_common.config import get_config
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedStudio
from py_common.util import dig, is_own_url, scraper_args

ensure_requirements("cloudscraper")
import cloudscraper  # noqa: E402

config = get_config(
    default="""
# Debug mode will save the latest API response to disk
debug = False

# Cookies straight from your browser
ts_token =
su_token =
"""
)

scraper = cloudscraper.create_scraper()

# Maps upsell_id from the API's site object to the parent network studio.
# upsell_id is the site ID of the network membership a sub-site upsells to,
# which reliably identifies which network a studio belongs to.
NETWORK_BY_UPSELL_ID: dict[int, ScrapedStudio] = {
    1: {"name": "TeamSkeet", "urls": ["https://www.teamskeet.com/"]},
    46: {"name": "Swappz", "urls": ["https://www.swappz.com/"]},
    47: {"name": "Freeuse", "urls": ["https://www.freeuse.com/"]},
    48: {"name": "Pervz", "urls": ["https://www.pervz.com/"]},
    49: {"name": "Family Strokes", "urls": ["https://www.familystrokes.com/"]},
    50: {"name": "Reptyle", "urls": ["https://app.reptyle.com/"]},
    159: {"name": "MYLF", "urls": ["https://www.mylf.com/"]},
}

studio_map = {
    # TeamSkeet
    "BFFS": "BFFs",
    "BadMilfs": "Bad MILFs",
    "DadCrush": "Dad Crush",
    "Extras": "TeamSkeet Extras",
    "GingerPatch": "Ginger Patch",
    "Hussie Pass": "Hussie Pass (Reptyle)",
    "StayHomePOV": "Stay Home POV",
    "StepSiblings": "Step Siblings",
    "TeenJoi": "Teen JOI",
    "TeamSkeet X BritStudioxxx": "TeamSkeet X BritStudio.XXX",
    "TeamSkeet X EvilAngel": "TeamSkeet X Evil Angel",
    "TeamSkeet X Joy Bear": "TeamSkeet X JoyBear",
    "TeamSkeet X Molly RedWolf": "TeamSkeet X MollyRedWolf",
    "TeamSkeet X OZ Fellatio Queens": "TeamSkeet X Aussie Fellatio Queens",
    "TeamSkeet X SpankMonster": "TeamSkeet X Spank Monster",
    # Family Strokes
    "Family Strokes": "Family Strokes: The Series",
    "Not My Grandpa": "Not My Grandpa!",
    # Freeuse
    "FreeUse Milf": "Freeuse MILF",
    "FreeUse Singles": "Freeuse Singles",
    "UsePOV": "Use POV",
    # MYLF
    "AnalMom": "Anal Mom",
    "BBCParadise": "BBC Paradise",
    "FullOfJoi": "Full Of JOI",
    "GotMylf": "Got MYLF",
    "LoneMilf": "Lone MILF",
    "MYLF Of The Month": "MYLF of the Month",
    "MilfBody": "MILF Body",
    "MomDrips": "Mom Drips",
    "MomShoot": "Mom Shoot",
    "MylfBlows": "MYLF Blows",
    "MylfBoss": "MYLF Boss",
    "MylfSelects": "MYLF Selects",
    "StayHomeMilf": "Stay Home MILF",
    # SayUncle
    "Black Godz": "BlackGodz",
    "BottomGames": "Bottom Games",
    "BoysDoPorn": "Boys Do Porn",
    "DadCreep": "Dad Creep",
    "DoctorTapes": "Doctor Tapes",
    "StayHomeBro": "Stay Home Bro",
    "StickyRub": "Sticky Rub",
    "MilitaryDick": "Military Dick",
    "TherapyDick": "Therapy Dick",
    "TroopSex": "Troop Sex",
    "YesFather": "Yes Father",
}

# Default tags for studios
# note that names are already translated through the above studio_map
default_tags = {
    "TeamSkeet Classics": ["Re-release"],
    "TeamSkeet Selects": ["Compilation"],
    "Mylf Classics": ["Re-release"],
    "Mylf Selects": ["Compilation"],
    "SayUncle Classics": ["Re-release"],
}

tags_map = {
    # As documented by feederbox826 TeamSkeet are inconsistent with this tag so we generalize it
    "Pumps": "Woman's Heels",
    "Boy / Girl": "Twosome (Straight)",
    "Girl / Girl": "Twosome (Lesbian)",
    "Boy / Boy": "Twosome (Gay)",
    "Boy / Girl / Girl": "Threesome (BGG)",
    "Boy / Boy / Girl": "Threesome (BBG)",
    "Girl / Girl / Girl": "Threesome (Lesbian)",
    "Boy / Boy / Boy": "Threesome (Gay)",
    "Boy / Girl / Boy / Girl": "Foursome (BBGG)",
    "Boy / Girl / Girl / Girl": "Foursome (BGGG)",
    "Girl / Boy / Boy / Boy": "Foursome (BBBG)",
    "2 Girl Bj": "Double Blowjob (2 Mouths)",
    "Veiny": "Veiny Dick",
}


Postprocess = Callable[[ScrapedScene, dict[str, Any]], ScrapedScene]


def default_postprocess(obj: Any, _: Any) -> Any:
    return obj


def format_date(raw: int | str) -> str:
    # Members APIs have UNIX epoch timestamps
    if isinstance(raw, int):
        return datetime.fromtimestamp(raw, tz=UTC).date().isoformat()

    # Other sites generally have ISO-8601-compliant datetimes
    return datetime.fromisoformat(raw).date().isoformat()


def upgrade_image(image_url: str) -> str:
    log.debug(f"Attempting to upgrade image: {image_url}")
    # members/full - 1600x900
    # bio_big - 1500x844
    # shared/hi - 1280x720
    # shared/med - 765x430
    for replacement in ["members/full", "bio_big", "shared/hi"]:
        newurl = image_url.replace("shared/med", replacement)
        try:
            log.debug(f"Trying {newurl}")
            if scraper.head(newurl, timeout=2.5).ok:
                log.debug(f"Found better image at {newurl}")
                return newurl
        except Exception as e:  # noqa: BLE001 any failure means no better image here
            log.debug(f"{newurl} failed: {e}")

    # try shared/hi on /tour url
    # get the subsite name
    subsite = image_url.split("/")[4]

    # replace with /tour/pics
    tourHi = image_url.replace(f"/{subsite}", f"/{subsite}/tour/pics").replace(
        "shared/med", "shared/hi"
    )

    try:
        log.debug(f"Trying {tourHi}")
        if scraper.head(tourHi, timeout=1).ok:
            log.debug(f"Found better image at {tourHi}")
            return tourHi
    except Exception as e:  # noqa: BLE001 any failure means no better image here
        log.debug(f"{tourHi} failed: {e}")

    # fallback to original image
    log.debug("Unable to find better image")
    return image_url


def _import_zip_module(zip_path: Path, module_name: str) -> ModuleType | None:
    if not zip_path.exists():
        return None
    zip_path_str = str(zip_path.absolute())
    if zip_path_str not in sys.path:
        sys.path.insert(0, zip_path_str)
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def _local() -> ModuleType | None:
    return _import_zip_module(Path(__file__).with_name("bin"), "psm_creds")


def _remote() -> ModuleType | None:
    cache_path = Path(__file__).with_name(".cache")
    stale = (
        not cache_path.exists()
        or time.time() - cache_path.stat().st_mtime > 24 * 60 * 60
    )
    if stale:
        try:
            response = scraper.get(
                "https://gist.githubusercontent.com/Maista6969/65e8958c565f33bc8b977fc45c17151e/raw/cache",
                timeout=5,
            )
            response.raise_for_status()
            cache_path.write_bytes(base64.b64decode(response.text))
        except Exception as e:  # noqa: BLE001 a stale cache is still usable
            log.debug(f"Unable to refresh credentials cache: {e}")
    return _import_zip_module(cache_path, "psm_creds")


_creds: dict[str, str] | None = None


def get_cookies_for(url: str) -> dict[str, str]:
    global _creds
    if _creds is None:
        if module := (_local() or _remote()):
            _creds = {"TS": module.TS, "SU": module.SU}
        elif config.ts_token or config.su_token:
            _creds = {"TS": config.ts_token, "SU": config.su_token}
        else:
            _creds = {}

    if "reptyle.com" in url and _creds.get("TS"):
        return {"access_token": _creds["TS"], "referer": url}
    if "sayuncle.com" in url and _creds.get("SU"):
        return {"access_token": _creds["SU"], "referer": url}
    return {}


def guess_extra_tags(scene: ScrapedScene) -> Generator[str, None, None]:
    studio_name = dig(scene, "studio", "name")
    studio_tags = default_tags.get(studio_name, [])
    yield from studio_tags

    # Do not guess scene makeup for compilations
    if "Compilation" in studio_tags:
        return

    genders = sorted(
        [dig(p, "gender", default="") for p in dig(scene, "performers", default=[])],
        reverse=True,
    )

    # currently only accounts for MALE and FEMALE because PSM doesn't
    # seem to feature anything outside of the binary on their sites
    guess = None
    match genders:
        case ["MALE", "FEMALE"]:
            guess = "Twosome (Straight)"
        case ["FEMALE", "FEMALE"]:
            guess = "Twosome (Lesbian)"
        case ["MALE", "MALE"]:
            guess = "Twosome (Gay)"

        case ["MALE", "FEMALE", "FEMALE"]:
            guess = "Threesome (BGG)"
        case ["MALE", "MALE", "FEMALE"]:
            guess = "Threesome (BBG)"
        case ["FEMALE", "FEMALE", "FEMALE"]:
            guess = "Threesome (Lesbian)"
        case ["MALE", "MALE", "MALE"]:
            guess = "Threesome (Gay)"

        case ["MALE", "MALE", "FEMALE", "FEMALE"]:
            guess = "Foursome (BBGG)"
        case ["MALE", "MALE", "MALE", "FEMALE"]:
            guess = "Foursome (BBBG)"
        case ["MALE", "FEMALE", "FEMALE", "FEMALE"]:
            guess = "Foursome (BGGG)"
        case ["MALE", "MALE", "FEMALE", "FEMALE"]:
            guess = "Foursome (BBGG)"
        case ["FEMALE", "FEMALE", "FEMALE", "FEMALE"]:
            guess = "Foursome (Lesbian)"
        case ["MALE", "MALE", "MALE", "MALE"]:
            guess = "Foursome (Gay)"

    if not guess:
        return
    log.trace(f"Adding '{guess}' tag based on scene performer makeup")
    yield guess


def to_scraped_performer(performer_from_api: dict[str, Any]) -> ScrapedPerformer:
    performer: ScrapedPerformer = {
        "name": dig(performer_from_api, ("name", "modelName", "title"))
    }
    if gender := dig(performer_from_api, "gender"):
        performer["gender"] = gender.upper()
    if ethnicity := dig(performer_from_api, "ethnicity"):
        performer["ethnicity"] = ethnicity
    if hair_color := dig(performer_from_api, "hairColor"):
        performer["hair_color"] = hair_color
    if img := dig(performer_from_api, "img"):
        performer["images"] = [img]

    return performer


def network_for(site: dict[str, Any]) -> ScrapedStudio | None:
    match site.get("upsell_id"):
        case int(upsell_id):
            return NETWORK_BY_UPSELL_ID.get(upsell_id)
        case str(upsell_id) if upsell_id.isdigit():
            return NETWORK_BY_UPSELL_ID.get(int(upsell_id))
    return None


def with_network_from_url(scene: ScrapedScene, url: str) -> ScrapedScene:
    "Newer sub-sites have no upsell_id, but their public pages live on the network's domain"
    host = urlsplit(url).netloc.removeprefix("www.")
    if (
        (studio := scene.get("studio"))
        and "parent" not in studio
        and host
        and not host.startswith("app.")
        and (
            network := next(
                (
                    n
                    for n in NETWORK_BY_UPSELL_ID.values()
                    if host in dig(n, "urls", 0, default="")
                ),
                None,
            )
        )
    ):
        return {**scene, "studio": {**studio, "parent": network}}
    return scene


def to_scraped_studio(studio_from_api: dict[str, Any]) -> ScrapedStudio:
    raw_name: str = dig(studio_from_api, ("siteName", "name"), default="")
    name = studio_map.get(raw_name, raw_name)
    studio: ScrapedStudio = {"name": name}
    if parent := network_for(studio_from_api):
        studio["parent"] = parent
    # Reptyle-branded studios can carry upsell_id=1 (TeamSkeet) during the brand
    # transition, so override the parent by name for those cases.
    if name and ("Reptyle" in name or "Hussie Pass" in name):
        studio["parent"] = {"name": "Reptyle", "urls": ["https://app.reptyle.com/"]}
    return studio


def get_object_code(result_from_api: dict[str, Any]) -> str | None:
    if (_id := dig(result_from_api, ("itemId", "id"))) and (isinstance(_id, int)):
        return str(_id)
    return None


def to_scraped_scene(
    scene_from_api: dict[str, Any], better_image: bool = True
) -> ScrapedScene:
    scene: ScrapedScene = {
        "title": scene_from_api["title"],
        "date": format_date(scene_from_api["publishedDate"]),
        "performers": [to_scraped_performer(m) for m in scene_from_api["models"]],
        "image": upgrade_image(scene_from_api["img"])
        if better_image
        else scene_from_api["img"],
    }

    if code := get_object_code(scene_from_api):
        scene["code"] = code

    if details := dig(scene_from_api, "description"):
        details = unescape(details)
        # Strip HTML tags
        details = re.sub(r"</?[^>]+>", "", details).strip()
        scene["details"] = details

    if site := dig(scene_from_api, "site"):
        scene["studio"] = to_scraped_studio(site)

    # Public scrapes have a string id like `name-of-scene` while
    # private scrapes have a numeric id like 12345
    if (slug := dig(scene_from_api, ("slug", "id"))) and (isinstance(slug, str)):
        if site and (network_url := dig(network_for(site) or {}, "urls", 0)):
            scene["urls"] = [f"{network_url}movies/{slug}"]
        else:
            scene["urls"] = [f"https://www.placeholder.com/movies/{slug}"]

    primary_tags = dig(scene_from_api, "primary_tags", default=[])
    tags = dig(scene_from_api, "tags", default=[])
    all_tags = [dig(tags_map, t, default=t) for t in primary_tags + tags if t != "null"]
    all_tags = [x for x in all_tags if x]
    all_tags.extend(guess_extra_tags(scene))
    scene["tags"] = [{"name": t} for t in sorted(set(all_tags))]

    return scene


# Reptyle's Astro pages don't embed their API endpoint and no single bundle index
# covers a whole network (ts_network lacks most Freeuse/MYLF/Pervz scenes),
# so we search every per-site index of the network at once
NETWORK_BUNDLES = (
    ("sayuncle.com", "https://tours-store.psmcdn.net/tour_sau_*/_search", "SayUncle"),
    (
        "",
        "https://tours-store.psmcdn.net/tour_*,-tour_sau_*/_search",
        "TeamSkeet",
    ),
)


def get_network_bundle_for(netloc: str) -> tuple[str, str]:
    for domain, api, network in NETWORK_BUNDLES:
        if domain in netloc:
            return api, network
    raise AssertionError("unreachable: last bundle matches every netloc")


def get_members_prefix(network: str) -> str:
    match network:
        case "SayUncle":
            return "https://app.sayuncle.com/movies/"
        case _:
            return "https://app.reptyle.com/movies/"


# Given a public URL belonging to a PSM site this will return
# a 3-tuple containing the API endpoint for its members area,
# the prefix for a members area URL and the public URL for the
# scene, if possible: if there's no way to determine the public
# URL then the input URL will be returned as then third element
def get_endpoint_for(url: str) -> tuple[str, str, str] | None:
    _, netloc, path, *_ = urlsplit(url)
    identifier = path.split("/")[-1]

    # Hardcode the endpoints for member URLs
    if "app.reptyle.com" in netloc:
        return (
            f"https://ma-store.reptyle.com/ts_index/_doc/movie-{identifier}/",
            "https://app.reptyle.com/movies/",
            url,
        )
    if "app.sayuncle.com" in netloc:
        return (
            f"https://ma-store.sayuncle.com/cm_index/_doc/movie-{identifier}/",
            "https://app.sayuncle.com/movies/",
            url,
        )

    # Otherwise we find the endpoint in the page HTML
    response = scraper.get(url)
    # This redirect sometimes goes to the "series" page instead of the
    # correct scene page so we'll need to reconstruct the URL
    scheme, netloc, *_ = urlsplit(response.url)
    final_url = urlunsplit((scheme, netloc, f"movies/{identifier}", None, None))
    raw_html = response.text

    if (
        (m := re.search(r'contentEndpoint":"([^"]+)"', raw_html))
        and (api := m.group(1))
        and (n := re.search(r'network_name":"([^"]+)"', raw_html))
        and (network := n.group(1))
    ):
        log.debug(f"Found {network} endpoint at {url} | {api}")
    else:
        api, network = get_network_bundle_for(netloc)
        log.debug(f"No endpoint in page data, falling back to {network} bundle | {api}")

    return (
        f'{api}?q=id.keyword:"{identifier}"&size=3',
        get_members_prefix(network),
        final_url,
    )


def scene_from_url(
    url: str,
    postprocess: Postprocess = default_postprocess,
) -> ScrapedScene | None:
    if not (tup := get_endpoint_for(url)):
        return None

    api_endpoint, members_prefix, final_url = tup
    cookies = get_cookies_for(url)
    scraper.cookies.update(cookies)

    log.debug(f"Asking API at {api_endpoint}")
    response = scraper.get(api_endpoint)
    if response.status_code != 200:
        log.debug(f"Got {response.status_code} result from {api_endpoint}")
        return None

    response = response.json()

    if config.debug:
        with open("psm_scene_response.json", "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2)

    # We can't use final_url here because it could have redirected
    # to a series page or even a different scene
    _, _, path, *_ = urlsplit(url)
    slug = path.split("/")[-1]

    # If the scene has been removed the search can
    # theoretically return multiple similar scenes (or even models)
    hits = dig(response, "hits", "hits", default=[])
    scene_candidates = [
        hit["_source"]
        for hit in hits
        if hit["_id"].startswith("movie") and hit["_source"]["id"] == slug
    ]

    # Scene objects are the same whether we get them from a "search" in an old-style
    # endpoint or a direct document reference in a new-stylee endpoint
    if not (result := dig(response, "_source") or dig(scene_candidates, 0)):
        log.warning(f"No scene found at {url}")
        return None
    if not (code := get_object_code(result)):
        log.warning("Unable to find scene code for result")
        return postprocess(to_scraped_scene(result), result)

    # If we can scrape the members URL we throw away the normal result and use
    # privileged member section data instead as it's almost certainly more correct
    if (
        (members_url := f"{members_prefix}{code}")
        and (members_url != url)
        and (scene := scene_from_url(members_url, postprocess=postprocess))
    ):
        scene["urls"] = [final_url, members_url]
        return with_network_from_url(scene, final_url)

    # Scraped from a public page, so the URL is already in Stash
    # and the one we constructed could be wrong
    scene = postprocess(to_scraped_scene(result), result)
    scene.pop("urls", None)
    return with_network_from_url(scene, final_url)


def scene_search(
    query: str,
    search_url: str = "https://ma-store.reptyle.com/rs/",
    postprocess: Postprocess = default_postprocess,
) -> list[ScrapedScene]:
    if not query:
        log.error("No query provided")
        return []

    params = {"q": query, "user_id": 1234567, "count": 8}

    cookies = get_cookies_for(search_url)
    scraper.cookies.update(cookies)

    response = scraper.get(search_url, params=params)
    if response.status_code != 200:
        log.error(f"Got {response.status_code} result when searching {response.url}")
        log.error(response.text)
        return []

    response = response.json()

    if config.debug:
        with open("psm_search_response.json", "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2)

    return [
        postprocess(to_scraped_scene(c["_source"], better_image=False), c["_source"])
        for c in dig(response, "hits", "hits", default=[])
        if c["_id"].startswith("movie")
    ]


def scene_from_fragment(
    fragment: dict[str, Any],
    search_url: str = "https://ma-store.reptyle.com/rs/",
    postprocess: Postprocess = default_postprocess,
) -> ScrapedScene | None:
    for url in fragment.get("urls") or []:
        if not is_own_url(url):
            continue
        log.debug(f"Using scene URL: '{url}'")
        if scene := scene_from_url(url, postprocess=postprocess):
            return scene
        log.debug("Failed to scrape scene from URL")
    if title := fragment.get("title"):
        log.debug(f"Searching for '{title}'")
        if scenes := scene_search(
            title, search_url=search_url, postprocess=postprocess
        ):
            return scenes.pop(0)
        log.debug("Failed to find scene by title")

    log.warning("Cannot scrape from this fragment: need to have title or url set")


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": query}:
            result = scene_search(query)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
