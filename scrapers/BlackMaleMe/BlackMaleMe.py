import json
import sys
from typing import Any
from py_common import log
from py_common.util import replace_at
from AyloAPI.scrape import (
    scraper_args,
    scene_from_url,
    scene_search,
    scene_from_fragment,
)


def blackmaleme(obj: Any, _) -> Any:
    # Flatten all studios to just "Black Male Me"
    return replace_at(obj, "studio", replacement=lambda _: {"name": "Black Male Me"})


if __name__ == "__main__":
    domains = ["blackmaleme"]
    op, args = scraper_args()
    result = None

    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, postprocess=blackmaleme)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, search_domains=domains, postprocess=blackmaleme)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(
                args, search_domains=domains, postprocess=blackmaleme
            )
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
