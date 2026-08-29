import json
import re
import sys
from typing import Any
from urllib.parse import unquote, urlparse

import requests
from algoliasearch.search.client import SearchClientSync
from algoliasearch.search.config import SearchConfig
from algoliasearch.search.models.search_response import SearchResponse

from Altwolia import domains
from Altwolia.scrape import clean_text, headers_for_homepage, match_ratio, sort_by_match

from py_common import log
from py_common.types import (
    Gender,
    ScrapedGallery,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedTag,
)
from py_common.util import guess_nationality, scraper_args

# virtualrealamateurporn.com is dead (confirmed live: both the bare domain
# and www. return a Cloudflare 530, origin unreachable) - dropped entirely.
# Every other site shares one Algolia app/key; studio names below are
# already exactly what the API's own site_slug implies and match StashDB,
# no override needed.
CONFIG = {
    "virtualrealgay": {
        "video_path": "vr-gay-porn-video",
        "actor_path": "vr-models",
        "studio_name": "VirtualRealGay",
    },
    "virtualrealjapan": {
        "video_path": "vr-japanese-video",
        "actor_path": "vr-models",
        "studio_name": "VirtualRealJapan",
    },
    "virtualrealpassion": {
        "video_path": "vr-female-pov-video",
        "actor_path": "vr-models",
        "studio_name": "VirtualRealPassion",
    },
    "virtualrealporn": {
        "video_path": "vr-porn-video",
        "actor_path": "vr-pornstars",
        "studio_name": "VirtualRealPorn",
    },
    "virtualrealtrans": {
        "video_path": "vr-trans-porn-video",
        "actor_path": "vr-models",
        "studio_name": "VirtualRealTrans",
    },
}

GENDER_MAP: dict[str, Gender] = {
    "MALE": "MALE",
    "FEMALE": "FEMALE",
    "FEMALE_TRANS": "TRANSGENDER_FEMALE",
    "SHEMALE": "TRANSGENDER_FEMALE",
}


def parse_gender(gender: str) -> Gender | None:
    return GENDER_MAP.get(gender)


def video_index(site: str) -> str:
    return f"vrn_{site}_videos"


def models_index(site: str) -> str:
    return f"vrn_{site}_models"


def video_url(site: str, slug: str) -> str:
    return f"https://{site}.com/{CONFIG[site]['video_path']}/{slug}/"


def actor_url(site: str, slug: str) -> str:
    return f"https://{site}.com/{CONFIG[site]['actor_path']}/{slug}/"


def slug_from_url(url: str) -> str:
    # Algolia's search doesn't reliably match a raw hyphen-joined slug as a
    # single token - converting to space-separated words fixes it (verified
    # live: 0 hits with hyphens, 1 exact hit with spaces)
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return unquote(slug).replace("-", " ")


def fetch_instance_token(url: str) -> tuple[str, str] | None:
    r = requests.get(url, headers=headers_for_homepage(url), timeout=10)
    if not (
        match := re.search(
            r'data-algolia-app-id="([^"]+)"\s+data-algolia-search-key="([^"]+)"', r.text
        )
    ):
        log.error(
            f"Failed to get app_id/key from '{url}': page structure may have changed"
        )
        return None
    return match.group(1), match.group(2)


def get_search_client() -> SearchClientSync | None:
    # The whole network shares one Algolia app/key, fetched from any one
    # site's homepage - cached under a single "virtualrealporn" key
    pair = domains.get_auth_for("virtualrealporn", fallback=fetch_instance_token)
    if pair is None:
        log.error(
            "Unable to get Algolia authentication for the VirtualRealPorn network"
        )
        return None
    app_id, api_key = pair
    config = SearchConfig(app_id, api_key)
    config.headers.update(headers_for_homepage("https://virtualrealporn.com"))
    return SearchClientSync(config=config)


def multi_search(
    client: SearchClientSync, index_names: list[str], params: dict[str, Any]
) -> list[dict[str, Any]]:
    "Runs a multi-index search, ignoring any non-scene/performer (facet-value) responses"
    responses = client.search(
        search_method_params={
            "requests": [
                {"indexName": index_name, **params} for index_name in index_names
            ]
        },
    )
    hits: list[dict[str, Any]] = []
    for result in responses.results:
        instance = result.actual_instance
        if isinstance(instance, SearchResponse) and instance.hits:
            hits.extend(hit.to_dict() for hit in instance.hits)
    return hits


