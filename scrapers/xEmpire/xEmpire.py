import json
import sys
from typing import Any

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
from py_common.util import scraper_args, replace_all


def xempire(obj: Any, api_object: dict[str, Any]) -> Any:
    return replace_all(obj, "name", lambda n: "XEmpire" if n == "Xempire" else n)


if __name__ == "__main__":
    op, args = scraper_args()

    site = "xempire"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=xempire)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=xempire)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=xempire)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=xempire)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=xempire)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=xempire)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
