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
from py_common.util import scraper_args

# Overrides for sub-brands whose API studio_name doesn't match StashDB's
# spelling exactly - every other domain in the network already matches as-is
site_map = {
    "samuelotoole": "Samuel O'Toole",
    "tommydxxx": "Tommy D XXX",
}


def determine_studio(api_object: dict[str, Any]) -> str | None:
    available_on_site = api_object.get("availableOnSite", [])
    site_match = next((site for site in site_map if site in available_on_site), None)
    return site_map.get(site_match) if site_match else None


def nextdoorstudios(obj: Any, api_object: dict[str, Any]) -> Any:
    if studio_override := determine_studio(api_object):
        return {**obj, "studio": {"name": studio_override}}
    return obj


if __name__ == "__main__":
    op, args = scraper_args()

    site = "nextdoorstudios"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=nextdoorstudios)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=nextdoorstudios)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=nextdoorstudios)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=nextdoorstudios)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
