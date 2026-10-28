import json
import sys
import urllib.parse

import requests

from py_common import log
from py_common.types import ScrapedScene
from py_common.util import scraper_args

scraper = requests.Session()


def milfVRsearchSceneByName(name: str) -> list:
    # The search API wants the CSRF token from the homepage's cookies
    homepage = scraper.get(url="https://milfvr.com")
    if csrf := homepage.cookies.get("csrfst"):
        scraper.headers.update({"x-csrf-token": csrf})

    search_url = (
        "https://www.milfvr.com/search/suggest.json?group=yes&q="
        + urllib.parse.quote(name)
    )
    search_result = scraper.get(url=search_url).json()
    log.debug(f"Payload is: {search_result}")

    returnData: list[ScrapedScene] = []
    for hit in search_result:
        if "icon" in hit and hit["icon"] == "movie":
            scene_id = hit["url"].split("-")[-1]
            thumb_url = f"https://images.povr.com/general/{scene_id[0]}/{scene_id[0:4]}/{scene_id}/cover/large.webp"
            s: ScrapedScene = {
                "title": hit["label"],
                "urls": [f"https://milfvr.com{hit['url']}"],
                "image": thumb_url,
            }
            returnData.append(s)

    return returnData


if __name__ == "__main__":
    op, args = scraper_args()
    returnValue: list

    match op, args:
        case "scene-by-name", {"name": name} if name:
            returnValue = milfVRsearchSceneByName(name)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    log.debug(f"JSON Return Value: {returnValue}")
    print(json.dumps(returnValue))
