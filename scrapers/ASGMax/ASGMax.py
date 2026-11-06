import json
import sys
from typing import Any

from Altwolia.scrape import (
    movie_from_url,
    own_site_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
)
from py_common import log
from py_common.types import ScrapedScene, ScrapedStudio
from py_common.util import dig, replace_all, scraper_args

SITE = "asgmax"

# Retired sites whose releases still render under asgmax.com; the index is shared
# with the rest of the network, whose retired sites don't
RETIRED_SITES = {"asgmaxpartners"}

OWN_BRANDS = {"ASGmax", "ASGmax Films"}
OWN_PARENT = "Alpha Studio Group"

# A distribution label for licensed partner channels, not a real network
PARTNERS = "ASGmax Partners"

NOT_A_STUDIO = {"On The Set", "Bonus Content"}


def determine_studio(api_object: dict[str, Any]) -> ScrapedStudio | None:
    """
    ASGMax carries other studios' catalogues, so studio_name is the network a
    scene was licensed from while mainChannel is the sub-brand it belongs to
    """
    network = (api_object.get("studio_name") or "").strip()
    channel = (dig(api_object, "mainChannel", "name") or "").strip()
    if channel in NOT_A_STUDIO:
        channel = ""
    if network in OWN_BRANDS:
        name = channel or ("ASGmax Originals" if network == "ASGmax" else network)
        return {"name": name, "parent": {"name": OWN_PARENT}}
    if not channel or dig(api_object, "mainChannel", "type") == "network":
        return {"name": network} if network else None
    if not network or network in (channel, PARTNERS):
        return {"name": channel}
    return {"name": channel, "parent": {"name": network}}


def asgmax(obj: Any, api_object: dict[str, Any]) -> Any:
    if studio := determine_studio(api_object):
        obj = replace_all(obj, "studio", lambda s: {**s, **studio})
    return obj


def asgmax_scene(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    scene = asgmax(scene, api_scene)
    if (
        not scene.get("urls")
        and api_scene.get("sitename") in RETIRED_SITES
        and (url := own_site_url(api_scene, SITE))
    ):
        scene["urls"] = [url]
    return scene


if __name__ == "__main__":
    op, args = scraper_args()

    site = SITE
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=asgmax_scene)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=asgmax_scene)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=asgmax_scene)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=asgmax)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
