import json
import re
import sys
from collections.abc import Callable
from typing import Any

from AyloAPI.scrape import (
    gallery_from_url,
    movie_from_url,
    performer_from_fragment,
    performer_from_url,
    performer_search,
    scene_from_fragment,
    scene_from_url,
    scene_search,
    scraper_args,
)
from py_common import log
from py_common.util import dig, replace_all

studio_map = {
    "dlf": "Dilfed",
    "DogHouseDigital": "Doghouse Digital",
    "LesbianOlderYounger": "Lesbian Older Younger",
    "SweetHeartVideo": "Sweetheart Video",
    "SweetSinner": "Sweet Sinner",
    "RealityJunkies": "Reality Junkies",
}


def milehigh(obj: Any, _) -> Any:
    fixed = replace_all(obj, "name", replacement=lambda x: studio_map.get(x, x))

    replacement = None
    match dig(fixed, "studio", "name"):
        case "Dilfed":
            replacement = "dilfed.com"
        case "Doghouse Digital":
            replacement = "doghousedigital.com"
        case "Family Sinners":
            replacement = "familysinners.com"
        case "Milfed" | "Lesbian Older Younger":
            replacement = "milfed.com"
        case "Reality Junkies":
            replacement = "realityjunkies.com"
        case "Sweet Sinner":
            replacement = "sweetsinner.com"
        case "Sweetheart Video":
            replacement = "sweetheartvideo.com"
        case _:
            replacement = "milehighmedia.com"

    # Replace the studio name in all URLs: even if there's no specific studio,
    # milehigh.com is wrong and needs to be replaced with milehighmedia.com
    fixed = replace_all(fixed, "url", lambda x: x.replace("milehigh.com", replacement))
    fixed = replace_all(fixed, "urls", lambda x: x.replace("milehigh.com", replacement))

    return fixed


def via_hub(scrape: Callable[..., Any], url: str) -> Any:
    """
    Each site's API token only sees its own studio, but the sites cross-list each
    other's scenes: adultmobile.com's token sees the whole Mile High Media catalogue
    """
    if result := scrape(url, postprocess=milehigh):
        return result
    if (hub_url := re.sub(r"//[^/]+", "//www.adultmobile.com", url, count=1)) != url:
        log.debug(f"Retrying through the network hub: {hub_url}")
        return scrape(hub_url, postprocess=milehigh)
    return None


if __name__ == "__main__":
    # Searched in order: milehighmedia.com redirects to adultmobile.com's join page
    domains = [
        "dilfed",
        "doghousedigital",
        "familysinners",
        "milfed",
        "realityjunkies",
        "sweetsinner",
        "sweetheartvideo",
        "milehighmedia",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = via_hub(gallery_from_url, url)
        case "scene-by-url", {"url": url} if url:
            result = via_hub(scene_from_url, url)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=milehigh)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=milehigh
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=milehigh)
        case "performer-by-fragment", args:
            result = performer_from_fragment(
                args, search_domains=domains, postprocess=milehigh
            )
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=milehigh
            )
        case "movie-by-url", {"url": url} if url:
            result = via_hub(movie_from_url, url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
