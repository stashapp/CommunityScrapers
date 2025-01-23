from datetime import datetime
import json
import re
import sys
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from py_common import log
from py_common.deps import ensure_requirements
ensure_requirements("algoliasearch")
from py_common.types import ScrapedPerformer, ScrapedTag
from py_common.util import dig, guess_nationality, scraper_args

from algoliasearch.search.client import SearchClientSync
from algoliasearch.search.config import SearchConfig


def get_api_auth(site: str) -> tuple[str, str]:
    homepage = f"https://www.{site}.com"
    headers = {
        "User-Agent":
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
        "Origin": homepage,
        "Referer": homepage
    }

    # make a request to the site's homepage to get API Key and Application ID
    r = requests.get(homepage, headers=headers)
    # extract JSON
    if not (match := re.search(r"window.env\s+=\s(.+);", r.text)):
        log.error('Cannot find JSON in homepage for API keys')
        sys.exit(1)
    data = json.loads(match.group(1))
    application_id = data['api']['algolia']['applicationID']
    api_key = data['api']['algolia']['apiKey']
    return application_id, api_key


def get_search_client(site: str) -> SearchClientSync:
    # Get API auth and initialise client
    app_id, api_key = get_api_auth(site)
    config = SearchConfig(
        app_id=app_id,
        api_key=api_key,
    )
    homepage = f"https://www.{site}.com"
    config.headers['Origin'] = homepage
    config.headers['Referer'] = homepage
    return SearchClientSync(config=config)


def default_postprocess(obj: Any, _) -> Any:
    return obj


tags_map = {
    90: "Athletic Woman",
    107: "White Woman",
    112: "Black Woman",
    113: "European Woman",
    121: "Latina Woman",
    125: "Black Hair (Female)",
    126: "Blond Hair (Female)",
    127: "Brown Hair (Female)",
    128: "Red Hair (Female)",
    215: "Rimming Him",
    274: "Rimming Her",
    374: "Black Man",
    376: "European Man",
    377: "Latino Man",
    378: "White Man",
    379: "Black Hair (Male)",
    380: "Blond Hair (Male)",
    381: "Brown Hair (Male)",
    383: "Red Hair (Male)",
    385: "Shaved Head",
    386: "Short Hair (Male)",
}
def to_tag(api_object: dict) -> ScrapedTag:
    mapped_tag = tags_map.get(api_object["id"], api_object["name"].strip())
    return {"name": mapped_tag}


def to_tags(api_object: dict) -> list[ScrapedTag]:
    tags = api_object.get("tags", [])
    return [to_tag(x) for x in tags if "name" in x or x.get("id") in tags_map.keys()]


def _construct_performer_url(api_result: dict, site: str) -> str:
    id_ = api_result["id"]
    slug = slugify(api_result["name"])
    return f"https://www.{site}.com/model/{id_}/{slug}"


## Helper functions to convert from Aylo's API to Stash's scaper return types
def to_scraped_performer(
    performer_from_api: dict, site: str | None = None
) -> ScrapedPerformer:
    if (type_ := dig(performer_from_api, "brand")) and type_ not in (
        "actorsandtags",
        # Older sites use this type
        "phpactors",
    ):
        wrong_type = performer_from_api.get("type", "mystery")
        wrong_id = performer_from_api.get("id", "unknown")
        log.error(f"Attempted to scrape a '{wrong_type}' (ID: {wrong_id}) as a scene.")
        raise ValueError("Invalid performer from API")
    # This is all we get when scraped as part of a scene or movie
    performer: ScrapedPerformer = {
        "name": performer_from_api["name"],
        "gender": performer_from_api["gender"],
    }

    if aliases := ", ".join(
        alias
        for alias in performer_from_api.get("aliases", [])
        if alias.lower() != performer["name"].lower()
    ):
        performer["aliases"] = aliases

    if details := performer_from_api.get("bio"):
        performer["details"] = details

    # All remaining fields are only available when scraped directly
    if height := performer_from_api.get("height"):
        # Convert to cm
        performer["height"] = str(round(height * 2.54))

    if weight := performer_from_api.get("weight"):
        # Convert to kg
        performer["weight"] = str(round(weight / 2.205))

    if birthdate := performer_from_api.get("birthday"):
        performer["birthdate"] = datetime.strptime(
            birthdate, "%Y-%m-%dT%H:%M:%S%z"
        ).strftime("%Y-%m-%d")

    if birthplace := performer_from_api.get("birthPlace"):
        performer["country"] = guess_nationality(birthplace)

    if measurements := performer_from_api.get("measurements"):
        performer["measurements"] = measurements

    images = dig(performer_from_api, "images", "master_profile") or {}
    # Performers can have multiple images, try to get the biggest versions
    if images := [
        img
        for alt in images.values()
        if (img := dig(alt, ("xx", "xl", "lg", "md", "sm"), "url"))
    ]:
        performer["images"] = images

    if tags := to_tags(performer_from_api):
        performer["tags"] = tags

    if site:
        performer["urls"] = [_construct_performer_url(performer_from_api, site)]

    return performer


