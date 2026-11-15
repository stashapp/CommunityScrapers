import json
import sys

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedScene
from py_common.util import scraper_args

ensure_requirements("requests")
import requests


def searchSceneByName(name: str) -> list[ScrapedScene]:
    result = requests.post(
        url="https://realjamvr.com/search/", data={"search": name}
    ).json()
    return [
        {
            "title": hit["name"],
            "urls": [f"https://realjamvr.com/scene/{hit['static_url']}"],
            "image": hit["image"],
        }
        for hit in result["scenes"]
    ]


if __name__ == "__main__":
    op, args = scraper_args()
    returnValue: list

    match op, args:
        case "scene-by-name", {"name": name} if name:
            returnValue = searchSceneByName(name)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    log.debug(f"JSON Return Value: {returnValue}")
    print(json.dumps(returnValue))
