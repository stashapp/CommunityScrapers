import json
import sys
from requests import head
from typing import Any
from py_common import log
from py_common.util import replace_all, replace_at
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
    "Its Gonna Hurt": "It's Gonna Hurt",
    "Poundhisass": "Pound His Ass",
}


def redirect(url: str) -> str:
    if not url or "gaywire.com/scene/" not in url:
        return url
    if (res := head(url)) and (redirect := res.headers.get("Location", url)):
        return redirect if not redirect.endswith("404") else url
    return url


def gaywire(obj: Any, _) -> Any:
    if obj is None:
        return None

    # API returns Gay Wire substudios as bangbros.com
    fixed = replace_all(
        obj,
        "url",
        lambda x: x.replace("www.bangbros.com", "gaywire.com"),
    )

    # Rename certain studios according to the map
    fixed = replace_at(
        fixed, "studio", "name", replacement=lambda x: studio_map.get(x, x)
    )

    fixed = replace_at(
        fixed, "studio", "parent", "name", replacement=lambda x: "Gay Wire"
    )

    return fixed


if __name__ == "__main__":
    domains = ["gaywire", "guyselector"]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            url = redirect(url)
            result = gallery_from_url(url, postprocess=gaywire)
        case "scene-by-url", {"url": url} if url:
            url = redirect(url)
            result = scene_from_url(url, postprocess=gaywire)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=gaywire)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            args = replace_all(args, "url", redirect)
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=gaywire
            )
        case "performer-by-url", {"url": url}:
            url = redirect(url)
            result = performer_from_url(url, postprocess=gaywire)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, search_domains=domains, postprocess=gaywire)
        case "movie-by-url", {"url": url} if url:
            url = redirect(url)
            result = movie_from_url(url, postprocess=gaywire)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