def get_site(url: str) -> str:
    """
    Extract the domain from the URL, e.g.

    www.evilangel.com -> evilangel
    evilangel.com -> evilangel
    """
    return urlparse(url).netloc.split(".")[-2]


def get_id(url: str) -> str:
    "Get the ID from a URL"
    if not (match := re.search(r"/(\d+)$", url)):
        log.error(
            "Can't get the ID from the URL. "
            "Are you sure that URL is from a site that uses the Algolia API?"
        )
        return None
    return match.group(1)


def uri_index_query(index: str) -> str:
    """
    Produces the URI path for a single index query
    """
    return f"/1/indexes/{index}/query"


def uri_one_record_by_id(index: str, id: str):
    """
    Produces the URI path for a single index object
    """
    return f"/1/indexes/{index}/{id}"


def performer_from_url(
    url,
    postprocess: Callable[
        [ScrapedPerformer, dict], ScrapedPerformer
    ] = default_postprocess,
) -> ScrapedPerformer | None:
    """
    Scrapes a performer from a URL, running an optional postprocess function on the result
    """
    actor_id = get_id(url)
    log.debug(f"Performer ID: {actor_id}")

    site = get_site(url)
    log.debug(f"Site: {site}")

    # Get API auth and initialise client
    client = get_search_client(site)

    response = client.search_single_index(
        index_name="all_actors_latest_desc",
        search_params={
            "facetFilters": [f"actor_id:{actor_id}"]
        }
    )

    log.debug(response)

    # # search performer by ID
    # request_body = {
    #     "params": "hitsPerPage=20&page=0&query=",
    #     "facetFilters": [f"actor_id:{actor_id}"]
    # }
    # res = session.post(uri_index_query("all_actors_latest_desc"), json=request_body)
    # log.debug(res.status_code)
    # log.debug(res.text)

    return {}
    # return postprocess(to_scraped_performer(api_performer_json), api_performer_json)


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    match op, args:
        # case "gallery-by-url", {"url": url} if url:
        #     url = redirect(url)
        #     result = gallery_from_url(url, postprocess=bangbros)
        # case "gallery-by-fragment":
        #     fixed = replace_all(args, "url", redirect)
        #     result = gallery_from_fragment(
        #         fixed, search_domains=domains, postprocess=bangbros
        #     )
        # case "scene-by-url", {"url": url} if url:
        #     url = redirect(url)
        #     result = scene_from_url(url, postprocess=bangbros)
        # case "scene-by-name", {"name": name} if name:
        #     result = scene_search(name, search_domains=domains, postprocess=bangbros)
        # case "scene-by-fragment" | "scene-by-query-fragment", args:
        #     args = replace_all(args, "url", redirect)
        #     result = scene_from_fragment(
        #         args, search_domains=domains, postprocess=bangbros
        #     )
        case "performer-by-url", {"url": url}:
            # url = redirect(url)
            result = performer_from_url(url)
        # case "performer-by-fragment", args:
        #     result = performer_from_fragment(args)
        # case "performer-by-name", {"name": name} if name:
        #     result = performer_search(
        #         name, search_domains=domains, postprocess=bangbros
        #     )
        # case "movie-by-url", {"url": url} if url:
        #     url = redirect(url)
        #     result = movie_from_url(url, postprocess=bangbros)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
