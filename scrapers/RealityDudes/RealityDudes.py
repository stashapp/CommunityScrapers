import json
import sys
from typing import Any

from AyloAPI.scrape import (
    gallery_from_fragment,
    gallery_from_url,
    movie_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
    scraper_args,
)
from py_common import log
from py_common.util import dig, replace_all


def realitydudes(obj: Any, _) -> Any:
    if dig(obj, "studio", "name") != "Papi":
        return obj

    # Papi still uses the old domain and model URL
    domain = "papi.com"
    model = "/pornstar/"

    fixed = replace_all(
        obj,
        "urls",
        lambda x: x.replace("realitydudes.com", domain).replace("/model/", model),
    )

    return fixed


if __name__ == "__main__":
    domains = [
        "realitydudes",
        "papi",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, postprocess=realitydudes)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(
                args, search_domains=domains, postprocess=realitydudes
            )
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=realitydudes)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(
                name, search_domains=domains, postprocess=realitydudes
            )
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=realitydudes
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=realitydudes)
        case "performer-by-fragment", args:
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=realitydudes
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=realitydudes
            )
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=realitydudes)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
