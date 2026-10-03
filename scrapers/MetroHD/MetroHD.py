import json
import re
import sys
from typing import Any

from AyloAPI.scrape import (
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
from py_common.util import replace_all

studio_map = {
    "Family Hook Ups": "Family Hookups",
    "Metro": "Metro HD",
}


def to_metrohd(url: str) -> str:
    # The API builds metro.com links, which 404, and the sub-site domains redirect to
    # listings: metrohd.com serves every scene, model and movie page itself
    return re.sub(
        r"//(www\.)?(metro|devianthardcore|familyhookups|girlgrind|kinkyspa|shewillcheat)\.com",
        "//www.metrohd.com",
        url,
    )


def metrohd(obj: Any, _) -> Any:
    fixed = replace_all(obj, "url", to_metrohd)
    fixed = replace_all(fixed, "urls", to_metrohd)
    return replace_all(fixed, "name", replacement=lambda x: studio_map.get(x, x))


if __name__ == "__main__":
    domains = [
        "devianthardcore",
        "familyhookups",
        "girlgrind",
        "kinkyspa",
        "shewillcheat",
        "metrohd",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url, postprocess=metrohd)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=metrohd)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=metrohd)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=metrohd
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=metrohd)
        case "performer-by-fragment", args:
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=metrohd
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, search_domains=domains, postprocess=metrohd)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=metrohd)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
