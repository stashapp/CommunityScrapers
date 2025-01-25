from base64 import b64decode
import configparser
import json
import re
import sys
from time import time
from typing import Any, Callable, Literal
from urllib.parse import urlparse

from py_common import log
from py_common.deps import ensure_requirements
ensure_requirements("algoliasearch", "requests")
from py_common.types import ScrapedGallery, ScrapedMovie, ScrapedPerformer, ScrapedScene
from py_common.util import dig, guess_nationality, scraper_args

from algoliasearch.search.client import SearchClientSync
from algoliasearch.search.config import SearchConfig
import requests

CONFIG_FILE = 'AlgoliaAPI.ini'
FIXED_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
IMAGE_CDN = "https://images03-fame.gammacdn.com"


def slugify(text: str) -> str:
    """
    This _should_ reproduce the behaviour of the title/name URL slug transform
    """
    return re.sub(r'[^a-zA-Z0-9-]+', '-', text)


def headers_for_homepage(homepage: str) -> dict[str, str]:
    return {
        "User-Agent": FIXED_USER_AGENT,
        "Origin": homepage,
        "Referer": homepage
    }


def api_auth_cache_write(site: str, app_id: str, api_key: str):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        config.get(site, 'valid_until')
    except configparser.NoSectionError:
        config.add_section(site)
    config.set(site, "app_id", app_id)
    config.set(site, "api_key", api_key)
    if match := re.search(r"validUntil=(\d+)", b64decode(api_key).decode('utf-8')):
        valid_until = match.group(1)
    else:
        valid_until = int(time())
    config.set(site, "valid_until", valid_until)
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as config_file:
        config.write(config_file)


def api_auth_cache_read(site: str) -> tuple[str, str] | tuple[None, None]:
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        valid_until = config.getint(site, 'valid_until')
        app_id = config.get(site, 'app_id')
        api_key = config.get(site, 'api_key')
    except configparser.NoSectionError as e:
        log.debug(f"Could not find section [{e.section}] in {CONFIG_FILE}")
        return None, None
    except configparser.NoOptionError as e:
        log.debug(f"Could not find option {e.option} in [{e.section}] in {CONFIG_FILE}")
        return None, None
    
    seconds_remaining = valid_until - int(time())
    if seconds_remaining < 600:
        return None, None
    
    log.debug(f'Using cached auth, valid for the next {seconds_remaining} seconds')
    
    return app_id, api_key


def get_api_auth(site: str) -> tuple[str, str]:
    # attempt to get cached API auth
    if (auth := api_auth_cache_read(site)) and auth[0] and auth[1]:
        return auth
    
    log.debug('No valid auth found in cache, fetching new auth')

    # make a request to the site's homepage to get API Key and Application ID
    homepage = get_homepage_url(site)
    r = requests.get(homepage, headers=headers_for_homepage(homepage))
    # extract JSON
    if not (match := re.search(r"window.env\s+=\s(.+);", r.text)):
        log.error('Cannot find JSON in homepage for API keys')
        sys.exit(1)
    data = json.loads(match.group(1))
    app_id = data['api']['algolia']['applicationID']
    api_key = data['api']['algolia']['apiKey']
    
    api_auth_cache_write(site, app_id, api_key)

    return app_id, api_key


def get_homepage_url(site: str) -> str:
    return f"https://www.{site}.com"


def get_search_client(site: str) -> SearchClientSync:
    # Get API auth and initialise client
    app_id, api_key = get_api_auth(site)
    config = SearchConfig(app_id, api_key)
    config.headers.update(headers_for_homepage(get_homepage_url(site)))
    return SearchClientSync(config=config)


def default_postprocess(obj: Any, _) -> Any:
    return obj


genders_map = {
    'shemale': 'transgender_female',
}
def parse_gender(gender: str) -> str:
    return genders_map.get(gender, gender)

