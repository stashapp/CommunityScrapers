import os
import json
import sys
import requests

try:
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit(1)

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
    # reversed because we want the most recent thumb
    for item in reversed(video['thumbnails']):
        if item.startswith("https://storage.pmvhaven.com/"):
            return item
    return ""

'''    
    This assumes a URL of https://pmvhaven.com/video/{title}_{alphanumericVideoId}
    As of 2024-01-01, this is the only valid video URL format. If this changes in
    the future (i.e. more than one valid URL type, or ID not present in URL) and
    requires falling back to the old cloudscraper method, an xpath of 
        //meta[@property="video-id"]/@content 
    can be used to pass into the PMVHaven API
'''

def sceneByURL():
    params = json.loads(sys.stdin.read())

    if not params['url']:
        fail('No URL entered')

    sceneId = params['url'].split('_')[-1]

    if not sceneId or not sceneId.isalnum():
        fail(f"Did not find scene ID from PMVStash video URL {params['url']}")

    data = getData(sceneId)

    if not 'video' in data or len(data['video']) < 1:
        fail(f"Video data not found in API response: {data}")

    video = getData(sceneId)['video'][0]

    tags = video['tags'] + video['categories']

    return {
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

if sys.argv[1] == 'sceneByURL':
    print(json.dumps(sceneByURL()))
