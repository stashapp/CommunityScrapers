import json
import re
import sys
import difflib
import requests
from datetime import datetime
from typing import Any, Callable
from urllib.parse import urlparse

import py_common.log as log
from py_common.util import dig, guess_nationality, scraper_args
from py_common.config import get_config
from py_common.types import (
    ScrapedGallery,
    ScrapedMovie,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedStudio,
    ScrapedTag,
)
import AyloAPI.domains as domains
from AyloAPI.slugger import slugify

config = get_config(
    default="""
# User Agent to use for the requests
user_agent = Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0

# Scrape markers when using 'Scrape with...'
scrape_markers = False

# Minimum similarity ratio to consider a match when searching
minimum_similarity = 0.75

# Debug mode will save the latest API response to disk
debug = False
"""
)


def default_postprocess(obj: Any, _) -> Any:
    return obj


## Temporary function to add markers to scenes, remove when/if Stash gets native support
def add_markers(scene_id: str, markers: list[dict]):
    from itertools import tee, filterfalse

    def partition(pred, iterable):
        t1, t2 = tee(iterable)
        return list(filter(pred, t2)), list(filterfalse(pred, t1))

    from py_common.graphql import callGraphQL

    def format_time(seconds: int) -> str:
        if seconds > 3600:
            return f"{seconds // 3600}:{(seconds // 60) % 60:02}:{seconds % 60:02}"
        return f"{(seconds // 60) % 60}:{seconds % 60:02}"

    raw_tags = callGraphQL("query allTags { allTags { name id aliases } }")
    if not raw_tags:
        log.error("Failed to get tags from Stash")
        return

    tags = {tag["name"].lower(): tag["id"] for tag in raw_tags["allTags"]}
    tags |= {
        alias.lower(): tag["id"]
        for tag in raw_tags["allTags"]
        for alias in tag["aliases"]
    }
    existing_markers = callGraphQL(
        "query FindScene($id: ID!){ findScene(id: $id) { scene_markers { title seconds } } }",
        {"id": scene_id},
    )
    if not existing_markers:
        log.error("Failed to get existing markers from Stash")
        return

    existing_markers = existing_markers["findScene"]["scene_markers"]

    valid, invalid = partition(lambda m: m["name"].lower() in tags, markers)
    if invalid:
        invalid_tags = ", ".join({m["name"] for m in invalid})
        log.debug(f"Skipping {len(invalid)} markers, tags do not exist: {invalid_tags}")

    log.debug(f"Adding {len(valid)} out of {len(markers)} markers to scene {scene_id}")
    create_query = "mutation SceneMarkerCreate($input: SceneMarkerCreateInput!) { sceneMarkerCreate(input: $input) {id}}"
    for marker in sorted(valid, key=lambda m: m["seconds"]):
        name = marker["name"]
        seconds = marker["seconds"]
        if any(m["seconds"] == marker["seconds"] for m in existing_markers):
            log.debug(
                f"Skipping marker '{name}' at {format_time(seconds)} because it already exists"
            )
            continue
        variables = {
            "input": {
                "title": name,
                "primary_tag_id": tags[name.lower()],
                "seconds": int(seconds),
                "scene_id": scene_id,
                "tag_ids": [],
            }
        }
        callGraphQL(create_query, variables)
        log.debug(f"Added marker '{name}' at {format_time(seconds)}")


# network stuff
def __raw_request(url, headers) -> requests.Response:
    log.trace(f"Sending GET request to {url}")
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 429:
        log.error(
            "[REQUEST] 429 Too Many Requests: "
            "you have sent too many requests in a given amount of time."
        )
        sys.exit(1)

    # Even a 404 will contain an instance token
    return response


def __api_request(url: str, headers: dict) -> dict | None:
    result = __raw_request(url, headers)
    api_response = result.json()
    if isinstance(api_response, list):
        api_search_errors = "\n- ".join(
            json.dumps(res, indent=None) for res in api_response
        )
        log.error(f"Errors from API:\n{api_search_errors}")
        return None

    if config.debug:
        with open("api_response.json", "w", encoding="utf-8") as f:
            json.dump(api_response, f, indent=2)

    return api_response["result"]


