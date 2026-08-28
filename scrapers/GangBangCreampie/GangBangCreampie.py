import json
import sys
from typing import Any

from Altwolia.scrape import (
    gallery_from_url,
    scene_from_fragment,
    scene_from_url,
    scene_search,
)

from py_common import log
from py_common.util import scraper_args

def gangbangcreampie(obj: Any, _) -> Any:
    return {**obj, "studio": {"name": "Gangbang Creampie"}}


if __name__ == "__main__":
    op, args = scraper_args()

    site = "gangbangcreampie"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=gangbangcreampie)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=gangbangcreampie)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=gangbangcreampie)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=gangbangcreampie)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
