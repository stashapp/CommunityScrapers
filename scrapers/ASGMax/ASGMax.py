import json
import sys
from typing import Any

from Altwolia.scrape import (
    movie_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
)
from py_common import log
from py_common.types import ScrapedStudio
from py_common.util import dig, replace_all, scraper_args

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


if __name__ == "__main__":
    op, args = scraper_args()

    site = "asgmax"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=asgmax)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=asgmax)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=asgmax)
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
