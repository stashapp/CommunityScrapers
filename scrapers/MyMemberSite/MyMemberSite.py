import json
import sys
import re
from urllib.parse import urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.util import scraper_args, dig
from py_common.types import ScrapedGallery, ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag

ensure_requirements("requests", "bs4:beautifulsoup4")

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
    }
)

def __api_request(scrape_url: str) -> dict:
    """
    Makes a GET request to the given URL and returns the JSON response.
    Exits if the request fails or if the response status is not 200.

    Parameters
    ----------
    scrape_url : str
        The URL to fetch.

    Returns
    -------
    dict
        The JSON response from the API.
    """
    log.debug(f"Fetching '{scrape_url}'")
    try:
        response = session.get(scrape_url, timeout=(3, 6))
    except requests.exceptions.RequestException as req_ex:
        log.error(f"Error fetching '{scrape_url}': {req_ex}")
        sys.exit(-1)

    if response.status_code != 200:
        log.error(f"Fetching '{scrape_url}' resulted in error status: {response.status_code}")
        sys.exit(-1)

    data = response.json()
    log.trace(f"Raw data from API: {data}")
    return data


def __parse_url(api_url: str, scraped_url: str) -> str:
    """
    Returns the studio name and the API URL corresponding to the given URL.

    Exits if the domain is not known or if the path does not conform to the expected format

    Parameters
    ----------
    api_url : str
        The base URL of the API.
    scraped_url : str
        The URL to parse.

    Returns
    -------
    str
        The API URL corresponding to the given URL.
    """
    path = urlparse(scraped_url).path
    if not (
        match := re.match(
            r"\/(?P<type>videos|photosets)\/(?P<id>\d+)(?:-(?P<name>.+))?$", path
        )
    ):
        log.error(f"Unable to parse URL '{scraped_url}'")
        sys.exit(-1)

    _type, _id, slug = match.groups()

    return f"{api_url}/{_type}/{_id}"


def __parse_api_url(scrape_url: str) -> str:
    """
    Fetches the page and extracts the subdomain meta tag to determine the API URL.
    Exits if the page cannot be fetched or if the meta tag is not found.

    Parameters
    ----------
    scrape_url : str
        The URL of the page to fetch.

    Returns
    -------
    str
        The API URL extracted from the meta tag.
    """
    response = requests.get(scrape_url)
    if response.status_code != 200:
        log.error(f"Fetching '{scrape_url}' resulted in error status: {response.status_code}")
        sys.exit(-1)

    html = BeautifulSoup(response.content, "html.parser")
    subdomain_tag = html.find("meta", {"name": "subdomain"})
    if not subdomain_tag or "content" not in subdomain_tag.attrs:
        log.error(f"Meta tag with name 'subdomain' not found in '{scrape_url}'")
        sys.exit(-1)

    return f"https://{subdomain_tag['content']}.mymember.site/api"


def __fetch_studio(api_url: str, scrape_url: str) -> ScrapedStudio:
    """
    Fetches the studio information from the API.
    Exits if the API request fails or if the site_info is not found in the response.

    Parameters
    ----------
    api_url : str
        The base URL of the API.
    scrape_url : str
        The original URL being scraped, used to construct the studio URL.

    Returns
    -------
    ScrapedStudio
        The scraped studio data.
    """
    response = __api_request(f"{api_url}/auth/init")
    if "site_info" not in response:
        log.error(f"site_info not found in '{api_url}/api/auth/init' response")
        sys.exit(-1)

    parsed_url = urlparse(scrape_url)
    studio_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    if parsed_url.netloc == "mymember.site":
        studio_url += f"/{parsed_url.path.split('/', 3)[1]}"

    return ScrapedStudio(
        name=response["site_info"].get("site_long_name", "MyMemberSite"),
        url=studio_url,
        image=response["site_info"].get("site_logo", ""),
    )


def gallery_from_url(gallery_url: str) -> ScrapedGallery:
    """
    Scrapes a gallery from the given URL.

    Parameters
    ----------
    gallery_url : str
        The URL of the gallery to scrape.

    Returns
    -------
    ScrapedGallery
        The scraped gallery data.
    """
    api_url: str = __parse_api_url(gallery_url)
    studio: ScrapedStudio = __fetch_studio(api_url, gallery_url)
    raw_gallery = __api_request(__parse_url(api_url, gallery_url))

    scraped: ScrapedGallery = {}

    if title := raw_gallery.get("title"):
        scraped["title"] = title

    if _id := raw_gallery.get("id"):
        scraped["code"] = str(_id)

    if date := raw_gallery.get("publish_date"):
        scraped["date"] = date.split("T")[0]

    if details := raw_gallery.get("description"):
        scraped["details"] = BeautifulSoup(details, "html.parser").get_text()

    if tags := raw_gallery.get("tags"):
        scraped["tags"] = [ScrapedTag(name=t["name"]) for t in tags]

    if cast := raw_gallery.get("casts"):
        scraped["performers"] = [ScrapedPerformer(name=p["screen_name"]) for p in cast]

    scraped["studio"] = studio

    return scraped


def scene_from_url(scene_url: str) -> ScrapedScene:
    """
    Scrapes a scene from the given URL.

    Parameters
    ----------
    scene_url : str
        The URL of the scene to scrape.

    Returns
    -------
    ScrapedScene
        The scraped scene data.
    """
    api_url: str = __parse_api_url(scene_url)
    studio: ScrapedStudio = __fetch_studio(api_url, scene_url)
    raw_scene = __api_request(__parse_url(api_url, scene_url))

    scraped: ScrapedScene = {}

    if title := raw_scene.get("title"):
        scraped["title"] = title

    if _id := raw_scene.get("id"):
        scraped["code"] = str(_id)

    if date := raw_scene.get("publish_date"):
        scraped["date"] = date.split("T")[0]

    if details := raw_scene.get("description"):
        scraped["details"] = BeautifulSoup(details, "html.parser").get_text()

    if tags := raw_scene.get("tags"):
        scraped["tags"] = [ScrapedTag(name=t["name"]) for t in tags]

    if cast := raw_scene.get("casts"):
        scraped["performers"] = [ScrapedPerformer(name=p["screen_name"]) for p in cast]

    if image := dig(raw_scene, ("poster_src", "cover_photo")):
        scraped["image"] = image

    scraped["studio"] = studio

    return scraped


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
