import json
import sys
import re
from urllib.parse import urlparse
import requests
from datetime import datetime

# initialize the session for making requests
session = requests.session()

try:
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit(1)


#  --------------------------------------------
# This is a scraper for: RealityLovers sites
#


def performerByURL():
    # read the input.  A URL must be passed in for the sceneByURL call
    inp = json.loads(sys.stdin.read())
    actor_id = re.sub(r".*/([0-9]*)/.*", r"\1", inp["url"])
    if not actor_id:
        log.error("No actor ID found in URL")
        return {}

    domain = urlparse(inp["url"]).netloc.replace("www.", "")
    api_url = f"https://engine.{domain}/content/actor?actorId={actor_id}"

    # Making some assumptions here
    gender = "TRANSGENDER_FEMALE" if "tsvirtuallovers" in domain else "FEMALE"

    scraped = session.get(api_url)
    scraped.raise_for_status()
    log.trace("Scraped the url: " + api_url)

    data = scraped.json()

    performer = {
        "name": data["name"],
        "image": re.sub(
            r".*,(\S+).*", r"\1", data["screenshots"][0]["galleryImgSrcSet"]
        ),
        "gender": gender,
    }
    if birthdate := data.get("birthDay"):
        performer["birthdate"] = birthdate
    if country := data.get("country"):
        performer["country"] = country
    if measurements := data.get("cupSize"):
        performer["measurements"] = measurements
    if height := data.get("height"):
        performer["height"] = height
    if weight := data.get("weight"):
        performer["weight"] = weight
    if details := data.get("description"):
        performer["details"] = details
    if tags := [{"name": x["name"]} for x in data.get("categories", [])]:
        performer["tags"] = tags
    if twitter := data.get("twitterLink"):
        performer["twitter"] = twitter
    if instagram := data.get("instagramLink"):
        performer["instagram"] = instagram

    return performer


def sceneByURL():
    # read the input.  A URL must be passed in for the sceneByURL call
    inp = json.loads(sys.stdin.read())
    scene_id = re.sub(r".*/([0-9]*)/.*", r"\1", inp["url"])
    if not scene_id:
        log.error("No scene ID found in URL")
        return {}
    domain = urlparse(inp["url"]).netloc.replace("www.", "")
    studio = "Reality Lovers"
    if "tsvirtuallovers" in domain:
        studio = "TS Virtual Lovers"

    api_url = f"https://engine.{domain}/content/videoDetail?contentId={scene_id}"
    scraped = session.get(api_url)
    if scraped.status_code >= 400:
        log.error("HTTP Error: %s" % scraped.status_code)
        return {}
    log.trace("Scraped the url: " + api_url)

    data = scraped.json()
    # log.debug(json.dumps(data))

    title = re.sub(r'\s+VR Porn Video$', '', data["title"])
    details = data["description"]

    # image
    image_url = re.sub(r".*,(\S+)\/.*", r"\1/00-Main-photo-Large.jpg", data["mainImages"][0]["imgSrcSet"])
    date = data["releaseDate"]

    # tags
    tags = [{"name": x["name"]} for x in data["categories"]]
    tags.append({'name': 'Virtual Reality'})
    if data["mainImages"][0]["perspective"] == 'VOYEUR':
        tags.extend([{'name': 'Non-POV'}, {'name': 'Voyeur'}])

    actors = [
        {"name": x["name"], "url": f"https://{domain}/{x['uri']}"}
        for x in data["starring"]
    ]

    # create our output
    return {
        "title": title,
        "date": date,
        "tags": tags,
        "details": details,
        "image": image_url,
        "studio": {"name": studio},
        "performers": actors,
    }


# Get the scene by the fragment.  The title is used as the search field.  Should return the JSON response.
def sceneByName():
    # read the input.  A title or name must be passed in
    inp = json.loads(sys.stdin.read())
    log.trace("Input: " + json.dumps(inp))
    query_value = inp["title"] if "title" in inp else inp["name"]
    if not query_value:
        log.error("No title or name Entered")
        return []
    log.trace("Query Value: " + query_value)

    # No way to know if the user wanted to search realitylovers or tsvirtuallovers, so search both
    raw_scenes = []
    for domain in ("realitylovers.com", "tsvirtuallovers.com"):
        api_url = f"https://engine.{domain}/content/search?max=100000&page=0&pornstar=0&category=0&s={query_value}"
        scraped_scenes = session.get(api_url)
        scraped_scenes.raise_for_status()
        scenes = scraped_scenes.json()
        new_scenes = [{"domain": domain, **s} for s in scenes["contents"]]
        log.debug(f"Found {len(new_scenes)} scenes from {domain}")
        raw_scenes.extend(new_scenes)

    results = []
    for scene in raw_scenes:
        # Parse the date published.  Get rid of the 'st' (like in 1st) via a regex. ex: "Sep 27th 2018"
        cleandate = re.sub(r"(st|nd|rd|th)", r"", scene["released"])
        date = datetime.strptime(cleandate, "%b %d %Y").strftime("%Y-%m-%d")
        main_image_src = re.sub(r".*1x,(.*) 2x", r"\1", scene["mainImageSrcset"])
        # Add the new scene to the results
        results.append(
            {
                "Title": scene["title"],
                "URL": f"https://{scene['domain']}/{scene['videoUri']}",
                "Image": main_image_src,
                "Date": date,
            }
        )

    return results


# Figure out what was invoked by Stash and call the correct thing
if sys.argv[1] == "performerByURL":
    print(json.dumps(performerByURL()))
elif sys.argv[1] in ("sceneByURL", "sceneByQueryFragment"):
    print(json.dumps(sceneByURL()))
elif sys.argv[1] == "sceneByName":
    scenes = sceneByName()
    print(json.dumps(scenes))
elif sys.argv[1] == "sceneByFragment":
    scenes = sceneByName()
    if len(scenes) > 0:
        # return the first query result
        print(json.dumps(scenes[0]))
    else:
        # empty array for no results
        log.info("No results")
        print("{}")
else:
    log.error("Unknown argument passed: " + sys.argv[1])
    print(json.dumps({}))
