from datetime import datetime
import json
import re
import sys
from typing import Any, Callable, Dict, List
from urllib.parse import urlparse

import requests

from py_common import log
from py_common.deps import ensure_requirements
ensure_requirements("algoliasearch")
from py_common.types import ScrapedPerformer, ScrapedTag
from py_common.util import dig, guess_nationality, scraper_args

from algoliasearch.search.client import SearchClientSync
from algoliasearch.search.config import SearchConfig
from algoliasearch.search.models.hit import Hit
from algoliasearch.search.models.search_params import SearchParams

IMAGE_CDN = "https://images03-fame.gammacdn.com"

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


def get_homepage(site: str) -> str:
    return f"https://www.{site}.com"


def get_search_client(site: str) -> SearchClientSync:
    # Get API auth and initialise client
    app_id, api_key = get_api_auth(site)
    config = SearchConfig(
        app_id=app_id,
        api_key=api_key,
    )
    homepage = get_homepage(site)
    config.headers['Origin'] = homepage
    config.headers['Referer'] = homepage
    return SearchClientSync(config=config)


def default_postprocess(obj: Any, _) -> Any:
    return obj


genders_map = {
    'shemale': 'transgender_female',
}


def _construct_performer_url(p: Hit, site: str) -> str:
    return f"https://www.{site}.com/en/pornstar/view/{p.url_name}/{p.actor_id}"


## Helper functions to convert from Algolia's API to Stash's scraper return type
def to_scraped_performer(performer_from_api: Hit, site: str) -> ScrapedPerformer:
    performer: ScrapedPerformer = {
        "name": performer_from_api.name,
        "gender": genders_map.get(performer_from_api.gender, performer_from_api.gender),
    }

    if details := performer_from_api.description:
        performer["details"] = details

    if eye_color := performer_from_api.attributes.get('eye_color'):
        performer["eye_color"] = eye_color

    if hair_color := performer_from_api.attributes.get('hair_color'):
        performer["hair_color"] = hair_color

    if ethnicity := performer_from_api.attributes.get('ethnicity'):
        performer["ethnicity"] = ethnicity

    if alternate_names := performer_from_api.attributes.get('alternate_names'):
        performer["aliases"] = alternate_names

    if height := performer_from_api.attributes.get('height'):
        performer["height"] = height

    if weight := performer_from_api.attributes.get('weight'):
        performer["weight"] = weight
    
    if home := performer_from_api.attributes.get('home'):
        performer["country"] = home

    if performer_from_api.has_pictures:
        main_pic = list(performer_from_api.pictures.values())[-1]
        performer["images"] = [f"{IMAGE_CDN}/actors{main_pic}"]

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
            "attributesToHighlight": [],
            "filters": f"actor_id:{actor_id}",
            "length": 1,
        },
    )

    log.debug(f"Number of search hits: {response.nb_hits}")

    if response.nb_hits:
        return to_scraped_performer(response.hits[0], site)
    return {}
    # return postprocess(to_scraped_performer(api_performer_json), api_performer_json)


def performer_search(name: str, sites: List[str]) -> list[ScrapedPerformer]:
    site = sites[0]
    # Get API auth and initialise client
    client = get_search_client(site)

    response = client.search_single_index(
        index_name="all_actors_latest_desc",
        search_params={
            "attributesToHighlight": [],
            "query": name,
            "length": 20,
        },
    )

    log.debug(f"Number of search hits: {response.nb_hits}")

    if response.nb_hits:
        return [ to_scraped_performer(hit, site) for hit in response.hits ]
    return []


def performer_from_fragment(args: Dict[str, Any]) -> ScrapedPerformer:
    """
    This receives:
    - name
    - urls
    - gender
    from the result of the performer-by-name search
    """
    # the first URL should be usable for a full search
    url = args.get("urls")[0]
    return performer_from_url(url)


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    log.debug(f"args: {args}")
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
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = performer_search(name, sites)
        # case "movie-by-url", {"url": url} if url:
        #     url = redirect(url)
        #     result = movie_from_url(url, postprocess=bangbros)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    log.debug(f"result: {result}")

    print(json.dumps(result))
