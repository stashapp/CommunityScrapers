import json
import sys
from typing import Never
import requests
import re

import py_common.log as log


def fail(message: str) -> Never:
    log.error(message)
    print("null")
    sys.exit(1)


def getData(sceneId: str):
    try:
        req = requests.post(
            "https://pmvhaven.com/api/v2/videoInput",
            json={"video": sceneId, "mode": "InitVideo", "view": True},
        )
    except Exception as e:
        fail(f"Error fetching from PMVHaven API (by video ID): {e}")
    return req.json()


def getVideoIdFromDownloadHash(downloadHash: str):
    # this endpoint doesn't include video tags for now, so will just use it to get video ID
    try:
        req = requests.post(
            "https://pmvhaven.com/api/v2/videoInput",
            json={"mode": "GetByHash", "data": {"_value": downloadHash}},
        )
    except Exception as e:
        fail(f"Error fetching from PMVHaven API (by DL hash): {e}")

    responseBody = req.json()

    if not (scenes := responseBody.get("data", [])):
        return None

    return scenes[0]["_id"]


def getIMG(video):
    # reversed because we want the most recent thumb
    for item in reversed(video["thumbnails"]):
        if not item:
            continue
        if item.startswith("https://storage.pmvhaven.com/") and "webp320" not in item:
            return item
    return ""

def getMusic(video):
    if len(video["music"]) > 0:
        return "Music:\n" + "\n".join(video["music"])
    return ""

def getVideoById(sceneId):
    data = getData(sceneId)

    if "video" not in data or len(data["video"]) < 1:
        fail(f"Video data not found in API response: {data}")

    video = data["video"][0]
    tags = video["tags"] + video["categories"]
    urlTitle = video["title"].replace(" ", "-")

    details = ""
    if video["description"] != None:
        details += video["description"]
    music = getMusic(video)
    if music:
        if len(details) > 0:
            details += "\n"
        details+=music

    return {
        "title": video["title"],
        "url": f"https://pmvhaven.com/video/{urlTitle}_{video['_id']}",
        "image": getIMG(video),
        "date": video["isoDate"].split("T")[0],
        "details": details,
        "studio": {"Name": video["creator"]},
        "tags": [{"name": x.strip()} for x in tags],
        "performers": [{"name": x.strip()} for x in video["stars"]],
    }


"""
    Assumes the video ID or the download hash is in the title of the Stash scene.
    The default file name when downloading from PMVHaven includes the download hash,
    so this will first assume the parameter is the download hash. If no results are
    returned then it will assume the parameter is the video ID and attempt data fetch.
"""


def sceneByFragment(params):
    if not params["title"]:
        fail("JSON blob did not contain title property")

    regex = re.search(r"([a-z0-9]{24})", params["title"])

    if not regex:
        fail(f"Did not find ID from video title {params['title']}")

    inputParam = regex.group(1)
    videoId = getVideoIdFromDownloadHash(inputParam)

    if videoId is None:
        videoId = inputParam

    return getVideoById(videoId)


"""    
    This assumes a URL of https://pmvhaven.com/video/{title}_{alphanumericVideoId}
    As of 2024-01-01, this is the only valid video URL format. If this changes in
    the future (i.e. more than one valid URL type, or ID not present in URL) and
    requires falling back to the old cloudscraper method, an xpath of 
        //meta[@property="video-id"]/@content 
    can be used to pass into the PMVHaven API
"""


def sceneByURL(params):
    if not params["url"]:
        fail("No URL entered")

    sceneId = params["url"].split("_")[-1]

    if not sceneId or not sceneId.isalnum():
        fail(f"Did not find scene ID from PMVStash video URL {params['url']}")

    data = getVideoById(sceneId)
    return data


if __name__ == "__main__":
    calledFunction = sys.argv[1]
    params = json.loads(sys.stdin.read())

    match calledFunction:
        case "sceneByURL":
            print(json.dumps(sceneByURL(params)))
        case "sceneByFragment":
            print(json.dumps(sceneByFragment(params)))
        case _:
            fail("This scrape method has not been implemented!")
