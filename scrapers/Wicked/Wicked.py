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
    scene_url,
)
from Altwolia.utils import append_scene_number
from py_common import log
from py_common.types import ScrapedScene
from py_common.util import scraper_args

# Wicked distributes these studios' releases, but credits itself as their studio
PARTNER_STUDIOS = {
    "wkaddicted2girls": "Addicted 2 Girls",
    "wkadulttime": "Adult Time",
    "wkeroticax": "EroticaX",
    "wkhardx": "HardX",
    "wkzerotolerancefilms": "Zero Tolerance Films",
}


def partner_studio(obj: Any, api_obj: dict[str, Any]) -> Any:
    # mainChannel misses some partner releases and is absent on photosets and movies
    if partner := next(
        (
            channel
            for channel in api_obj.get("channels") or []
            if channel.get("type") == "Partner Channel"
        ),
        None,
    ):
        obj["studio"] = {
            "name": PARTNER_STUDIOS.get(partner["id"], partner["name"].strip())
        }
    return obj


def wicked(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    scene = partner_studio(scene, api_scene)
    # Fix the URLs that come out as wickedpartners.com
    if (
        not scene.get("urls")
        and (sitename := api_scene.get("sitename"))
        and (url_title := api_scene.get("url_title"))
        and (clip_id := api_scene.get("clip_id"))
    ):
        scene["urls"] = [scene_url("wicked", sitename, url_title, clip_id)]
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
            result = gallery_from_url(url, site, postprocess=partner_studio)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=partner_studio)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, site)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=partner_studio)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
