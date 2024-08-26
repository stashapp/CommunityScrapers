import json
import sys
from typing import Any
from py_common import log
from py_common.util import replace_at, replace_all
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


def tube8vip(obj: Any, _) -> Any:
    # comes back as weird studio name Premium with parent Elite
    # so we flatten all studios to just "Tube8Vip" to match StashDB
    fixed = replace_at(obj, "studio", replacement=lambda _: {"name": "Tube8Vip"})
    fixed = replace_all(
        fixed, "url", replacement=lambda url: url.replace("elite.com", "tube8vip.com")
    )
    return fixed


if __name__ == "__main__":
    domains = [
        "tube8vip",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url, postprocess=tube8vip)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=tube8vip)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=tube8vip)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=tube8vip
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=tube8vip)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=tube8vip
            )
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=tube8vip)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
