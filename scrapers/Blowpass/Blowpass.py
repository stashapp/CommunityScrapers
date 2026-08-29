import json
import sys
from typing import Any

from Altwolia.scrape import (
    gallery_from_fragment,
    gallery_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
)

from py_common import log
from py_common.util import replace_all, scraper_args

studio_rename = {
    "1000facials": "1000 Facials",
    "immorallive": "Immoral Live",
    "MommyBlowsBest": "Mommy Blows Best",
    "onlyteenblowjobs": "Only Teen Blowjobs",
    "Sunlustxxx": "Sun Lust XXX",
}


def determine_studio(api_object: dict[str, Any]) -> str | None:
    if api_object.get("serie_name") == "Squirting Orgies":
        return "Squirting Orgies"
    return studio_rename.get(api_object.get("studio_name"))


def blowpass(obj: Any, api_object: dict[str, Any]) -> Any:
    if studio_override := determine_studio(api_object):
        obj = replace_all(obj, "studio", lambda s: {**s, "name": studio_override})
    return obj


if __name__ == "__main__":
    op, args = scraper_args()

    site = "blowpass"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=blowpass)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=blowpass)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=blowpass)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=blowpass)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=blowpass)
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
