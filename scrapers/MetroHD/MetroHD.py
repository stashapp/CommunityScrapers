import json
import sys
from typing import Any
from py_common import log
from py_common.util import dig, replace_all, replace_at
from AyloAPI.scrape import (
    gallery_from_url,
    scraper_args,
    scene_from_url,
    scene_search,
    scene_from_fragment,
    performer_from_url,
    performer_from_fragment,
    performer_search,
    movie_from_url,
)


def metrohd(obj: Any, _) -> Any:
    replacement = None
    match dig(obj, "studio", "name"):
        case "Deviant Hardcore":
            replacement = "devianthardcore.com"
        case "Family Hookups":
            replacement = "familyhookups.com"
        case "Girl Grind":
            replacement = "girlgrind.com"
        case "Kinky Spa":
            replacement = "kinkyspa.com"
        case "She Will Cheat":
            replacement = "shewillcheat.com"
        case _:
            replacement = "metrohd.com"

    # Replace the studio name in all URLs: even if there's no specific studio,
    # metro.com is wrong and needs to be replaced with metrohd.com
    fixed = replace_all(obj, "url", lambda x: x.replace("metro.com", replacement))

    # The API returns Metro as a studio name but we know them as Metro HD
    fixed = replace_at(
        fixed, "studio", "name", replacement=lambda x: x.replace("Metro", "Metro HD")
    )
    fixed = replace_at(
        fixed,
        "studio",
        "parent",
        "name",
        replacement=lambda x: x.replace("Metro", "Metro HD"),
    )
    return fixed


if __name__ == "__main__":
    domains = [
        "devianthardcore",
        "familyhookups",
        "girlgrind",
        "kinkyspa",
        "shewillcheat",
        "metrohd",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url, postprocess=metrohd)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=metrohd)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=metrohd)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=metrohd
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=metrohd)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, search_domains=domains, postprocess=metrohd)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=metrohd)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
