import json
import re
import sys
from base64 import b64encode
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, Callable

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    ScrapedGallery,
    ScrapedMovie,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedTag,
)
from py_common.util import (
    dig,
    feet_to_cm,
    guess_nationality,
    is_valid_url,
    lb_to_kg,
    scraper_args,
)

ensure_requirements("algoliasearch", "requests", "bs4:beautifulsoup4")

import requests  # noqa: E402
from algoliasearch.search.client import SearchClientSync  # noqa: E402
from algoliasearch.search.config import SearchConfig  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

import Altwolia.domains as domains  # noqa: E402

IMAGE_CDN = "https://images03-fame.gammacdn.com"
TRANSFORM_IMAGE_CDN = "https://transform.gammacdn.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0"
)

def default_postprocess(obj: Any, _) -> Any:
    return obj


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9-]+", "-", text)


def headers_for_homepage(homepage: str) -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Origin": homepage, "Referer": homepage}


def clean_text(text: str) -> str:
    text = text.replace("\\", "")
    text = re.sub(r"<\s*/?br\s*/?\s*>", "\n", text)
    return BeautifulSoup(text, "html.parser").get_text("", strip=False)


def get_search_client(site: str) -> SearchClientSync | None:
    def fetch_instance_token(url: str) -> tuple[str, str] | None:
        r = requests.get(url, headers=headers_for_homepage(url), timeout=10)
        if not (script_tag := re.search(r"window\.env\s*=\s*(.+);", r.text)):
            log.error(f"Failed to get app_id/key from '{url}': not an Algolia site?")
            return None
        page_json = json.loads(script_tag.group(1))
        return dig(page_json, "api", "algolia", "applicationID"), dig(
            page_json, "api", "algolia", "apiKey"
        )

    pair = domains.get_auth_for(site, fallback=fetch_instance_token)
    if pair is None:
        log.error(f"Unable to get Algolia authentication for '{site}'")
        return None

    app_id, api_key = pair
    config = SearchConfig(app_id, api_key)
    config.headers.update(headers_for_homepage(f"https://www.{site}.com"))
    return SearchClientSync(config=config)


def id_from_url(url: str) -> str | None:
    if match := re.search(r"/(\d+)$", url):
        return match.group(1)
    log.error(f"Could not find an ID in '{url}': are you sure this site uses Algolia?")
    return None


def gallery_url(site: str, url_title: str, set_id: str) -> str:
    return f"https://www.{site}.com/en/photo/{url_title}/{set_id}"


def performer_url(site: str, url_name: str, actor_id: str) -> str:
    return f"https://www.{site}.com/en/pornstar/view/{url_name}/{actor_id}"


def movie_url(site: str, url_title: str, movie_id: str) -> str:
    return f"https://www.{site}.com/en/movie/{url_title}/{movie_id}"


def scene_url(site: str, sitename: str, url_title: str, clip_id: str) -> str:
    return f"https://www.{site.lower()}.com/en/video/{sitename.lower()}/{url_title}/{clip_id}"


def name_values_as_csv(objects: list[dict[str, Any]]) -> str:
    return ", ".join(obj.get("name", "") for obj in objects)


def name_values_as_list(objects: list[dict[str, Any]]) -> list[ScrapedTag]:
    return [{"name": obj.get("name", "")} for obj in objects]


def list_to_name_values(values: list[str]) -> list[ScrapedTag]:
    return [{"name": v} for v in values]


def actors_to_performers(
    actors: list[dict[str, Any]], site: str
) -> list[ScrapedPerformer]:
    performers: list[ScrapedPerformer] = []
    for actor in actors:
        performer: ScrapedPerformer = {
            "name": actor["name"].strip(),
            "gender": actor["gender"].upper(),
        }
        if (url_name := actor.get("url_name")) and (actor_id := actor.get("actor_id")):
            performer["urls"] = [performer_url(site, url_name, actor_id)]
        performers.append(performer)
    return performers


