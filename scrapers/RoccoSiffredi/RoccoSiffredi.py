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

from Altwolia.utilities import append_scene_number

from py_common import log
from py_common.util import replace_all, scraper_args


def roccosiffredi(obj: Any, _) -> Any:
    obj = append_scene_number(obj, _)
    # Movie URLs use /en/dvd/ on the site itself, not /en/movie/
    return replace_all(obj, "urls", lambda x: x.replace("/en/movie/", "/en/dvd/"))


if __name__ == "__main__":
    op, args = scraper_args()

    site = "roccosiffredi"
    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=roccosiffredi)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=roccosiffredi)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=roccosiffredi)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=roccosiffredi)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=roccosiffredi)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site, postprocess=roccosiffredi)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site, postprocess=roccosiffredi)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=roccosiffredi)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
