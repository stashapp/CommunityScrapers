import json
import sys
from typing import Any
from py_common import log
from py_common.util import dig, replace_all
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
    "es": "Erotic Spice",
    "fmf": "Forgive Me Father",
    "lha": "Love Her Ass",
    "pdt": "Pretty Dirty Teens",
    "sw": "Sex Working",
}


def deviante(obj: Any, _) -> Any:
    fixed = replace_all(obj, "name", replacement=lambda x: studio_map.get(x, x))

    replacement = None
    match dig(fixed, "studio", "name"):
        case "Erotic Spice":
            replacement = "eroticspice.com"
        case "Forgive Me Father":
            replacement = "forgivemefather.com"
        case "Love Her Ass":
            replacement = "loveherass.com"
        case "Pretty Dirty Teens":
            replacement = "prettydirtyteens.com"
        case "Sex Working":
            replacement = "sexworking.com"
        case _:
            replacement = "deviante.com"

    # All deviante URLs use /video/ instead of the standard /scene/
    # and also have separate domains per studio
    fixed = replace_all(
        fixed,
        "url",
        lambda x: x.replace("/scene/", "/video/").replace("deviante.com", replacement),
    )

    return fixed


if __name__ == "__main__":
    domains = [
        "eroticspice",
        "forgivemefather",
        "loveherass",
        "prettydirtyteens",
        "sexworking",
    ]
    op, args = scraper_args()
    result = None

    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url, postprocess=deviante)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=deviante)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=deviante)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=deviante
            )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url, postprocess=deviante)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(
                name, search_domains=domains, postprocess=deviante
            )
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, postprocess=deviante)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
