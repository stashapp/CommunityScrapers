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
    "tp": "TwinkPop",
    "Men": "Men.com",
}


def men(obj: Any, _) -> Any:
    fixed = replace_at(
        obj, "studio", "name", replacement=lambda x: studio_map.get(x, x)
    )
    fixed = replace_at(
        fixed, "studio", "parent", "name", replacement=lambda x: studio_map.get(x, x)
    )

    # TwinkPop is the only special case for now
    is_twinkpop = dig(fixed, "studio", "name") == "TwinkPop"
    scene = "/scene/" if is_twinkpop else "/sceneid/"
    model = "/pornstar/" if is_twinkpop else "/modelprofile/"
    domain = "twinkpop.com" if is_twinkpop else "men.com"

    fixed = replace_all(
        fixed,
        "url",
        lambda x: x.replace("/scene/", scene)
        .replace("/model/", model)
        .replace("men.com", domain),
    )

    return fixed


if __name__ == "__main__":
    domains = [
        "men",
        "bigdicksatschool",
        "godsofmen",
        "jizzorgy",
        "menofuk",
        "str8togay",
        "thegayoffice",
        "toptobottom",
        "twinkpop",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url, postprocess=men)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=men)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=men)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, search_domains=domains, postprocess=men)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=men)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, search_domains=domains, postprocess=men)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=men)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
