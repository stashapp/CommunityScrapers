import json
import sys
from typing import Any

from AyloAPI.scrape import (
    gallery_from_fragment,
    gallery_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
    scraper_args,
)
from py_common import log
from py_common.types import ScrapedStudio
from py_common.util import dig, replace_at

studio_map = {
    "twistys": "Twistys",
    "TwistysHard": "Twistys Hard",
    "whengirlsplay": "When Girls Play",
}

# Listed after the main `twistys` collection, so the core never picks them
secondary_studios = {
    "bo": "Busty Ones",
    "ef": "Euro Foxes",
}


def twistys(obj: Any, raw: Any) -> Any:
    name = dig(obj, "studio", "name")
    studio: ScrapedStudio = {
        "name": next(
            (
                secondary_studios[c["shortName"]]
                for c in dig(raw, "collections", default=[])
                if c["shortName"] in secondary_studios
            ),
            studio_map.get(name, name),
        )
    }
    if studio["name"] != "Twistys":
        studio["parent"] = {"name": "Twistys"}
    return replace_at(obj, "studio", replacement=lambda _: studio)


if __name__ == "__main__":
    domains = ["twistys"]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, postprocess=twistys)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(
                args, search_domains=domains, postprocess=twistys
            )
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
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=twistys
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, search_domains=domains, postprocess=twistys)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
