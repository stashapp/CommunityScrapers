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
from py_common.util import replace_all, replace_at


def tube8vip(obj: Any, raw: Any) -> Any:
    fixed = replace_all(
        obj, "urls", replacement=lambda url: url.replace("elite.com", "tube8vip.com")
    )
    # Own releases are brand "elite" (studio "Elite", parent "Premium"); the token
    # also sees most of the Aylo catalogue, which keeps its own studios
    if raw.get("brand") != "elite":
        return fixed
    return replace_at(
        fixed, "studio", replacement=lambda _: {"name": "Premium - Channel"}
    )


def is_tube8vip(obj: ScrapedScene | ScrapedGallery | None) -> bool:
    return any("tube8vip.com/" in url for url in (obj or {}).get("urls", []))


if __name__ == "__main__":
    domains = [
        "tube8vip",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, postprocess=tube8vip)
        case "gallery-by-fragment", args:
            if is_tube8vip(
                gallery := gallery_from_fragment(
                    args, search_domains=domains, postprocess=tube8vip
                )
            ):
                result = gallery
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=tube8vip)
        case "scene-by-name", {"name": name} if name:
            result = [
                scene
                for scene in scene_search(
                    name, search_domains=domains, postprocess=tube8vip
                )
                if is_tube8vip(scene)
            ]
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            if is_tube8vip(
                scene := scene_from_fragment(
                    args, search_domains=domains, postprocess=tube8vip
                )
            ):
                result = scene
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=tube8vip)
        case "performer-by-fragment", args:
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=tube8vip
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=tube8vip
            )
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
