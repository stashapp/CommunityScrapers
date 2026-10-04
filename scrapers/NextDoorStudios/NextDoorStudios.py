import json
import sys
from collections.abc import Callable
from typing import Any

from Altwolia.domains import site_name
from Altwolia.scrape import (
    gallery_from_fragment,
    gallery_from_url,
    movie_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
)
from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedGallery, ScrapedScene
from py_common.util import replace_all, scraper_args

ensure_requirements("algoliasearch")
from algoliasearch.http.exceptions import AlgoliaException  # noqa: E402

# The network's search key sees every sub-site except Next Door Hookups; some
# sub-sites' own keys only work from the network's domain, so it goes first
SITE = "nextdoorstudios"

# Overrides for sub-brands whose API studio_name doesn't match StashDB's
# spelling exactly - every other domain in the network already matches as-is
site_map = {
    "samuelotoole": "Samuel O'Toole",
    "tommydxxx": "Tommy D XXX",
}


def determine_studio(api_object: dict[str, Any]) -> str | None:
    available_on_site = api_object.get("availableOnSite", [])
    if api_object.get("studio_name") == "Next Door Studios":
        movie_title = api_object.get("movie_title")
        if isinstance(movie_title, str) and movie_title.startswith("NDE - "):
            return "Next Door Ebony"
    site_match = next((site for site in site_map if site in available_on_site), None)
    return site_map.get(site_match) if site_match else None


def nextdoorstudios(obj: Any, api_object: dict[str, Any]) -> Any:
    if studio_override := determine_studio(api_object):
        return replace_all(obj, "studio", lambda s: {**s, "name": studio_override})
    return obj


def from_own_site(scrape: Callable[..., Any], target: Any, url: str | None) -> Any:
    "Retries with the search key of the site in the URL"
    if not url or (own := site_name(url)) == SITE:
        return None
    try:
        return scrape(target, own, postprocess=nextdoorstudios)
    except AlgoliaException as e:
        log.debug(f"Search key for '{own}' was rejected: {e}")
        return None


def scene_by_url(url: str) -> ScrapedScene | None:
    return scene_from_url(url, SITE, postprocess=nextdoorstudios) or from_own_site(
        scene_from_url, url, url
    )


def scene_by_fragment(fragment: dict[str, Any]) -> ScrapedScene | None:
    return scene_from_fragment(
        fragment, SITE, postprocess=nextdoorstudios
    ) or from_own_site(
        scene_from_fragment, fragment, next(iter(fragment.get("urls") or []), None)
    )


def gallery_by_url(url: str) -> ScrapedGallery | None:
    return gallery_from_url(url, SITE, postprocess=nextdoorstudios) or from_own_site(
        gallery_from_url, url, url
    )


def gallery_by_fragment(fragment: dict[str, Any]) -> ScrapedGallery | None:
    return gallery_from_fragment(
        fragment, SITE, postprocess=nextdoorstudios
    ) or from_own_site(gallery_from_fragment, fragment, fragment.get("url"))


if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_by_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, SITE, postprocess=nextdoorstudios)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_by_fragment(args)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_by_url(url)
        case "gallery-by-fragment", args:
            result = gallery_by_fragment(args)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, SITE)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, SITE)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, SITE)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, SITE, postprocess=nextdoorstudios)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
