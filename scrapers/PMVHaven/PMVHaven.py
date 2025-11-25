import json
import sys
from typing import Never
import re

import py_common.log as log
from py_common.util import dig
from py_common.deps import ensure_requirements

ensure_requirements("requests")
import requests  # noqa: E402


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


def getVideoById(sceneId):
    data = getData(sceneId)

    if not (video := dig(data, "video", 0)):
        fail(f"Video data not found in API response: {data}")

    urlTitle = video["title"].replace(" ", "-")

    scraped = {
        "title": video["title"],
        "url": f"https://pmvhaven.com/video/{urlTitle}_{video['_id']}",
        "image": getIMG(video),
        "date": video["isoDate"].split("T")[0],
        "performers": [{"name": x.strip()} for x in dig(video, "stars", default=[])],
    }

    if description := dig(video, "description"):
        scraped["details"] = description

    if songs := dig(video, "music"):
        music = "Music:\n" + "\n".join(songs)
        if "details" in scraped:
            scraped["details"] += "\n" + music
        else:
            scraped["details"] = music

    if creator := dig(video, "creator"):
        scraped["studio"] = {"name": creator}

    tags = dig(video, "tags", default=[]) + dig(video, "categories", default=[])
    # remove duplicates and sort
    scraped["tags"] = sorted(
        {tag.strip().lower(): tag.strip() for tag in tags}.values()
    )
    scraped["tags"] = [{"name": tagName} for tagName in scraped["tags"]]

    return scraped


def sceneByFragment(params):
   """
    Assumes the video ID or the download hash is in the title or file name of the 
    Stash scene. The default file name when downloading from PMVHaven includes the 
    download hash, so this will first assume the parameter is the download hash. If no 
    results are returned then it will assume the parameter is the video ID and attempt 
    data fetch.
    """
    
    fileName = dig(params, "files", 0, "path")

    if not (title := dig(params, "title")):
        fail("JSON blob did not contain title property")

    if not (match := re.search(r"([a-z0-9]{24})", title)):
        if not (match := re.search(r"([a-z0-9]{24})", fileName)):
            fail(f"Did not find ID from video title '{title}' or fileName '{fileName}'")

    inputParam = match.group(1)
    videoId = getVideoIdFromDownloadHash(inputParam)

    if videoId is None:
        videoId = inputParam

    return getVideoById(videoId)


def sceneByURL(params):
    """
    This assumes a URL of https://pmvhaven.com/video/{title}_{alphanumericVideoId}
    As of 2024-01-01, this is the only valid video URL format. If this changes in
    the future (i.e. more than one valid URL type, or ID not present in URL) and
    requires falling back to the old cloudscraper method, an xpath of
        //meta[@property="video-id"]/@content
    can be used to pass into the PMVHaven API
    """

    if not (url := dig(params, "url")):
        fail("No URL entered")

    sceneId = url.split("_")[-1]

    if not (sceneId and sceneId.isalnum()):
        fail(f"Did not find scene ID from PMVStash video URL {url}")

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
