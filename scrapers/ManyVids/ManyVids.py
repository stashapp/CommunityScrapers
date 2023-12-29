import json
import os
import re
import sys
from urllib.parse import quote_plus
from html import unescape

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit()

try:
    from lxml import html
    import requests
    from bs4 import BeautifulSoup as bs
except ModuleNotFoundError:
    log.error(
        "You need to install the python modules mentioned in requirements.txt"
    )
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal from the directory the scraper is located: pip install -r requirements.txt"
    )
    sys.exit()

def get_request(url: str) -> requests.Response:
    """
    wrapper function over requests.get to set common options
    """
    log.trace(f"GET {url}")
    return requests.get(url, timeout=(3, 10))

def post_request(url: str, json: dict) -> requests.Response:
    """
    wrapper function over requests.post to set common options
    """
    with requests.Session() as session:
        log.trace(f"POST {url} {json}")
        poke = session.get("https://www.manyvids.com/Vids/", timeout=(3, 10))
        root = html.fromstring(poke.content)
        token = root.xpath('//html/@data-mvtoken')
        if not token:
            log.error("Failed to get @data-mvtoken from page")
        xsrf_token = session.cookies.get("XSRF-TOKEN")
        if not xsrf_token:
            log.error("Failed to get XSRF-TOKEN from cookies")
        res = session.post(
            url,
            json=json | {"mvtoken": token[0]},
            headers={"X-XSRF-TOKEN": xsrf_token, "x-requested-with": "XMLHttpRequest"},
            timeout=(3, 10)
        )
        return res


def get_model_name(model_id: str) -> str | None:
    """
    Get model name from its id
    Manyvids redirects to the model profile page as long as you provide the id in the url
    The url_handler (we use x) doesnt matter if the model_id is valid
    """
    try:
        response = get_request(
            f'https://www.manyvids.com/Profile/{model_id}/x/Store/Videos/')
        root = html.fromstring(response.content)
        name = root.xpath(
            '//h1[contains(@class,"mv-model-display__stage-name")]/text()[1]')
        return name[0].strip()
    except Exception as exc:
        log.debug(f"Failed to get name for '{model_id}': {exc}")


def clean_text(details: str) -> str:
    """
    remove escaped backslashes and html parse the details text
    """
    if details:
        details = re.sub(r"\\", "", details)
        details = bs(details, features='lxml').get_text()
    return details


def map_ethnicity(ethnicity: str) -> str:
    ethnicities = {
            "Alaskan": "alaskan",
            "Asian": "asian",
            "Black / Ebony": "black",
            "East Indian": "east indian",
            "Latino / Hispanic": "hispanic",
            "Middle Eastern": "middle eastern",
            "Mixed": "mixed",
            "Native American": "native american",
            "Pacific Islander": "pacific islander",
            "White / Caucasian": "white",
            "Other": "other"
    }

    return ethnicities.get(ethnicity, ethnicity)

def get_scene(scene_id: str) -> dict:
    """
    Get and parse scene meta from manyvid's video player json api
    """
    try:
        response = get_request(
            f"https://video-player-bff.estore.kiwi.manyvids.com/videos/{scene_id}"
        )
    except requests.exceptions.RequestException as api_error:
        log.error(f"Error {api_error} while requesting data from API")
        return {}

    meta = response.json()
    log.debug(f"Raw response from API: {json.dumps(meta)}")
    scrape = {}
    scrape['title'] = meta['title']
    scrape['details'] = unescape(meta['description'])
    scrape['code'] = scene_id

    sceneURLPartial = meta.get('url')
    if sceneURLPartial:
        scrape["url"] = f'https://www.manyvids.com{sceneURLPartial}'
    else:
        log.debug("No scene url found")

    if meta.get('modelId'):
        model_name = get_model_name(meta['modelId'])
        if model_name:
            scrape['performers'] = [{'name': model_name}]
            scrape['studio'] = {"name": model_name}
        else:
            log.debug("No model name found")

    image = meta.get('screenshot')
    if not image:
        log.debug("No screenshot found, using thumbnail")
        image = meta.get('thumbnail')
    scrape['image'] = image

    date = meta.get('launchDate')
    if date:
        date = re.sub(r"T.*", "", date)
        scrape['date'] = date
    else:
        log.debug("No date found")

    scrape['tags'] = [{"name": x} for x in meta.get('tags', [])]

    log.debug(f"Scraped data: {json.dumps(scrape)}")
    return scrape


