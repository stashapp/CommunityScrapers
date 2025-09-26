import json
import sys
import urllib.parse
import requests

from py_common import log
from py_common.util import scraper_args
from py_common.types import SceneSearchResult

scraper = requests.Session()

def milfVRsearchSceneByName(name: str) -> list:
    prep_cookies = scraper.get(url='https://milfvr.com')
    site_cookies = prep_cookies.cookies.get_dict()
    scraper.headers.update({
       'x-csrf-token': site_cookies['csrfst']
    })
    scraper.cookies.update(site_cookies)

    search_url = "https://www.milfvr.com/search/suggest.json?group=yes&q=" + urllib.parse.quote(name)
    search_result = scraper.get(url=search_url).json()
    log.debug(f"Payload is: {search_result}")

    # player-config experiment
    # files = {
    #     'item_id': (None, '6351323'),
    # }
    # debug with player config
    # player = scraper.post(url=f"https://www.{HOSTNAME}/ajax/player-config.json", files=files)
    # player_data = player.json()
    # print(f"Player config: {player.json()}")

    returnData: list[SceneSearchResult] = []
    for hit in search_result:
        if ('icon' in hit and hit['icon'] == 'movie'):
          scene_id = hit['url'].split('-')[-1]
          thumb_url = f"https://images.povr.com/general/{scene_id[0]}/{scene_id[0:4]}/{scene_id}/cover/large.webp"
          s: SceneSearchResult = {
              'title': hit['label'],
              'url': f"https://milfvr.com{hit['url']}",
              'image': thumb_url
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