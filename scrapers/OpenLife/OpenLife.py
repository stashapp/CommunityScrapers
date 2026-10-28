import json
import sys
from typing import Any

from Altwolia.scrape import (
    gallery_from_fragment,
    gallery_from_url,
    own_site_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
)
from py_common import log
from py_common.types import ScrapedScene
from py_common.util import scraper_args

SITE = "openlife"

# Retired performer sites whose releases still render under openlife.com
RETIRED_SITES = {"ashleyfires", "devonlee", "dylanryder", "lanesisters", "tealconrad"}


def openlife(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    if (
        not scene.get("urls")
        and api_scene.get("sitename") in RETIRED_SITES
        and (url := own_site_url(api_scene, SITE))
    ):
        scene["urls"] = [url]
    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, SITE, postprocess=openlife)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, SITE, postprocess=openlife)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, SITE, postprocess=openlife)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, SITE)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, SITE)
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url, SITE)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, SITE)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, SITE)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