def _movie_cover_image_url(cover_path: str, position: Literal["front", "back"]) -> str:
    return f"https://transform.gammacdn.com/movies{cover_path}_{position}_400x625.jpg?width=450&height=636"

def _gallery_url(site: str, url_title: str, set_id: str) -> str:
    return f"{get_homepage_url(site)}/en/photo/{url_title}/{set_id}"

def _performer_url(site: str, url_name: str, actor_id: str) -> str:
    return f"{get_homepage_url(site)}/en/pornstar/view/{url_name}/{actor_id}"

def _movie_url(site: str, url_title: str, movie_id: str) -> str:
    return f"{get_homepage_url(site)}/en/movie/{url_title}/{movie_id}"

def _scene_url(site: str, sitename: str, url_title: str, clip_id: str) -> str:
    return f"{get_homepage_url(site)}/en/video/{sitename}/{url_title}/{clip_id}"


# Helper function to convert from Algolia's API to Stash's scraper return type
def to_scraped_performer(performer_from_api: dict[str, Any], site: str) -> ScrapedPerformer:
    performer: ScrapedPerformer = {
        "name": performer_from_api["name"],
        "gender": parse_gender(performer_from_api["gender"]),
    }

    if details := performer_from_api["description"]:
        performer["details"] = details

    if eye_color := performer_from_api["attributes"]["eye_color"]:
        performer["eye_color"] = eye_color

    if hair_color := performer_from_api["attributes"]["hair_color"]:
        performer["hair_color"] = hair_color

    if ethnicity := performer_from_api["attributes"]["ethnicity"]:
        performer["ethnicity"] = ethnicity

    if alternate_names := performer_from_api["attributes"]["alternate_names"]:
        performer["aliases"] = alternate_names

    if height := performer_from_api["attributes"]["height"]:
        performer["height"] = height

    if weight := performer_from_api["attributes"]["weight"]:
        performer["weight"] = weight
    
    if home := performer_from_api["attributes"]["home"]:
        performer["country"] = guess_nationality(home)

    if performer_from_api["has_pictures"]:
        main_pic = list(performer_from_api["pictures"].values())[-1]
        performer["images"] = [f"{IMAGE_CDN}/actors{main_pic}"]

    performer["urls"] = [_performer_url(site, performer_from_api["url_name"], performer_from_api["actor_id"])]

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
def to_scraped_scene(scene_from_api: dict[str, Any], site: str) -> ScrapedScene:
    scene: ScrapedScene = {
        "code": str(scene_from_api["clip_id"]),
        "title": scene_from_api["title"]
    }

    if description := scene_from_api["description"]:
        scene["details"] = description

    if scene_from_api["url_title"]:
        sitename = scene_from_api.get("sitename")
        url_title = scene_from_api.get("url_title")
        scene["urls"] = [
            _scene_url(site_available, sitename, url_title, scene["code"])
            for site_available in scene_from_api["availableOnSite"]
        ]

    if release_date := scene_from_api["release_date"]:
        scene["date"] = release_date

    if (images := dig(scene_from_api, "pictures", ("nsfw", "sfw"), "top")) and (
        image := next(iter(images.values()), None)
    ):
        scene["image"] = f"https://images03-fame.gammacdn.com/movies{image}"

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
    if studio_name := scene_from_api["studio_name"]:
        scene["studio"] = { "name": studio_name }

    if scene_from_api["movie_id"]:
        scene["movies"] = [{
            "name": scene_from_api["movie_title"],
            "date": scene_from_api["movie_date_created"],
            "synopsis": scene_from_api["movie_desc"],
            "url": _movie_url(site, scene_from_api["url_movie_title"], scene_from_api["movie_id"]),
        }]

    if categories := scene_from_api["categories"]:
        scene["tags"] = categories_to_tags(categories)

    if actors := scene_from_api["actors"]:
        scene["performers"] = actors_to_performers(actors, site)

    if directors := scene_from_api["directors"]:
        scene["director"] = directors_to_csv_string(directors)

    return scene