def sort_scenes_by_match(
    api_scenes: list[dict[str, Any]], fragment: dict[str, Any] | None
) -> list[dict[str, Any]]:
    if not fragment:
        return api_scenes
    return sort_by_match(
        api_scenes,
        lambda s: [
            match_ratio(
                (fragment.get("title") or "").lower(), (s.get("title") or "").lower()
            ),
            match_ratio(fragment.get("date"), (s.get("published_at") or "")[:10]),
            match_ratio(
                fragment.get("details"), clean_text(s.get("description") or "")
            ),
        ],
    )


def sort_actors_by_match(
    api_actors: list[dict[str, Any]], name: str | None
) -> list[dict[str, Any]]:
    if not name:
        return api_actors
    return sort_by_match(
        api_actors,
        lambda a: [match_ratio(name.lower(), (a.get("name") or "").lower())],
    )


def scene_actors_to_performers(
    actors: list[dict[str, Any]], site: str
) -> list[ScrapedPerformer]:
    # Scene-embedded actor stubs only carry name/slug/avatar - no gender or
    # country, unlike the standalone models index
    performers: list[ScrapedPerformer] = []
    for actor in actors:
        performer: ScrapedPerformer = {"name": actor["name"].strip()}
        if slug := actor.get("slug"):
            performer["urls"] = [actor_url(site, slug)]
        performers.append(performer)
    return performers


def to_scraped_performer(api_performer: dict[str, Any]) -> ScrapedPerformer:
    site = api_performer.get("site_slug", "")
    performer: ScrapedPerformer = {"name": api_performer.get("name", "").strip()}
    if (gender := api_performer.get("gender")) and (
        parsed_gender := parse_gender(gender)
    ):
        performer["gender"] = parsed_gender
    if description := api_performer.get("description"):
        performer["details"] = clean_text(description)
    if eyes_color := api_performer.get("eyes_color"):
        performer["eye_color"] = eyes_color.strip().capitalize()
    if hair_color := api_performer.get("hair_color"):
        performer["hair_color"] = hair_color.strip().capitalize()
    if country_code := api_performer.get("country_code"):
        performer["country"] = guess_nationality(country_code.strip())
    if avatar := api_performer.get("avatar_url"):
        performer["images"] = [avatar]
    if slug := api_performer.get("slug"):
        performer["urls"] = [actor_url(site, slug)]
    return performer


def to_scraped_scene(api_scene: dict[str, Any]) -> ScrapedScene:
    site = api_scene.get("site_slug", "")
    scene: ScrapedScene = {}
    if object_id := api_scene.get("objectID"):
        scene["code"] = str(object_id)
    if title := api_scene.get("title"):
        scene["title"] = title.strip()
    if description := api_scene.get("description"):
        scene["details"] = clean_text(description)
    if (slug := api_scene.get("url_slug")) and site in CONFIG:
        scene["urls"] = [video_url(site, slug)]
    if published_at := api_scene.get("published_at"):
        scene["date"] = published_at[:10]
    if cover := api_scene.get("cover_url"):
        scene["image"] = cover
    if site in CONFIG:
        scene["studio"] = {"name": CONFIG[site]["studio_name"]}

    # "tags" on this API is internal/promotional labels (e.g. "most-viewed",
    # "exclusive-video"), not content descriptors - only categories qualify
    tags: list[ScrapedTag] = [{"name": c} for c in api_scene.get("categories", [])]
    tags.append({"name": "Virtual Reality"})
    scene["tags"] = tags

    if actors := api_scene.get("actors"):
        scene["performers"] = scene_actors_to_performers(actors, site)
    return scene


def to_scraped_gallery(api_scene: dict[str, Any]) -> ScrapedGallery:
    # VirtualRealPorn has no separate photo sets - scene pages double as
    # galleries, so a gallery is just a scene's fields relabelled
    scene = to_scraped_scene(api_scene)
    gallery: ScrapedGallery = {}
    if title := scene.get("title"):
        gallery["title"] = title
    if details := scene.get("details"):
        gallery["details"] = details
    if urls := scene.get("urls"):
        gallery["urls"] = urls
    if date := scene.get("date"):
        gallery["date"] = date
    if studio := scene.get("studio"):
        gallery["studio"] = studio
    if tags := scene.get("tags"):
        gallery["tags"] = tags
    if performers := scene.get("performers"):
        gallery["performers"] = performers
    if code := scene.get("code"):
        gallery["code"] = code
    return gallery


def api_scenes_search(
    query: str, sites: list[str], length: int = 5
) -> list[dict[str, Any]]:
    if not (client := get_search_client()):
        return []
    index_names = [video_index(site) for site in sites if site in CONFIG]
    if not index_names:
        return []
    if len(index_names) == 1:
        response = client.search_single_index(
            index_name=index_names[0],
            search_params={
                "attributesToHighlight": [],
                "query": query,
                "length": length,
            },
        )
        return [hit.to_dict() for hit in response.hits]
    return multi_search(client, index_names, {"query": query, "length": length})


