import os
import json
import sys
import requests
from urllib.parse import urlparse

try:
    from py_common import log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

#bugfix for socks5 proxies, due to pySocks implementation incompatibility with Stash
proxy = os.environ.get('HTTPS_PROXY', '')
if proxy != "" and proxy.startswith("socks5://"):
    proxy = proxy.replace("socks5://", "socks5h://")
    os.environ['HTTPS_PROXY'] = proxy
    os.environ['HTTP_PROXY'] = proxy

def getData(sceneId):
    try:
        log.debug(sceneId)
        req = requests.post("https://pmvhaven.com/api/v2/videoInput", json={
            "video": sceneId,
            "mode": "InitVideo",
            "view": True
        })
        log.debug(req.json())
    except Exception as e:
        log.error(f"scrape error {e}")
        sys.exit(1)
    return req.json()

def getIMG(data):
    for item in data['thumbnails']:
        if item.startswith("https://storage.pmvhaven.com/"):
            return item
    return ""

def main():
    params = json.loads(sys.stdin.read())
    if not params['url']:
        log.error('No URL entered.')
        sys.exit(1)
    
    data = getData(params['url'].split('_')[-1])['video'][0]

    tags = data['tags'] + data['categories']

    ret = {
        'title': data['title'],
        'image': getIMG(data),
        'date': data['isoDate'].split('T')[0],
        'details': data['description'],
        'studio': {
            'Name': data['creator']
        },
        'tags':[
            {
                'name': x.strip()
            } for x in tags
        ],
        'performers': [
            {
                'name': x.strip()
            } for x in data['stars']
        ]
    }
    print(json.dumps(ret))

if __name__ == "__main__":
    main()
