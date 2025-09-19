import json
#import re
#import os
import sys
#import cloudscraper
import requests
#import urllib

from py_common import log
from py_common.util import scraper_args

def searchSceneByName(_name: str) -> list:
    myUrl = "https://realjamvr.com/search/" 
    formData = {"search": _name}
    log.debug(f"about to post.")
    result = requests.post(url=myUrl, data=formData).json()
    log.debug(f"Results of post: {result}")

    returnData = []
    for hit in result['scenes']:
        log.debug(f"Hit: {hit}")
        s = {}
        s['title'] = hit['name']
        s['url'] = 'https://realjamvr.com/scene/' + hit['static_url']
        s['image'] = hit['image']
        log.debug(f"S: {s}")
        returnData.append(s)

    log.debug(f"Returning: {returnData}")
    return returnData

if __name__ == "__main__" or __name__.endswith("Babepedia"):
    op, args = scraper_args()
    returnValue: list
    log.debug(f"current option is {op}")

    match op, args:
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            log.debug(f"Scene search value: {name}")
            sites = extra
            returnValue = searchSceneByName(name)
        case "scene-by-fragment", {"name": name, "extra": extra} if name and extra:
            log.debug(f"God to Frag: {args}")
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    log.debug(f"JSON Return Value: {returnValue}")
    print(json.dumps(returnValue))