def to_scraped_performer(api_performer: dict[str, Any], site: str) -> ScrapedPerformer:
    performer: ScrapedPerformer = {"name": api_performer.get("name", "").strip()}
    if gender := api_performer.get("gender"):
        performer["gender"] = gender.strip().upper()
    if details := api_performer.get("description"):
        performer["details"] = clean_text(details)
    if eye_color := dig(api_performer, "attributes", "eye_color"):
        performer["eye_color"] = eye_color.strip()
    if hair_color := dig(api_performer, "attributes", "hair_color"):
        performer["hair_color"] = hair_color.strip()
    if ethnicity := dig(api_performer, "attributes", "ethnicity"):
        performer["ethnicity"] = ethnicity.strip()
    if alternate_names := dig(api_performer, "attributes", "alternate_names"):
        performer["aliases"] = alternate_names.strip()
    if height := dig(api_performer, "attributes", "height"):
        performer["height"] = feet_to_cm(height.strip())
    if weight := dig(api_performer, "attributes", "weight"):
        performer["weight"] = lb_to_kg(weight.strip())
    if endowment := dig(api_performer, "attributes", "endowment"):
        performer["penis_length"] = feet_to_cm("0'" + endowment.strip())
    if home := dig(api_performer, "attributes", "home"):
        performer["country"] = guess_nationality(home.strip())
    if api_performer.get("has_pictures") and (
        pictures := api_performer.get("pictures")
    ):
        main_pic = list(pictures.values())[-1]
        performer["images"] = [f"{IMAGE_CDN}/actors{main_pic}"]
    if (url_name := api_performer.get("url_name")) and (
        actor_id := api_performer.get("actor_id")
    ):
        performer["urls"] = [performer_url(site, url_name, actor_id)]
    return performer


def movie_from_api_scene(api_scene: dict[str, Any], site: str) -> ScrapedMovie:
    """
    Builds the movie stub attached to a scene's `movies` field. Uses the same
    date logic as `to_scraped_movie` so that re-scraping this movie's own URL
    never contradicts what was attached here.
    """
    movie: ScrapedMovie = {}
    if not (movie_title := api_scene.get("movie_title")):
        return movie
    movie["name"] = movie_title
    if movie_id := api_scene.get("movie_id"):
        if date := (
            movie_release_date(movie_id, site) or api_scene.get("movie_date_created")
        ):
            movie["date"] = date
    elif movie_date_created := api_scene.get("movie_date_created"):
        movie["date"] = movie_date_created
    if movie_desc := api_scene.get("movie_desc"):
        movie["synopsis"] = clean_text(movie_desc)
    if (url_movie_title := api_scene.get("url_movie_title")) and movie_id:
        movie["urls"] = [movie_url(site, url_movie_title, movie_id)]
    return movie


@lru_cache
def movie_exists(movie_id: int | str, site: str) -> bool:
    """
    A scene's `movie_id` being set doesn't mean it was ever published as its
    own movie page - on some sites the large majority are synthetic stubs
    whose constructed URL just 404s. Confirmed across several networks at
    wildly different rates (near-0% on some, 90-100% on others), so this is
    checked unconditionally rather than trusted from the scene data alone.
    """
    if not (client := get_search_client(site)):
        return False
    response = client.search_single_index(
        index_name="all_movies",
        search_params={
            "attributesToHighlight": [],
            "filters": f"movie_id:{movie_id}",
            "hitsPerPage": 1,
        },
    )
    return bool(response.nb_hits)


def scene_urls(api_scene: dict[str, Any]) -> list[str]:
    if (
        (url_title := api_scene.get("url_title"))
        and (sitename := api_scene.get("sitename"))
        and (clip_id := api_scene.get("clip_id"))
        and (available_on := api_scene.get("availableOnSite"))
    ):
        urls = [
            scene_url(site, sitename, url_title, clip_id)
            for site in available_on
            if domains.has_own_site(site)
        ]
        return urls
    return []


def largest_scene_image(api_scene: dict[str, Any]) -> str | None:
    "Picks the highest resolution scene cover image, preferring the NSFW version"
    if images := dig(api_scene, "pictures", ("nsfw", "sfw"), "top"):
        return next(iter(images.values()), None)
    return None


def scene_number(api_scene: dict[str, Any]) -> int | None:
    """Return the numeric suffix of a scene's clip path, if it has one."""
    if not (clip_path := api_scene.get("clip_path")):
        return None
    if not (match := re.search(r"_(\d+)$", clip_path)):
        return None
    return int(match.group(1))


