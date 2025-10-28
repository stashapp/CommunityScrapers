"""
Stash scraper that uses the Algolia API Python client
"""
from base64 import b64decode, b64encode
import configparser
from difflib import SequenceMatcher
import json
import os
import re
import sys
from time import time
from typing import Any, Callable, Literal, TypeVar
from urllib.parse import urlparse
from zipfile import ZipFile

from py_common import graphql, log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedGallery, ScrapedMovie, ScrapedPerformer, ScrapedScene
from py_common.util import dig, guess_nationality, is_valid_url, scraper_args
ensure_requirements("algoliasearch", "bs4:beautifulsoup4", "requests")

from algoliasearch.search.client import SearchClientSync
from algoliasearch.search.config import SearchConfig
from bs4 import BeautifulSoup as bs
import requests

T = TypeVar('T')

CONFIG_FILE = 'AlgoliaAPI.ini'
FIXED_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
IMAGE_CDN = "https://images03-fame.gammacdn.com"
TRANSFORM_IMAGE_CDN = "https://transform.gammacdn.com"


def slugify(text: str) -> str:
    "This _should_ reproduce the behaviour of the title/name URL slug transform"
    return re.sub(r'[^a-zA-Z0-9-]+', '-', text)

def headers_for_homepage(homepage: str) -> dict[str, str]:
    "Generates the request headers required for a homepage of a site"
    return { "User-Agent": FIXED_USER_AGENT, "Origin": homepage, "Referer": homepage }

def api_auth_cache_write(site: str, app_id: str, api_key: str):
    "Saves the API auth (app_id and api_key) to the CONFIG_FILE " \
    "so that it can be loaded in future runs of this script"
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
    "Attempts to load a previously obtained set of API auth credentials" \
    "(`app_id` and `api_key`) for a `site`, if it exists in the" \
    "CONFIG_FILE and is still valid for a reasonable amount of time"
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
    "Gets the API auth (`app_id` and `api_key`) for a `site`, either from previously cached in" \
    "CONFIG_FILE, or retrieved from the site's homepage"
    # attempt to get cached API auth
    if (auth := api_auth_cache_read(site)) and auth[0] and auth[1]:
        return auth
    log.debug('No valid auth found in cache, fetching new auth')
    # make a request to the site's homepage to get API Key and Application ID
    homepage = homepage_url(site)
    r = requests.get(homepage, headers=headers_for_homepage(homepage), timeout=10)
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
    "Generates the homepage (base URL) for a site/domain"
    return f"https://www.{site}.com"

def clean_text(details: str) -> str:
    "Remove escaped backslashes and html parse the details text."
    if details:
        details = details.replace("\\", "")
        # replace breaks with newlines
        details = re.sub(r"<\s*\/?br\s*\/?\s*>", "\n", details)
        # don't strip to preserve newlines
        # don't add additional newlines
        details = bs(details, features='html.parser').get_text("", strip=False)
    return details

def get_search_client(site: str) -> SearchClientSync:
    "Initialises a search client with API auth credentials (`app_id` and `api_key`) and request" \
    "headers"
    app_id, api_key = get_api_auth(site)
    config = SearchConfig(app_id, api_key)
    config.headers.update(headers_for_homepage(homepage_url(site)))
    return SearchClientSync(config=config)

def default_postprocess(obj: T, _) -> T:
    "This is the default function for the postprocess argument"
    return obj

genders_map = {'shemale': 'transgender_female'}
def parse_gender(gender: str) -> str:
    "Gets corresponding value from map, else returns argument value"
    return genders_map.get(gender, gender)

def movie_cover_image_url(cover_path: str, position: Literal["front", "back"]) -> str:
    "Gets corresponding value from map, else returns argument value"
    return (
        f"{TRANSFORM_IMAGE_CDN}/movies"
        f"{cover_path}_{position}_400x625.jpg?width=450&height=636"
    )

def gallery_url(site: str, url_title: str, set_id: str) -> str:
    "Generates URL for a gallery (photo set)"
    return f"{homepage_url(site)}/en/photo/{url_title}/{set_id}"

