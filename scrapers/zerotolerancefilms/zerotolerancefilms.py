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
from py_common import log
from py_common.types import ScrapedScene
from py_common.util import replace_all, scraper_args

# studio_name credits partner releases to Zero Tolerance, and some of its own to
# Wicked, Burning Angel or TBD: the channel names the actual studio
CHANNEL_STUDIOS = {
    "3rddegree": "3rd Degree",
    "addicted2girls": "Addicted 2 Girls",
    "diabolic": "Diabolic",
    "thirddegreefilms": "3rd Degree",
    "ztfadulttime": "Adult Time",
    "ztfhardx": "HardX",
    "ztfilms": "Zero Tolerance Films",
}

# Photosets and movies don't always carry a channel
SITE_STUDIOS = {
    "3rddegreefilms": "3rd Degree",
    "addicted2girls": "Addicted 2 Girls",
    "diabolic": "Diabolic",
    "zerotolerancefilms": "Zero Tolerance Films",
}

NETWORK_STUDIOS = {"3rd Degree", "Addicted 2 Girls", "Diabolic"}


def studio_name(api_object: dict[str, Any]) -> str | None:
    channel = next(iter(api_object.get("channels") or []), {})
    if name := CHANNEL_STUDIOS.get(channel.get("id")):
        return name
    if channel.get("type") == "Partner Channel":
        return channel.get("name")
    return SITE_STUDIOS.get(api_object.get("sitename"))


def zerotolerancefilms(obj: Any, api_object: dict[str, Any]) -> Any:
    if not (name := studio_name(api_object)):
        return obj
    studio = {"name": name}
    if name in NETWORK_STUDIOS:
        studio["parent"] = {"name": "Zero Tolerance Films"}
    return replace_all(obj, "studio", lambda _: studio)


def with_url(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    scene = zerotolerancefilms(scene, api_scene)
    # Partner releases are only listed on the retired zerotolerancepartners site
    if (
        not scene.get("urls")
        and (sitename := api_scene.get("sitename"))
        and (url_title := api_scene.get("url_title"))
        and (clip_id := api_scene.get("clip_id"))
    ):
        scene["urls"] = [scene_url("zerotolerancefilms", sitename, url_title, clip_id)]
    return scene


if __name__ == "__main__":
    op, args = scraper_args()

    site = "zerotolerancefilms"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=with_url)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=with_url)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=with_url)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=zerotolerancefilms)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=zerotolerancefilms)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site, postprocess=zerotolerancefilms)
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