def _create_headers_for(domain: str) -> dict[str, str]:
    # If we haven't stored a token we must provide a function to get one
    def get_instance_token(url: str) -> str | None:
        r = __raw_request(url, {"User-Agent": config.user_agent})
        if r and (token := r.cookies.get("instance_token")):
            return token
        log.error(
            f"Failed to get instance_token from '{url}': "
            "are you sure this site is in the Aylo network?"
        )

    api_token = domains.get_token_for(domain, fallback=get_instance_token)
    if api_token is None:
        log.error(f"Unable to get an API token for '{domain}'")
        return {}

    api_headers = {
        "Instance": api_token,
        "User-Agent": config.user_agent,
        "Origin": f"https://{domain}",
        "Referer": f"https://{domain}",
    }
    return api_headers


def _construct_url(api_result: dict) -> str:
    """
    Tries to construct a valid public URL for an API result

    This will often result in scene links that point to the parent network site,
    so we might want to add wrapper scrapers that can add the correct URL as well

    For example, a scene from We Live Together will have an URL for realitykings.com
    but that scene is also on welivetogether.com and that might be considered more canonical
    """

    brand = api_result["brand"]
    type_ = api_result["type"]
    id_ = api_result["id"]
    slug = slugify(api_result["title"])
    return f"https://www.{brand}.com/{type_}/{id_}/{slug}"


def _construct_performer_url(api_result: dict, site: str) -> str:
    id_ = api_result["id"]
    slug = slugify(api_result["name"])
    return f"https://www.{site}.com/model/{id_}/{slug}"


## Helper functions for the objects returned from Aylo's API
def get_studio(api_object: dict) -> ScrapedStudio | None:
    studio_name = dig(api_object, "collections", 0, "name")
    parent_name = dig(api_object, "brandMeta", ("displayName", "name", "shortName"))
    if studio_name:
        if parent_name.lower() != studio_name.lower():
            return {
                "name": studio_name,
                "parent": {"name": parent_name},
            }
        return {"name": studio_name}
    elif parent_name:
        return {"name": parent_name}

    log.error(f"No studio for {api_object['type']} with id {api_object['id']}")
    return None


# As documented by AdultSun, these tag IDs appear to be neutral but
# are actually gendered so we can map them to their gender-specific counterparts
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


def to_marker(api_object: dict) -> dict:
    return {
        **to_tag(api_object),
        "seconds": api_object["startTime"],
    }


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
        performer["url"] = _construct_performer_url(performer_from_api, site)

    return performer


def to_scraped_movie(movie_from_api: dict) -> ScrapedMovie:
    if movie_from_api["type"] not in ("movie", "serie"):
        wrong_type = movie_from_api["type"]
        wrong_id = movie_from_api["id"]
        log.error(f"Attempted to scrape a '{wrong_type}' (ID: {wrong_id}) as a movie.")
        raise ValueError("Invalid movie from API")

    movie: ScrapedMovie = {
        "name": movie_from_api["title"],
        "synopsis": dig(movie_from_api, "description"),
        "url": _construct_url(movie_from_api),
    }

    if front_image := dig(movie_from_api, "images", "cover", "0", "xx", "url"):
        movie["front_image"] = re.sub(r"/m=[^/]+", "", front_image)
    elif poster := dig(movie_from_api, "images", "poster", "0", "xx", "url"):
        movie["front_image"] = re.sub(r"/m=[^/]+", "", poster)

    if date := dig(movie_from_api, "dateReleased"):
        movie["date"] = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z").strftime(
            "%Y-%m-%d"
        )

    if studio := get_studio(movie_from_api):
        movie["studio"] = studio

    return movie


def to_scraped_scene(scene_from_api: dict) -> ScrapedScene:
    if not scene_from_api["type"] == "scene":
        wrong_type = scene_from_api["type"]
        wrong_id = scene_from_api["id"]
        log.error(f"Attempted to scrape a '{wrong_type}' (ID: {wrong_id}) as a scene.")
        raise ValueError("Invalid scene from API")

    scene: ScrapedScene = {
        "title": scene_from_api["title"],
        "code": str(scene_from_api["id"]),
        "details": dig(scene_from_api, "description"),
        "date": datetime.strptime(
            scene_from_api["dateReleased"], "%Y-%m-%dT%H:%M:%S%z"
        ).strftime("%Y-%m-%d"),
        "url": _construct_url(scene_from_api),
        "performers": [
            to_scraped_performer(p, dig(scene_from_api, "brand"))
            for p in scene_from_api["actors"]
        ],
        "tags": to_tags(scene_from_api),
    }

    if image := dig(
        scene_from_api,
        "images",
        ("poster", "poster_fallback"),
        "0",
        ("xx", "xl", "lg", "md", "sm", "xs"),
        "url",
    ):
        scene["image"] = re.sub(r"/m=[^/]+", "", image)

    if dig(scene_from_api, "parent", "type") in ("movie", "serie"):
        scene["movies"] = [to_scraped_movie(scene_from_api["parent"])]

    if studio := get_studio(scene_from_api):
        scene["studio"] = studio

    if config.scrape_markers and (markers := scene_from_api.get("timeTags")):
        scene["markers"] = [to_marker(m) for m in markers]  # type: ignore

    return scene