def performer_url(site: str, url_name: str, actor_id: str) -> str:
    "Generates URL for a performer (actor)"
    return f"{homepage_url(site)}/en/pornstar/view/{url_name}/{actor_id}"

def movie_url(site: str, url_title: str, movie_id: str) -> str:
    "Generates URL for a movie/group (movie)"
    return f"{homepage_url(site)}/en/movie/{url_title}/{movie_id}"

def scene_url(site: str, sitename: str, url_title: str, clip_id: str) -> str:
    "Generates URL for a scene"
    return f"{homepage_url(site.lower())}/en/video/{sitename.lower()}/{url_title}/{clip_id}"

def to_scraped_performer(performer_from_api: dict[str, Any], site: str) -> ScrapedPerformer:
    "Helper function to convert from Algolia's API to Stash's scraper return type"
    performer: ScrapedPerformer = {}
    if _name := performer_from_api.get("name"):
        performer["name"] = _name.strip()
    if gender := performer_from_api.get("gender"):
        performer["gender"] = parse_gender(gender.strip())
    if details := performer_from_api.get("description"):
        performer["details"] = clean_text(details)
    if eye_color := dig(performer_from_api, "attributes", "eye_color"):
        performer["eye_color"] = eye_color.strip()
    if hair_color := dig(performer_from_api, "attributes", "hair_color"):
        performer["hair_color"] = hair_color.strip()
    if ethnicity := dig(performer_from_api, "attributes", "ethnicity"):
        performer["ethnicity"] = ethnicity.strip()
    if alternate_names := dig(performer_from_api, "attributes", "alternate_names"):
        performer["aliases"] = alternate_names.strip()
    if height := dig(performer_from_api, "attributes", "height"):
        performer["height"] = height.strip()
    if weight := dig(performer_from_api, "attributes", "weight"):
        performer["weight"] = weight.strip()
    if home := dig(performer_from_api, "attributes", "home"):
        performer["country"] = guess_nationality(home.strip())
    if performer_from_api.get("has_pictures") and (pictures := performer_from_api.get("pictures")):
        main_pic = list(pictures.values())[-1]
        performer["images"] = [f"{IMAGE_CDN}/actors{main_pic}"]
    if (
        (url_name := performer_from_api.get("url_name"))
        and (actor_id := performer_from_api.get("actor_id"))
    ):
        performer["urls"] = [performer_url(site, url_name, actor_id)]
    return performer

def site_from_url(_url: str) -> str:
    "Extract the (second level) domain from the URL, e.g. www.evilangel.com -> evilangel"
    return urlparse(_url).netloc.split(".")[-2]

def id_from_url(_url: str) -> str | None:
    "Get the ID from a URL"
    if match := re.search(r"/(\d+)$", _url):
        return match.group(1)
    log.error("Are you sure that URL is from a site that uses the Algolia API?")
    return None

def movie_from_api_scene(scene_from_api: dict[str, Any], site: str) -> ScrapedMovie:
    "Scrape a movie from an API scene's properties"
    movie: ScrapedMovie = {}
    if movie_title := scene_from_api.get("movie_title"):
        movie["name"] = movie_title
        if movie_date_created := scene_from_api.get("movie_date_created"):
            movie["date"] = movie_date_created
        if movie_desc := scene_from_api.get("movie_desc"):
            movie["synopsis"] = clean_text(movie_desc)
        if (
            (url_movie_title := scene_from_api.get("url_movie_title"))
            and (movie_id := scene_from_api.get("movie_id"))
        ):
            movie["url"] = movie_url(site, url_movie_title, movie_id)
    return movie

def scene_urls(scene_from_api: dict[str, Any]) -> list[str] | None:
    "Generates URLs for a scene"
    if (
        (url_title := scene_from_api.get("url_title"))
        and (sitename := scene_from_api.get("sitename"))
        and (clip_id := scene_from_api.get("clip_id"))
        and (available_on_site := scene_from_api.get("availableOnSite"))
    ):
        return [
            scene_url(site_available, sitename, url_title, clip_id)
            for site_available in available_on_site
        ]
    return None

