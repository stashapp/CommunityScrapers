import json
import sys
from typing import Any
from urllib.parse import urlparse

from Altwolia.scrape import (
    gallery_from_fragment,
    gallery_from_url,
    movie_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
)

from py_common import log
from py_common.util import dig, replace_all, scraper_args

# This map just contains overrides when using a channel name as the studio
channel_name_map = {
    "Adam And Eve Pictures": "Adam & Eve Pictures",
    "Age & Beauty": "Age and Beauty",
    "Black Money Erotica": "Adult Time x Black Money Erotica",
    "Bratty Sis": "Adult Time x Bratty Sis",
    "Cuck Hunter": "Adult Time x Cuck Hunter",
    "Frameleaks": "Adult Time x Frameleaks",
    "Heteroflexible": "HeteroFlexible",
    "Horny Household": "Adult Time x Horny Household",
    "Hussie Pass": "Adult Time x Hussie Pass",
    "JOI Mom": "J.O.I Mom",
    "Lady Lazarus": "Adult Time x Lady Lazarus",
    "LesbianX": "Adult Time x LesbianX",
    "LucidFlix": "Adult Time x LucidFlix",
    # API returns a curly apostrophe, StashDB's studio uses a straight one
    "Mommy’s Boy": "Mommy's Boy",
    "Slayed": "Adult Time x Slayed",
    "Taboo Heat": "Adult Time x Taboo Heat",
    "Vixen": "Adult Time x Vixen",
}

# Each network_name requiring a map/override should have a key-value here
network_name_map = {}

# Each serie_name requiring a map/override should have a key-value here
serie_name_map = {
    "20 Questions": "20 Random Questions With",
    "Oopsie": "Oopsie!",
    "Transfixed Muses": "Transfixed",
}

# Each site found in availableOnSite requiring a map/override should have a
# key-value here
site_map = {
    "AdultTimePilots": "Adult Time Pilots",
    "agentredgirl": "Agent Red Girl",
    "asmrfantasy": "ASMR Fantasy",
    "bethecuck": "Be the Cuck",
    "devilstgirls": "Devil's Tgirls",
    "girlsunderarrest": "Girls Under Arrest",
    "grinders-channel": "Grinders",
    "howwomenorgasm-channel": "How Women Orgasm",
    "officemsconduct-channel": "Transfixed",
    "SuperHornyFunTime": "Super Horny Fun Time",
}

# Each sitename_pretty requiring a map/override should have a key-value here
sitename_pretty_map = {
    "Devilstgirls": "Devil's Tgirls",
}


def determine_studio(api_object: dict[str, Any]) -> str | None:
    """
    Determine studio name from API object properties to use instead of the
    `studio_name` property scraped by default
    """
    available_on_site = api_object.get("availableOnSite", [])
    main_channel_name = dig(api_object, "mainChannel", "name")
    network_name = api_object.get("network_name")
    serie_name = api_object.get("serie_name")
    sitename_pretty = api_object.get("sitename_pretty")
    log.debug(
        f"available_on_site: {available_on_site}, "
        f"main_channel_name: {main_channel_name}, "
        f"network_name: {network_name}, "
        f"serie_name: {serie_name}, "
        f"sitename_pretty: {sitename_pretty}, "
    )

    if serie_name in [
        *serie_name_map,
        "Accidental Gangbang",
        "Casey: A True Story",
        "Daddy's Girl",
        "Feed Me",
        "Future Darkly",
        "Go Stuck Yourself",
        "How Women Orgasm",
        "LeTS Be Bad",
        "Mommy's Boy",
        "Oopsie",
        "Perspective",
        "Poly Family Life",
        "Sister Trick",
        "Sweet Sweet Sally Mae",
        "Teen Overload",
        "Teenage Lesbian",
        "The Mike and Joanna Show",
        "Tomboyish",
        "Up Close",
        "Up Close VR",
        "Women's World",
    ]:
        log.debug(f"matched serie_name '{serie_name}'")
        return serie_name_map.get(serie_name, serie_name)
    # steps through availableOnSite, and picks the first match
    if site_match := next(
        (site for site in available_on_site if site in site_map), None
    ):
        log.debug(f"matched site '{site_match}' in {available_on_site}")
        return site_map.get(site_match, site_match)
    if network_name in ["Adult Time Films"]:
        log.debug(f"matched network_name '{network_name}'")
        return network_name_map.get(network_name, network_name)
    if sitename_pretty in [*sitename_pretty_map, "Devil's Film", "Transfixed"]:
        log.debug(f"matched sitename_pretty '{sitename_pretty}'")
        return sitename_pretty_map.get(sitename_pretty, sitename_pretty)
    if main_channel_name:
        # most scenes have the studio name as the main channel name
        log.debug(f"matched main_channel_name '{main_channel_name}'")
        return channel_name_map.get(main_channel_name, main_channel_name)
    log.debug("no override matched")
    return None


