from base64 import b64decode, b64encode
import configparser
import json
import re
import sys
from time import time
from typing import Any, Callable, Literal
from urllib.parse import urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedGallery, ScrapedMovie, ScrapedPerformer, ScrapedScene
from py_common.util import dig, guess_nationality, is_valid_url, scraper_args

ensure_requirements("algoliasearch", "bs4:beautifulsoup4", "requests")
from algoliasearch.search.client import SearchClientSync
from algoliasearch.search.config import SearchConfig
from bs4 import BeautifulSoup as bs
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
    """
    Saves the API auth (app_id and api_key) to the CONFIG_FILE
    so that it can be loaded in future runs of this script
    """
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
    """
    Attempts to load a previously obtained set of API auth credentials
    (`app_id` and `api_key`) for a `site`, if it exists in the
    CONFIG_FILE and is still valid for a reasonable amount of time
    """
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
    """
    Gets the API auth (`app_id` and `api_key`) for a `site`, either
    from previously cached in CONFIG_FILE, or retrieved from the
    site's homepage
    """
    # attempt to get cached API auth
    if (auth := api_auth_cache_read(site)) and auth[0] and auth[1]:
        return auth
    
    log.debug('No valid auth found in cache, fetching new auth')

    # make a request to the site's homepage to get API Key and Application ID
    homepage = homepage_url(site)
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


def homepage_url(site: str) -> str:
    return f"https://www.{site}.com"


def clean_text(details: str) -> str:
    """
    Remove escaped backslashes and html parse the details text.
    """
    if details:
        details = details.replace("\\", "")
        details = re.sub(r"<\s*\/?br\s*\/?\s*>", "\n", details)
        details = bs(details, features='html.parser').get_text()
        details = '\n'.join(line.strip() for line in details.split('\n') if line.strip())
    return details


def get_search_client(site: str) -> SearchClientSync:
    """
    Initialises a search client with API auth credentials
    (`app_id` and `api_key`) and request headers
    """
    # Get API auth and initialise client
    app_id, api_key = get_api_auth(site)
    config = SearchConfig(app_id, api_key)
    config.headers.update(headers_for_homepage(homepage_url(site)))
    return SearchClientSync(config=config)


def default_postprocess(obj: Any, _) -> Any:
    return obj


genders_map = {
    'shemale': 'transgender_female',
}
def parse_gender(gender: str) -> str:
    return genders_map.get(gender, gender)

def movie_cover_image_url(cover_path: str, position: Literal["front", "back"]) -> str:
    return f"https://transform.gammacdn.com/movies{cover_path}_{position}_400x625.jpg?width=450&height=636"

def gallery_url(site: str, url_title: str, set_id: str) -> str:
    return f"{homepage_url(site)}/en/photo/{url_title}/{set_id}"

def performer_url(site: str, url_name: str, actor_id: str) -> str:
    return f"{homepage_url(site)}/en/pornstar/view/{url_name}/{actor_id}"

def movie_url(site: str, url_title: str, movie_id: str) -> str:
    return f"{homepage_url(site)}/en/movie/{url_title}/{movie_id}"

def scene_url(site: str, sitename: str, url_title: str, clip_id: str) -> str:
    return f"{homepage_url(site)}/en/video/{sitename}/{url_title}/{clip_id}"


def to_scraped_performer(performer_from_api: dict[str, Any], site: str) -> ScrapedPerformer:
    """
    Helper function to convert from Algolia's API to Stash's scraper return type
    """
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

    performer["urls"] = [performer_url(site, performer_from_api["url_name"], performer_from_api["actor_id"])]

    return performer


def site_from_url(url: str) -> str:
    """
    Extract the (second level) part of the domain from the URL, e.g.

    - www.evilangel.com -> evilangel
    - evilangel.com -> evilangel
    """
    return urlparse(url).netloc.split(".")[-2]


def id_from_url(url: str) -> str | None:
    "Get the ID from a URL"
    if match := re.search(r"/(\d+)$", url):
        return match.group(1)
    else:
        log.error(
            "Can't get the ID from the URL. "
            "Are you sure that URL is from a site that uses the Algolia API?"
        )
        return None


