import py_common.log as log
import json
import re
import requests
import sys
from lxml import html

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
    tags = []
    for tag in tags_data:
        tags.append({ "Name": tag["name"] })
    return tags

def scrape_scene_performers(url):
    performers_data = url_json(url)
    performers = []
    for performer in performers_data:
        performers.append({ "Name": performer["name"] })
    return performers

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
    cleaned_details = scene_data["content"]["rendered"].replace("<p>", "").replace("</p>", "").replace("</span>", "").strip()
    scene = {
        "Date": scene_data["date"].split("T")[0],
        "Title": scene_data["title"]["rendered"],
        "Details": re.sub(r"<span .+>", "", cleaned_details),
        "Studio": {
            # urldecode for peter's kingdom
            "Name": studio_data["name"].replace("&#039;", "'")
        },
        "Tags": scrape_scene_tags(hostname, scene_data["id"]),
        "Image": scrape_scene_media(scene_data["_links"]["wp:featuredmedia"][0]["href"]),
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
        performers = []
        for performer in performers_data:
            performers.append({ "Name": performer["name"] })
        scene["Performers"] = performers
    # return to handler
    return scene

def scrape_scene_performers_lxml(body):
    # fallback for performers
    tree = html.fromstring(body)
    performers = []
    for performer in tree.xpath("//span[contains(.,'Starring')]/a | //a[contains(@href,'performers') and @class='jet-listing-dynamic-terms__link']"):
        performer_name = performer.text_content().strip()
        performers.append({ "Name": performer_name })
    return performers

def scrape_wp_scene(url: str):
    """Scrape the wordpress page for /wp-json endpoints
    and continue scraping with those URLs
    """
    # use regex to find the wp-json URL
    site_data = session.get(url)
    if site_data.status_code != 200:
        log.error(f"Error fetching {url}: {site_data.status_code}")
        return None
    wp_json_url = re.search(r'type="application\/json" href="(.+?\/wp-json\/wp\/v2\/videos\/\d+)"', site_data.text)
    if wp_json_url:
        # found the URL, descend into the scraper pits
        scraped = scrape_scene_video(wp_json_url[1])
        if scraped:
            # if performers are empty, scrape with lxml
            if not scraped.get("Performers"):
                log.debug("No performers found, scraping with lxml")
                scraped["Performers"] = scrape_scene_performers_lxml(site_data.text)
            print(json.dumps(scraped))
    else:
        log.error(f"Error: No wp-json URL found in {url}, site is probably incompatible")
        return None

def main():
    if sys.argv[1] == "scene":
        FRAGMENT = json.loads(sys.stdin.read())
        url = FRAGMENT.get("url")
        # scrape url
        scrape_wp_scene(url)

if __name__ == "__main__":
    main()
