"Scraper for RealityLovers network"
import concurrent.futures
import itertools
import json
import sys
import re
from urllib.parse import urlparse
from datetime import datetime

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    ScrapedPerformer,
    ScrapedScene,
)
from py_common.util import is_valid_url
ensure_requirements("bs4:beautifulsoup4", "requests")

import requests
import requests.cookies
from bs4 import BeautifulSoup as bs

# initialize the session for making requests
session = requests.session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0"
})
disclaimer_cookie = requests.cookies.create_cookie('agreedToDisclaimer', 'true')
session.cookies.set_cookie(disclaimer_cookie)

DOMAIN_STUDIO_MAP = {
    "kinkvr.com": "KinkVR",
    "playgirlstories.com": "Play Girl Stories",
    "realitylovers.com": "Reality Lovers",
    "tsvirtuallovers.com": "TS Virtual Lovers",
    "wearecrazy.com": "We Are Crazy",
}


def parse_date(date_str):
    "Convert the date format to YYYY-MM-DD"
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
    "Pick the largest resolution image from an img srcset"
    srcset = img_tag['srcset']
    srcset_list = [item.split() for item in srcset.split(',')]

    # Extract URL and width pairs
    url_width_pairs = [(url, int(width[:-1])) for url, width in srcset_list]

    # Find the URL with the largest width
    return max(url_width_pairs, key=lambda x: x[1])[0]


filename_transforms = [
    lambda s : re.sub(r'[^/]+$', '00_Main_photo_Large.jpg', s),
    lambda s : re.sub(r'[^/]+$', '00-Main-photo-Large.jpg', s),
    lambda s : re.sub(r'\w+_main_', '', s).replace('small.jpg', 'large@2x.jpg'),
]


def replace_filename_in_url(urls_str):
    "Modify the filename part of the URL"
    # Find the first URL in the string
    match = re.match(r'([^ ,]+)', urls_str)
    if match:
        first_url = match.group(1)
        log.debug(f"matched: {first_url}")

        for filename_transform in filename_transforms:
            new_url = filename_transform(first_url)
            if is_valid_url(new_url):
                log.debug(f"new_url (valid): {new_url}")
                return new_url
            log.debug(f"new_url (invalid): {new_url}")
    return None


def clean_text(details: str) -> str:
    "remove escaped backslashes and html parse the details text"
    if details:
        details = re.sub(r"\\", "", details)
        # details = re.sub(r"<\s*/?br\s*/?\s*>", "\n",
        #                  details)  # bs.get_text doesnt replace br's with \n
        details = re.sub(r'</?p>', '\n', details)
        details = bs(details, features='html.parser').get_text()
        # Remove leading/trailing/double whitespaces
        details = '\n'.join(
            [
                ' '.join([s for s in x.strip(' ').split(' ') if s != ''])
                for x in ''.join(details).split('\n')
            ]
        )
        details = details.strip()
    return details


def performer_by_url() -> ScrapedPerformer:
    "Scraper performer by studio URL"
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


def scene_by_url() -> ScrapedScene:
    "Use studio URL to scrape the REST API by ID"
    # read the input.  A URL must be passed in for the sceneByURL call
    inp = json.loads(sys.stdin.read())
    log.debug(f"inp: {inp}")
    scene_id = re.sub(r".*/([0-9]*)/.*", r"\1", inp["url"])
    if not scene_id:
        log.error("No scene ID found in URL")
        return {}
    domain = urlparse(inp["url"]).netloc.replace("www.", "")
    studio = DOMAIN_STUDIO_MAP.get(domain, 'Reality Lovers')

    api_url = f"https://engine.{domain}/content/videoDetail?contentId={scene_id}"
    scraped = session.get(api_url)
    if scraped.status_code >= 400:
        log.error(f"HTTP Error: {scraped.status_code}")
        return {}
    log.trace("Scraped the url: " + api_url)

    data = scraped.json()
    log.trace(json.dumps(data))

    title = re.sub(r'\s+VR( Porn( Video)?)?$', '', data["title"])
    details = clean_text(data["description"])

    # image
    # log.debug(f'data["mainImages"][0]["imgSrcSet"]: {data["mainImages"][0]["imgSrcSet"]}')
    image_url = replace_filename_in_url(data["mainImages"][0]["imgSrcSet"])
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

    code = str(data["contentId"])

    # create our output
    return {
        "title": title,
        "date": date,
        "tags": tags,
        "details": details,
        "image": image_url,
        "studio": {"name": studio},
        "performers": actors,
        "urls": [inp["url"]],
        "code": code,
    }


def scene_by_name() -> list[ScrapedScene]:
    """
    Get the scene by the fragment. The title is used as the search field.
    Scrapes the search page for scene results.
    """
    # read the input.  A title or name must be passed in
    inp = json.loads(sys.stdin.read())
    log.trace("Input: " + json.dumps(inp))
    query_value = inp["title"] if "title" in inp else inp["name"]
    if not query_value:
        log.error("No title or name Entered")
        return []
    log.trace("Query Value: " + query_value)

    results = []
    # send requests concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # list of futures for each domain scene search
        futures = [
            executor.submit(web_search_scenes, query_value, domain)
            # No way to know which site to search by title search text, so search all
            for domain in DOMAIN_STUDIO_MAP
        ]
        domain_list_of_scene_list = [
            future.result()
            for future in concurrent.futures.as_completed(futures)
        ]
        results.extend(list(itertools.chain.from_iterable(domain_list_of_scene_list)))

    return results


def web_search_scenes(query_value: str, domain: str) -> list[ScrapedScene]:
    """
    Searches scenes using the API.
    Parse each search result into a ScrapedScene.
    """
    search_results = session.get(
        f"https://engine.{domain}/content/search?max=100000&page=0&pornstar=0&category=0&perspective=&sort=&s={query_value}",
        headers={"Referer": f"https://{domain}/"},
    )
    search_results.raise_for_status()

    _results = []
    for scene in search_results.json().get("contents", []):
        log.debug(f"scene: {scene}")

        # release date
        release_date = parse_date(scene.get("released"))

        # title
        title = scene.get("title")
        log.debug(f"title: {title}")

        # url
        uri_path = scene.get("videoUri")
        log.debug(f"uri_path: {uri_path}")
        url = f"https://{domain}/{uri_path}"

        # image
        img = {
            "srcset": scene.get("mainImageSrcset"),
        }
        log.debug(f"img: {img}")
        image_url = find_largest_image(img)
        log.debug(f"image_url: {image_url}")

        # performers
        performers = [
            {"name": actor["name"], "url": f"https://{domain}/{actor['uri']}"}
            for actor in scene.get("actors", [])
        ]

        # description
        details = clean_text(scene.get("description", ""))

        _results.append({
            "title": title,
            "url": url,
            "image": image_url,
            "date": release_date,
            "studio": { "name": DOMAIN_STUDIO_MAP.get(domain) },
            "performers": performers,
            "details": details,
        })
    return _results


# Figure out what was invoked by Stash and call the correct thing
if sys.argv[1] == "performerByURL":
    print(json.dumps(performer_by_url()))
elif sys.argv[1] in ("sceneByURL", "sceneByQueryFragment"):
    print(json.dumps(scene_by_url()))
elif sys.argv[1] == "sceneByName":
    scenes = scene_by_name()
    print(json.dumps(scenes))
elif sys.argv[1] == "sceneByFragment":
    scenes = scene_by_name()
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
