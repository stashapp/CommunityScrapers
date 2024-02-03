import json
import sys
from typing import Any
from py_common import log
from py_common.util import dig, replace_all, replace_at
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

studio_map = {
    "lpi": "Let's Post It",
    "Lets Try Anal": "Let's Try Anal",
}


def mofos(obj: Any, _) -> Any:
    # Rename certain studios according to the map
    fixed = replace_at(
        obj, "studio", "name", replacement=lambda x: studio_map.get(x, x)
    )

    domain = None
    match dig(fixed, "studio", "name"):
        case "I Know That Girl":
            domain = "iknowthatgirl.com"
        case _:
            domain = "mofos.com"

    fixed = replace_all(
        fixed,
        "url",
        lambda x: x.replace("mofos.com", domain),
    )

    return fixed


if __name__ == "__main__":
    domains = [
        "mofos",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url, postprocess=mofos)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=mofos)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=mofos)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=mofos
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=mofos)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, search_domains=domains, postprocess=mofos)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=mofos)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
