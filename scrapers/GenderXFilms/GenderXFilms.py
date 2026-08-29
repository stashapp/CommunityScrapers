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


def genderxfilms(obj: Any, _) -> Any:
    return replace_all(obj, "studio", lambda s: {**s, "name": "GenderXFilms"})


if __name__ == "__main__":
    op, args = scraper_args()

    site = "genderxfilms"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=genderxfilms)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=genderxfilms)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=genderxfilms)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=genderxfilms)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=genderxfilms)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=genderxfilms)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
