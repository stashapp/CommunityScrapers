import requests
import json
import re
import sys
from py_common import log
from datetime import datetime

# bellesa original series/studio filtering
# ignore all redistribution scenes
bellesa_studio_handles = [
    "bellesa-house",
    "bellesa-films",
    "bellesa-blind-date",
    "belle-says",
    "bellesa-house-party",
    "zero-to-hero"
]

# Replace bellesa tags with stash tags (make sure hyphen is preserved)
tag_replacements = {
    "penetration": "Vaginal Penetration",
    "dick-riding": "Riding",
    "porn for women": "Erotica",
    "sex": "Hardcore",
    "lesbian-rough": "Rough",
    "unscripted": "Gonzo",
    "partner-swapping": "Swapping",
    "masturbating": "Masturbation",
    "brunnette": "Brown Hair",
    "real couples": "Real Couple",
    "threesome fmf": "Threesome (BGG)",
    "sweaty sex": "Sweaty",
    "hot guy tattoos": "Tattoos",
    "tattos": "Tattoos",
    "girl girl": "Twosome (Lesbian)",
    "sidefuck": "Side Fuck",
    "hairpulling": "Hair Pulling",
    "gbg": "Threesome (BGG)",
    "gameshow": "Game Show",
    "male anal fingering": "Anal Fingering",
    "snowball": "Cum Swapping",
    "cumkiss": "Cum Kissing",
    "girl eats guys ass": "Rimming Him",
    "male rimjob": "Rimming Him",
    "sloppy": "Sloppy Blowjob",
    "bi": "Bisexual",
    "lesbian ass eating": "Rimming (Lesbian)",
    "fake breasts": "Fake Tits",
    "girl rims guy": "Rimming Him",
    "titty suck": "Breast Sucking",
    "light choking": "Choking",
    "nipple suck": "Nipple Play",
    "tall guy": "Tall Man",
}
# tags that do not have a stash equivalent or are invalid either way
# make sure hyphens are preserved
bad_tags = [
    "original",
    "hot guy",
    "hot girls",
    "bellesa",
    "bellesa houses",
    "bs", # belle says
    "bellesa original",
    "bh", # bellesa house
    "special",
    "zth", # zero to hero
    "z2h", # zero 2 hero
    "euro house", # bellesa euro house
]

# parse response for stash
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
    # remove studio from tags
    bad_tags.append(res["studio"]["name"].lower())
    # remove performers from tags
    for performer in res["performers"]:
        bad_tags.append(performer["name"].lower())
    for tag in temptags:
        # filter out bad tags
        lower = tag.lower()
        if lower not in bad_tags:
            # replace tags
            if lower in tag_replacements:
                tag = tag_replacements[lower]
            # replace hyphens with spaces
            tag = tag.replace("-", " ")
            res["tags"].append({"name": tag})
    # parse unix date to YYYY-MM-DD
    res["date"] = datetime.fromtimestamp(data["posted_on"]).strftime('%Y-%m-%d')
    print(json.dumps(res))

def scrape_scene(url):
    # replace URL with api url
    videoIDmatch = re.search(r'(\/videos?\/)(\d+)(\/.+)?', url)
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
    if data["access"]["plus"] != 1 or data["access"]["bellesa"] == 1:
        log.error("This video URL is from bellesa.co (free) and not bellesaplus.co (premium)")
        print("{}")
        sys.exit(1)
    # check if scene is from bellesa original series/studio
    if data["content_provider"][0]["handle"] not in bellesa_studio_handles:
        log.error("This video is not from a bellesa original series/studio")
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