def api_scene_from_id(
    object_id: str, sites: list[str], fragment: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    if not (client := get_search_client()):
        return None
    index_names = [video_index(site) for site in sites if site in CONFIG]
    if len(index_names) == 1:
        response = client.search_single_index(
            index_name=index_names[0],
            search_params={
                "attributesToHighlight": [],
                "filters": f"objectID:{object_id}",
                "length": 1,
            },
        )
        api_scenes = [hit.to_dict() for hit in response.hits]
    else:
        api_scenes = multi_search(
            client, index_names, {"filters": f"objectID:{object_id}", "length": 1}
        )
    if not api_scenes:
        return None
    return sort_scenes_by_match(api_scenes, fragment)[0]


def scene_from_id(
    object_id: str, sites: list[str], fragment: dict[str, Any] | None = None
) -> ScrapedScene | None:
    if api_scene := api_scene_from_id(object_id, sites, fragment):
        return to_scraped_scene(api_scene)
    return None


def scene_search(
    query: str, sites: list[str], fragment: dict[str, Any] | None = None
) -> list[ScrapedScene]:
    api_scenes = api_scenes_search(query, sites)
    return [
        to_scraped_scene(api_scene)
        for api_scene in sort_scenes_by_match(api_scenes, fragment)
    ]


def scene_from_url(url: str, site: str) -> ScrapedScene | None:
    scenes = scene_search(slug_from_url(url), [site])
    return scenes[0] if scenes else None


def scene_from_fragment(
    fragment: dict[str, Any], sites: list[str]
) -> ScrapedScene | None:
    if url := fragment.get("url"):
        site = domains.site_name(url)
        return scene_from_url(url, site)
    if code := fragment.get("code"):
        return scene_from_id(code, sites, fragment)
    if title := fragment.get("title"):
        if scenes := scene_search(title, sites, fragment):
            return scenes[0]
    return None


def gallery_from_url(url: str, site: str) -> ScrapedGallery | None:
    api_scenes = api_scenes_search(slug_from_url(url), [site])
    if not api_scenes:
        return None
    return to_scraped_gallery(sort_scenes_by_match(api_scenes, None)[0])


def gallery_from_fragment(
    fragment: dict[str, Any], sites: list[str]
) -> ScrapedGallery | None:
    if url := fragment.get("url"):
        site = domains.site_name(url)
        return gallery_from_url(url, site)
    if code := fragment.get("code"):
        if api_scene := api_scene_from_id(code, sites, fragment):
            return to_scraped_gallery(api_scene)
        return None
    if title := fragment.get("title"):
        api_scenes = api_scenes_search(title, sites)
        if api_scenes:
            return to_scraped_gallery(sort_scenes_by_match(api_scenes, fragment)[0])
    return None


def performer_search(query: str, sites: list[str]) -> list[ScrapedPerformer]:
    if not (client := get_search_client()):
        return []
    index_names = [models_index(site) for site in sites if site in CONFIG]
    if not index_names:
        return []
    if len(index_names) == 1:
        response = client.search_single_index(
            index_name=index_names[0],
            search_params={"attributesToHighlight": [], "query": query, "length": 20},
        )
        api_performers = [hit.to_dict() for hit in response.hits]
    else:
        api_performers = multi_search(
            client, index_names, {"query": query, "length": 20}
        )
    return [
        to_scraped_performer(api_performer)
        for api_performer in sort_actors_by_match(api_performers, query)
    ]


def performer_from_url(url: str) -> ScrapedPerformer | None:
    site = domains.site_name(url)
    performers = performer_search(slug_from_url(url), [site])
    return performers[0] if performers else None


def performer_from_fragment(
    fragment: dict[str, Any], sites: list[str]
) -> ScrapedPerformer | None:
    if url := fragment.get("url"):
        return performer_from_url(url)
    if name := fragment.get("name"):
        if performers := performer_search(name, sites):
            return performers[0]
    return None


if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, domains.site_name(url))
        case "scene-by-name", {"name": name, "extra": extra} if name and extra:
            result = scene_search(name, extra)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            sites = args.pop("extra")
            result = scene_from_fragment(args, sites)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, domains.site_name(url))
        case "gallery-by-fragment", args:
            sites = args.pop("extra")
            result = gallery_from_fragment(args, sites)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            sites = args.pop("extra")
            result = performer_from_fragment(args, sites)
        case "performer-by-name", {"name": name, "extra": extra} if name and extra:
            result = performer_search(name, extra)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
