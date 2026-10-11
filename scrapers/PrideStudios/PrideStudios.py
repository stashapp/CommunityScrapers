import json
import re
import sys
from typing import Any

from Altwolia.scrape import (
    gallery_from_fragment,
    gallery_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_id,
    scene_from_url,
    scene_search,
    scene_url,
)
from py_common import log
from py_common.util import replace_all, scraper_args

# studio_name is generic "Pride Studios" for every channel; scenes name the
# channel in mainChannel, photosets only in channels (which labels the
# network's own sets "Pride Originals")
FALLBACK_STUDIO = "Pride Studios"


def channel_name(api_object: dict[str, Any]) -> str | None:
    match api_object:
        case {"sitename": "pridestudios"}:
            return None
        case {"mainChannel": {"name": name}} | {"channels": [{"name": name}, *_]}:
            return name
    return None


def pridestudios(obj: Any, api_object: dict[str, Any]) -> Any:
    studio_name = channel_name(api_object) or FALLBACK_STUDIO
    if studio_name == FALLBACK_STUDIO:
        return replace_all(obj, "studio", lambda s: {**s, "name": FALLBACK_STUDIO})
    return replace_all(
        obj,
        "studio",
        lambda s: {**s, "name": studio_name, "parent": {"name": FALLBACK_STUDIO}},
    )


def pridestudios_scene(scene: Any, api_scene: dict[str, Any]) -> Any:
    scene = pridestudios(scene, api_scene)
    # retired channel domains redirect to the hub, so Altwolia emits no URL for them
    if not scene.get("urls") and (
        (sitename := api_scene.get("sitename"))
        and (url_title := api_scene.get("url_title"))
        and (clip_id := api_scene.get("clip_id"))
    ):
        scene["urls"] = [scene_url("pridestudios", sitename, url_title, str(clip_id))]
    return scene


if __name__ == "__main__":
    op, args = scraper_args()

    site = "pridestudios"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url and (
            film := re.search(r"/en/film/(\d+)", url)
        ):
            result = scene_from_id(film.group(1), site, postprocess=pridestudios_scene)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=pridestudios_scene)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=pridestudios_scene)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=pridestudios_scene)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=pridestudios)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=pridestudios)
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
