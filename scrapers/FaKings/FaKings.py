import json
import sys
from py_common import log
from py_common.util import scraper_args
from FAKNetwork.scrape import scene_by_url, scene_search, scene_by_fragment

if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url" | "scene-by-query-fragment", {"url": url} if url:
            result = scene_by_url(url)
        case "scene-by-name", {"name": query}:
            result = scene_search(query, site="fakings")
        case "scene-by-fragment", fragment:
            result = scene_by_fragment(fragment)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
