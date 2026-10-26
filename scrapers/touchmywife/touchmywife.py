import json
import sys
from typing import Any

import requests

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
from AyloAPI.slugger import slugify
from py_common import log
from py_common.types import ScrapedPerformer, ScrapedScene
from py_common.util import replace_all, replace_at

SITE = "https://www.touchmywife.com"


def resolve(url: str) -> str:
    # URLs from before the move to Aylo redirect to the scene's new ID
    if "touchmywife.com/en/video/" in url:
        return requests.head(url, timeout=10, allow_redirects=True).url
    return url


def resolve_fragment(fragment: dict[str, Any]) -> dict[str, Any]:
    return {**fragment, "urls": [resolve(url) for url in fragment.get("urls") or []]}


def touchmywife(scene: ScrapedScene, api_scene: dict[str, Any]) -> ScrapedScene:
    # The API credits the LeviProductions brand, which has no site of its own
    scene = replace_at(
        scene, "studio", "parent", replacement=lambda _: {"name": "Manipulative Media"}
    )
    scene = replace_all(
        scene,
        "urls",
        lambda url: url.replace("https://www.leviproductions.com", SITE),
    )
    scene["urls"] = [f"{SITE}/video/{api_scene['id']}/{slugify(api_scene['title'])}"]
    return scene


def model_url(
    performer: ScrapedPerformer, api_performer: dict[str, Any]
) -> ScrapedPerformer:
    performer["urls"] = [
        f"{SITE}/model/{api_performer['id']}/{slugify(api_performer['name'])}"
    ]
    return performer


if __name__ == "__main__":
    domains = [
        "touchmywife",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(resolve(url), postprocess=touchmywife)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(
                resolve_fragment(args),
                search_domains=domains,
                postprocess=touchmywife,
            )
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(resolve(url), postprocess=touchmywife)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=touchmywife)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                resolve_fragment(args),
                search_domains=domains,
                postprocess=touchmywife,
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=model_url)
        case "performer-by-fragment", args:
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=model_url
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=model_url
            )
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
