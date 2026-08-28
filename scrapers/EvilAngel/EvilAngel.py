import json
import re
import sys
from typing import Any

from Altwolia.domains import site_name
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
from py_common.util import dig, replace_at, scraper_args

# This map just contains overrides when using a channel name as the studio
channel_name_map = {
    "AnalPlaytime": "Anal Acrobats",
    "Anal Trixxx": "AnalTriXXX",
    "Belladonna": "Belladonna Entertainment",
    "Christoph Clark": "Christoph Clark Online",
    "Jonni Darkko ": "Jonni Darkko XXX",  # trailing space is in the API
    "LatexPlaytime": "Latex Playtime",
    "Le Wood": "LeWood",
    "Secret Crush ": "Secret Crush",  # trailing space is in the API
}

serie_name_map = {
    "TransPlaytime": "TS Playground",
    "XXXmailed": "Blackmailed",
    "Anal.Oil.Latex.": "Latex Playtime",
}

# christophclarkonline/christophsbignaturaltits/gapingangels/euro-angels and
# cockchokingsluts/jakemalone are deliberately NOT here: they routinely co-occur
# on the same scene's availableOnSite (Christoph Clark's niche channels are all
# tagged onto his umbrella site; Cock Choking Sluts scenes are usually also
# tagged jakemalone), so which one is actually "the" studio can't be derived
# from availableOnSite alone. mainChannel is the more reliable signal for that
# whole cluster, so those are handled via channel_name_map/the literal list below
# instead
site_map = {
    "iloveblackshemales": "I Love Black Shemales",
    "johnleslie": "John Leslie",
    "lexingtonsteele": "Lexington Steele",
    "nachovidalhardcore": "Nacho Vidal Hardcore",
    "pansexualx": "PansexualX",
    "pantypops": "Panty Pops",
    "povblowjobs": "POV Blowjobs",
    "roccosiffredi": "Rocco Siffredi",
    "shemaleidol": "Shemale Idol",
    "sheplayswithhercock": "She Plays With Her Cock",
    "strapattackers": "Strap Attackers",
    "tittycreampies": "Titty Creampies",
    "transgressivexxx": "TransgressiveXXX",
    "tsfactor": "TS Factor",
}


def determine_studio(api_object: dict[str, Any]) -> str | None:
    """
    Determine studio name from API object properties to use instead of the
    `studio_name` property scraped by default
    """
    available_on_site = api_object.get("availableOnSite", [])
    main_channel_name = dig(api_object, "mainChannel", "name")
    serie_name = api_object.get("serie_name")
    log.debug(
        f"available_on_site: {available_on_site}, "
        f"main_channel_name: {main_channel_name}, "
        f"serie_name: {serie_name}, "
    )

    # Some Shemale Idol scenes are missing the "shemaleidol" availableOnSite
    # tag entirely and only carry "tsfactor", which would otherwise shadow
    # them via the site_map match below - checked here, ahead of site_map
    if serie_name == "She-Male Idol":
        log.debug("matched serie_name 'She-Male Idol'")
        return "Shemale Idol"

    if site_match := next(
        (site for site in site_map if site in available_on_site), None
    ):
        log.debug(f"matched site '{site_match}'")
        return site_map.get(site_match, site_match)
    if serie_name in [
        *serie_name_map,
        "PansexualX",
        "Panty Pops",
    ]:
        log.debug(f"matched serie_name '{serie_name}'")
        return serie_name_map.get(serie_name, serie_name)
    if main_channel_name in [
        *channel_name_map,
        "Aiden Riley",
        "Buttman",
        "Christoph's Big Natural Tits",
        "Cock Choking Sluts",
        "Euro Angels",
        "Gaping Angels",
        "Jake Malone",
        "Kevin Moore",
        "Transsexual Angel",
        "TransgressiveXXX",
    ]:
        log.debug(f"matched main_channel_name '{main_channel_name}'")
        return channel_name_map.get(main_channel_name, main_channel_name)
    if director_match := next(
        (
            item
            for item in [
                "Joey Silvera",
                "Mike Adriano",
            ]
            if item in [c.get("name") for c in api_object.get("channels", [])]
        ),
        None,
    ):
        log.debug(f"matched director_match '{director_match}'")
        return director_match
    if movie_desc := (api_object.get("movie_desc") or api_object.get("description")):
        if "BAM Visions" in movie_desc:
            log.debug("matched 'BAM Visions' in movie_desc")
            return "BAM Visions"
    log.debug("Did not match any studio override logic")
    return None


def fix_ts_trans_find_replace(text: str) -> str:
    """
    At some point in time, there was a mass find-replace performed that replaced
    all occurrences of "TS" or "ts" with "Trans".

    The problem with this is that it replaced every match naively, resulting in
    these examples:
    - tits -> tiTrans
    - hits -> hiTrans

    This regex sub should undo those changes, but leave the intended change:
    - TS -> Trans
    """
    return re.sub(r"(?<=[a-z])Trans", "ts", text)


def has_working_url_pattern(_url: str) -> bool:
    # These guys run their own storefronts using AdultEmpireCash
    return site_name(_url) not in ["lewood", "lexingtonsteele"]


def evilangel(obj: Any, api_object: dict[str, Any]) -> Any:
    if studio_override := determine_studio(api_object):
        obj = {**obj, "studio": {"name": studio_override}}

    obj = replace_at(obj, "details", replacement=fix_ts_trans_find_replace)
    obj = replace_at(obj, "synopsis", replacement=fix_ts_trans_find_replace)

    if urls := obj.get("urls"):
        obj = {**obj, "urls": [url for url in urls if has_working_url_pattern(url)]}

    return obj


if __name__ == "__main__":
    op, args = scraper_args()

    site = "evilangel"
    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=evilangel)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=evilangel)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=evilangel)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=evilangel)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=evilangel)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=evilangel)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
