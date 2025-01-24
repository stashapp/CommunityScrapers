import json
import re
import sys
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from py_common import log
from py_common.deps import ensure_requirements
ensure_requirements("algoliasearch")
from py_common.types import ScrapedPerformer, ScrapedScene
from py_common.util import guess_nationality, scraper_args

from algoliasearch.search.client import SearchClientSync
from algoliasearch.search.config import SearchConfig
from algoliasearch.search.models.hit import Hit

FIXED_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
IMAGE_CDN = "https://images03-fame.gammacdn.com"


def headers_for_homepage(homepage: str) -> dict[str, str]:
    return {
        "User-Agent": FIXED_USER_AGENT,
        "Origin": homepage,
        "Referer": homepage
    }


def get_api_auth(homepage: str) -> tuple[str, str]:
    # make a request to the site's homepage to get API Key and Application ID
    r = requests.get(homepage, headers=headers_for_homepage(homepage))
    # extract JSON
    if not (match := re.search(r"window.env\s+=\s(.+);", r.text)):
        log.error('Cannot find JSON in homepage for API keys')
        sys.exit(1)
    data = json.loads(match.group(1))
    application_id = data['api']['algolia']['applicationID']
    api_key = data['api']['algolia']['apiKey']
    return application_id, api_key


def get_homepage_url(site: str) -> str:
    return f"https://www.{site}.com"


def get_search_client(site: str) -> SearchClientSync:
    homepage = get_homepage_url(site)
    # Get API auth and initialise client
    app_id, api_key = get_api_auth(homepage)
    config = SearchConfig(
        app_id=app_id,
        api_key=api_key,
    )
    config.headers.update(headers_for_homepage(homepage))
    return SearchClientSync(config=config)


def default_postprocess(obj: Any, _) -> Any:
    return obj


genders_map = {
    'shemale': 'transgender_female',
}
def parse_gender(gender: str) -> str:
    return genders_map.get(gender, gender)

def _construct_performer_url(performer: Hit, site: str) -> str:
    return f"{get_homepage_url(site)}/en/pornstar/view/{performer.url_name}/{performer.actor_id}"

def _construct_movie_url(scene: Hit, site: str) -> str:
    return f"{get_homepage_url(site)}/en/movie/{scene.url_movie_title}/{scene.movie_id}"

def _construct_scene_url(scene: Hit, site: str) -> str:
    return f"{get_homepage_url(site)}/en/video/{scene.sitename}/{scene.url_title}/{scene.clip_id}"


# Helper function to convert from Algolia's API to Stash's scraper return type
def to_scraped_performer(performer_from_api: Hit, site: str) -> ScrapedPerformer:
    performer: ScrapedPerformer = {
        "name": performer_from_api.name,
        "gender": parse_gender(performer_from_api.gender),
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
        performer["country"] = guess_nationality(home)

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


# Helper function to convert from Algolia's API to Stash's scraper return type
def to_scraped_scene(scene_from_api: Hit, site: str) -> ScrapedScene:
    scene: ScrapedScene = {
        "code": str(scene_from_api.clip_id),
        "title": scene_from_api.title
    }

    if description := scene_from_api.description:
        scene["details"] = description

    if scene_from_api.url_title:
        scene["urls"] = [
            _construct_scene_url(scene_from_api, site_available)
            for site_available in scene_from_api.availableOnSite
        ]

    if release_date := scene_from_api.release_date:
        scene["date"] = release_date

    if pictures := scene_from_api.pictures:
        try:
            scene['image'] = 'https://images03-fame.gammacdn.com/movies' + next(
                iter(pictures['nsfw']['top'].values()))
        except:
            try:
                scene['image'] = 'https://images03-fame.gammacdn.com/movies' + next(
                        iter(pictures['sfw']['top'].values()))
            except:
                log.warning("Can't locate image.")

    """
    A studio name can come from:
    - studio
    - channel
    - serie
    - segment
    - sitename
    - network
    e.g. see the complexity in `determine_studio_name_from_json` in Algolia.py

    possibly this script should be a class that can be sub-classed with a custom studio parser/postprocessor
    (or just imported reused functions like the Aylo scrapers seem to do)
    """
    if studio_name := scene_from_api.studio_name:
        scene["studio"] = { "name": studio_name }

    if scene_from_api.movie_id:
        scene["movies"] = [{
            "name": scene_from_api.movie_title,
            "date": scene_from_api.movie_date_created,
            "synopsis": scene_from_api.movie_desc,
            "url": _construct_movie_url(scene_from_api, site),
        }]

    if categories := scene_from_api.categories:
        scene["tags"] = [
            {
                "name": category["name"]
            }
            for category in categories
        ]

    if actors := scene_from_api.actors:
        scene["performers"] = [
            {
                "name": actor["name"],
                "gender": parse_gender(actor["gender"]),
                "urls": [
                    _construct_performer_url(
                        Hit.from_dict({
                            "objectID": "00000-000-000",
                            "url_name": actor["url_name"],
                            "actor_id": actor["actor_id"],
                        }),
                        site,
                    )
                ]
            }
            for actor in actors
        ]

    if directors := scene_from_api.directors:
        scene["director"] = ", ".join([ director["name"] for director in directors ])

    return scene


def scene_from_url(
    url, postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedPerformer | None:
    """
    Scrapes a scene from a URL, running an optional postprocess function on the result
    """
    clip_id = get_id(url)
    log.debug(f"Clip ID: {clip_id}")

    site = get_site(url)
    log.debug(f"Site: {site}")

    # Get API auth and initialise client
    client = get_search_client(site)

    response = client.search_single_index(
        index_name="all_scenes",
        search_params={
            "attributesToHighlight": [],
            "filters": f"clip_id:{clip_id}",
            "length": 1,
        },
    )

    log.debug(f"Number of search hits: {response.nb_hits}")

    if response.nb_hits:
        return postprocess(to_scraped_scene(response.hits[0], site), response.hits[0])
    return {}


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
        return postprocess(to_scraped_performer(response.hits[0], site), response.hits[0])
    return {}


def performer_search(name: str, sites: list[str]) -> list[ScrapedPerformer]:
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


def performer_from_fragment(args: dict[str, Any]) -> ScrapedPerformer:
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
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
            # result = scene_from_url(url, postprocess=bangbros)
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
