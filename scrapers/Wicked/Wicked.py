import json
import sys
from typing import Any

from Altwolia.scrape import (
    gallery_from_url,
    movie_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
)
from Altwolia.utils import append_scene_number
from py_common.types import ScrapedScene
from py_common import log
from py_common.util import scraper_args


def wicked(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    return append_scene_number(scene, api_scene, separator=" - ")


if __name__ == "__main__":
    op, args = scraper_args()
    site = "wicked"
    log.debug(f"args: {args}")

    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=wicked)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=wicked)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=wicked)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
