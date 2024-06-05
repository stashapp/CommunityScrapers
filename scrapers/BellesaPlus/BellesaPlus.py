import requests
import json
import re
import sys
from py_common import log
from datetime import datetime

# Replace bellesa tags with stash tags (make sure hyphen is preserved)
tag_replacements = {
    "Penetration": "Vaginal Penetration",
    "Dick-Riding": "Riding",
    "Porn For Women": "Erotica",
    "Sex": "Hardcore",
    "Lesbian-Rough": "Rough",
    "Unscripted": "Gonzo",
    "Partner-Swapping": "Swapping",
    "Masturbating": "Masturbation"
}
# tags that do not have a stash equivalent or are invalid either way
# make sure hyphens are preserved
bad_tags = [
    "original",
    "hot-guy",
    "hot-girls",
    "bellesa",
    "bellesa-houses"
]

def parse_response(data):
    res = {}
    res["title"] = data["title"]
    res["details"] = data["description"]
    res["image"] = data["image"]
    res["code"] = str(data["id"])
    res["studio"] = {}
    res["studio"]["name"] = data["content_provider"][0]["name"]
    res["performers"] = []
    for performer in data["performers"]:
        res["performers"].append({"name": performer["name"]})
    res["tags"] = []
    # clean tags
    temptags = data["tags"].split(",")
    # remove studio
    studioTag = res["studio"]["name"].lower()
    # remove studio from tags
    bad_tags.append(studioTag)
    # remove performers from tags
    for performer in res["performers"]:
        bad_tags.append(performer["name"].lower())
    for tag in temptags:
        # filter out bad tags
        if tag.lower() not in bad_tags:
            # replace tags
            if tag in tag_replacements:
                tag = tag_replacements[tag]
            # replace hyphens with spaces
            tag = tag.replace("-", " ")
            res["tags"].append({"name": tag})
    # Date
    date = datetime.fromtimestamp(data["posted_on"]).strftime('%Y-%m-%d')
    res["date"] = date
    print(json.dumps(res))

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
    # check if response is nested
    if data.get("value") is not None:
        # if nested, proceed to nested data
        data = data["value"]
    # if not nested, proceed normally

    # check if response is from bellesaplus
    # bellesa scenes also include free redistributions and delayed scenes
    if data["plus"] != 1 or data["bellesa"] == 1:
        log.error("This video URL is from bellesa.co (free) and not bellesaplus.co (premium)")
        print("{}")
        sys.exit(1)
    parse_response(data)

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