import json
import sys
from typing import Any

from AyloAPI.scrape import (
    scene_from_fragment,
    scene_from_url,
    scene_search,
    scraper_args,
)
from py_common import log
from py_common.util import replace_all, replace_at


def blackmaleme(obj: Any, _) -> Any:
    # Flatten all studios to just "Black Male Me"
    fixed = replace_at(obj, "studio", replacement=lambda _: {"name": "Black Male Me"})
    # The API brands these scenes as Bromo, but they live on the studio's own domain too
    return replace_all(
        fixed, "url", lambda url: url.replace("www.bromo.com", "www.blackmaleme.com")
    )


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
