import json
import sys
from typing import Any

from Altwolia.scrape import (
    gallery_from_fragment,
    gallery_from_url,
    movie_from_url,
    own_site_url,
    partner_studio,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
)
from py_common import log
from py_common.types import ScrapedScene
from py_common.util import replace_all, scraper_args

SITE = "genderxfilms"

# Retired sites whose releases still render under genderxfilms.com
RETIRED_SITES = {"genderxpartners"}


def genderxfilms(obj: Any, api_object: dict[str, Any]) -> Any:
    studio = partner_studio(api_object) or {"name": "GenderXFilms"}
    return replace_all(obj, "studio", lambda s: {**s, **studio})


def genderxfilms_scene(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    scene = genderxfilms(scene, api_scene)
    if (
        not scene.get("urls")
        and api_scene.get("sitename") in RETIRED_SITES
        and (url := own_site_url(api_scene, SITE))
    ):
        scene["urls"] = [url]
    return scene


if __name__ == "__main__":
    op, args = scraper_args()

    site = SITE
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=genderxfilms_scene)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=genderxfilms_scene)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=genderxfilms_scene)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=genderxfilms)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=genderxfilms)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=genderxfilms)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