def get_model_bio(url_handle: str, performer_url: str) -> dict:
    """
    Get and parse model profile from manyvid's json endpoint
    """
    try:
        response = get_request(
            f"https://bkxljkxlbh.execute-api.us-east-1.amazonaws.com/prod/profiles/{url_handle}"
        )
    except requests.exceptions.RequestException as api_error:
        log.error(f"Error {api_error} while requesting data from manyvids api")
        return {}
    model_meta = response.json()
    log.debug(f"Raw response from API: {json.dumps(model_meta)}")

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
    if scrape['gender'] == "Trans":
        scrape['gender'] = "transgender_female"

    scrape['twitter'] = model_meta.get('socLnkTwitter')
    scrape['instagram'] = model_meta.get('socLnkInstagram')
    
    ### Get the rest meta from the model about page
    try:
        response = get_request(performer_url)
        page_tree = html.fromstring(response.content)

        # top scene tags for performer
        tags = page_tree.xpath('//li[@class="mv-top-tags__item"]//text()')
        scrape['tags'] = [{"name": x.strip()} for x in tags if x.strip() != ""]

        ethnicity = page_tree.xpath("//span[@class='mv-about__container__details__list-label'][contains(text(), 'Ethnicity')]/following-sibling::span/text()")
        if ethnicity:
            scrape['ethnicity'] = map_ethnicity(ethnicity[0])

        country = page_tree.xpath("//span[@class='mv-about__container__details__list-label'][contains(text(), 'Nationality')]/following-sibling::span/img/@alt")
        if country:
            scrape['country'] = country[0]

        eye_color = page_tree.xpath("//span[@class='mv-about__container__details__list-label'][contains(text(), 'Eye Color')]/following-sibling::span/text()")
        if eye_color:
            scrape["eye_color"] = eye_color[0]

        hair_color = page_tree.xpath("//span[@class='mv-about__container__details__list-label'][contains(text(), 'Hair Color')]/following-sibling::span/text()")
        if hair_color:
            scrape["hair_color"] = hair_color[0]

        tattoos = page_tree.xpath("//span[@class='mv-about__container__details__list-label'][contains(text(), 'Tattoos')]/following-sibling::span/text()")
        if tattoos:
            scrape["tattoos"] = tattoos[0]

        piercings = page_tree.xpath("//span[@class='mv-about__container__details__list-label'][contains(text(), 'Piercings')]/following-sibling::span/text()")
        if piercings:
            scrape["piercings"] = piercings[0]

        measurements = page_tree.xpath("//span[@class='mv-about__container__details__list-label'][contains(text(), 'Measurements')]/following-sibling::span/text()")
        if measurements:
            scrape["measurements"] = measurements[0]

        height = page_tree.xpath("//span[@class='mv-about__container__details__list-label'][contains(text(), 'Height')]/following-sibling::span/text()")
        if height:
            scrape["height"] = height[0]
            match = re.match(r".*\s(\d+)\s*cm.*", height[0])
            if match:
                scrape["height"] = match.group(1)

        weight = page_tree.xpath("//span[@class='mv-about__container__details__list-label'][contains(text(), 'Weight')]/following-sibling::span/text()")
        if weight:
            scrape["weight"] = weight[0]
            match = re.match(r"(\d+)\s*Lbs.*", weight[0])
            if match:
                scrape["weight"] = f"{round(float(match.group(1))*0.45359237)}"

        fake_tits = page_tree.xpath("//span[@class='mv-about__container__details__list-label'][contains(text(), 'Breast Size')]/following-sibling::*[contains(text(), 'Natural') or contains(text(), 'Cohesive Gel') or contains(text(), 'Silicon') or contains(text(), 'Saline')]/text()")
        if fake_tits:
            natural_match = re.match(r"^Natural.*$", fake_tits[0])
            if natural_match:
                scrape["fake_tits"] = "No"
            else:
                scrape["fake_tits"] = re.sub(r"\s+?[0-9]+.*", "", fake_tits[0])
        career_length = page_tree.xpath("//*[@class='mv-about__banner-info']/strong/text()")
        if career_length:
            scrape["career_length"] = re.sub(r"^Joined\s+", "", career_length[0]) + " - today"
    except requests.exceptions.RequestException as url_error:
        log.error(f"Error while requesting data from profile page: {url_error}")

    log.debug(f"Scraped data: {json.dumps(scrape)}")
    return scrape


