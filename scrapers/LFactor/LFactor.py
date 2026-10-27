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
from py_common.util import replace_all, scraper_args

# The index credits the site as LFactor, and some of its releases as Devils Film
STUDIO = {"name": "Lesbian Factor", "parent": {"name": "Devil's Film (Network)"}}


def lfactor(obj: Any, api_object: dict[str, Any]) -> Any:
    # This token searches the whole shared index, so only rename the site's own releases
    if api_object.get("sitename") != "lesbianfactor":
        return obj
    return replace_all(obj, "studio", lambda _: STUDIO)


if __name__ == "__main__":
    op, args = scraper_args()

    site = "lesbianfactor"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=lfactor)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=lfactor)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=lfactor)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=lfactor)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=lfactor)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=lfactor)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
