"""
Stash scraper for Evil Angel (Network) that uses the Algolia API Python client
"""
import json
import re
import sys
from typing import Any
from urllib.parse import urlparse

from AlgoliaAPI.AlgoliaAPI import (
    ScrapedGallery,
    ScrapedMovie,
    gallery_from_fragment,
    gallery_from_url,
    movie_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
    site_from_url
)

from py_common import log
from py_common.types import ScrapedScene
from py_common.util import scraper_args

channel_name_map = {
    "AnalPlaytime": "Anal Acrobats",
    "Anal Trixxx": "AnalTriXXX",
    "Jonni Darkko ": "Jonni Darkko XXX",    # trailing space is in the API
    "LatexPlaytime": "Latex Playtime",
    "Le Wood": "LeWood",
    "Secret Crush ": "Secret Crush",    # trailing space is in the API
}
"""
This map just contains overrides when using a channel name as the studio
"""

serie_name_map = {
    "TransPlaytime": "TS Playground",
    "XXXmailed": "Blackmailed",
    "Anal.Oil.Latex.": "Latex Playtime",
}
"""
Each serie_name requiring a map/override should have a key-value here
"""

site_map = {
    "christophclarkonline": "Christoph Clark Online",
    "christophsbignaturaltits": "Christoph's Big Natural Tits",
    "gapingangels": "Gaping Angels",
    "iloveblackshemales": "I Love Black Shemales",
    "jakemalone": "Jake Malone",
    "johnleslie": "John Leslie",
    "lexingtonsteele": "Lexington Steele",
    "nachovidalhardcore": "Nacho Vidal Hardcore",
    "pansexualx": "PansexualX",
    "pantypops": "Panty Pops",
    "povblowjobs": "POV Blowjobs",
    "roccosiffredi": "Rocco Siffredi",
    "sheplayswithhercock": "She Plays With Her Cock",
    "strapattackers": "Strap Attackers",
    "tittycreampies": "Titty Creampies",
    "transgressivexxx": "TransgressiveXXX",
    "tsfactor": "TS Factor",
}
"""
Each site found in the logic should have a key-value here
"""

def determine_studio(api_object: dict[str, Any]) -> str | None:
    """
    Determine studio name from API object properties to use instead of the
    `studio_name` property scraped by default
    """
    available_on_site = api_object.get("availableOnSite", [])
    main_channel_name = api_object.get("mainChannel", {}).get("name")
    serie_name = api_object.get("serie_name")
    log.debug(
        f"available_on_site: {available_on_site}, "
        f"main_channel_name: {main_channel_name}, "
        f"serie_name: {serie_name}, "
    )

    # steps through api_scene["availableOnSite"], and picks the first match
    if site_match := next(
        (site for site in available_on_site if site in site_map),
        None
    ):
        log.debug(f"matched site '{site_match}'")
        return site_map.get(site_match, site_match)
    if serie_name in [
        *serie_name_map,
        "PansexualX",
    ]:
        log.debug(f"matched serie_name '{serie_name}'")
        return serie_name_map.get(serie_name, serie_name)
    if main_channel_name in [
        *channel_name_map,
        "Buttman",
        "Cock Choking Sluts",
        "Euro Angels",
        "Transsexual Angel",
        "TransgressiveXXX",
    ]:
        log.debug(f"matched main_channel_name '{main_channel_name}'")
        return channel_name_map.get(main_channel_name, main_channel_name)
    if director_match := next(
        (item for item in [
            "Joey Silvera",
            "Mike Adriano",
        ] if item in [c.get("name") for c in api_object.get("channels", [])]),
        None
    ):
        log.debug(f"matched director_match '{director_match}'")
        return director_match
    if movie_desc := api_object.get("movie_desc"):
        if "BAM Visions" in movie_desc:
            log.debug("matched 'BAM Visions' in movie_desc")
            return "BAM Visions"
    log.debug("Did not match any studio override logic")
    return None


def fix_ts_trans_find_replace(text: str) -> str | None:
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
    if text:
        return re.sub(r"(?<=[a-z])Trans", "ts", text)
    return None


def fix_url(_url: str) -> str:
    """
    Replaces the host part of the URL if criteria matched
    """
    if _url:
        site = site_from_url(_url)
        # if the site does not have a real/working domain
        if site in [
            "lewood",   # real site, but uses AdultEmpireCash system rather than Algolia
            "lexingtonsteele",
        ]:
            return urlparse(_url)._replace(netloc="www.evilangel.com").geturl()
    return _url


def postprocess_scene(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    """
    Applies post-processing to the scene
    """
    if studio_override := determine_studio(api_scene):
        scene["studio"] = { "name": studio_override }

    if details := scene.get("details"):
        scene["details"] = fix_ts_trans_find_replace(details)

    if _url := scene.get("url"):
        scene["url"] = fix_url(_url)

    if urls := scene.get("urls"):
        scene["urls"] = [fix_url(url) for url in urls]

    return scene


def postprocess_movie(movie: ScrapedMovie, api_movie: dict[str, Any]) -> ScrapedMovie:
    """
    Applies post-processing to the movie
    """
    if studio_override := determine_studio(api_movie):
        movie["studio"] = { "name": studio_override }

    if synopsis := movie.get("synopsis"):
        movie["synopsis"] = fix_ts_trans_find_replace(synopsis)

    return movie


def postprocess_gallery(gallery: ScrapedGallery, api_gallery: dict[str, Any]) -> ScrapedGallery:
    """
    Applies post-processing to the gallery
    """
    if studio_override := determine_studio(api_gallery):
        gallery["studio"] = { "name": studio_override }

    if details := gallery.get("details"):
        gallery["details"] = fix_ts_trans_find_replace(details)

    return gallery


if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url, "extra": extra} if url and extra:
            sites = extra
            result = gallery_from_url(url, sites, postprocess=postprocess_gallery)
        case "gallery-by-fragment", args:
            sites = args.pop("extra")
            result = gallery_from_fragment(args, sites, postprocess=postprocess_gallery)
        case "scene-by-url", {"url": url, "extra": extra} if url and extra:
            sites = extra
            result = scene_from_url(url, sites, postprocess=postprocess_scene)
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = scene_search(name, sites, postprocess=postprocess_scene)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            sites = args.pop("extra")
            result = scene_from_fragment(args, sites, postprocess=postprocess_scene)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = performer_search(name, sites)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=postprocess_movie)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
