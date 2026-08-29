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


def gloryholesecrets(obj: Any, _) -> Any:
    return replace_all(obj, "studio", lambda s: {**s, "name": "Gloryhole Secrets"})


if __name__ == "__main__":
    op, args = scraper_args()

    site = "gloryholesecrets"
    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site, postprocess=gloryholesecrets)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site, postprocess=gloryholesecrets)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site, postprocess=gloryholesecrets)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site, postprocess=gloryholesecrets)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site, postprocess=gloryholesecrets)
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