def directors_to_csv_string(directors):
    return ", ".join([ director["name"] for director in directors ])

def categories_to_tags(categories):
    return [{ "name": category["name"] } for category in categories]

def actors_to_performers(actors: list[dict[str, Any]], site: str):
    return [
        {
            "name": actor["name"],
            "gender": parse_gender(actor["gender"]),
            "urls": [ _performer_url(site, actor["url_name"], actor["actor_id"]) ]
        }
        for actor in actors
    ]


def api_scene_from_id(
    clip_id,
    sites: list[str],
) -> dict[str, Any] | None:
    """
    Searches a scene from a clip_id
    """
    # TODO: handle multiple sites
    site = sites[0]
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
        return response.hits[0].to_dict()
    return None


def scene_from_id(
    clip_id,
    sites: list[str],
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedScene | None:
    """
    Scrapes a scene from a clip_id, running an optional postprocess function on the result
    """
    # TODO: handle multiple sites
    site = sites[0]

    api_scene = api_scene_from_id(clip_id, sites)

    if api_scene:
        return postprocess(to_scraped_scene(api_scene, site), api_scene)
    return None


def gallery_from_scene_id(
    clip_id,
    sites: list[str],
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedScene | None:
    """
    Scrapes a gallery from a clip_id, running an optional postprocess function on the result
    """
    # TODO: handle multiple sites
    site = sites[0]
    log.debug(f"Site: {site}")

    api_scene = api_scene_from_id(clip_id, sites)

    if api_scene:
        return postprocess(to_scraped_gallery(api_scene, site), api_scene)
    return None


def scene_from_url(
    url, postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedScene | None:
    """
    Scrapes a scene from a URL, running an optional postprocess function on the result
    """
    clip_id = get_id(url)
    log.debug(f"Clip ID: {clip_id}")

    site = get_site(url)
    log.debug(f"Site: {site}")

    return scene_from_id(clip_id, [site])


def to_scraped_gallery(api_hit: dict[str, Any], site: str) -> ScrapedGallery | None:
    """
    Scrapes an API search hit (could be scene or photoset) into a ScrapedGallery
    """
    gallery: ScrapedGallery = {}

    # scenes can include corresponding photoset_name
    if photoset_name := api_hit.get("photoset_name"):
        gallery["title"] = photoset_name
    # photosets have their own title (as do scenes)
    elif title := api_hit.get("title"):
        gallery["title"] = title

    if description := api_hit.get("description"):
        gallery["details"] = description

    gallery["urls"] = []
    # scenes can include photoset_id
    if photoset_id := api_hit.get("photoset_id"):
        gallery["code"] = photoset_id
        gallery["urls"].append(_gallery_url(site, api_hit.get("photoset_url_name"), photoset_id))
    # photosets have set_id
    if set_id := api_hit.get("set_id"):
        gallery["code"] = str(set_id)
        gallery["urls"].append(_gallery_url(site, api_hit.get("url_title"), set_id))
    # api photosets can have clip_title
    if clip_title := api_hit.get("clip_title"):
        gallery["urls"].append(_scene_url(site, api_hit.get("sitename"), slugify(clip_title), api_hit.get("clip_id")))

    # photoset has date_online
    if date_online := api_hit.get("date_online"):
        gallery["date"] = date_online
    # scene has release_date
    elif release_date := api_hit.get("release_date"):
        gallery["date"] = release_date

    if studio_name := api_hit.get("studio_name"):
        gallery["studio"] = { "name": studio_name }

    if categories := api_hit.get("categories"):
        gallery["tags"] = categories_to_tags(categories)

    if actors := api_hit.get("actors"):
        gallery["performers"] = actors_to_performers(actors, site)

    if directors := api_hit.get("directors"):
        gallery["photographer"] = directors_to_csv_string(directors)
    
    return gallery


def gallery_from_set_id(
    set_id,
    sites: list[str],
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> ScrapedGallery | None:
    """
    Scrapes a gallery from a set_id, running an optional postprocess function on the result
    """
    # TODO: handle multiple sites
    site = sites[0]
    log.debug(f"Site: {site}")

    # Get API auth and initialise client
    client = get_search_client(site)

    response = client.search_single_index(
        index_name="all_photosets",
        search_params={
            "attributesToHighlight": [],
            "filters": f"set_id:{set_id}",
            "length": 1,
        },
    )

    log.debug(f"Number of search hits: {response.nb_hits}")

    if response.nb_hits:
        first_result = response.hits[0].to_dict()
        return postprocess(to_scraped_gallery(first_result, site), first_result)
    return {}


def gallery_from_url(
    url,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> ScrapedGallery | None:
    """
    Scrapes a gallery from a URL, running an optional postprocess function on the result
    """
    url_id = get_id(url)
    site = get_site(url)
    log.debug(f"Site: {site}")

    # some sites have public photoset URLs, so can be searched by public photoset ID
    if "/photo/" in url:
        log.debug(f"set_id: {url_id}")
        return gallery_from_set_id(url_id, [site])
    
    # some sites do not have public photosets, but we should be able to use a scene URL
    if "/video/" in url:
        log.debug(f"clip_id: {url_id}")
        return gallery_from_scene_id(url_id, [site])

    return None


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
        first_hit = response.hits[0].to_dict()
        return postprocess(to_scraped_performer(first_hit, site), first_hit)
    return None


# Helper function to convert from Algolia's API to Stash's scraper return type
def to_scraped_movie(movie_from_api: dict[str, Any], site: str) -> ScrapedMovie:
    movie: ScrapedMovie = {}

    if title := movie_from_api.get("title"):
        movie["name"] = title

    if date_created := movie_from_api.get("date_created"):
        movie["date"] = date_created

    if length := movie_from_api.get("length"):
        movie["duration"] = str(length)

    if directors := movie_from_api.get("directors"):
        movie["director"] = directors_to_csv_string(directors)

    if description := movie_from_api.get("description"):
        movie["synopsis"] = description

    if studio_name := movie_from_api.get("studio_name"):
        movie["studio"] = { "name": studio_name }

    if cover_path := movie_from_api.get("cover_path"):
        movie["front_image"] = _movie_cover_image_url(cover_path, 'front')
        movie["back_image"] = _movie_cover_image_url(cover_path, 'back')

    if url_title := movie_from_api.get("url_title"):
        movie["url"] = _movie_url(site, url_title, movie_from_api.get("movie_id"))

    return movie


def movie_from_url(
    url, postprocess: Callable[[ScrapedMovie, dict], ScrapedMovie] = default_postprocess
) -> ScrapedMovie | None:
    """
    Scrapes a movie from a URL, running an optional postprocess function on the result
    """
    movie_id = get_id(url)
    log.debug(f"movie_id: {movie_id}")

    site = get_site(url)
    log.debug(f"Site: {site}")

    # Get API auth and initialise client
    client = get_search_client(site)

    response = client.search_single_index(
        index_name="all_movies",
        search_params={
            "attributesToHighlight": [],
            "filters": f"movie_id:{movie_id}",
            "length": 1,
        },
    )

    log.debug(f"Number of search hits: {response.nb_hits}")

    if response.nb_hits:
        first_hit = response.hits[0].to_dict()
        return postprocess(to_scraped_movie(first_hit, site), first_hit)
    return None


def performer_search(name: str, sites: list[str]) -> list[ScrapedPerformer]:
    # TODO: handle multiple sites
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
        return [ to_scraped_performer(hit.to_dict(), site) for hit in response.hits ]
    return []


def scene_search(
    query: str,
    sites: list[str] | None = None,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> list[ScrapedScene]:
    # TODO: handle multiple sites
    site = sites[0]
    # Get API auth and initialise client
    client = get_search_client(site)

    response = client.search_single_index(
        index_name="all_scenes",
        search_params={
            "attributesToHighlight": [],
            "query": query,
            "length": 20,
        },
    )

    log.debug(f"Number of search hits: {response.nb_hits}")

    if response.nb_hits:
        return [ to_scraped_scene(hit.to_dict(), site) for hit in response.hits ]
    return []


def gallery_search(
    query: str,
    sites: list[str] | None = None,
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> list[ScrapedGallery]:
    # TODO: handle multiple sites
    site = sites[0]
    # Get API auth and initialise client
    client = get_search_client(site)

    response = client.search_single_index(
        index_name="all_photosets",
        search_params={
            "attributesToHighlight": [],
            "query": query,
            "length": 20,
        },
    )

    log.debug(f"Number of search hits: {response.nb_hits}")

    if response.nb_hits:
        return [ to_scraped_gallery(hit.to_dict(), site) for hit in response.hits ]
    return []


def scene_from_fragment(args: dict[str, Any], sites: list[str]) -> ScrapedScene:
    """
    This receives:
    - extra
    from the scraper YAML
    - url
    - title
    - code
    - details
    - director
    - date
    - urls
    from the result of the scene-by-name search
    """
    # the first URL should be usable for a full search
    if "urls" in args and len(args["urls"]) > 0:
        return scene_from_url(args["urls"][0])

    # if the (studio) code is present, search by clip_id
    if "code" in args and len(args["code"]) > 0:
        return scene_from_id(args["code"], sites)
    
    # if a title is present, search by text
    if "title" in args and len(args["title"]) > 0:
        scenes = scene_search(args["title"], sites)
        if len(scenes) > 0:
            return scenes[0]
    
    return {}


def gallery_from_fragment(
    fragment: dict[str, Any],
    sites: list[str],
    # min_ratio=config.minimum_similarity,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> ScrapedGallery | None:
    """
    Scrapes a gallery from a fragment, which must contain at least one of the following:
    - url: the URL of the scene the gallery belongs to
    - title: the title of the scene the gallery belongs to

    If min_ratio is provided _AND_ the fragment contains a title but no URL,
    the search will only return a scene if a match with at least that ratio is found

    If postprocess is provided it will be called on the result before returning
    """
    log.debug(f"in gallery_from_fragment, fragment: {fragment}")
    if url := fragment.get("url"):
        log.debug('doing gallery_from_fragment with gallery_from_url')
        return gallery_from_url(url)

    if title := fragment.get("title"):
        log.debug('doing gallery_from_fragment with gallery_search')
        scraped_galleries = gallery_search(title, sites)

        # one match
        if len(scraped_galleries) == 1:
            return scraped_galleries[0]

        # TODO: do some match scoring here based on any other matching/near fragment properties

        # TODO: remove this first result return logic
        if len(scraped_galleries) > 1:
            return scraped_galleries[0]

    return None


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
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url)
            # result = gallery_from_url(url, postprocess=bangbros)
        case "gallery-by-fragment", args:
            sites = args.pop("extra")
            result = gallery_from_fragment(args, sites)
            # result = gallery_from_fragment(
            #     fixed, search_domains=domains, postprocess=bangbros
            # )
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
            # result = scene_from_url(url, postprocess=bangbros)
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = scene_search(name, sites)
            # result = scene_search(name, search_domains=domains, postprocess=bangbros)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            sites = args.pop("extra")
            result = scene_from_fragment(args, sites)
            # result = scene_from_fragment(
            #     args, search_domains=domains, postprocess=bangbros
            # )
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = performer_search(name, sites)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url)
            # result = movie_from_url(url, postprocess=bangbros)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    log.debug(f"result: {result}")

    print(json.dumps(result))