def append_scene_number(obj: Any, api_scene: dict[str, Any]) -> Any:
    """Append a clip-path scene number to a scene title when one is available."""
    if (title := obj.get("title")) and (number := scene_number(api_scene)) is not None:
        obj["title"] = f"{title}, Scene {number}"
    return obj


def to_scraped_scene(api_scene: dict[str, Any], site: str) -> ScrapedScene:
    scene: ScrapedScene = {}
    if clip_id := api_scene.get("clip_id"):
        scene["code"] = str(clip_id)
    if title := api_scene.get("title"):
        scene["title"] = title.strip()
    if description := api_scene.get("description"):
        scene["details"] = clean_text(description)
    if urls := scene_urls(api_scene):
        scene["urls"] = urls
    if release_date := api_scene.get("release_date"):
        scene["date"] = release_date
    if image := largest_scene_image(api_scene):
        scene["image"] = f"{IMAGE_CDN}/movies{image}"
    if studio_name := api_scene.get("studio_name"):
        scene["studio"] = {"name": studio_name}
    if (movie_id := api_scene.get("movie_id")) and movie_exists(movie_id, site):
        scene["movies"] = [movie_from_api_scene(api_scene, site)]

    tags = name_values_as_list(api_scene.get("categories", []))
    tags += list_to_name_values(api_scene.get("content_tags", []))
    if tags:
        scene["tags"] = tags

    if actors := api_scene.get("actors"):
        scene["performers"] = actors_to_performers(actors, site)
    if directors := api_scene.get("directors"):
        scene["director"] = name_values_as_csv(directors)

    return scene


def to_scraped_gallery(api_hit: dict[str, Any], site: str) -> ScrapedGallery:
    "Converts an API search hit (scene or photoset) to a ScrapedGallery"
    gallery: ScrapedGallery = {}
    # scenes can include a corresponding photoset_name; photosets have their own title
    if title := (api_hit.get("photoset_name") or api_hit.get("title")):
        gallery["title"] = title.strip()
    if description := api_hit.get("description"):
        gallery["details"] = clean_text(description)

    urls = []
    # scenes _can_ include photoset_id/photoset_url_name
    if (photoset_id := api_hit.get("photoset_id")) and (
        photoset_url_name := api_hit.get("photoset_url_name")
    ):
        gallery["code"] = photoset_id
        urls.append(gallery_url(site, photoset_url_name, photoset_id))
    # photosets have set_id/url_title instead
    if (set_id := api_hit.get("set_id")) and (url_title := api_hit.get("url_title")):
        gallery["code"] = str(set_id)
        urls.append(gallery_url(site, url_title, set_id))
    # api photosets can also carry the originating scene's clip_title
    if scene_data := {
        k: api_hit[k] for k in ("clip_title", "sitename", "clip_id") if k in api_hit
    }:
        if (
            (clip_title := scene_data.get("clip_title"))
            and (sitename := scene_data.get("sitename"))
            and (clip_id := scene_data.get("clip_id"))
        ):
            urls.append(scene_url(site, sitename, slugify(clip_title), clip_id))
    if urls:
        gallery["urls"] = urls

    # photosets have date_online, scenes have release_date
    if date := (api_hit.get("date_online") or api_hit.get("release_date")):
        gallery["date"] = date
    if studio_name := api_hit.get("studio_name"):
        gallery["studio"] = {"name": studio_name}
    if categories := api_hit.get("categories"):
        gallery["tags"] = name_values_as_list(categories)
    if actors := api_hit.get("actors"):
        gallery["performers"] = actors_to_performers(actors, site)
    if directors := api_hit.get("directors"):
        gallery["photographer"] = name_values_as_csv(directors)
    if picture := api_hit.get("picture"):
        log.info(f"Cover image: {TRANSFORM_IMAGE_CDN}/photo_set{picture}")

    return gallery


def movie_cover_image_url(cover_path: str, position: str) -> str:
    return f"{TRANSFORM_IMAGE_CDN}/movies{cover_path}_{position}_400x625.jpg?width=450&height=636"


