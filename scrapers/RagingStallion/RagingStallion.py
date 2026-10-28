import json
import sys
from typing import Any

from Altwolia.scrape import (
    gallery_from_fragment,
    gallery_from_url,
    movie_from_url,
    own_site_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
)
from Altwolia.utils import append_scene_number
from py_common import log
from py_common.util import replace_all, scraper_args

SITE = "ragingstallion"

# Retired sites whose releases still render under ragingstallion.com
RETIRED_SITES = {"ragingstallionpartners"}

studio_map = {
    "Hot House": "Hot House Entertainment",
    "Naked Sword Originals": "NakedSword",
}


def rename_studio(studio: dict[str, Any]) -> dict[str, Any]:
    if isinstance(name := studio.get("name"), str):
        return {**studio, "name": studio_map.get(name, name)}
    return studio


def rename_studios(obj: Any) -> Any:
    return replace_all(obj, "studio", rename_studio)


def ragingstallion(scene: Any, api_scene: dict[str, Any]) -> Any:
    scene = rename_studios(append_scene_number(scene, api_scene))
    if (
        not scene.get("urls")
        and api_scene.get("sitename") in RETIRED_SITES
        and (url := own_site_url(api_scene, SITE))
    ):
        scene["urls"] = [url]
    return scene


def ragingstallion_group(group: Any, _) -> Any:
    return rename_studios(group)


def ragingstallion_gallery(gallery: Any, _) -> Any:
    return rename_studios(gallery)


if __name__ == "__main__":
    op, args = scraper_args()
    site = SITE
    log.debug(f"args: {args}")

    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=ragingstallion)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=ragingstallion)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=ragingstallion)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=ragingstallion_gallery)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(
                args, site, postprocess=ragingstallion_gallery
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=ragingstallion_group)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
