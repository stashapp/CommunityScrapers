"""
Stash scraper for Rocco Siffredi that uses the Algolia API Python client
"""
import json
import sys
from typing import Any

from AlgoliaAPI.AlgoliaAPI import (
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
from py_common.types import ScrapedMovie, ScrapedScene
from py_common.util import scraper_args

def fix_movie_url(_url: str) -> str:
    """
    Fixes the movie URL
    """
    return _url.replace("/en/movie/", "/en/dvd/")

def postprocess_scene(scene: ScrapedScene, _: dict[str, Any]) -> ScrapedScene:
    """
    Applies post-processing to the scene
    """
    if movies := scene.get("movies"):
        scene["movies"] = [
            {
                "url": fix_movie_url(movie.pop("url")),
                **movie
            } for movie in movies
        ]

    return scene


def postprocess_movie(movie: ScrapedMovie, _: dict[str, Any]) -> ScrapedMovie:
    """
    Applies post-processing to the movie
    """
    if _url := movie.get("url"):
        movie["url"] = fix_movie_url(_url)

    return movie


if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url, "extra": extra} if url and extra:
            sites = extra
            result = gallery_from_url(url, sites)
        case "gallery-by-fragment", args:
            sites = args.pop("extra")
            result = gallery_from_fragment(args, sites)
        case "scene-by-url", {"url": url, "extra": extra} if url and extra:
            sites = extra
            result = scene_from_url(url, sites, postprocess=postprocess_scene)
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = scene_search(name, sites, postprocess=postprocess_scene)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            sites = args.pop("extra")
            result = scene_from_fragment(args, sites, postprocess=postprocess_scene)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = performer_search(name, sites)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=postprocess_movie)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