def to_scraped_scene(scene_from_api: dict[str, Any], site: str) -> ScrapedScene:
    """
    Helper function to convert from Algolia's API to Stash's scraper return type
    """
    scene: ScrapedScene = {
        "code": str(scene_from_api["clip_id"]),
        "title": scene_from_api["title"]
    }

    if description := scene_from_api["description"]:
        scene["details"] = clean_text(description)

    if scene_from_api["url_title"]:
        sitename = scene_from_api.get("sitename")
        url_title = scene_from_api.get("url_title")
        scene["urls"] = [
            scene_url(site_available, sitename, url_title, scene["code"])
            for site_available in scene_from_api["availableOnSite"]
        ]

    if release_date := scene_from_api["release_date"]:
        scene["date"] = release_date

    if (images := dig(scene_from_api, "pictures", ("nsfw", "sfw"), "top")) and (
        image := next(iter(images.values()), None)
    ):
        scene["image"] = f"{IMAGE_CDN}/movies{image}"

    """
    A studio name can come from:
    - studio
    - channel
    - serie
    - segment
    - sitename
    - network

    create a custom postprocess function in the network scraper to determine
    the studio name, see EvilAngel.py for an example
    """
    if studio_name := scene_from_api["studio_name"]:
        scene["studio"] = { "name": studio_name }

    if scene_from_api["movie_id"]:
        scene["movies"] = [{
            "name": scene_from_api["movie_title"],
            "date": scene_from_api["movie_date_created"],
            "synopsis": scene_from_api["movie_desc"],
            "url": movie_url(site, scene_from_api["url_movie_title"], scene_from_api["movie_id"]),
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
            "urls": [ performer_url(site, actor["url_name"], actor["actor_id"]) ]
        }
        for actor in actors
    ]