def movie_cover_image_urls(
    api_movie: dict[str, Any], site: str
) -> tuple[str | None, str | None]:
    "Checks front/back cover images exist and that back isn't just a duplicate of front"
    if not (cover_path := api_movie.get("cover_path")):
        return None, None

    front_url = movie_cover_image_url(cover_path, "front")
    back_url = movie_cover_image_url(cover_path, "back")
    if not is_valid_url(back_url):
        return (front_url if is_valid_url(front_url) else None), None

    headers = headers_for_homepage(f"https://www.{site}.com")
    front_bytes = requests.get(front_url, headers=headers, timeout=10).content
    back_bytes = requests.get(back_url, headers=headers, timeout=10).content
    if b64encode(front_bytes) == b64encode(back_bytes):
        log.debug("Front and back cover images are identical, not scraping back image")
        back_url = None

    return (front_url if is_valid_url(front_url) else None), back_url


def movie_release_date(movie_id: int | str, site: str) -> str | None:
    """
    A movie's own `date_created` is just when it was added to the API, often
    long before any of its scenes are actually released - the latest of its
    scenes' `release_date`s is a much better proxy for when it's fully out
    See: https://github.com/stashapp/CommunityScrapers/issues/2257
    """
    if not (client := get_search_client(site)):
        return None
    response = client.search_single_index(
        index_name="all_scenes",
        search_params={
            "attributesToHighlight": [],
            "attributesToRetrieve": ["release_date"],
            "filters": f"movie_id:{movie_id}",
            "hitsPerPage": 1000,
        },
    )
    dates = [
        release_date
        for hit in response.hits
        if (release_date := hit.to_dict().get("release_date"))
    ]
    return max(dates) if dates else None


def to_scraped_movie(api_movie: dict[str, Any], site: str) -> ScrapedMovie:
    movie: ScrapedMovie = {}
    if title := api_movie.get("title"):
        movie["name"] = title.strip()
    if movie_id := api_movie.get("movie_id"):
        if date := (
            movie_release_date(movie_id, site) or api_movie.get("date_created")
        ):
            movie["date"] = date
    elif date_created := api_movie.get("date_created"):
        movie["date"] = date_created
    if length := api_movie.get("length"):
        movie["duration"] = str(length)
    if directors := api_movie.get("directors"):
        movie["director"] = name_values_as_csv(directors)
    if description := api_movie.get("description"):
        movie["synopsis"] = clean_text(description)
    if studio_name := api_movie.get("studio_name"):
        movie["studio"] = {"name": studio_name}

    front_image, back_image = movie_cover_image_urls(api_movie, site)
    if front_image:
        movie["front_image"] = front_image
    if back_image:
        movie["back_image"] = back_image

    if (url_title := api_movie.get("url_title")) and (
        movie_id := api_movie.get("movie_id")
    ):
        movie["urls"] = [movie_url(site, url_title, movie_id)]

    tags = name_values_as_list(api_movie.get("categories", []))
    tags += list_to_name_values(api_movie.get("content_tags", []))
    if tags:
        movie["tags"] = tags

    return movie


## Closeness-of-match scoring, used to rank search results against a fragment
def match_ratio(a: str | None, b: str | None) -> float | None:
    if a and b:
        return SequenceMatcher(None, a, b).ratio()
    return None


def scalar_match(candidate: int | float, reference: int | float) -> float:
    return 1 - abs(candidate - reference) / reference


def sort_by_match(
    api_objects: list[dict[str, Any]],
    scores: Callable[[dict[str, Any]], list[float | None]],
) -> list[dict[str, Any]]:
    def average_score(api_object: dict[str, Any]) -> float:
        values = [v for v in scores(api_object) if v is not None]
        return sum(values) / len(values) if values else 0

    return sorted(api_objects, key=average_score, reverse=True)


def sort_scenes_by_match(
    api_scenes: list[dict[str, Any]], fragment: dict[str, Any] | None
) -> list[dict[str, Any]]:
    if not fragment:
        return api_scenes
    return sort_by_match(
        api_scenes,
        lambda s: [
            match_ratio(
                (fragment.get("title") or "").lower(), s.get("title", "").lower()
            ),
            match_ratio(fragment.get("date"), s.get("release_date")),
            match_ratio(
                fragment.get("director"), name_values_as_csv(s.get("directors", []))
            ),
            match_ratio(fragment.get("details"), clean_text(s.get("description", ""))),
        ],
    )


