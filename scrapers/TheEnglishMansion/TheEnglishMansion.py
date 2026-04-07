import json
import re
import sys
from datetime import datetime, timedelta
import py_common.log as log
from py_common.config import get_config
from py_common.types import ScrapedScene
from py_common.util import scraper_args
from py_common.deps import ensure_requirements

ensure_requirements("requests", "bs4:beautifulsoup4")
import requests
from bs4 import BeautifulSoup


config = get_config(default="""
# The English Mansion members auth
PIPSESSID=
# PHPSESSID is also tied to user agent, please update this to match the user agent of your browser when you copied the cookie.
USER_AGENT=
""")

# setup a session
session = requests.Session()
session.headers.update({
  "Cookie": f"PHPSESSID={config['PIPSESSID']}",
  "User-Agent": config["USER_AGENT"]
})

def test_login():
    # Test if the session is authenticated by accessing a page that requires login
    test_url = "https://members.theenglishmansion.com/members/favourites.html"
    response = session.get(test_url)
    if "security_code" in response.text:
        log.error("Failed to check login status. please check your PHPSESSID")
        sys.exit(1)

# scrape gallery url to get stable url for scene via view movie
def stable_url_from_gallery(url: str) -> str:
    test_login()
    response = session.get(url)
    log.debug(response.text)
    # get movies from the page
    match = re.search(r"<a href='(\/members\/movies\.html.+)'", response.text)
    if match:
        return "https://members.theenglishmansion.com" + match.group(1)
    else:
        log.error("Failed to extract stable URL from gallery page")
        sys.exit(1)

def safe_find(soup, selector):
    element = soup.select_one(selector)
    return element.text.strip() if element else None

# scrape movie url to get scene details for one scene
def scrape_scene_from_page(url: str) -> ScrapedScene:
    test_login()
    # extract id from url as validation
    match = re.search(r'#(\d+)$', url)
    if not match:
        log.error("Failed to extract scene ID from URL, URL format should end with #<id>")
        sys.exit(1)
    id = match.group(1)

    # scrape the page
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # grab div from id
    anchor = soup.find("a", attrs={"name": id})
    if not anchor:
        log.error(f"Failed to find scene anchor with ID {id} on page")
        sys.exit(1)
    container = anchor.find_next_sibling()
    if not container:
        log.error(f"Failed to find scene container for ID {id}")
        sys.exit(1)

    # construct scene elem
    scene: ScrapedScene = {}
    
    title = safe_find(container, 'div.mtb-col2')
    if title:
        scene['title'] = title

    date = safe_find(container, 'div.mtb-col3')
    if date:
        date = date.replace("Updated ", "")
        date = datetime.strptime(date, '%b %d, %Y').isoformat()
        scene['date'] = date.split("T")[0]

    length_str = safe_find(container, 'div.smb-col1 .length')
    # convert hh:mm:ss to seconds
    if length_str:
        temp = datetime.strptime(length_str, '%H:%M:%S')
        delta = timedelta(hours=temp.hour, minutes=temp.minute, seconds=temp.second)
        scene['duration'] = int(delta.total_seconds())

    cover_elem = container.select_one('div.movie-trailer550.vidwrapper a')
    if cover_elem:
        cover_url = cover_elem['style'].split('url(')[1].rstrip(');') # pyright: ignore[reportAttributeAccessIssue]
        # cover can be accessed without auth
        scene['image'] = f"https://members.theenglishmansion.com{cover_url}"
    description = safe_find(container, 'p[style="text-align: center; margin-top: 10px; padding-bottom: 10px;"]')
    if description:
        scene['details'] = description
    tags = container.select('p[style="text-align: center; padding-bottom: 10px;"] a')
    tag_names: list[str] = [tag.text.strip() for tag in tags]
    if tag_names:
        scene["tags"] = [{"name": x} for x in tag_names] # type: ignore
    performers = container.select('a[href^="search.html?mistress="]')
    performer_names: list[str] = [performer.text.strip() for performer in performers]
    if performer_names:
        scene["performers"] = [{"name": x} for x in performer_names] # type: ignore

    return scene

def main():
    try:
        op, args = scraper_args()
        output = {}

        match op, args:
            case "scene-by-url", {"url": url}:
                url = stable_url_from_gallery(url)
                output = scrape_scene_from_page(url)
            case _:
                log.error(f"Operation {op} not implemented")

        log.debug(f"Output: {output}")
        print(json.dumps(output or {}))
    except Exception as e:
        log.error(f"Error running scraper: {e}")

if __name__ == "__main__":
    main()