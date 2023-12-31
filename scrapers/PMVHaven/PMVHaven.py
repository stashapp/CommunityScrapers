import os
import json
import sys
import requests

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

def fail(message):
    log.error(message)
    sys.exit(1)

def getData(sceneId):
    try:
        req = requests.post("https://pmvhaven.com/api/v2/videoInput", json={
            "video": sceneId,
            "mode": "InitVideo",
            "view": True
        })
    except Exception as e:
        fail(f"Error fetching data from PMVHaven API: {e}")
    return req.json()

def getIMG(video):
    for item in video['thumbnails']:
        if item.startswith("https://storage.pmvhaven.com/"):
            return item
    return ""

'''    
    This assumes a URL of https://pmvhaven.com/video/{title}_{alphanumericVideoId}
    As of 2023-12-31, this is the only valid video URL format. If this changes in
    the future (i.e. more than one valid URL type, or ID not present in URL) and
    requires falling back to the old cloudscraper method, an xpath of 
        //meta[@property="video-id"]/@content 
    can be used to pass into the PMVHaven API
'''

def main():
    params = json.loads(sys.stdin.read())

    if not params['url']:
        fail('No URL entered.')

    sceneId = params['url'].split('_')[-1]

    if not sceneId or not sceneId.isalnum():
        fail(f"Did not find scene ID from PMVStash video URL {params['url']}")

    data = getData(sceneId)

    if not 'video' in data or len(data['video']) < 1:
        fail(f"Video data not found in data: {data}")

    video = getData(sceneId)['video'][0]

    tags = video['tags'] + video['categories']

    ret = {
        'title': video['title'],
        'image': getIMG(video),
        'date': video['isoDate'].split('T')[0],
        'details': video['description'],
        'studio': {
            'Name': video['creator']
        },
        'tags':[
            {
                'name': x.strip()
            } for x in tags
        ],
        'performers': [
            {
                'name': x.strip()
            } for x in video['stars']
        ]
    }
    print(json.dumps(ret))

if __name__ == "__main__":
    main()
