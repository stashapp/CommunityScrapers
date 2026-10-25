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
from py_common.types import ScrapedGallery, ScrapedScene
from py_common.util import replace_at

studio_map = {
    "TransAngels": "Trans Angels",
}


def rename_studio(name: str) -> str:
    return studio_map.get(name, name)


def transangels(obj: Any, _) -> Any:
    fixed = replace_at(obj, "studio", "name", replacement=rename_studio)
    return replace_at(fixed, "studio", "parent", "name", replacement=rename_studio)


def is_own(obj: ScrapedScene | ScrapedGallery | None) -> bool:
    # The transangels token also sees a Why Not Bi release
    return any(
        domain in url
        for url in (obj or {}).get("urls", [])
        for domain in ("transangels.com/", "transharder.com/")
    )


if __name__ == "__main__":
    domains = [
        "transangels",
        "transharder",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, postprocess=transangels)
        case "gallery-by-fragment", args:
            if is_own(
                gallery := gallery_from_fragment(
                    args, search_domains=domains, postprocess=transangels
                )
            ):
                result = gallery
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=transangels)
        case "scene-by-name", {"name": name} if name:
            result = [
                scene
                for scene in scene_search(
                    name, search_domains=domains, postprocess=transangels
                )
                if is_own(scene)
            ]
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            if is_own(
                scene := scene_from_fragment(
                    args, search_domains=domains, postprocess=transangels
                )
            ):
                result = scene
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=transangels)
        case "performer-by-fragment", args:
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=transangels
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=transangels
            )
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
