import json
import sys
from typing import Any
from py_common import log
from py_common.util import dig, replace_all
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


def milehigh(obj: Any, _) -> Any:
    replacement = None
    match dig(obj, "studio", "name"):
        case "Icon Male":
            replacement = "iconmale.com"
        case "Noir Male":
            replacement = "noirmale.com"
        case _:
            replacement = "milehighmedia.com"

    # Replace the studio name in all URLs: even if there's no specific studio,
    # milehigh.com is wrong and needs to be replaced with milehighmedia.com
    fixed = replace_all(obj, "url", lambda x: x.replace("milehigh.com", replacement))

    return fixed


if __name__ == "__main__":
    domains = [
        "iconmale",
        "noirmale",
        "taboomale",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url, postprocess=milehigh)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=milehigh)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=milehigh)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=milehigh
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=milehigh)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=milehigh
            )
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=milehigh)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