MEMBERS_HOST = "members.adulttime.com"

PUBLIC_DOMAINS = {
    "21naturals", "21sextreme", "21sextury", "accidentalgangbang",
    "ageandbeauty", "agentredgirl", "allgirlmassage", "analteenangels",
    "asmrfantasy", "assholefever", "devilsfilm", "devilsfilmparodies",
    "devilsgangbangs", "devilstgirls", "dpfanatics", "fantasymassage",
    "femalesubmission", "femboyish", "footsiebabes", "futaworld",
    "getupclose", "girlstryanal", "girlsunderarrest", "girlsway",
    "givemeteens", "hairyundies", "hentaisexschool", "heteroflexible",
    "isthisreal", "jerk-buddies", "joymii", "ladygonzo", "lezbebad",
    "lezcuties", "massage-parlor", "milkingtable", "mixedx", "modeltime",
    "moderndaysins", "mommysboy", "mommysgirl", "nudefightclub",
    "nurumassage", "oopsie", "oopsieanimated", "outofthefamily",
    "peternorth", "prettydirty", "puretaboo", "sistertrick",
    "soapymassage", "thebrats", "transfixed", "trickyspa", "truelesbian",
    "upclosevr", "vivid", "webyoung", "welikegirls", "wheretheboysarent",
    "whiteghetto",
}

# A handful of availableOnSite tags don't literally match their real
# domain name (e.g. futaworld's own scenes are tagged "futaworld-at")
SITE_ALIASES = {
    "futaworld-at": "futaworld",
}


def public_url(api_object: dict[str, Any]) -> str | None:
    "A direct link on a PUBLIC_DOMAINS site, if this object has one"
    sitename = api_object.get("sitename")
    domain = next(
        (
            resolved
            for site in api_object.get("availableOnSite", [])
            if (resolved := SITE_ALIASES.get(site.lower(), site.lower()))
            in PUBLIC_DOMAINS
        ),
        None,
    )
    if not (sitename and domain):
        return None
    if (clip_id := api_object.get("clip_id")) and (
        url_title := api_object.get("url_title")
    ):
        return f"https://www.{domain}.com/en/video/{sitename}/{url_title}/{clip_id}"
    if (movie_id := api_object.get("movie_id")) and (
        url_title := api_object.get("url_title")
    ):
        return f"https://www.{domain}.com/en/movie/{url_title}/{movie_id}"
    if (set_id := api_object.get("set_id")) and (
        url_title := api_object.get("url_title")
    ):
        return f"https://www.{domain}.com/en/photo/{url_title}/{set_id}"
    return None


def adulttime(obj: Any, api_object: dict[str, Any]) -> Any:
    if studio_override := determine_studio(api_object):
        obj = replace_all(obj, "studio", lambda s: {**s, "name": studio_override})

    sitename = api_object.get("sitename")

    def to_members_url(url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path
        if sitename and "/en/video/" in path:
            head, _, tail = path.partition("/en/video/")
            _, _, rest = tail.partition("/")
            path = f"{head}/en/video/{sitename}/{rest}"
        return parsed._replace(netloc=MEMBERS_HOST, path=path).geturl()

    obj = replace_all(obj, "urls", to_members_url)

    if (
        not obj.get("urls")
        and sitename
        and (clip_id := api_object.get("clip_id"))
    ):
        url_title = api_object.get("url_title", "")
        obj = {
            **obj,
            "urls": [f"https://{MEMBERS_HOST}/en/video/{sitename}/{url_title}/{clip_id}"],
        }

    if (link := public_url(api_object)) and (urls := obj.get("urls")):
        obj = {**obj, "urls": [link, *urls]}

    return obj


if __name__ == "__main__":
    op, args = scraper_args()

    site = "girlsway"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=adulttime)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=adulttime)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=adulttime)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=adulttime)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=adulttime)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site, postprocess=adulttime)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site, postprocess=adulttime)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site, postprocess=adulttime)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=adulttime)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
