import json
import sys
from typing import Any
from py_common import log
from py_common.util import replace_all
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
    "Lets Doe It": "LetsDoeIt",
}


def letsdoeit(obj: Any, _) -> Any:
    # Rename certain studios according to the map
    fixed = replace_all(obj, "name", replacement=lambda x: studio_map.get(x, x))

    return fixed


if __name__ == "__main__":
    domains = [
        "letsdoeit",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, postprocess=letsdoeit)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=letsdoeit)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=letsdoeit)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=letsdoeit
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=letsdoeit)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=letsdoeit
            )
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=letsdoeit)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