def api_scene_from_id(
    clip_id,
    sites: list[str],
) -> dict[str, Any] | None:
    """
    Searches a scene from a clip_id and returns the API result as-is

    It is a separate function to allow gallery scraping to use scene info
    as some sites do not have publicly available galleries.
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
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess
) -> ScrapedGallery | None:
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
    clip_id = id_from_url(url)
    log.debug(f"Clip ID: {clip_id}")

    site = site_from_url(url)
    log.debug(f"Site: {site}")

    return scene_from_id(clip_id, [site], postprocess)


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
        gallery["details"] = clean_text(description)

    gallery["urls"] = []
    # scenes can include photoset_id
    if photoset_id := api_hit.get("photoset_id"):
        gallery["code"] = photoset_id
        gallery["urls"].append(gallery_url(site, api_hit.get("photoset_url_name"), photoset_id))
    # photosets have set_id
    if set_id := api_hit.get("set_id"):
        gallery["code"] = str(set_id)
        gallery["urls"].append(gallery_url(site, api_hit.get("url_title"), set_id))
    # api photosets can have clip_title
    if clip_title := api_hit.get("clip_title"):
        gallery["urls"].append(scene_url(site, api_hit.get("sitename"), slugify(clip_title), api_hit.get("clip_id")))

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
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
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
    return None


def gallery_from_url(
    url,
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> ScrapedGallery | None:
    """
    Scrapes a gallery from a URL, running an optional postprocess function on the result
    """
    url_id = id_from_url(url)
    site = site_from_url(url)
    log.debug(f"Site: {site}")

    # some sites have public photoset URLs, so can be searched by public photoset ID
    if "/photo/" in url:
        log.debug(f"set_id: {url_id}")
        return gallery_from_set_id(url_id, [site], postprocess)
    
    # some sites do not have public photosets, but we should be able to use a scene URL
    if "/video/" in url:
        log.debug(f"clip_id: {url_id}")
        return gallery_from_scene_id(url_id, [site], postprocess)

    return None


def performer_from_url(
    url,
    postprocess: Callable[[ScrapedPerformer, dict], ScrapedPerformer] = default_postprocess,
) -> ScrapedPerformer | None:
    """
    Scrapes a performer from a URL, running an optional postprocess function on the result
    """
    actor_id = id_from_url(url)
    log.debug(f"Performer ID: {actor_id}")

    site = site_from_url(url)
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


def to_scraped_movie(movie_from_api: dict[str, Any], site: str) -> ScrapedMovie:
    """
    Helper function to convert from Algolia's API to Stash's scraper return type
    """
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
        movie["synopsis"] = clean_text(description)

    if studio_name := movie_from_api.get("studio_name"):
        movie["studio"] = { "name": studio_name }

    if cover_path := movie_from_api.get("cover_path"):
        front_image_url = movie_cover_image_url(cover_path, 'front')
        if is_valid_url(front_image_url):
            movie["front_image"] = front_image_url
        back_image_url = movie_cover_image_url(cover_path, 'back')
        if is_valid_url(back_image_url):
            res_front = requests.get(front_image_url, headers=headers_for_homepage(homepage_url(site)))
            res_back = requests.get(back_image_url, headers=headers_for_homepage(homepage_url(site)))
            if b64encode(res_front.content) == b64encode(res_back.content):
                log.debug("Front and Back images identical, NOT scraping back image")
            else:
                movie["back_image"] = back_image_url

    if url_title := movie_from_api.get("url_title"):
        movie["url"] = movie_url(site, url_title, movie_from_api.get("movie_id"))

    return movie


def movie_from_url(
    url, postprocess: Callable[[ScrapedMovie, dict], ScrapedMovie] = default_postprocess
) -> ScrapedMovie | None:
    """
    Scrapes a movie from a URL, running an optional postprocess function on the result
    """
    movie_id = id_from_url(url)
    log.debug(f"movie_id: {movie_id}")

    site = site_from_url(url)
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


def performer_search(
    name: str, 
    sites: list[str],
    postprocess: Callable[[ScrapedPerformer, dict], ScrapedPerformer] = default_postprocess,
) -> list[ScrapedPerformer]:
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
        return [
            postprocess(to_scraped_performer(hit.to_dict(), site), hit.to_dict())
            for hit in response.hits
        ]
    return []


def scene_search(
    query: str,
    sites: list[str],
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
        return [
            postprocess(to_scraped_scene(hit.to_dict(), site), hit.to_dict())
            for hit in response.hits
        ]
    return []


def gallery_search(
    query: str,
    sites: list[str],
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
        return [
            postprocess(to_scraped_gallery(hit.to_dict(), site), hit.to_dict())
            for hit in response.hits ]
    return []


def scene_from_fragment(
    args: dict[str, Any],
    sites: list[str],
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> ScrapedScene:
    """
    This receives:
    - sites
    from the scraper YAML (array items)
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
        return scene_from_url(args["urls"][0], postprocess)

    # if the (studio) code is present, search by clip_id
    if "code" in args and len(args["code"]) > 0:
        return scene_from_id(args["code"], sites, postprocess)
    
    # if a title is present, search by text
    if "title" in args and len(args["title"]) > 0:
        scenes = scene_search(args["title"], sites, postprocess)
        if len(scenes) > 0:
            return scenes[0]
    
    return {}


def gallery_from_fragment(
    fragment: dict[str, Any],
    sites: list[str],
    # min_ratio=config.minimum_similarity,
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
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
        return gallery_from_url(url, postprocess)

    if title := fragment.get("title"):
        scraped_galleries = gallery_search(title, sites, postprocess)

        # one match
        if len(scraped_galleries) == 1:
            return scraped_galleries[0]

        # TODO: do some match scoring here based on any other matching/near fragment properties

        # TODO: remove this first result return logic
        if len(scraped_galleries) > 1:
            return scraped_galleries[0]

    return None


def performer_from_fragment(
    args: dict[str, Any],
    postprocess: Callable[[ScrapedPerformer, dict], ScrapedPerformer] = default_postprocess,
) -> ScrapedPerformer:
    """
    This receives:
    - name
    - urls
    - gender
    from the result of the performer-by-name search
    """
    # the first URL should be usable for a full search
    url = args.get("urls")[0]
    return performer_from_url(url, postprocess)


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url)
        case "gallery-by-fragment", args:
            sites = args.pop("extra")
            result = gallery_from_fragment(args, sites)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = scene_search(name, sites)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            sites = args.pop("extra")
            result = scene_from_fragment(args, sites)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name, "extra": extra} if name and extra:
            result = performer_search(name, extra)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    log.debug(f"result: {result}")

    print(json.dumps(result))
