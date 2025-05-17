import json
import re
import sys
from html import unescape

import py_common.log as log
from py_common.deps import ensure_requirements
from py_common.util import scraper_args, dig

ensure_requirements("requests", "lxml")
from lxml import html  # noqa: E402
import requests  # noqa: E402

session = requests.Session()


def url_json(url: str):
    req = session.get(url)
    data = req.json()
    return data


def scrape_scene_tags(hostname: str, postid: int):
    tags_url = f"https://{hostname}/wp-json/wp/v2/video-categories?post={postid}"
    # try other tags-Url if fails
    if session.head(tags_url).status_code != 200:
        tags_url = f"https://{hostname}/wp-json/wp/v2/video-category?post={postid}"
    tags_data = url_json(tags_url)
    log.debug(f"Tags URL: {tags_url}")
    return [{"name": unescape(p["name"])} for p in tags_data]


def scrape_scene_performers(url):
    performers_data = url_json(url)
    return [{"name": unescape(p["name"]) for p in performers_data}]


def scrape_scene_media(url):
    media_data = url_json(url)
    return media_data["guid"]["rendered"]


def scrape_scene_video(url: str):
    """Scrape the /wp-json/videos endpoint for the scene
    This starts giving us some data back but we are missing thumbnails
    """
    scene_data = url_json(url)
    hostname = url.split("/")[2]
    # start constructing with sub-scrapers
    studio_data = url_json(f"https://{hostname}/wp-json")
    details = re.sub(r"</?[^>]+>", "", scene_data["content"]["rendered"]).strip()

    scene = {
        "title": unescape(scene_data["title"]["rendered"]),
        "date": scene_data["date"].split("T")[0],
        "details": unescape(details),
        "tags": scrape_scene_tags(hostname, scene_data["id"]),
        "image": scrape_scene_media(
            scene_data["_links"]["wp:featuredmedia"][0]["href"]
        ),
        "studio": {"name": unescape(studio_data["name"])},
    }
    # pull performers link if exists
    wp_terms = scene_data["_links"]["wp:term"]
    for term in wp_terms:
        if term["taxonomy"] == "performers":
            performers_url = term["href"]
            break
    else:
        performers_url = None
    if performers_url:
        performers_data = url_json(performers_url)
        scene["performers"] = [{"name": unescape(p["name"])} for p in performers_data]
    # return to handler
    return scene


def scrape_scene_performers_lxml(body):
    # fallback for performers
    performers = "//span[contains(.,'Starring')]/a | //a[contains(@href,'performers') and @class='jet-listing-dynamic-terms__link']"
    tree = html.fromstring(body)
    return [{"name": p.text_content().strip()} for p in tree.xpath(performers)]


def scrape_wp_scene(url: str):
    """Scrape the wordpress page for /wp-json endpoints
    and continue scraping with those URLs
    """
    # use regex to find the wp-json URL
    site_data = session.get(url)
    if site_data.status_code != 200:
        log.error(f"Error fetching {url}: {site_data.status_code}")
        return None

    pattern = r'type="application\/json" href="(.+?\/wp-json\/wp\/v2\/videos\/\d+)"'
    if not (wp_json_url := re.search(pattern, site_data.text)):
        log.error(f"No wp-json URL found in {url}, site is probably incompatible")
        return None

    # found the URL, descend into the scraper pits
    scraped = scrape_scene_video(wp_json_url[1])
    # if performers are empty, scrape with lxml
    if not dig(scraped, "performers"):
        log.debug("No performers found, scraping with lxml")
        scraped["performers"] = scrape_scene_performers_lxml(site_data.text)

    return scraped


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url}:
            result = scrape_wp_scene(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