def largest_scene_image(scene_from_api: dict[str, Any]) -> str | None:
    "Picks the highest resolution scene cover image, preferring the NSFW version"
    if images := dig(scene_from_api, "pictures", ("nsfw", "sfw"), "top"):
        return next(iter(images.values()), None)
    return None

def to_scraped_scene(scene_from_api: dict[str, Any], site: str) -> ScrapedScene:
    "Helper function to convert from Algolia's API to Stash's scraper return type"
    scene: ScrapedScene = {}
    if clip_id := scene_from_api.get("clip_id"):
        scene["code"] = str(clip_id)
    if title := scene_from_api.get("title"):
        scene["title"] = title.strip()
    if description := scene_from_api.get("description"):
        scene["details"] = clean_text(description)
    if _scene_urls := scene_urls(scene_from_api):
        scene["urls"] = _scene_urls
    if release_date := scene_from_api.get("release_date"):
        scene["date"] = release_date
    if _largest_scene_image := largest_scene_image(scene_from_api):
        scene["image"] = f"{IMAGE_CDN}/movies{_largest_scene_image}"
    # for studio name overrides, see EvilAngel.py or AdultTime.py for examples
    if studio_name := scene_from_api.get("studio_name"):
        scene["studio"] = { "name": studio_name }
    if scene_from_api.get("movie_id"):
        scene["movies"] = [movie_from_api_scene(scene_from_api, site)]
        # log out scene number
        try:
            movie_title = scene_from_api.get("movie_title")
            clip_path = scene_from_api.get("clip_path")
            [_, scene_number] = clip_path.split("_")
            # it may be possible to populate the Scene Number field in the stash scene via a hook
            # or something, but for now just log it out as an editing aid
            log.info(f"{movie_title}, Scene #{scene_number}")
        except Exception as e:
            log.error(f"Could not determine scene number: {e}")
    if categories := scene_from_api.get("categories"):
        scene["tags"] = name_values_as_list(categories)
    if actors := scene_from_api.get("actors"):
        scene["performers"] = actors_to_performers(actors, site)
    if directors := scene_from_api.get("directors"):
        scene["director"] = name_values_as_csv(directors)
    return scene

def name_values_as_csv(objects: list[dict[str, Any]]) -> str:
    "Transforms list of objects with name property to CSV string"
    return ", ".join([ obj.get("name") for obj in objects ])

def name_values_as_list(objects: list[dict[str, Any]]) -> list[str]:
    "Transforms list of objects with name property to list of objects with only the name property"
    return [{ "name": obj.get("name") } for obj in objects]

def actors_to_performers(actors: list[dict[str, Any]], site: str) -> list[ScrapedPerformer]:
    "Converts API actors to list of ScrapedPerformer"
    return [
        {
            "name": actor.get("name").strip(),
            "gender": parse_gender(actor.get("gender")),
            "urls": [ performer_url(site, actor.get("url_name"), actor.get("actor_id")) ]
        }
        for actor in actors
    ]

def scalar_match(scalar_candidate: int | float, scalar_reference: int | float) -> float:
    "Calculates a ratio match of two scalar values, e.g. seconds, bytes, etc."
    return 1 - abs(scalar_candidate - scalar_reference) / scalar_reference

