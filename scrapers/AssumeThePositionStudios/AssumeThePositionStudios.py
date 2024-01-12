import json
import sys
import requests
import re

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()


def debugPrint(t):
    log.debug(t + "\n");

def scrape_scene(url):
    query = """
query scrapeSceneURL($url: String!) {
    scrapeSceneURL(url: $url) {
        title
        details
        code
        date
        image
        urls
        studio {
            name
            url
            image
            parent {
                name
                url
                image
            }
        }
        tags {
            name
        }
        performers {
            aliases
            birthdate
            career_length
            country
            death_date
            details
            ethnicity
            eye_color
            fake_tits
            gender
            hair_color
            height
            instagram
            images
            measurements
            name
            piercings
            tags {
                name
            }
            tattoos
            twitter
            url
            weight
        }
    }
}"""

    variables = {"url": url}
    result = graphql.callGraphQL(query, variables)
    log.debug(f"result {result}")
    res = result["scrapeSceneURL"]
    res["url"] = url
    return res


fragment = json.loads(sys.stdin.read())
debugPrint(json.dumps(fragment))
title = fragment.get("title")

debugPrint("title is " + title)
if m := re.match(r"(\d+)_[a-z]+_[a-z]+_\d+_([A-Z]+).*", title):
    #Turn the content id from the filename into a scene id
    contentId = int(m.group(1))
    siteCode = m.group(2)
    debugPrint("Site code is " + siteCode)
    if siteCode.casefold() == "WBP".casefold():
        apiUrl = "https://www.worstbehaviorproductions.com/api/site/21/updates/0"
        sceneUrlFragment = "https://worstbehaviorproductions.com/trailer?updateId="
    elif siteCode.casefold() == "ATP".casefold():
        apiUrl = "https://assumethepositionstudios.com/api/site/13/updates/0"
        sceneUrlFragment = "https://assumethepositionstudios.com/trailer?updateId="
    else:
        debugPrint("Unknown site code " + siteCode)
        sys.exit();

    debugPrint("Searching for " + str(contentId) + " on " + apiUrl)
    page = requests.get(apiUrl)
    updates = json.loads(page.content)
    matches = [scene for scene in updates["data"] if scene["scene"]["id"] == contentId]
    if len(matches) != 1:
        debugPrint("Couldn't find match for " + str(contentId) + " found " + str(len(matches)) + " matches")
        sys.exit()
    debugPrint("Match is " + json.dumps(matches[0]))
    sceneId = matches[0]["id"]

    #Build a scene url from the sceneId
    sceneUrl = sceneUrlFragment + str(sceneId)
    debugPrint("Scene URL is " + sceneUrl)

    result = scrape_scene(sceneUrl)
    print(json.dumps(result))
else:
    debugPrint("title didn't match")
    print(json.dumps({}))