## Primary functions used to scrape from Aylo's API
def scene_from_url(
    url, postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedScene | None:
    """
    Scrapes a scene from a URL, running an optional postprocess function on the result
    """

    if not (match := re.search(r"/(\d+)/", url)):
        log.error(
            "Can't get the ID of the Scene. "
            "Are you sure that URL is from a site in the Aylo Network?"
        )
        return None
    scene_id = match.group(1)

    log.debug(f"Scene ID: {scene_id}")

    # Extract the domain from the URL
    domain = domains.site_name(url)

    api_URL = f"https://site-api.project1service.com/v2/releases/{scene_id}"
    api_headers = _create_headers_for(domain)
    if not api_headers:
        return None
    api_scene_json = __api_request(api_URL, api_headers)

    if not api_scene_json:
        return None

    # If you scrape a trailer we can still get the correct scene data
    if (
        dig(api_scene_json, "type") != "scene"
        and dig(api_scene_json, "parent", "type") == "scene"
    ):
        log.debug("Result is a trailer, getting scene data from parent")
        api_scene_json = api_scene_json["parent"]

    return postprocess(to_scraped_scene(api_scene_json), api_scene_json)


def gallery_from_url(
    url,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> ScrapedGallery | None:
    """
    Scrapes a gallery from a URL, running an optional postprocess function on the result

    Note that most Aylo sites do not have public links to galleries, so this will treat scenes as galleries
    """

    scene = scene_from_url(url, postprocess=postprocess)
    if not scene:
        return None

    temp = {
        "title": scene.get("title"),
        "details": scene.get("details"),
        "url": scene.get("url"),
        "date": scene.get("date"),
        "studio": scene.get("studio"),
        "tags": scene.get("tags"),
        "performers": scene.get("performers"),
        "code": scene.get("code"),
    }

    gallery: ScrapedGallery = {k: v for k, v in temp.items() if v is not None}  # type: ignore

    return gallery


def performer_from_url(
    url,
    postprocess: Callable[
        [ScrapedPerformer, dict], ScrapedPerformer
    ] = default_postprocess,
) -> ScrapedPerformer | None:
    """
    Scrapes a performer from a URL, running an optional postprocess function on the result
    """

    if not (match := re.search(r"/(\d+)/", url)):
        log.error(
            "Can't get the ID of the performer. "
            "Are you sure that URL is from a site in the Aylo Network?"
        )
        return None
    performer_id = match.group(1)

    log.debug(f"Performer ID: {performer_id}")

    # Extract the domain from the URL
    domain = urlparse(url).netloc.split(".")[-2]

    api_URL = f"https://site-api.project1service.com/v1/actors/{performer_id}"
    api_headers = _create_headers_for(domain)
    api_performer_json = __api_request(api_URL, api_headers)
    if not api_performer_json:
        return None

    return postprocess(to_scraped_performer(api_performer_json), api_performer_json)


def movie_from_url(
    url, postprocess: Callable[[ScrapedMovie, dict], ScrapedMovie] = default_postprocess
) -> ScrapedMovie | None:
    """
    Scrapes a movie from a URL, running an optional postprocess function on the result
    """

    if not (match := re.search(r"/(\d+)/", url)):
        log.error(
            "Can't get the ID of the movie. "
            "Are you sure that URL is from a site in the Aylo Network?"
        )
        return None
    movie_id = match.group(1)

    log.debug(f"Movie ID: {movie_id}")

    # Extract the domain from the URL
    domain = urlparse(url).netloc.split(".")[-2]

    api_URL = f"https://site-api.project1service.com/v2/releases/{movie_id}"
    api_headers = _create_headers_for(domain)
    api_movie_json = __api_request(api_URL, api_headers)
    if not api_movie_json:
        return None

    with open("api_response.json", "w", encoding="utf-8") as f:
        json.dump(api_movie_json, f, indent=2)

    if dig(api_movie_json, "type") in ("movie", "serie"):
        return postprocess(to_scraped_movie(api_movie_json), api_movie_json)

    # If you scrape a scene or trailer, we can still get the correct movie data
    if dig(api_movie_json, "parent", "type") in ("movie", "serie"):
        log.debug("Result is a scene or trailer, getting movie data from parent")
        return movie_from_url(
            url.replace(f"/{movie_id}/", f"/{api_movie_json['parent']['id']}/"),
            postprocess=postprocess,
        )
    return postprocess(
        to_scraped_movie(api_movie_json["parent"]), api_movie_json["parent"]
    )


# Since the "Scrape with..." function in Stash expects a single result, we provide
# this function to return the first result that exceeds the threshold so
# that users don't need to use scene_search directly and THEN take the first result
def find_scene(
    query: str,
    search_domains: list[str] | None = None,
    min_ratio: float = 0.9,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> ScrapedScene | None:
    """
    Searches the Aylo API for scenes matching the given query and returns the
    first match that exceeds `min_ratio` similarity: a float between 0 and 1.

    Differs from `scene_from_query` in that it only returns the first match,
    returning early as soon as it finds a match that exceeds the threshold.

    If search_domains is provided it will only search those domains,
    otherwise it will search all (this could be very slow!)

    Domains should not include the "www." or ".com" parts of the domain: 'brazzers', 'realitykings', etc.

    If postprocess is provided it will be called on the result before returning
    """
    if not query:
        log.error("No query provided")
        return None

    if not search_domains:
        log.warning("Searcing all known domains, this could be very slow!")
        search_domains = domains.all_domains()

    log.debug(f"Matching '{query}' against {len(search_domains)} sites")

    def matcher(candidate_title: str):
        return round(
            difflib.SequenceMatcher(
                None, query.lower(), candidate_title.lower()
            ).ratio(),
            3,
        )

    for domain in search_domains:
        log.debug(f"Searching '{domain}'")

        api_headers = _create_headers_for(domain)
        search_url = f"https://site-api.project1service.com/v2/releases?search={query}&type=scene"
        api_response = __api_request(search_url, api_headers)

        if api_response is None:
            log.error(f"Failed to search '{domain}'")
            continue
        if not api_response:
            log.debug(f"No results from '{domain}'")
            continue

        best_match = max(api_response, key=lambda x: matcher(x["title"]))
        ratio = matcher(best_match["title"])
        if ratio >= min_ratio:
            log.info(
                f"Found scene '{best_match['title']}' with {ratio:.2%} similarity "
                f"to '{query}' (exceeds {min_ratio:.2%} threshold) "
                f"on '{domain}'"
            )
            return postprocess(to_scraped_scene(best_match), best_match)
        else:
            log.info(
                f"Giving up on '{domain}': best result '{best_match['title']}' "
                f"with {ratio:.2%} similarity"
            )

    log.error(f"No scenes found for '{query}'")
    return None


# Since the "Scrape with..." function in Stash expects a single result, we provide
# this function to return the first result that exceeds the threshold so
# that users don't need to use performer_search directly and THEN take the first result
def find_performer(
    query: str,
    search_domains: list[str] | None = None,
    min_ratio: float = 0.9,
    postprocess: Callable[
        [ScrapedPerformer, dict], ScrapedPerformer
    ] = default_postprocess,
) -> ScrapedPerformer | None:
    """
    Searches the Aylo API for performers matching the given query and returns the
    first match that exceeds `min_ratio` similarity: a float between 0 and 1.

    Differs from `search_performer` in that it only returns the first match,
    returning early as soon as it finds a match that exceeds the threshold.

    If search_domains is provided it will only search those domains,
    otherwise it will search all (this could be very slow!)

    Domains should not include the "www." or ".com" parts of the domain: 'brazzers', 'realitykings', etc.

    If postprocess is provided it will be called on the result before returning
    """
    if not query:
        log.error("No query provided")
        return None

    if not search_domains:
        log.warning("Searcing all known domains, this could be very slow!")
        search_domains = domains.all_domains()

    log.debug(f"Matching '{query}' against {len(search_domains)} sites")

    def matcher(candidate_name: str):
        return round(
            difflib.SequenceMatcher(
                None, query.lower(), candidate_name.lower()
            ).ratio(),
            3,
        )

    for domain in search_domains:
        log.debug(f"Searching {domain}")

        api_headers = _create_headers_for(domain)
        search_url = f"https://site-api.project1service.com/v1/actors?search={query}"
        api_response = __api_request(search_url, api_headers)

        if api_response is None:
            log.error(f"Failed to search {domain}")
            continue
        if not api_response:
            log.debug(f"No results from {domain}")
            continue

        best_match = max(api_response, key=lambda x: matcher(x["name"]))
        ratio = matcher(best_match["name"])
        if ratio >= min_ratio:
            log.info(
                f"Found performer '{best_match['name']}' with {ratio:.2%} similarity "
                f"to '{query}' (exceeds {min_ratio:.2%} threshold) "
                f"on '{domain}'"
            )
            return postprocess(to_scraped_performer(best_match, domain), best_match)
        else:
            log.info(
                f"Giving up on '{domain}': best result '{best_match['name']}' "
                f"with {ratio:.2%} similarity"
            )

    log.error(f"No performers found for '{query}'")
    return None


def scene_search(
    query: str,
    search_domains: list[str] | None = None,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> list[ScrapedScene]:
    """
    Searches the Aylo API for the given query and returns a list of ScrapedScene

    If search_domains is provided it will only search those domains,
    otherwise it will search all known domains (this could be very slow!)

    Domains should not include the "www." or ".com" parts of the domain: 'brazzers', 'realitykings', etc.

    If postprocess is provided it will be called on each result before returning
    """
    if not query:
        log.error("No query provided")
        return []

    if not search_domains:
        log.warning("Searcing all known domains, this could be very slow!")
        search_domains = domains.all_domains()

    log.debug(f"Searching for '{query}' on {len(search_domains)} sites")

    # The source of the results will be based on the token used (Brazzers, Reality Kings, etc.)
    search_url = f"https://site-api.project1service.com/v2/releases?search={query}&type=scene&limit=10"
    search_results = []
    already_seen = set()

    def matcher(candidate: ScrapedScene):
        return round(
            difflib.SequenceMatcher(
                None,
                query.lower(),
                candidate["title"].lower(),  # type: ignore (title is always set)
            ).ratio(),
            3,
        )

    for domain in search_domains:
        log.debug(f"Searching {domain}")

        api_headers = _create_headers_for(domain)
        api_response = __api_request(search_url, api_headers)
        if api_response is None:
            log.error(f"Failed to search {domain}")
            continue
        if not api_response:
            log.debug(f"No results from {domain}")
            continue

        candidates = [
            postprocess(to_scraped_scene(result), result)
            for result in api_response
            if result["id"] not in already_seen
        ]
        search_results.extend(
            c
            for c in candidates
            if matcher(c) > 0.5 and c.get("code") not in already_seen
        )
        already_seen.update(c.get("code") for c in candidates)

        # Try to to avoid more than 10ish results or this will take forever
        if len(search_results) >= 10:
            log.warning("Found more than 10 results, stopping search")
            break

    log.info(f"Search finished, found {len(search_results)} candidates")

    return sorted(search_results, key=matcher, reverse=True)


def performer_search(
    query: str,
    search_domains: list[str] | None = None,
    postprocess: Callable[
        [ScrapedPerformer, dict], ScrapedPerformer
    ] = default_postprocess,
) -> list[ScrapedPerformer]:
    """
    Searches the Aylo API for the given query and returns a list of ScrapedPerformer

    If search_domains is provided it will only search those domains,
    otherwise it will search all known domains (this could be very slow!)

    Domains should not include the "www." or ".com" parts of the domain: 'brazzers', 'realitykings', etc.

    If postprocess is provided it will be called on each result before returning
    """
    if not query:
        log.error("No query provided")
        return []

    if not search_domains:
        log.warning("Searcing all known domains, this could be very slow!")
        search_domains = domains.all_domains()

    log.debug(f"Searching for '{query}' on {len(search_domains)} sites")

    # The source of the results will be based on the token used (Brazzers, Reality Kings, etc.)
    search_url = (
        f"https://site-api.project1service.com/v1/actors?search={query}&limit=10"
    )
    search_results = []
    already_seen = set()

    def matcher(candidate: ScrapedPerformer):
        return round(
            difflib.SequenceMatcher(
                None,
                query.lower(),
                candidate["name"].lower(),  # type: ignore (name is always set)
            ).ratio(),
            3,
        )

    for domain in search_domains:
        log.debug(f"Searching {domain}")

        api_headers = _create_headers_for(domain)
        api_response = __api_request(search_url, api_headers)
        if api_response is None:
            log.error(f"Failed to search {domain}")
            continue
        if not api_response:
            log.debug(f"No results from {domain}")
            continue

        candidates = [
            postprocess(to_scraped_performer(result, domain), result)
            for result in api_response
        ]

        search_results.extend(
            c
            for c in candidates
            if matcher(c) > 0.5 and c.get("name") not in already_seen
        )
        already_seen.update(c.get("name") for c in candidates)

        # Try to to avoid more than 10ish results or this will take forever
        if len(search_results) >= 10:
            log.warning("Found more than 10 results, stopping search")
            break

    log.debug(f"Search finished, found {len(search_results)} candidates")

    return sorted(search_results, key=matcher, reverse=True)


def scene_from_fragment(
    fragment: dict,
    search_domains: list[str] | None = None,
    min_ratio=config.minimum_similarity,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> ScrapedScene | None:
    """
    Scrapes a scene from a fragment, which must contain at least one of the following:
    - url: the URL of the scene
    - title: the title of the scene

    If domains is provided it will only search those domains,
    otherwise it will search all known domains (this could be very slow!)

    If min_ratio is provided _AND_ the fragment contains a title but no URL,
    the search will only return a scene if a match with at least that ratio is found

    If postprocess is provided it will be called on the result before returning
    """
    log.debug(f"Fragment scraping scene {fragment['id']}")
    if url := fragment.get("url"):
        log.debug(f"Using scene URL: '{url}'")
        if scene := scene_from_url(url, postprocess=postprocess):
            if markers := scene.pop("markers", []):  # type: ignore
                if fragment["id"] and config.scrape_markers:
                    add_markers(fragment["id"], markers)
                else:
                    log.debug(
                        f"This scene has {len(markers)} markers,"
                        " you can enable scraping them in config.ini"
                    )
            return scene
        log.debug("Failed to scrape scene from URL")
    if title := fragment.get("title"):
        log.debug(f"Searching for '{title}'")
        if scene := find_scene(
            title, search_domains, min_ratio, postprocess=postprocess
        ):
            return scene
        log.debug("Failed to find scene by title")

    log.warning("Cannot scrape from this fragment: need to have title or url set")


def performer_from_fragment(
    fragment: dict,
    search_domains: list[str] | None = None,
    min_ratio=0.9,
    postprocess: Callable[
        [ScrapedPerformer, dict], ScrapedPerformer
    ] = default_postprocess,
) -> ScrapedPerformer | None:
    """
    Scrapes a performer from a fragment, which must contain one of the following:
    - url: the URL of the performer page (anywhere in the Aylo network)
    - name: the name of the performer

    If domains is provided it will only search those domains,
    otherwise it will search all known domains (this could be very slow!)

    If min_ratio is provided _AND_ the fragment contains a title but no URL,
    the search will only return a scene if a match with at least that ratio is found

    If postprocess is provided it will be called on the result before returning
    """
    log.debug("Fragment scraping performer...")
    if url := fragment.get("url"):
        log.debug(f"Using performer URL: '{url}'")
        return performer_from_url(url, postprocess=postprocess)
    elif name := fragment.get("name"):
        log.debug(f"Searching for '{name}'")
        return find_performer(name, search_domains, min_ratio, postprocess=postprocess)

    log.warning("Cannot scrape from this fragment: need to have url or name set")


def main_scraper():
    """
    Takes arguments from stdin or from the command line and dumps output as JSON to stdout
    """
    op, args = scraper_args()
    result = None
    match op, args:
        case "gallery-by-url" | "gallery-by-fragment", {"url": url} if url:
            result = gallery_from_url(url)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name, "extra": _domains} if name:
            result = scene_search(name, search_domains=_domains)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            _domains = args.get("extra", None)
            result = scene_from_fragment(args, search_domains=_domains)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            _domains = args.get("extra", None)
            result = performer_from_fragment(args, search_domains=_domains)
        case "performer-by-name", {"name": name, "extra": _domains} if name:
            result = performer_search(name, search_domains=_domains)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))


if __name__ == "__main__":
    main_scraper()