def add_scene_match_metadata(
    api_scene: dict[str, Any],
    fragment: dict[str, Any] | None,
) -> dict[str, Any]:
    "Adds match ratio metadata"
    if fragment:
        api_scene["__match_metadata"] = {}
        if fragment_title := fragment.get("title"):
            api_scene["__match_metadata"]["title"] = SequenceMatcher(
                None, fragment_title.lower(), api_scene.get("title").lower()
            ).ratio()
        if fragment_date := fragment.get("date"):
            api_scene["__match_metadata"]["date"] = SequenceMatcher(
                None, fragment_date, api_scene.get("release_date")
            ).ratio()
        if (
            (fragment_director := fragment.get("director"))
            and (api_scene_directors := api_scene.get("directors"))
        ):
            api_scene["__match_metadata"]["director"] = SequenceMatcher(
                None, fragment_director, name_values_as_csv(api_scene_directors)
            ).ratio()
        if (
            (fragment_details := fragment.get("details"))
            and (api_scene_description := api_scene.get("description"))
        ):
            api_scene["__match_metadata"]["details"] = SequenceMatcher(
                None, fragment_details, clean_text(api_scene_description)
            ).ratio()
        if fragment_files := fragment.get("files"):
            if api_scene_length := api_scene.get("length"):
                api_scene["__match_metadata"]["duration"] = scalar_match(
                    fragment_files[0]["duration"], api_scene_length
                )
            if (
                (api_scene_video_formats := api_scene.get("video_formats"))
                and (api_scene_size := next(iter([
                    video_format for video_format in api_scene_video_formats
                    if video_format.get("format") == f'{fragment_files[0]["height"]}p'
                ]), {}).get("size"))
            ):
                api_scene["__match_metadata"]["size"] = scalar_match(
                    fragment_files[0]["size"], int(api_scene_size)
                )
        log.debug(
            f"API scene title: {api_scene.get('title')}, "
            f"__match_metadata: {api_scene['__match_metadata']}"
        )
    return api_scene

