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

from Altwolia.utils import append_scene_number, append_studio_name
from py_common.types import ScrapedScene
from py_common import log
from py_common.util import scraper_args

FALLBACK_STUDIO = "Fisting Inferno"


def fistinginferno(obj: Any, api_object: dict[str, Any]) -> Any:
    return append_studio_name(obj, api_object, fallback=FALLBACK_STUDIO)


def fistinginferno_scene(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    return append_scene_number(fistinginferno(scene, api_scene), api_scene)


if __name__ == "__main__":
    op, args = scraper_args()

    site = "fistinginferno"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=fistinginferno_scene)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=fistinginferno_scene)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=fistinginferno_scene)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=fistinginferno)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=fistinginferno)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=fistinginferno)
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
