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
from py_common.util import dig, replace_all, replace_at

studio_map = {
    "rks": "RK Shorts",
}


def rename_studio(name: str) -> str:
    return studio_map.get(name, name)


def rk(obj: Any, _) -> Any:
    # Rename certain studios according to the map
    fixed = replace_at(obj, "studio", "name", replacement=rename_studio)

    domain = None
    match dig(fixed, "studio", "name"):
        case "Look At Her Now":
            domain = "lookathernow.com"
        case _:
            domain = "realitykings.com"

    fixed = replace_all(
        fixed,
        "urls",
        lambda x: x.replace("realitykings.com", domain),
    )

    return fixed


if __name__ == "__main__":
    domains = [
        "realitykings",
        "lookathernow",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, postprocess=rk)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, search_domains=domains, postprocess=rk)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=rk)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=rk)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, search_domains=domains, postprocess=rk)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=rk)
        case "performer-by-fragment", args:
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=rk
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, search_domains=domains, postprocess=rk)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=rk)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