def sort_actors_by_match(
    api_actors: list[dict[str, Any]], fragment: dict[str, Any] | None
) -> list[dict[str, Any]]:
    if not fragment or not (fragment_name := fragment.get("name")):
        return api_actors
    return sort_by_match(
        api_actors,
        lambda a: [match_ratio(fragment_name.lower(), a.get("name", "").lower())],
    )


def sort_photosets_by_match(
    api_photosets: list[dict[str, Any]], fragment: dict[str, Any] | None
) -> list[dict[str, Any]]:
    if not fragment:
        return api_photosets
    return sort_by_match(
        api_photosets,
        lambda p: [
            match_ratio(
                (fragment.get("title") or "").lower(), p.get("title", "").lower()
            ),
            match_ratio(fragment.get("date"), p.get("date_online")),
            match_ratio(
                fragment.get("photographer"), name_values_as_csv(p.get("directors", []))
            ),
            match_ratio(fragment.get("details"), clean_text(p.get("description", ""))),
        ],
    )


## Scene/gallery/movie/performer lookups
def api_scene_from_id(
    clip_id: str, site: str, fragment: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    if not (client := get_search_client(site)):
        return None
    response = client.search_single_index(
        index_name="all_scenes",
        search_params={
            "attributesToHighlight": [],
            "filters": f"clip_id:{clip_id}",
            "length": 1,
        },
    )
    if not response.nb_hits:
        return None
    hits = [hit.to_dict() for hit in response.hits]
    return sort_scenes_by_match(hits, fragment)[0]


def scene_from_id(
    clip_id: str,
    site: str,
    fragment: dict[str, Any] | None = None,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> ScrapedScene | None:
    if not (api_scene := api_scene_from_id(clip_id, site, fragment)):
        return None
    return postprocess(to_scraped_scene(api_scene, site), api_scene)


def scene_from_url(
    url: str,
    site: str,
    fragment: dict[str, Any] | None = None,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> ScrapedScene | None:
    if not (clip_id := id_from_url(url)):
        return None
    return scene_from_id(clip_id, site, fragment, postprocess)


def gallery_from_scene_id(
    clip_id: str,
    site: str,
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> ScrapedGallery | None:
    if not (api_scene := api_scene_from_id(clip_id, site)):
        return None
    return postprocess(to_scraped_gallery(api_scene, site), api_scene)


def gallery_from_set_id(
    set_id: str,
    site: str,
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> ScrapedGallery | None:
    if not (client := get_search_client(site)):
        return None
    response = client.search_single_index(
        index_name="all_photosets",
        search_params={
            "attributesToHighlight": [],
            "filters": f"set_id:{set_id}",
            "length": 1,
        },
    )
    if not response.nb_hits:
        return None
    api_photoset = response.hits[0].to_dict()
    return postprocess(to_scraped_gallery(api_photoset, site), api_photoset)


def gallery_from_url(
    url: str,
    site: str,
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> ScrapedGallery | None:
    if not (url_id := id_from_url(url)):
        return None
    # some sites have public photoset URLs, searchable by set_id;
    # others only have scene URLs, so fall back to the scene's own photoset
    if "/photo/" in url:
        return gallery_from_set_id(url_id, site, postprocess)
    if "/video/" in url:
        return gallery_from_scene_id(url_id, site, postprocess)
    return None


def movie_from_url(
    url: str,
    site: str,
    postprocess: Callable[[ScrapedMovie, dict], ScrapedMovie] = default_postprocess,
) -> ScrapedMovie | None:
    if not (movie_id := id_from_url(url)):
        return None
    if not (client := get_search_client(site)):
        return None
    response = client.search_single_index(
        index_name="all_movies",
        search_params={
            "attributesToHighlight": [],
            "filters": f"movie_id:{movie_id}",
            "length": 1,
        },
    )
    if not response.nb_hits:
        return None
    api_movie = response.hits[0].to_dict()
    return postprocess(to_scraped_movie(api_movie, site), api_movie)


def performer_from_url(
    url: str,
    site: str,
    postprocess: Callable[
        [ScrapedPerformer, dict], ScrapedPerformer
    ] = default_postprocess,
) -> ScrapedPerformer | None:
    if not (actor_id := id_from_url(url)):
        return None
    if not (client := get_search_client(site)):
        return None
    response = client.search_single_index(
        index_name="all_actors_latest_desc",
        search_params={
            "attributesToHighlight": [],
            "filters": f"actor_id:{actor_id}",
            "length": 1,
        },
    )
    if not response.nb_hits:
        return None
    api_performer = response.hits[0].to_dict()
    return postprocess(to_scraped_performer(api_performer, site), api_performer)


def scene_search(
    query: str,
    site: str,
    fragment: dict[str, Any] | None = None,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> list[ScrapedScene]:
    if not (client := get_search_client(site)):
        return []
    response = client.search_single_index(
        index_name="all_scenes",
        search_params={"attributesToHighlight": [], "query": query, "length": 20},
    )
    if not response.nb_hits:
        return []
    hits = [hit.to_dict() for hit in response.hits]
    return [
        postprocess(to_scraped_scene(api_scene, site), api_scene)
        for api_scene in sort_scenes_by_match(hits, fragment)
    ]


def gallery_search(
    query: str,
    site: str,
    fragment: dict[str, Any] | None = None,
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> list[ScrapedGallery]:
    if not (client := get_search_client(site)):
        return []
    response = client.search_single_index(
        index_name="all_photosets",
        search_params={"attributesToHighlight": [], "query": query, "length": 20},
    )
    if not response.nb_hits:
        return []
    hits = [hit.to_dict() for hit in response.hits]
    return [
        postprocess(to_scraped_gallery(api_photoset, site), api_photoset)
        for api_photoset in sort_photosets_by_match(hits, fragment)
    ]


def performer_search(
    query: str,
    site: str,
    postprocess: Callable[
        [ScrapedPerformer, dict], ScrapedPerformer
    ] = default_postprocess,
) -> list[ScrapedPerformer]:
    if not (client := get_search_client(site)):
        return []
    response = client.search_single_index(
        index_name="all_actors_latest_desc",
        search_params={"attributesToHighlight": [], "query": query, "length": 20},
    )
    if not response.nb_hits:
        return []
    hits = [hit.to_dict() for hit in response.hits]
    return [
        postprocess(to_scraped_performer(api_performer, site), api_performer)
        for api_performer in hits
    ]


def scene_from_fragment(
    fragment: dict[str, Any],
    site: str,
    postprocess: Callable[[ScrapedScene, dict], ScrapedScene] = default_postprocess,
) -> ScrapedScene | None:
    if urls := fragment.get("urls"):
        return scene_from_url(urls[0], site, fragment, postprocess)
    if code := fragment.get("code"):
        return scene_from_id(code, site, fragment, postprocess)
    if (title := fragment.get("title")) and (scenes := scene_search(title, site, fragment, postprocess)):
        # best match is sorted first
        return scenes[0]
    return None


def gallery_from_fragment(
    fragment: dict[str, Any],
    site: str,
    postprocess: Callable[[ScrapedGallery, dict], ScrapedGallery] = default_postprocess,
) -> ScrapedGallery | None:
    if url := fragment.get("url"):
        return gallery_from_url(url, site, postprocess)
    if code := fragment.get("code"):
        return gallery_from_set_id(code, site, postprocess)
    if title := fragment.get("title"):
        if galleries := gallery_search(title, site, fragment, postprocess):
            return galleries[0]
    return None


def performer_from_fragment(
    fragment: dict[str, Any],
    site: str,
    postprocess: Callable[
        [ScrapedPerformer, dict], ScrapedPerformer
    ] = default_postprocess,
) -> ScrapedPerformer | None:
    if not (url := fragment.get("url")):
        return None
    return performer_from_url(url, site, postprocess)


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    site = (args.get("extra") or [domains.site_name(args.get("url") or "")])[0]

    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url, site)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name, site)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args, site)
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url, site)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args, site)
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url, site)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args, site)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name, site)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url, site)
        case _:
            log.error(f"Operation: {op}, arguments: {args}")
            sys.exit(1)

    print(json.dumps(result))
