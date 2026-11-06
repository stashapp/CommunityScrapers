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


def whynotbi(obj: Any, _) -> Any:
    # The API names the parent "WhyNotBy", so flatten to the site's own name
    return replace_at(obj, "studio", replacement=lambda _: {"name": "Why Not Bi"})


def is_why_not_bi(obj: ScrapedScene | ScrapedGallery | None) -> bool:
    # The whynotbi token also searches a few Men releases
    return any("whynotbi.com/" in url for url in (obj or {}).get("urls", []))


if __name__ == "__main__":
    domains = [
        "whynotbi",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, postprocess=whynotbi)
        case "gallery-by-fragment", args:
            if is_why_not_bi(
                gallery := gallery_from_fragment(
                    args, search_domains=domains, postprocess=whynotbi
                )
            ):
                result = gallery
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=whynotbi)
        case "scene-by-name", {"name": name} if name:
            result = [
                scene
                for scene in scene_search(
                    name, search_domains=domains, postprocess=whynotbi
                )
                if is_why_not_bi(scene)
            ]
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            if is_why_not_bi(
                scene := scene_from_fragment(
                    args, search_domains=domains, postprocess=whynotbi
                )
            ):
                result = scene
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=whynotbi)
        case "performer-by-fragment", args:
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=whynotbi
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=whynotbi
            )
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
