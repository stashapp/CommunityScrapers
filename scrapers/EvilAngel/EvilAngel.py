import json
import sys
from typing import Any

from AlgoliaAPI.AlgoliaAPI import (
  gallery_from_fragment,
  gallery_from_url,
  movie_from_url,
  performer_from_fragment,
  performer_from_url,
  performer_search,
  scene_from_fragment,
  scene_from_url,
  scene_search
)

from py_common import log
from py_common.types import ScrapedScene
from py_common.util import scraper_args


def postprocess_evilangel_scene(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    available_on_site = api_scene.get("availableOnSite", [])
    main_channel_name = api_scene.get("mainChannel", {}).get("name")
    serie_name = api_scene.get("serie_name")
    sitename_pretty = api_scene.get("sitename_pretty")
    log.debug(
        f"available_on_site: {available_on_site}, "
        f"main_channel_name: {main_channel_name}, "
        f"serie_name: {serie_name}, "
        f"sitename_pretty: {sitename_pretty}"
    )

    # determine studio override with custom logic
    if main_channel_name in [
        "Le Wood",
        "TransgressiveXXX",
    ]:
        scene["studio"] = { "name": main_channel_name }
    elif serie_name in [
        "TransPlaytime"
    ]:
        scene["studio"] = { "name": serie_name }
    elif sitename_pretty in [
        "PansexualX",
    ]:
        scene["studio"] = { "name": sitename_pretty }
    elif site_match := next(
        (item for item in [
            "tsfactor"
        ] if item in available_on_site),
        None
    ):
        if channel_name := next((channel["name"] for channel in api_scene["channels"] if channel["id"] == site_match)):
            scene["studio"] = { "name": channel_name }

    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url)
        case "gallery-by-fragment", args:
            sites = args.pop("extra")
            result = gallery_from_fragment(args, sites)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=postprocess_evilangel_scene)
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = scene_search(name, sites, postprocess=postprocess_evilangel_scene)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            sites = args.pop("extra")
            result = scene_from_fragment(args, sites, postprocess=postprocess_evilangel_scene)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = performer_search(name, sites)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
