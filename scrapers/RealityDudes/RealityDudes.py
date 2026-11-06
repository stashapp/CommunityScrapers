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
from py_common.util import replace_all


def realitydudes(obj: Any, _) -> Any:
    # papi.com is only a landing page: Papi's scenes and models live on realitydudes.com
    return replace_all(
        obj,
        "urls",
        lambda url: url.replace("www.papi.com/", "www.realitydudes.com/"),
    )


def is_reality_dudes(obj: ScrapedScene | ScrapedGallery | None) -> bool:
    # The papi token also searches Men, Sean Cody and Bromo releases
    return any("realitydudes.com/" in url for url in (obj or {}).get("urls", []))


if __name__ == "__main__":
    # papi's token is the only one that sees Boys First Time, Gay Revenge and Reality Thugs
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
            if is_reality_dudes(
                gallery := gallery_from_fragment(
                    args, search_domains=domains, postprocess=realitydudes
                )
            ):
                result = gallery
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=realitydudes)
        case "scene-by-name", {"name": name} if name:
            result = [
                scene
                for scene in scene_search(
                    name, search_domains=domains, postprocess=realitydudes
                )
                if is_reality_dudes(scene)
            ]
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            if is_reality_dudes(
                scene := scene_from_fragment(
                    args, search_domains=domains, postprocess=realitydudes
                )
            ):
                result = scene
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
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
