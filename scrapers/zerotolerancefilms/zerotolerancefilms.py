import json
import sys
from typing import Any

from Altwolia.scrape import (
    gallery_from_fragment,
    gallery_from_url,
    movie_from_url,
    scene_from_fragment,
    scene_from_url,
    scene_search,
)

from py_common import log
from py_common.util import dig, scraper_args


def determine_studio(api_object: dict[str, Any]) -> str | None:
    if dig(api_object, "mainChannel", "name") == "Addicted2Girls":
        return "Addicted 2 Girls"
    if api_object.get("studio_name") == "Zero Tolerance":
        return "Zero Tolerance Films"
    return None


def zerotolerancefilms(obj: Any, api_object: dict[str, Any]) -> Any:
    if studio_override := determine_studio(api_object):
        obj = {**obj, "studio": {"name": studio_override}}
    return obj


if __name__ == "__main__":
    op, args = scraper_args()

    site = "zerotolerancefilms"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=zerotolerancefilms)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=zerotolerancefilms)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=zerotolerancefilms)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=zerotolerancefilms)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=zerotolerancefilms)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=zerotolerancefilms)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
