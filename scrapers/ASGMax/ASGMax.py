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
from py_common.util import dig, scraper_args


def determine_studio(api_object: dict[str, Any]) -> str | None:
    if api_object.get("studio_name") != "ASGmax":
        return None
    if dig(api_object, "mainChannel", "name") == "ASGmax VR":
        return "ASGmax VR"
    return "ASGmax Originals"


def asgmax(obj: Any, api_object: dict[str, Any]) -> Any:
    if studio_override := determine_studio(api_object):
        obj = {**obj, "studio": {"name": studio_override}}
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
