import json
import sys
import requests

from py_common import log
from py_common.util import scraper_args

def searchSceneByName(_name: str) -> list:
    myUrl = "https://realjamvr.com/search/" 
    formData = {"search": _name}
    result = requests.post(url=myUrl, data=formData).json()

    returnData = []
    for hit in result['scenes']:
        s = {}
        s['title'] = hit['name']
        s['url'] = 'https://realjamvr.com/scene/' + hit['static_url']
        s['image'] = hit['image']
        returnData.append(s)

    return returnData

if __name__ == "__main__" or __name__.endswith("Babepedia"):
    op, args = scraper_args()
    returnValue: list

    match op, args:
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            returnValue = searchSceneByName(name)
        case "scene-by-fragment", args:
            returnValue = args
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    log.debug(f"JSON Return Value: {returnValue}")
    print(json.dumps(returnValue))