def scrape_scene(scene_url: str) -> dict | None:
    if scene_id := re.search(r".+/Video/(\d+)(/.+)?", scene_url):
        return get_scene(scene_id.group(1))
    else:
        log.error(f"Failed to get video ID from '{scene_url}'")


def scrape_performer(performer_url: str) -> dict | None:
    scraped = None
    if (handler_match := re.search(r".+/Profile/(\d+)/([^/]+)/.*", performer_url)):
        performer_id = handler_match.group(1)
        url_handler = handler_match.group(2).lower()
        performer_about_url = f"https://www.manyvids.com/Profile/{performer_id}/{url_handler}/About/"
        scraped = get_model_bio(url_handler, performer_about_url)
        scraped["url"] = performer_url
        return scraped
    else:
        log.error(f"Failed to get performer ID from '{performer_url}'")


def performer_by_name(name: str, max_results: int = 25) -> list[dict] | None:
    search_url = f'https://www.manyvids.com/MVGirls/?keywords={quote_plus(name)}&search_type=0&sort=10&page=1'
    xpath_url = '//h4[contains(@class,"profile-pic-name")]/a[@title]'
    try:
        response = get_request(search_url)
    except Exception as search_exc:
        log.error(f"Failed to search for performer '{name}': {search_exc}")
        return
    root = html.fromstring(response.content)
    perf_nodes = root.xpath(xpath_url)[:max_results]
    performers = [{"name": perf.text.strip(), "url": perf.get('href')} for perf in perf_nodes]
    return performers

def scene_by_name(name: str, max_results: int = 10) -> list[dict] | None:
    try:
        response = post_request("https://www.manyvids.com/api/vids/", {"sort":10,"page":1,"type":"video","keywords":name})
    except Exception as search_exc:
        log.error(f"Failed to search for scene '{name}': {search_exc}")
        return
    meta = response.json()
    if "error" in meta:
        log.error(f"Failed to search for scene '{name}': {meta['error']}")
        return []
    vids = [res['video'] for res in meta['content']['items'][:max_results]]
    scrapes = []
    for vid in vids:
        scrape = {}
        scrape['Title'] = vid['title']
        scrape['URL'] = 'https://www.manyvids.com' + vid['preview']['path']
        scrape['Image'] = vid['videoThumb']
        scrapes.append(scrape)
    return scrapes


def main():
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url")
    name = fragment.get("name")

    result = None
    if "scene_by_url" in sys.argv or "scene_by_query_fragment" in sys.argv:
        if url:
            result = scrape_scene(url)
        else:
            log.error("Missing URL: this should not be possible when called from Stash")
    elif "scene_by_name" in sys.argv:
        if name:
            result = scene_by_name(name)
        else:
            log.error("Missing search query: this should not be possible when called from Stash")
    elif "performer_by_url" in sys.argv:
        if url:
            result = scrape_performer(url)
        else:
            log.error("Missing URL: this should not be possible when called from Stash")
    elif "performer_by_name" in sys.argv:
        if name:
            result = performer_by_name(name)
        else:
            log.error("Missing search query: this should not be possible when called from Stash")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
