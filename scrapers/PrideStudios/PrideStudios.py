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
from py_common.util import dig, replace_all, scraper_args

# studio_name is generic "Pride Studios" for extrabigdicks/menover30 scenes,
# but mainChannel correctly distinguishes the real sub-brands
FALLBACK_STUDIO = "Pride Studios"


def pridestudios(obj: Any, api_object: dict[str, Any]) -> Any:
    studio_name = dig(api_object, "mainChannel", "name") or FALLBACK_STUDIO
    if studio_name == FALLBACK_STUDIO:
        return replace_all(obj, "studio", lambda s: {**s, "name": FALLBACK_STUDIO})
    return replace_all(
        obj,
        "studio",
        lambda s: {**s, "name": studio_name, "parent": {"name": FALLBACK_STUDIO}},
    )


if __name__ == "__main__":
    op, args = scraper_args()

    site = "pridestudios"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=pridestudios)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=pridestudios)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=pridestudios)
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
