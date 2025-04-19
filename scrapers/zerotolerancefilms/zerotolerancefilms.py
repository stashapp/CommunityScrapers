"""
Stash scraper for ZeroToleranceFilms that uses the Algolia API Python client
"""
import json
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
from py_common.util import scraper_args

def fix_url(_url: str) -> str:
    "Replaces the host part of the URL if criteria matched"
    if _url:
        site = site_from_url(_url)
        # if the site does not have a real/working domain
        if site in [
            "flixcontentzerotolerancefilms",
        ]:
            return urlparse(_url)._replace(netloc="www.zerotolerancefilms.com").geturl()
    return _url

channel_name_map = {
    "Addicted2Girls": "Addicted 2 Girls",
    "Zero Tolerance": "Zero Tolerance Films",
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
}
"""
Each serie_name requiring a map/override should have a key-value here
"""

site_map = {
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
    network_name = api_object.get("network_name")
    serie_name = api_object.get("serie_name")
    log.debug(
        f"available_on_site: {available_on_site}, "
        f"main_channel_name: {main_channel_name}, "
        f"network_name: {network_name}, "
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
    ]:
        log.debug(f"matched serie_name '{serie_name}'")
        return serie_name_map.get(serie_name, serie_name)
    if network_name in [
        *network_name_map,
    ]:
        log.debug(f"matched network_name '{network_name}'")
        return network_name_map.get(network_name, network_name)
    if main_channel_name:
        log.debug(f"matched main_channel_name '{main_channel_name}'")
        # most scenes have the studio name as the main channel name
        return channel_name_map.get(main_channel_name, main_channel_name)
    return None


def postprocess_scene(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    """
    Applies post-processing to the scene
    """
    if studio_override := determine_studio(api_scene):
        scene["studio"] = { "name": studio_override }

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
