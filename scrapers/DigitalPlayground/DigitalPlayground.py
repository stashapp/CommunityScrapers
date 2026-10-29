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
from py_common.types import ScrapedStudio
from py_common.util import replace_all

studio_map = {
    "DP Parody": "DP Parodies",
    "dpw": "DP World",
    "Dpstar Sex Challenges": "Sex Challenges",
    "Episodes": "Digital Playground Episodes",
}


def rename_studio(studio: ScrapedStudio) -> ScrapedStudio:
    name = studio["name"]
    renamed: ScrapedStudio = {**studio, "name": studio_map.get(name, name)}
    if parent := studio.get("parent"):
        renamed["parent"] = rename_studio(parent)
    return renamed


def digitalplayground(obj: Any, _) -> Any:
    fixed = replace_all(obj, "studio", replacement=rename_studio)
    fixed = replace_all(
        fixed,
        "urls",
        lambda x: x.replace("/model/", "/modelprofile/").replace("/serie/", "/movie/"),
    )

    return fixed


if __name__ == "__main__":
    domains = [
        "digitalplayground",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, postprocess=digitalplayground)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(
                args, search_domains=domains, postprocess=digitalplayground
            )
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=digitalplayground)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(
                name, search_domains=domains, postprocess=digitalplayground
            )
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=digitalplayground
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=digitalplayground)
        case "performer-by-fragment", args:
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=digitalplayground
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=digitalplayground
            )
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=digitalplayground)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
