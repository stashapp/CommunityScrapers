import json
import sys
import urllib
import cloudscraper

from py_common import log
from py_common.util import scraper_args

scraper = cloudscraper.create_scraper()

def searchSceneByName(name: str) -> list:
    myUrl = "https://www.milfvr.com/search/suggest.json?group=yes&q=" + urllib.parse.quote(name)
    log.debug(f"myUrl is: {myUrl}")

    getCookies = scraper.get(url='https://milfvr.com')

    myCookies = getCookies.cookies.get_dict()
    log.debug(f"My cookies are: {myCookies}")
    
    myHeaders = {
          'priority': 'u=1, i'
          , 'referer': 'https://www.milfvr.com'
          , 'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Brave";v="140"'
          , 'sec-ch-ua-arch': '"x86"'
          , 'sec-ch-ua-full-version-list': '"Chromium";v="140.0.0.0", "Not=A?Brand";v="24.0.0.0", "Brave";v="140.0.0.0"'
          , 'sec-ch-ua-mobile': '?0'
          , 'sec-ch-ua-model': '""'
          , 'sec-ch-ua-platform': '"Linux"'
          , 'sec-ch-ua-platform-version': '"6.12.43"'
          , 'sec-fetch-dest': 'empty'
          , 'sec-fetch-mode': 'cors'
          , 'sec-fetch-site': 'same-origin'
          , 'sec-gpc': '1'
          , 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
          , 'x-csrf-token': myCookies['csrfst']
          , 'x-requested-with': 'XMLHttpRequest'
        }
    log.debug(f"My headers are: {myHeaders}")

    result = scraper.get(url=myUrl, headers=myHeaders, cookies=myCookies).json()
    log.debug(f"Payload is: {result}")

    returnData = []
    for hit in result:
        if ('icon' in hit and hit['icon'] == 'movie'):
          s = {}
          s['title'] = hit['label']
          s['url'] = 'https://milfvr.com' + hit['url']
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
