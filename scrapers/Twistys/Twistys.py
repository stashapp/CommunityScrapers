import json
import sys
from typing import Any
from py_common import log
from py_common.util import dig, replace_at
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
    "anettedawn": "Anette Dawn",
    "twistys": "Twistys",
    "TwistysHard": "Twistys Hard",
    "whengirlsplay": "When Girls Play",
}


def twistys(obj: Any, raw: Any) -> Any:
    fixed = replace_at(
        obj, "studio", "name", replacement=lambda x: studio_map.get(x, x)
    )

    # These are not real studios in the API, so we need to fix them up
    # if we find a better way to differentiate between these then this needs fixed
    special_studios = {
        "bf": "Blue Fantasies",
        "bo": "Busty Ones",
        "ef": "Euro Foxes",
    }
    # Scene can belong to multiple studios, we only grab the first one
    studio_name = next(
        (
            special_studios.get(c["shortName"])
            for c in dig(raw, "collections", default=[])
            if c["shortName"] in special_studios.keys()
        ),
        dig(fixed, "studio", "name"),
    )
    return replace_at(
        fixed,
        "studio",
        replacement=lambda _: {"name": studio_name, "parent": {"name": "Twistys"}},
    )


if __name__ == "__main__":
    domains = ["twistys"]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url, postprocess=twistys)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=twistys)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=twistys)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=twistys
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=twistys)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, search_domains=domains, postprocess=twistys)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=twistys)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
