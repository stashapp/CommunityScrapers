import json
import sys
from typing import Any

from Altwolia.scrape import (
    gallery_from_fragment,
    gallery_from_url,
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

SITE = "dogfartnetwork"

# Retired sites whose releases still render under dogfartnetwork.com
RETIRED_SITES = {"dfxtrapartners"}

SITENAME_PRETTY_MAP = {
    "Dfxtra": "DFXtra",
    "DownlowBoys": "Downlow Boys",
}

# Licensed third-party content, not one of the network's own sites
PARTNERS = {"Dfxtrapartners"}


def dogfartnetwork(obj: Any, api_object: dict[str, Any]) -> Any:
    if partner := partner_studio(api_object):
        return replace_all(obj, "studio", lambda _: partner)
    if not (pretty := api_object.get("sitename_pretty")):
        return obj
    studio_name = SITENAME_PRETTY_MAP.get(pretty, pretty)
    studio = {"name": studio_name}
    if studio_name not in PARTNERS:
        studio["parent"] = {"name": "Dogfart Network"}
    return replace_all(obj, "studio", lambda s: {**s, **studio})


def dogfartnetwork_scene(
    scene: ScrapedScene, api_scene: dict[str, Any]
) -> ScrapedScene:
    scene = dogfartnetwork(scene, api_scene)
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
            result = scene_from_url(url, site, postprocess=dogfartnetwork_scene)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=dogfartnetwork_scene)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=dogfartnetwork_scene)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=dogfartnetwork)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=dogfartnetwork)
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
