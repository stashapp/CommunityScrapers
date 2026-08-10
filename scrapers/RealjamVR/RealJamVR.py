import json
import sys
import requests

from py_common import log
from py_common.util import scraper_args

def searchSceneByName(name: str) -> list:
    myUrl = "https://realjamvr.com/search/" 
    formData = {"search": name}
    result = requests.post(url=myUrl, data=formData).json()

    returnData = []
    for hit in result['scenes']:
        s = {}
        s['title'] = hit['name']
        s['url'] = 'https://realjamvr.com/scene/' + hit['static_url']
        s['image'] = hit['image']
        returnData.append(s)

    return returnData

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
