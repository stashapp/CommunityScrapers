import json
import sys
from typing import Any
from py_common import log
from py_common.util import replace_at
from AyloAPI.scrape import (
    gallery_from_url,
    scraper_args,
    scene_from_url,
    scene_search,
    scene_from_fragment,
    performer_from_url,
    performer_from_fragment,
    performer_search,
    movie_from_url,
)


def bromo(obj: Any, _) -> Any:
    # Bromo have updated their scenes so they have proper studios now
    return obj


if __name__ == "__main__":
    domains = ["bromo"]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url, postprocess=bromo)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=bromo)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=bromo)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=bromo
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=bromo)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, search_domains=domains, postprocess=bromo)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=bromo)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
