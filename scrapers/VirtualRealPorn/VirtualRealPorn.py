"""
Stash scraper for Evil Angel (Network) that uses the Algolia API Python client
"""
import json
import sys
from typing import Any, Callable
from urllib.parse import urlparse

from AlgoliaAPI.AlgoliaAPI import (
    ScrapedGallery,
    clean_text,
    default_postprocess,
    get_search_client,
    parse_gender,
    site_from_url,
    sort_api_actors_by_match,
    sort_api_scenes_by_match
)

from py_common import log
from py_common.types import ScrapedPerformer, ScrapedScene
from py_common.util import dig, guess_nationality, scraper_args

CONFIG = {
    "virtualrealamateurporn": {
        "indexes": {
            "videos": "en_videos_virtualrealamateur",
        },
        "studio_name": "VirtualRealAmateur",
    },
    "virtualrealgay": {
        "indexes": {
            "models": "en_models_virtualrealgay",
            "videos": "en_videos_virtualrealgay",
        },
        "studio_name": "VirtualRealGay",
    },
    "virtualrealjapan": {
        "indexes": {
            "videos": "en_videos_virtualrealjapan",
        },
        "studio_name": "VirtualRealJapan",
    },
    "virtualrealpassion": {
        "indexes": {
            "models": "en_models_virtualrealpassion",
            "videos": "en_videos_virtualrealpassion",
        },
        "studio_name": "VirtualRealPassion",
    },
    "virtualrealporn": {
        "indexes": {
            "models": "en_models_virtualrealporn",
            "videos": "en_videos_virtualrealporn",
        },
        "studio_name": "VirtualRealPorn",
    },
    "virtualrealtrans": {
        "indexes": {
            "models": "en_models_virtualrealtrans",
            "videos": "en_videos_virtualrealtrans",
        },
        "studio_name": "VirtualRealTrans",
    },
}

def indexes_for_sites(index_type: str, sites: list[str]) -> list[str]:
    """
    Returns a list of index names for the given sites and index type
    """
    return [
        CONFIG[site]["indexes"][index_type]
        for site in sites
        if site in CONFIG and index_type in CONFIG[site]["indexes"]
    ]

def actors_to_performers(actors: list[dict[str, Any]], site: str) -> list[ScrapedPerformer]:
    "Converts API actors to list of ScrapedPerformer"
    return [
        {
            "name": actor.get("name").strip(),
            "gender": parse_gender(actor.get("gender")),
            "country": actor.get("country"),
        }
        for actor in actors
    ]

def to_scraped_performer(performer_from_api: dict[str, Any], site: str) -> ScrapedPerformer:
    "Helper function to convert from Algolia's API to Stash's scraper return type"
    performer: ScrapedPerformer = {}
    if _name := performer_from_api.get("name"):
        performer["name"] = _name.strip()
    if gender := performer_from_api.get("gender"):
        performer["gender"] = parse_gender(gender.strip())
    if eye_color := performer_from_api.get("eyesColor"):
        performer["eye_color"] = eye_color.strip()
    if hair_color := performer_from_api.get("hairColor"):
        performer["hair_color"] = hair_color.strip()
    if country := performer_from_api.get("country"):
        performer["country"] = guess_nationality(country.strip())
    if image_url := performer_from_api.get("imageURL"):
        performer["images"] = [image_url]
    if permalink := performer_from_api.get("permalink"):
        performer["url"] = permalink
    return performer

def to_scraped_scene(scene_from_api: dict[str, Any], site: str) -> ScrapedScene:
    "Helper function to convert from Algolia's API (VirtualRealPorn variant) to Stash's scraper return type"
    scene: ScrapedScene = {}
    # studio from CONFIG
    if studio := CONFIG.get(site, {}).get("studio_name", site):
        scene["studio"] = {"name": studio}
    # rest from API object
    if object_id := scene_from_api.get("objectID"):
        scene["code"] = str(object_id)
    if title := scene_from_api.get("title"):
        scene["title"] = title.strip()
    if description := scene_from_api.get("description"):
        scene["details"] = clean_text(description)
    if permalink := scene_from_api.get("permalink"):
        scene["url"] = permalink
    if release_date := scene_from_api.get("release_date"):
        # release date is in 'YYYY-MM-DD HH:MM:SS' format, we only want the date part, i.e. first 10 characters
        scene["date"] = release_date[:10]
    if poster := scene_from_api.get("poster"):
        scene["image"] = poster
    if categories := scene_from_api.get("categories"):
        # add fixed tag "Virtual Reality" if not present
        if "Virtual Reality" not in categories:
            categories.append("Virtual Reality")
        scene["tags"] = [{"name": c} for c in categories]
    if casting := scene_from_api.get("casting"):
        scene["performers"] = actors_to_performers(casting, site)
    return scene

