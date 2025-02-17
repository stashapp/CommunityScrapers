"Scraper for RealityLovers network"
import json
import sys
import re
from urllib.parse import urlparse
from datetime import datetime

import requests.cookies

from py_common import log
from py_common.deps import ensure_requirements
ensure_requirements("bs4:beautifulsoup4", "requests")

import requests
from bs4 import BeautifulSoup as bs

# initialize the session for making requests
session = requests.session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0"
})
disclaimer_cookie = requests.cookies.create_cookie('agreedToDisclaimer', 'true')
session.cookies.set_cookie(disclaimer_cookie)


def parse_date(date_str):
    # Use regex to match the date and capture groups
    match = re.match(r'(\w+) (\d+)[a-z]+ (\d+)', date_str)
    if match:
        month, day, year = match.groups()
        # Construct a new date string without the suffixes
        new_date_str = f"{month} {day} {year}"
        # Parse the date
        date_obj = datetime.strptime(new_date_str, "%b %d %Y")
        # Convert to the desired format
        return date_obj.strftime("%Y-%m-%d")
    raise ValueError("Date string does not match expected format")


def find_largest_image(img_tag):
    srcset = img_tag['srcset']
    srcset_list = [item.split() for item in srcset.split(',')]

    # Extract URL and width pairs
    url_width_pairs = [(url, int(width[:-1])) for url, width in srcset_list]

    # Find the URL with the largest width
    return max(url_width_pairs, key=lambda x: x[1])[0]


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
        search_results_page = session.get(f"https://{domain}/search/?s={query_value}")
        search_results_page.raise_for_status()
        # log.trace(f"search_results_page.text: {search_results_page.text}")

        soup = bs(search_results_page.text, "html.parser")
        grid_view = soup.find('div', id='gridView')
        _scenes = grid_view.find_all('div', class_='video-grid-view')
        log.debug(f"Found {len(_scenes)} scenes from {domain}")
        raw_scenes.extend(_scenes)

    results = []
    for scene in raw_scenes:
        # release date
        release_text = scene.find('p', class_='card-text').text
        log.debug(f"release_text: {release_text}")
        release_date = parse_date(release_text.replace('Released: ', ''))

        # title
        title = scene.find('p', class_='card-title').text
        log.debug(f"title: {title}")

        # url
        uri_path = scene.find('a').get('href')
        log.debug(f"uri_path: {uri_path}")
        url = f"https://{domain}{uri_path}"

        # image
        image_url = find_largest_image(scene.find('img'))

        results.append(
            {
                "Title": title,
                "URL": url,
                "Image": image_url,
                "Date": release_date,
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
