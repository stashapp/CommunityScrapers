import json
import sys
from typing import Any

from AyloAPI.scrape import (
    gallery_from_fragment,
    gallery_from_url,
    movie_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
    scraper_args,
)
from py_common import log
from py_common.util import dig, replace_all


def czechhunter(obj: Any, _) -> Any:
    replacement = None
    match dig(obj, "studio", "name"):
        case "Czech Hunter":
            replacement = "czechhunter.com"
        case "Debt Dandy":
            replacement = "debtdandy.com"
        case "Dirty Scout":
            replacement = "dirtyscout.com"
        case _:
            # This will never be correct, but I don't see a better way to handle it
            replacement = "bigstr.com"

    # Replace the studio name in all URLs
    fixed = replace_all(obj, "urls", lambda x: x.replace("bigstr.com", replacement))

    return fixed


if __name__ == "__main__":
    domains = [
        "czechhunter",
        "debtdandy",
        "dirtyscout",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, postprocess=czechhunter)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(
                args, search_domains=domains, postprocess=czechhunter
            )
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=czechhunter)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=czechhunter)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=czechhunter
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=czechhunter)
        case "performer-by-fragment", args:
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=czechhunter
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=czechhunter
            )
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=czechhunter)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
