import json
import sys
from requests import head
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

studio_map = {
    "AvaSpice": "Ava Spice",
    "MomIsHorny": "Mom Is Horny",
}


def redirect(url: str) -> str:
    if not url or "/video/" not in url:
        return url
    if (res := head(url)) and (redirect := res.headers.get("Location", url)):
        return redirect if not redirect.endswith("404") else url
    return url


def bangbros(obj: Any, _) -> Any:
    domain = (
        "virtualporn.com"
        if dig(obj, "studio", "name") == "Virtual Porn"
        else "bangbros.com"
    )

    # All bangbros URLs omit the standard www. subdomain prefix
    # and all scene URLs use /video/ instead of the standard /scene/
    fixed = replace_all(
        obj,
        "url",
        lambda x: x.replace("/scene/", "/video/").replace("www.bangbros.com", domain),
    )

    # Rename certain studios according to the map
    fixed = replace_at(
        fixed, "studio", "name", replacement=lambda x: studio_map.get(x, x)
    )

    return fixed


if __name__ == "__main__":
    domains = [
        "bangbros",
        "virtualporn",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            url = redirect(url)
            result = gallery_from_url(url, postprocess=bangbros)
        case "scene-by-url", {"url": url} if url:
            url = redirect(url)
            result = scene_from_url(url, postprocess=bangbros)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=bangbros)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            args = replace_all(args, "url", redirect)
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=bangbros
            )
        case "performer-by-url", {"url": url}:
            url = redirect(url)
            result = performer_from_url(url, postprocess=bangbros)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=bangbros
            )
        case "movie-by-url", {"url": url} if url:
            url = redirect(url)
            result = movie_from_url(url, postprocess=bangbros)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
