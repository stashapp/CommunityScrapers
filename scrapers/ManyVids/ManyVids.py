import json
import os
import re
import sys
from urllib.parse import quote_plus

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__)) # get current script directory
parent = os.path.dirname(csd) #  parent directory (should be the scrapers one)
sys.path.append(parent) # add parent dir to sys path so that we can import py_common from there

try:
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit()

try:
    from lxml import html
except ModuleNotFoundError:
    log.error(
        "You need to install the lxml module. (https://lxml.de/installation.html#installation)"
    )
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml"
    )
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    log.error(
        "You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)"
    )
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests"
    )
    sys.exit()
try:
    from bs4 import BeautifulSoup as bs
except ModuleNotFoundError:
    log.error(
        "You need to install the BeautifulSoup module. (https://www.crummy.com/software/BeautifulSoup/bs4/doc/)"
    )
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install beautifulsoup4"
    )
    sys.exit()


def get_request(url: str) -> requests.Response():
    """
    wrapper function over requests.get to set common options
    """
    mv_headers = {
        "User-Agent":
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
        "Referer": "https://www.manyvids.com/"
    }
    return requests.get(url, headers=mv_headers, timeout=(3, 10))


def get_model_name(model_id: str) -> str:
    """
    Get model name from its id
    Manyvids redirects to the model profile page as long as you provide the id in the url
    The url_handler ( we use x) doesnt matter if the model_id is valid
    """
    try:
        response = get_request(
            f'https://www.manyvids.com/Profile/{model_id}/x/Store/Videos/')
        root = html.fromstring(response.content)
        name = root.xpath(
            '//h1[contains(@class,"mv-model-display__stage-name")]/text()[1]')
        return name[0].strip()
    except:
        log.debug(f"Failed to get name for {model_id}")
        return None

def clean_text(details: str) -> dict:
    """
    remove escaped \ and html parse the details text
    """
    if details:
        details = re.sub(r"\\", "", details)
        details = bs(details, features='lxml').get_text()
    return details

def get_scene(scene_id: str) -> dict:
    """
    Get and parse scene meta from manyvid's video player json api
    """
    try:
        response = get_request(
            f"https://video-player-bff.estore.kiwi.manyvids.com/videos/{scene_id}"
        )
    except requests.exceptions.RequestException as api_error:
        log.error(f"Error {api_error} while requesting data from manyvids api")
        return None

    meta = response.json()
    scrape = {}
    scrape['title'] = meta.get('title')
    scrape['details'] = meta.get('description')
    if meta.get('modelId'):
        model_name = get_model_name(meta['modelId'])
        if model_name:
            scrape['performers'] = []
            scrape['performers'].append({'name': model_name})
    scrape['image'] = meta.get('thumbnail')
    date = meta.get('launchDate')
    if date:
        date = re.sub(r"T.*", "", date)
        scrape['date'] = date
    if meta.get('tags'):
        scrape['tags'] = [{"name": x} for x in meta['tags']]

    return scrape


def get_model_bio(url_handle: str) -> dict:
    """
    Get and parse model profile from manyvid's json endpoint
    """
    try:
        response = get_request(
            f"https://bkxljkxlbh.execute-api.us-east-1.amazonaws.com/prod/profiles/{url_handle}"
        )
    except requests.exceptions.RequestException as api_error:
        log.error(f"Error {api_error} while requesting data from manyvids api")
        return None
    model_meta = response.json()
    #log.debug(json.dumps(model_meta)) # useful to get all json entries 
    scrape = {}
    scrape['name'] = model_meta.get('displayName')
    scrape['image'] = model_meta.get('portrait')
    date = model_meta.get('dob')
    if date:
        date = re.sub(r"T.*", "", date)
        scrape['birthdate'] = date

    description = model_meta.get('description')
    scrape['details'] = clean_text(description)

    scrape['gender'] = model_meta.get('identification')
    scrape['twitter'] = model_meta.get('socLnkTwitter')
    scrape['instagram'] = model_meta.get('socLnkInstagram')
    return scrape


def scrape_scene(scene_url: str) -> None:
    id_match = re.search(r".+/Video/(\d+)/.+", scene_url)
    if id_match:
        scene_id = id_match.group(1)
        scraped = get_scene(scene_id)
        if scraped:
            print(json.dumps(scraped))
            return
    print("{}")


def scrape_performer(performer_url: str) -> None:
    handler_match = re.search(r".+/Profile/\d+/([^/]+)/.+", performer_url)
    if handler_match:
        url_handler = handler_match.group(1)
        scraped = get_model_bio(
            url_handler.lower())  # url handler needs to be lower case
        if scraped:
            scraped["url"] = performer_url
            print(json.dumps(scraped))
            return
    print("{}")


def performer_by_name(name: str, max_results: int = 25) -> None:
    performers = []
    if name:
        search_url = f'https://www.manyvids.com/MVGirls/?keywords={name}&search_type=0&sort=10&page=1'
        xpath_url = '//h4[contains(@class,"profile-pic-name")]/a[@title]/@href'
        xpath_name = '//h4[contains(@class,"profile-pic-name")]/a[@title]/text()[1]'
    try:
        response = get_request(search_url)
        root = html.fromstring(response.content)
        names = root.xpath(xpath_name)
        urls = root.xpath(xpath_url)
        if len(names) != len(urls):
            log.warning("Different number of search results! Aborting")
        else:
            if max_results > len(names):
                max_results = len(names)
            log.debug(f"Found {max_results} performers with name {name}")
            for i in range(0, max_results):
                performers.append({"name": names[i].strip(), "url": urls[i]})
    except Exception as search_exc:
        log.error(f"Failed to search for {name}: {search_exc}")
    print(json.dumps(performers))


def main():
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url")
    name = fragment.get("name")

    if url is None and name is None:
        log.error("No URL/Name provided")
        sys.exit(1)

    if url and "performer_by_url" in sys.argv:
        scrape_performer(url)
    elif name and "performer_by_name" in sys.argv:
        search_name = quote_plus(name)
        performer_by_name(search_name)
    elif url:
        scrape_scene(url)


if __name__ == "__main__":
    main()
