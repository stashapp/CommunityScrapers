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


def seancody(obj: Any, raw: Any) -> Any:
    # The SeanCody and SC BlackMaleMe collections are filed as plain Sean Cody
    if raw.get("brand", "seancody") != "seancody":
        return obj
    return replace_at(obj, "studio", replacement=lambda _: {"name": "Sean Cody"})


def is_sean_cody(obj: ScrapedScene | ScrapedGallery | None) -> bool:
    # The seancody token also sees a Men release
    return any("seancody.com/" in url for url in (obj or {}).get("urls", []))


if __name__ == "__main__":
    domains = ["seancody"]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, postprocess=seancody)
        case "gallery-by-fragment", args:
            if is_sean_cody(
                gallery := gallery_from_fragment(
                    args, search_domains=domains, postprocess=seancody
                )
            ):
                result = gallery
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=seancody)
        case "scene-by-name", {"name": name} if name:
            result = [
                scene
                for scene in scene_search(
                    name, search_domains=domains, postprocess=seancody
                )
                if is_sean_cody(scene)
            ]
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            if is_sean_cody(
                scene := scene_from_fragment(
                    args, search_domains=domains, postprocess=seancody
                )
            ):
                result = scene
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=seancody)
        case "performer-by-fragment", args:
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=seancody
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=seancody
            )
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
