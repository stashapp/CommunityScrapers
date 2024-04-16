import json
import sys
from typing import Any
from py_common import log
from py_common.util import dig, replace_all, replace_at
from AyloAPI.scrape import (
    gallery_from_url,
    scraper_args,
    scene_from_url,
    scene_search,
    scene_from_fragment,
    performer_from_url,
    performer_from_fragment,
    performer_search,
    movie_from_url,
)

studio_map = {
    "JugFuckers": "Jug Fuckers",
    "Shes Gonna Squirt": "She's Gonna Squirt",
}


def bangbros(obj: Any, _) -> Any:
    # All brazzers URLs use /video/ instead of the standard /scene/
    # and /pornstar/ instead of the standard /model
    fixed = replace_all(
        obj,
        "url",
        lambda x: x.replace("/scene/", "/video/").replace("/model/", "/pornstar/"),
    )

    # Rename certain studios according to the map
    fixed = replace_at(
        fixed, "studio", "name", replacement=lambda x: studio_map.get(x, x)
    )

    # Brazzers Live special case: if the scene has the tag "Brazzers Live" we need to set the studio name to "Brazzers Live"
    if any(t["name"] == "Brazzers Live" for t in dig(obj, "tags", default=[])):
        fixed = replace_at(
            fixed, "studio", "name", replacement=lambda _: "Brazzers Live"
        )

    return fixed


if __name__ == "__main__":
    domains = [
        "brazzers",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url, postprocess=bangbros)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=bangbros)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=bangbros)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=bangbros
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=bangbros)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=bangbros
            )
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=bangbros)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