def api_scene_from_id(
    object_id: int | str,
    sites: list[str],
    fragment: dict[str, Any] = None,
) -> dict[str, Any] | None:
    "Searches a scene from a clip_id and returns the API result as-is"
    site = sites[0] # All VirtualRealPorn network sites appear to use the same API keys
    log.debug(f"Site: {site}")
    index_names = indexes_for_sites("videos", sites)
    # if single index provided, use search_single_index for efficiency
    if len(index_names) == 1:
        index_name = index_names[0]
        response = get_search_client("virtualrealporn").search_single_index(
            index_name=index_name,
            search_params={
                "attributesToHighlight": [],
                "filters": f"objectID:{object_id}",
                "length": 1,
            },
        )
        log.debug(f"Number of search hits: {response.nb_hits}")
    else: # multiple indices
        responses = get_search_client("virtualrealporn").search(
            search_method_params={
                "requests": [
                    {
                        "indexName": index_name,
                        "filters": f"objectID:{object_id}",
                        "length": 1,
                    }
                    for index_name in index_names
                ]
            },
        )
        # find the first response with hits
        response = next(
            (res.actual_instance for res in responses.results if res.actual_instance.nb_hits > 0),
            None,
        )
        log.debug(f"Number of search hits: {response.nb_hits if response else 0}")
    if response.nb_hits:
        if response.nb_hits == 1:
            return response.hits[0].to_dict()
        if response.nb_hits > 1:
            return sort_api_scenes_by_match(
                [hit.to_dict() for hit in response.hits], fragment
            )[0]
    return None

def scene_from_id(
    object_id,
    sites: list[str],
    fragment: dict[str, Any] = None,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedScene | None:
    "Scrapes a scene from an objectID, running an optional postprocess function on the result"
    site = sites[0] # TODO: handle multiple sites?
    api_scene = api_scene_from_id(object_id, sites, fragment)
    if api_scene:
        return postprocess(to_scraped_scene(api_scene, site), api_scene)
    return None

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
    if _url := fragment.get("url"): # if a URL is present, scrape by URL
        return scene_from_url(_url, postprocess)
    if code := fragment.get("code"): # if the (studio) code is present, search by objectID
        return scene_from_id(code, sites, fragment, postprocess)
    if title := fragment.get("title"): # if a title is present, search by text
        if len(scenes := scene_search(title, sites, fragment, postprocess)) > 0:
            return scenes[0] # best match is sorted at the top
    return {}

def scene_search(
    query: str,
    sites: list[str],
    fragment: dict[str, Any] = None,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene | ScrapedGallery] = default_postprocess,
) -> list[ScrapedScene]:
    "Searches the API for scenes with a text query"
    log.debug(f"scene_search, query: {query}, sites: {sites}, fragment: {fragment}")
    site = sites[0] # VirtualRealPorn network sites appear to use the same API keys
    # set a default api_scenes list
    api_scenes: list[dict[str, Any]] = []
    index_names = indexes_for_sites("videos", sites)
    # if single index provided, use search_single_index for efficiency
    if len(index_names) == 1:
        index_name = index_names[0]
        search_response = get_search_client("virtualrealporn").search_single_index(
            index_name=index_name,
            search_params={
                "attributesToHighlight": [],
                "query": query,
                "length": 20,
            },
        )
        log.debug(f"Number of search hits: {search_response.nb_hits}")
        if search_response.nb_hits:
            # convert Algolia client search Hits to list of dicts
            api_scenes = [hit.to_dict() for hit in search_response.hits]
    else: # multiple indices
        search_responses = get_search_client("virtualrealporn").search(
            search_method_params={
                "requests": [
                    {
                        "indexName": index_name,
                        "query": query,
                        "filters": "visibleBy:group/all",
                        "length": 20,
                        "offset": 0,
                    }
                    for index_name in index_names
                ]
            },
        )
        log.debug(f"Number of search hits: {", ".join([ f"{res.actual_instance.index}: {res.actual_instance.nb_hits}" for res in search_responses.results ])}")
        api_scenes = [ hit.to_dict() for res in search_responses.results for hit in res.actual_instance.hits]
    log.debug(f"api_scenes: {api_scenes}")
    if len(api_scenes) == 1: # single search result
        return [postprocess(to_scraped_scene(api_scenes[0], site), api_scenes[0])]
    if len(api_scenes) > 1: # multiple search results
        return [
            postprocess(to_scraped_scene(api_scene, site), api_scene)
            for api_scene in sort_api_scenes_by_match(api_scenes, fragment) # sort
        ]
    return []

def scene_from_url(
    _url: str,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess
) -> ScrapedScene | None:
    "Scrapes a scene from a URL, running an optional postprocess function on the result"
    slug = urlparse(_url).path.rstrip("/").split("/")[-1]
    site = site_from_url(_url)
    log.debug(f"slug: {slug}, site: {site}")
    scenes = scene_search(slug, [site], indexes_for_sites("videos", [site]), postprocess=postprocess)
    log.debug(f"scenes: {scenes}")
    if scenes:
        return scenes[0]
    return None

def gallery_from_scene(scene: ScrapedScene) -> ScrapedGallery | None:
    "Convert a ScrapedScene to a ScrapedGallery"
    gallery: ScrapedGallery = {}
    # copy relevant fields from scene to gallery
    gallery["title"] = scene.get("title")
    gallery["details"] = scene.get("details")
    gallery["url"] = scene.get("url")
    gallery["urls"] = scene.get("urls")
    gallery["date"] = scene.get("date")
    gallery["studio"] = scene.get("studio")
    gallery["tags"] = scene.get("tags")
    gallery["performers"] = scene.get("performers")
    gallery["code"] = scene.get("code")
    # map director to photographer
    gallery["photographer"] = scene.get("director")
    return gallery

