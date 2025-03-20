"""
Stash scraper for Adult Time (Network) that uses the Algolia API Python client
"""
import json
import re
import sys
from typing import Any
from urllib.parse import urlparse

from AlgoliaAPI.AlgoliaAPI import (
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
from py_common.types import ScrapedGallery, ScrapedMovie, ScrapedScene
from py_common.util import dig, scraper_args


def url_title_from_path(path: str) -> str:
    """
    Extracts the url_title part of a URI path
    """
    return re.sub(r".*/(.*)/\d+$", "/\\1/", path)


def sitename_from_url(_url: str) -> str | None:
    """
    Extracts the sitename part of a URI path
    """
    if match := re.search(r"/en/video/(.*)/.*/\d+$", _url):
        return match.group(1)
    return None


preview_site_map = {
    "daddysboy": "daddysboy.org",
    "dareweshare": "dareweshare.net",
    "gostuckyourself-channel": "gostuckyourself.net",
    "kissmefuckme": "kissmefuckme.net",
    "milfoverload-channel": "milfoverload.net",
    "mommysboy": "mommysboy.net",
    "preggoworld-channel": "preggoworld.net",
    "watchyoucheat": "watchyoucheat.net",
    "womensworld": "adulttimepilots.net",
}


def preview_urls(urls: list[str]) -> list[str]:
    """
    some sites have scene preview pages using the url_title as the path, e.g.
    - https://adulttimepilots.com/Expose-Her-Therapy/
    - https://daddysboy.org/A-Bets-A-Bet-Pop/
    - https://dareweshare.net/Thats-Good-Teamwork/
    """
    if matching_urls := [
        urlparse(url)
        for sitename in preview_site_map
        for url in urls
        if sitename_from_url(url) == sitename
    ]:
        return [
            parsed_url._replace(
                netloc=preview_site_map.get(sitename_from_url(parsed_url.path).lower()),
                path=url_title_from_path(parsed_url.path).lower(),
            ).geturl()
            for parsed_url in matching_urls
        ]
    return []


def fix_url(_url: str) -> str:
    """
    Replaces the host part of the URL if criteria matched
    """
    if _url:
        site = site_from_url(_url)
        # if the site does not have a real/working domain
        if site.endswith("-channel") or site in [
            "blackforwife",
            "daddysboy",
            "feedme",
            "grinders",
            "kissmefuckme",
            "myyoungerlover",
            "nakedyogalife",
            "raunch",
            "shewantshim",
            "superhornyfuntime",
            "switch",
            "themikeandjoannashow",
            "theyeslist",
            "toywithme",
            "unrelatedx",
            "watchyoucheat",
            "womensworld",
        ]:
            return urlparse(_url)._replace(netloc="members.adulttime.com").geturl()
        if site == "futaworld-at":
            return urlparse(_url)._replace(netloc="www.futaworld.com").geturl()
    return _url


channel_name_map = {
    "Age & Beauty": "Age and Beauty",
    "Heteroflexible": "HeteroFlexible",
    "JOI Mom": "J.O.I Mom",
    "Vixen": "Adult Time x Vixen",
}
"""
This map just contains overrides when using a channel name as the studio
"""

network_name_map = {
}
"""
Each network_name requiring a map/override should have a key-value here
"""

serie_name_map = {
    "Transfixed Muses": "Transfixed",
}
"""
Each serie_name requiring a map/override should have a key-value here
"""

site_map = {
    "agentredgirl": "Agent Red Girl",
    "asmrfantasy": "ASMR Fantasy",
    "bethecuck": "Be the Cuck",
    "girlsunderarrest": "Girls Under Arrest",
    "SuperHornyFunTime": "Super Horny Fun Time",
}
"""
Each site found in the logic should have a key-value here
"""

sitename_pretty_map = {
}
"""
Each sitename_pretty requiring a map/override should have a key-value here
"""


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

    # determine studio override with custom logic
    # steps through from api_scene["availableOnSite"], and picks the first match
    if site_match := next(
        (site for site in available_on_site if site in site_map),
        None
    ):
        log.debug(f"matched site '{site_match}' in {available_on_site}")
        return site_map.get(site_match, site_match)
    if serie_name in [
        *serie_name_map,
        "Casey: A True Story",
        "Feed Me",
        "Future Darkly",
        "Go Stuck Yourself",
        "How Women Orgasm",
        "Mommy's Boy",
        "Oopsie",
        "Sister Trick",
        "Up Close VR",
        "Women's World",
    ]:
        log.debug(f"matched serie_name '{serie_name}' in {serie_name_map.keys()}")
        return serie_name_map.get(serie_name, serie_name)
    if network_name in [
        "Adult Time Films"
    ]:
        return network_name_map.get(network_name, network_name)
    if sitename_pretty in [
        "Devil's Film"
    ]:
        return sitename_pretty_map.get(sitename_pretty, sitename_pretty)
    if main_channel_name:
        # most scenes have the studio name as the main channel name
        return channel_name_map.get(main_channel_name, main_channel_name)
    return None



def process_action_tags(action_tags: list[dict[str, str | int]]) -> None:
    """
    action_tags is a list of {"name": str, "timecode": int}

    You could use this to add markers via GraphQL
    """
    log.trace(f"action_tags: {action_tags}")

    # add some code here to use the action_tags data
    # just return without doing anything for now


def postprocess_scene(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    """
    Applies post-processing to the scene
    """
    if studio_override := determine_studio(api_scene):
        scene["studio"] = { "name": studio_override }

    if _url := scene.get("url"):
        # log.debug(f'scene"[url]" (before): {scene["url"]}')
        scene["url"] = fix_url(_url)
        # log.debug(f'scene"[url]" (after): {scene["url"]}')

    if urls := scene.get("urls"):
        # log.debug(f'scene"[urls]" (before): {scene["urls"]}')
        scene["urls"] = [fix_url(url) for url in urls]
        # log.debug(f'scene"[urls]" (after fix): {scene["urls"]}')
        scene["urls"].extend(preview_urls(scene["urls"]))
        # log.debug(f'scene"[urls]" (after extend with preview): {scene["urls"]}')

    if action_tags := api_scene.get("action_tags"):
        process_action_tags(action_tags)

    return scene


def postprocess_movie(movie: ScrapedMovie, api_movie: dict[str, Any]) -> ScrapedMovie:
    """
    Applies post-processing to the movie
    """
    if studio_override := determine_studio(api_movie):
        movie["studio"] = { "name": studio_override }

    return movie


def postprocess_gallery(gallery: ScrapedGallery, api_gallery: dict[str, Any]) -> ScrapedGallery:
    """
    Applies post-processing to the gallery
    """
    if studio_override := determine_studio(api_gallery):
        gallery["studio"] = { "name": studio_override }

    return gallery


if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, postprocess=postprocess_gallery)
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
