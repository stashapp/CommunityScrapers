import requests
import json
import re
import sys
from py_common import log
from datetime import datetime

def scrape_scene(url):
    # replace URL with api url
    videoIDmatch = re.search(r'(\/videos\/)(\d+)(\/.+)', url)
    if videoIDmatch is None:
        log.error("Invalid URL")
        sys.exit(1)
    videoID = videoIDmatch.group(2)
    api_url = f"https://www.bellesa.co/api/rest/v1/videos/{videoID}"
    response = requests.get(api_url)
    data = response.json()
    # check if response is from bellesaplus
    if (data.get("reference") != "plusSubscriptionRequired"):
        log.error("This video URL is from bellesa.co and is a re-release.")
        print("{}")
        sys.exit(1)
    body = data["value"]
    # craft dictionary response to stash
    res = {}
    res["title"] = body["title"]
    res["description"] = body["description"]
    res["image"] = body["image"]
    res["code"] = str(body["id"])
    res["studio"] = {}
    res["studio"]["name"] = body["content_provider"][0]["name"]
    res["performers"] = []
    for performer in body["performers"]:
        res["performers"].append({"name": performer["name"]})
    res["tags"] = []
    # clean tags
    temptags = body["tags"].split(",")
    # remove studio
    studioTag = res["studio"]["name"].lower()
    # create badtags array - studio name, performers
    badtags = ["original", studioTag]
    for performer in res["performers"]:
        badtags.append(performer["name"])
    for tag in temptags:
        # filter out bad tags
        if tag.lower() not in badtags:
            res["tags"].append({"name": tag})
    # Date
    res["date"] = datetime.fromtimestamp(body["posted_on"]).strftime('%Y-%m-%d')
    print(json.dumps(res))

def main():
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url")
    # If nothing is passed to the script:
    if url is None:
        log.error("No URL provided")
        sys.exit(1)
    # If we've been given a URL:
    if url is not None:
        scrape_scene(url)

if __name__ == "__main__":
    main()