def sort_api_scenes_by_match(
    api_scenes: list[dict[str, Any]],
    fragment: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    "Sorts the list of API scenes by the closeness match(es) to fragment key-values"
    log.debug(f'Evaluating API scenes closeness match score, with fragment: {fragment}')
    if fragment:
        return sorted(
            [add_scene_match_metadata(api_scene, fragment) for api_scene in api_scenes],
            key=lambda api_scene: sum(
                                        api_scene.get("__match_metadata").values()
                                    ) / len(api_scene.get("__match_metadata"))
                                    if api_scene.get("__match_metadata").values() else 0,
            reverse=True,
        )
    return api_scenes

def api_scene_from_id(
    clip_id: int | str,
    sites: list[str],
    fragment: dict[str, Any] = None,
) -> dict[str, Any] | None:
    "Searches a scene from a clip_id and returns the API result as-is"
    site = sites[0] # TODO: handle multiple sites?
    log.debug(f"Site: {site}")
    response = get_search_client(site).search_single_index(
        index_name="all_scenes",
        search_params={
            "attributesToHighlight": [],
            "filters": f"clip_id:{clip_id}",
            "length": 1,
        },
    )
    log.debug(f"Number of search hits: {response.nb_hits}")
    if response.nb_hits:
        if response.nb_hits == 1:
            return response.hits[0].to_dict()
        if response.nb_hits > 1:
            return sort_api_scenes_by_match(
                [hit.to_dict() for hit in response.hits], fragment
            )[0]
    return None

def scene_from_id(
    clip_id,
    sites: list[str],
    fragment: dict[str, Any] = None,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedScene | None:
    "Scrapes a scene from a clip_id, running an optional postprocess function on the result"
    site = sites[0] # TODO: handle multiple sites?
    api_scene = api_scene_from_id(clip_id, sites, fragment)
    if api_scene:
        return postprocess(to_scraped_scene(api_scene, site), api_scene)
    return None

def gallery_from_scene_id(
    clip_id: int | str,
    sites: list[str],
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess
) -> ScrapedGallery | None:
    "Scrapes a gallery from a clip_id, running an optional postprocess function on the result"
    site = sites[0] # TODO: handle multiple sites
    log.debug(f"Site: {site}")
    api_scene = api_scene_from_id(clip_id, sites)
    if api_scene:
        return postprocess(to_scraped_gallery(api_scene, site), api_scene)
    return None

def scene_from_url(
    _url: str,
    sites: list[str],
    fragment: dict[str, Any] = None,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedScene | None:
    "Scrapes a scene from a URL, running an optional postprocess function on the result"
    clip_id = id_from_url(_url)
    site = sites[0] # TODO: handle multiple sites
    log.debug(f"Clip ID: {clip_id}, Site: {site}")
    return scene_from_id(clip_id, [site], fragment, postprocess)

def scene_url_from_photoset(photoset_from_api: dict[str, Any], site: str) -> str | None:
    "Extracts scene URL from API photoset properties"
    if (
        (clip_title := photoset_from_api.get("clip_title"))
        and (sitename := photoset_from_api.get("sitename"))
        and (clip_id := photoset_from_api.get("clip_id"))
    ):
        return scene_url(site, sitename, slugify(clip_title), clip_id)
    return None

def to_scraped_gallery(api_hit: dict[str, Any], site: str) -> ScrapedGallery | None:
    "Scrapes an API search hit (could be scene or photoset) into a ScrapedGallery"
    gallery: ScrapedGallery = {}
    if (
        (title := api_hit.get("photoset_name")) # scenes can include corresponding photoset_name
        or (title := api_hit.get("title")) # photosets have their own title (as do scenes)
    ):
        gallery["title"] = title.strip()
    if description := api_hit.get("description"):
        gallery["details"] = clean_text(description)
    gallery["urls"] = []
    # scenes _can_ include photoset_id and photoset_url_title
    if (
        (photoset_id := api_hit.get("photoset_id"))
        and (photoset_url_name := api_hit.get("photoset_url_name"))
    ):
        gallery["code"] = photoset_id
        gallery["urls"].append(gallery_url(site, photoset_url_name, photoset_id))
    # photosets have set_id and url_title
    if (
        (set_id := api_hit.get("set_id"))
        and (url_title := api_hit.get("url_title"))
    ):
        gallery["code"] = str(set_id)
        gallery["urls"].append(gallery_url(site, url_title, set_id))
    if _scene_url := scene_url_from_photoset(api_hit, site): # api photosets can have clip_title
        gallery["urls"].append(_scene_url)
    if (
        (date := api_hit.get("date_online")) # photoset has date_online
        or (date := api_hit.get("release_date")) # scene has release_date
    ):
        gallery["date"] = date
    if studio_name := api_hit.get("studio_name"):
        gallery["studio"] = { "name": studio_name }
    if categories := api_hit.get("categories"):
        gallery["tags"] = name_values_as_list(categories)
    if actors := api_hit.get("actors"):
        gallery["performers"] = actors_to_performers(actors, site)
    if directors := api_hit.get("directors"):
        gallery["photographer"] = name_values_as_csv(directors)
    # photosets have their own cover image
    if picture := api_hit.get("picture"):
        # just log this out, to aid user in selecting the cover image
        log.info(f"Cover image: {TRANSFORM_IMAGE_CDN}/photo_set{picture}")
    return gallery

def gallery_from_set_id(
    set_id: int | str,
    sites: list[str],
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> ScrapedGallery | None:
    "Scrapes a gallery from a set_id, running an optional postprocess function on the result"
    site = sites[0] # TODO: handle multiple sites?
    log.debug(f"Site: {site}")
    response = get_search_client(site).search_single_index(
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
    _url: str,
    sites: list[str],
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> ScrapedGallery | None:
    "Scrapes a gallery from a URL, running an optional postprocess function on the result"
    url_id = id_from_url(_url)
    site = sites[0]
    log.debug(f"Site: {site}")
    if "/photo/" in _url: # some sites have public photoset URLs, so can be searched by set_id
        log.debug(f"set_id: {url_id}")
        return gallery_from_set_id(url_id, [site], postprocess)
    if "/video/" in _url: # some sites do not have public photosets, but we can use scene URL
        log.debug(f"clip_id: {url_id}")
        return gallery_from_scene_id(url_id, [site], postprocess)
    return None

def performer_from_url(
    _url: str,
    postprocess: Callable[[ScrapedPerformer, dict], ScrapedPerformer] = default_postprocess,
) -> ScrapedPerformer | None:
    "Scrapes a performer from a URL, running an optional postprocess function on the result"
    actor_id = id_from_url(_url)
    site = site_from_url(_url)
    log.debug(f"Performer ID: {actor_id}, Site: {site}")
    response = get_search_client(site).search_single_index(
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

def movie_cover_image_urls(
    movie_from_api: dict[str, Any],
    site: str
) -> tuple[str | None, str | None]:
    "Checks front and back cover images exist and that the back isn't just a duplicate of the front"
    back_is_duplicate = False
    if cover_path := movie_from_api.get("cover_path"):
        front_image_url = movie_cover_image_url(cover_path, 'front')
        back_image_url = movie_cover_image_url(cover_path, 'back')
        if is_valid_url(back_image_url):
            headers = headers_for_homepage(homepage_url(site))
            res_front = requests.get(front_image_url, headers=headers, timeout=10)
            res_back = requests.get(back_image_url, headers=headers, timeout=10)
            if back_is_duplicate := b64encode(res_front.content) == b64encode(res_back.content):
                log.debug("Front and Back images identical, NOT scraping back image")
    return (
        front_image_url if is_valid_url(front_image_url) else None,
        back_image_url if not back_is_duplicate else None,
    )

def to_scraped_movie(movie_from_api: dict[str, Any], site: str) -> ScrapedMovie:
    "Helper function to convert from Algolia's API to Stash's scraper return type"
    movie: ScrapedMovie = {}
    if title := movie_from_api.get("title"):
        movie["name"] = title.strip()
    if date_created := movie_from_api.get("date_created"):
        movie["date"] = date_created
    if length := movie_from_api.get("length"):
        movie["duration"] = str(length)
    if directors := movie_from_api.get("directors"):
        movie["director"] = name_values_as_csv(directors)
    if description := movie_from_api.get("description"):
        movie["synopsis"] = clean_text(description)
    if studio_name := movie_from_api.get("studio_name"):
        movie["studio"] = { "name": studio_name }
    if _movie_cover_image_urls := movie_cover_image_urls(movie_from_api, site):
        if _movie_cover_image_urls[0]:
            movie["front_image"] = _movie_cover_image_urls[0]
        if _movie_cover_image_urls[1]:
            movie["back_image"] = _movie_cover_image_urls[1]
    if (
        (url_title := movie_from_api.get("url_title"))
        and (movie_id := movie_from_api.get("movie_id"))
    ):
        movie["url"] = movie_url(site, url_title, movie_id)
    return movie

def movie_from_url(
    _url: str,
    postprocess: Callable[[ScrapedMovie, dict], ScrapedMovie] = default_postprocess
) -> ScrapedMovie | None:
    "Scrapes a movie from a URL, running an optional postprocess function on the result"
    movie_id = id_from_url(_url)
    site = site_from_url(_url)
    log.debug(f"movie_id: {movie_id}, Site: {site}")
    response = get_search_client(site).search_single_index(
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

def add_actor_match_metadata(
    api_actor: dict[str, Any],
    fragment: dict[str, Any] | None
) -> dict[str, Any]:
    "Adds match ratio metadata"
    if fragment:
        api_actor["__match_metadata"] = {}
        if fragment_name := fragment.get("name"):
            api_actor["__match_metadata"]["name"] = max(
                SequenceMatcher(
                    None,
                    fragment_name.lower(),
                    api_actor.get("name").lower()
                ).get_matching_blocks(),
                key=lambda x: x.size
            ).size # higher score for longer matching sequence
        log.debug(
            f"name: {api_actor.get('name')}, "
            f"__match_metadata: {api_actor['__match_metadata']}"
        )
    return api_actor

def sort_api_actors_by_match(
    api_actors: list[dict[str, Any]],
    fragment: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    "Sorts the list of API actors by the closeness match(es) to fragment key-values"
    log.debug(f'Evaluating API actors closeness match score, with fragment: {fragment}')
    if fragment:
        return sorted(
            [add_actor_match_metadata(api_actor, fragment) for api_actor in api_actors],
            key=lambda api_scene: sum(
                                        api_scene.get("__match_metadata").values()
                                    ) / len(api_scene.get("__match_metadata"))
                                    if api_scene.get("__match_metadata").values() else 0,
            reverse=True,
        )
    return api_actors

def performer_search(
    query: str,
    sites: list[str],
    postprocess: Callable[[ScrapedPerformer, dict], ScrapedPerformer] = default_postprocess,
) -> list[ScrapedPerformer]:
    "Searches the API for actors with a text query"
    site = sites[0] # TODO: handle multiple sites?
    # Get API auth and initialise client
    response = get_search_client(site).search_single_index(
        index_name="all_actors_latest_desc",
        search_params={
            "attributesToHighlight": [],
            "query": query,
            "length": 20,
        },
    )
    log.debug(f"Number of search hits: {response.nb_hits}")
    if response.nb_hits:
        if len(api_actors := [hit.to_dict() for hit in response.hits]) == 1: # single search result
            return [postprocess(to_scraped_performer(api_actors[0], site), api_actors[0])]
        if len(api_actors) > 1: # multiple search results
            return [
                postprocess(to_scraped_performer(api_actor, site), api_actor)
                for api_actor in sort_api_actors_by_match(api_actors, {"name": query}) # sort
            ]
    return []

def scene_search(
    query: str,
    sites: list[str],
    fragment: dict[str, Any] = None,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> list[ScrapedScene]:
    "Searches the API for scenes with a text query"
    site = sites[0] # TODO: handle multiple sites?
    response = get_search_client(site).search_single_index(
        index_name="all_scenes",
        search_params={
            "attributesToHighlight": [],
            "query": query,
            "length": 20,
        },
    )
    log.debug(f"Number of search hits: {response.nb_hits}")
    if response.nb_hits:
        if len(api_scenes := [hit.to_dict() for hit in response.hits]) == 1: # single search result
            return [postprocess(to_scraped_scene(api_scenes[0], site), api_scenes[0])]
        if len(api_scenes) > 1: # multiple search results
            return [
                postprocess(to_scraped_scene(api_scene, site), api_scene)
                for api_scene in sort_api_scenes_by_match(api_scenes, fragment) # sort
            ]
    return []

def add_photoset_match_metadata(
    api_photoset: dict[str, Any],
    fragment: dict[str, Any] | None,
    db_gallery_file_count: int | None,
) -> dict[str, Any]:
    "Adds match ratio metadata"
    if fragment:
        api_photoset["__match_metadata"] = {}
        if fragment_title := fragment.get("title"):
            api_photoset["__match_metadata"]["title"] = SequenceMatcher(
                None,
                fragment_title.lower(),
                api_photoset.get("title").lower()
            ).ratio()
        if fragment_date := fragment.get("date"):
            api_photoset["__match_metadata"]["date"] = SequenceMatcher(
                None,
                fragment_date,
                api_photoset.get("date_online")
            ).ratio()
        if (
            (fragment_photographer := fragment.get("photographer"))
            and (api_photoset_directors := api_photoset.get("directors"))
        ):
            api_photoset["__match_metadata"]["director"] = SequenceMatcher(
                None,
                fragment_photographer,
                name_values_as_csv(api_photoset_directors)
            ).ratio()
        if (
            (fragment_details := fragment.get("details"))
            and (api_photoset_description := api_photoset.get("description"))
        ):
            api_photoset["__match_metadata"]["details"] = SequenceMatcher(
                None,
                fragment_details,
                clean_text(api_photoset_description)
            ).ratio()
        if (
            db_gallery_file_count
            and (api_photoset_num_of_pictures := api_photoset.get("num_of_pictures"))
            and int(api_photoset_num_of_pictures) != 0
        ):
            log.debug(
                f"db_gallery_file_count: ({type(db_gallery_file_count)}): {db_gallery_file_count}, "
                f"api_photoset_num_of_pictures: ({type(api_photoset_num_of_pictures)}): "
                f"{api_photoset_num_of_pictures}"
            )
            api_photoset["__match_metadata"]["num_of_pictures"] = scalar_match(
                db_gallery_file_count, int(api_photoset_num_of_pictures)
            )
        log.debug(
            f"name: {api_photoset.get('title')}, "
            f"__match_metadata: {api_photoset['__match_metadata']}"
        )
    return api_photoset

def sort_api_photosets_by_match(
    api_photosets: list[dict[str, Any]],
    fragment: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    "Sorts list of API photosets by the closeness match(es) to fragment key-values"
    log.debug(f'Evaluating API photosets closeness match score, with fragment: {fragment}')
    if fragment:
        db_gallery_file_count = None
        if fragment.get("id") and (db_gallery_path := graphql.getGalleryPath(fragment.get("id"))):
            if os.path.exists(db_gallery_path) and not os.path.isfile(db_gallery_path):
                db_gallery_file_count = len([
                    f for f in os.listdir(db_gallery_path)
                    if os.path.isfile(os.path.join(db_gallery_path, f))
                ])
            elif os.path.isfile(db_gallery_path) and db_gallery_path.lower().endswith(".zip"):
                with ZipFile(db_gallery_path, 'r') as zip_gallery:
                    db_gallery_file_count = len(zip_gallery.namelist())
        log.debug(f"db_gallery_file_count: {db_gallery_file_count}")
        return sorted(
            [
                add_photoset_match_metadata(api_photoset, fragment, db_gallery_file_count)
                for api_photoset in api_photosets
            ],
            key=lambda api_photoset: sum(
                                        api_photoset.get("__match_metadata").values()
                                    ) / len(api_photoset.get("__match_metadata"))
                                    if api_photoset.get("__match_metadata").values() else 0,
            reverse=True,
        )
    return api_photosets

def gallery_search(
    query: str,
    sites: list[str],
    fragment: dict[str, Any] | None,
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> list[ScrapedGallery]:
    "Searches the API for photo sets with a text query"
    site = sites[0] # TODO: handle multiple sites
    response = get_search_client(site).search_single_index(
        index_name="all_photosets",
        search_params={
            "attributesToHighlight": [],
            "query": query,
            "length": 20,
        },
    )
    log.debug(f"Number of search hits: {response.nb_hits}")
    if response.nb_hits:
        if len(api_photosets := [hit.to_dict() for hit in response.hits]) == 1:
            return [
                postprocess(to_scraped_gallery(api_photoset, site), api_photoset)
                for api_photoset in api_photosets
            ]
        if len(api_photosets) > 1:
            return [
                postprocess(to_scraped_gallery(api_photoset, site), api_photoset)
                for api_photoset in sort_api_photosets_by_match(api_photosets, fragment)
            ]
    return []

def scene_from_fragment(
    fragment: dict[str, Any],
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
    if urls := fragment.get("urls"): # the first URL should be usable for a full search
        return scene_from_url(urls[0], sites, fragment, postprocess)
    if code := fragment.get("code"): # if the (studio) code is present, search by clip_id
        return scene_from_id(code, sites, fragment, postprocess)
    if title := fragment.get("title"): # if a title is present, search by text
        if len(scenes := scene_search(title, sites, fragment, postprocess)) > 0:
            return scenes[0] # best match is sorted at the top
    return {}

def gallery_from_fragment(
    fragment: dict[str, Any],
    sites: list[str],
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> ScrapedGallery | None:
    "Scrapes a gallery from a fragment. URL, code, title"
    log.debug(f"in gallery_from_fragment, fragment: {fragment}")
    if _url := fragment.get("url"):
        return gallery_from_url(_url, sites, postprocess)
    if code := fragment.get("code"):
        return gallery_from_set_id(code, sites, postprocess)
    if title := fragment.get("title"):
        if len(scraped_galleries := gallery_search(title, sites, fragment, postprocess)) > 0:
            return scraped_galleries[0] # single match, or top match of multiple matches
    return None

def performer_from_fragment(
    fragment: dict[str, Any],
    postprocess: Callable[[ScrapedPerformer, dict], ScrapedPerformer] = default_postprocess,
) -> ScrapedPerformer:
    """
    This receives:
    - name
    - urls
    - gender
    from the result of the performer-by-name search
    """
    _url = fragment.get("urls")[0] # the first URL should be usable for a full search
    return performer_from_url(_url, postprocess)

if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url, "extra": extra} if url and extra:
            domains = extra
            result = gallery_from_url(url, domains)
        case "gallery-by-fragment", args:
            domains = args.pop("extra")
            result = gallery_from_fragment(args, domains)
        case "scene-by-url", {"url": url, "extra": extra} if url and extra:
            domains = extra
            result = scene_from_url(url, domains)
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            domains = extra
            result = scene_search(name, domains)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            domains = args.pop("extra")
            result = scene_from_fragment(args, domains)
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