def gallery_from_url(
    _url: str,
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess
) -> ScrapedGallery | None:
    """
    Scrapes a gallery from a URL, running an optional postprocess function on the result

    VirtualRealPorn does not appear to have galleries, but photo sets appear on the scene pages
    so we can treat scenes as galleries for this purpose
    """
    if scene := scene_from_url(_url, postprocess=postprocess):
        return gallery_from_scene(scene)
    return None

def gallery_from_fragment(
    fragment: dict[str, Any],
    sites: list[str],
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> ScrapedGallery | None:
    "Scrapes a gallery from a fragment. URL, code, title"
    scene = scene_from_fragment(fragment, sites, postprocess=postprocess)
    log.debug(f"in gallery_from_fragment, scene: {scene}")
    if scene:
        return gallery_from_scene(scene)
    return None

def performer_search(
    query: str,
    sites: list[str],
    fragment: dict[str, Any] = None,
    postprocess: Callable[[ScrapedPerformer, dict], ScrapedPerformer] = default_postprocess,
) -> list[ScrapedPerformer]:
    "Searches the API for actors with a text query"
    log.debug(f"performer_search, query: {query}, sites: {sites}, fragment: {fragment}")
    site = sites[0] # VirtualRealPorn network sites appear to use the same API keys
    # set a default api_models list
    api_models: list[dict[str, Any]] = []
    index_names = indexes_for_sites("models", sites)
    # if single index provided, use search_single_index for efficiency
    if len(index_names) == 1:
        index_name = index_names[0]
        search_response = get_search_client("virtualrealporn").search_single_index(
            index_name=index_name,
            search_params={
                "attributesToHighlight": [],
                "query": query,
                "length": 20,
            },
        )
        log.debug(f"Number of search hits: {search_response.nb_hits}")
        if search_response.nb_hits:
            # convert Algolia client search Hits to list of dicts
            api_models = [hit.to_dict() for hit in search_response.hits]
    else: # multiple indices
        search_responses = get_search_client("virtualrealporn").search(
            search_method_params={
                "requests": [
                    {
                        "indexName": index_name,
                        "query": query,
                        "filters": "visibleBy:group/all",
                        "length": 20,
                        "offset": 0,
                    }
                    for index_name in index_names
                ]
            },
        )
        log.debug(f"Number of search hits: {", ".join([ f"{res.actual_instance.index}: {res.actual_instance.nb_hits}" for res in search_responses.results ])}")
        api_models = [ hit.to_dict() for res in search_responses.results for hit in res.actual_instance.hits]
    log.debug(f"api_models: {api_models}")
    if len(api_models) == 1: # single search result
        return [postprocess(to_scraped_performer(api_models[0], site), api_models[0])]
    if len(api_models) > 1: # multiple search results
        return [
            postprocess(to_scraped_performer(api_model, site), api_model)
            for api_model in sort_api_actors_by_match(api_models, {"name": query}) # sort
        ]
    return []

def performer_from_url(
    _url: str,
    postprocess: Callable[[ScrapedPerformer, dict], ScrapedPerformer] = default_postprocess,
) -> ScrapedPerformer | None:
    "Scrapes a performer from a URL, running an optional postprocess function on the result"
    slug = urlparse(_url).path.rstrip("/").split("/")[-1]
    site = site_from_url(_url)
    log.debug(f"Performer slug: {slug}, Site: {site}")
    performers = performer_search(slug, [site], postprocess=postprocess)
    log.debug(f"performers: {performers}")
    if performers:
        return performers[0]
    return None

def performer_from_fragment(
    fragment: dict[str, Any],
    sites: list[str],
    postprocess: Callable[[ScrapedPerformer, dict], ScrapedPerformer] = default_postprocess,
) -> ScrapedPerformer:
    """
    This receives:
    - name
    - urls
    - gender
    from the result of the performer-by-name search
    """
    if urls := fragment.get("urls"):
        # find first URL that contains "virtualreal"
        if _url := next((url for url in urls if "virtualreal" in url), None):
            return performer_from_url(_url, postprocess)
    if name := fragment.get("name"): # if a name is present, search by text
        if len(performers := performer_search(name, sites, fragment, postprocess)) > 0:
            return performers[0] # best match is sorted at the top
    return {}


if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url, "extra": extra} if url and extra:
            sites = extra
            result = gallery_from_url(url)
        case "gallery-by-fragment", args:
            sites = args.pop("extra")
            result = gallery_from_fragment(args, sites)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = scene_search(name, sites, index_names=indexes_for_sites("videos", sites))
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            sites = args.pop("extra")
            result = scene_from_fragment(args, sites)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            sites = args.pop("extra")
            result = performer_from_fragment(args, sites)
        case "performer-by-name", {"name": name, "extra": extra} if name and extra:
            sites = extra
            result = performer_search(name, sites)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
