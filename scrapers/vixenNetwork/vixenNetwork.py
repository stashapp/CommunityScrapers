import difflib
import json
import re
import sys
from typing import Any
from urllib.parse import urlparse

from py_common import log
from py_common.config import get_config
from py_common.graphql import callGraphQL
from py_common.proxy import stash_requests
from py_common.types import ScrapedScene
from py_common.util import dig, is_own_url, scraper_args

config = get_config(
    default="""
# Create the official chapter markers when scraping a scene that's in Stash,
# needs the url and api_key of your Stash in py_common's config.ini
scrape_markers = False

# Max allowed difference (seconds) between the scene's file and the official runtime,
# markers are skipped if the file is a different cut
marker_duration_tolerance = 10

# Minimum similarity ratio to consider a match when searching by title
minimum_similarity = 0.75
"""
)

SITES = {
    "blacked": "Blacked",
    "blackedraw": "Blacked Raw",
    "deeper": "Deeper",
    "milfy": "Milfy",
    "slayed": "Slayed",
    "tushy": "Tushy",
    "tushyraw": "Tushy Raw",
    "vixen": "Vixen",
    "wifey": "Wifey",
}

# The API tags acts and positions but rarely the premise every scene on a site shares
SITE_TAGS = {
    "blacked": ["Black Male"],
    "blackedraw": ["Black Male"],
    "milfy": ["MILF"],
    "slayed": ["Lesbian"],
    "tushy": ["Anal Sex"],
    "tushyraw": ["Anal Sex"],
}

VIDEO_QUERY = """
query getVideo($videoSlug: String, $site: Site) {
  findOneVideo(input: { slug: $videoSlug, site: $site }) {
    title
    slug
    description
    releaseDate
    videoId
    runLength
    models { name }
    directors { name }
    categories { name }
    images { poster { src width } }
    chapters { video { title seconds } }
  }
}
"""

SEARCH_QUERY = """
query getSearchResults($query: String!, $site: Site!, $first: Int) {
  searchVideos(input: { query: $query, site: $site, first: $first }) {
    edges {
      node {
        title
        slug
        description
        releaseDate
        videoId
        models { name }
        images { listing { src width } }
      }
    }
  }
}
"""


def call_api(site: str, query: str, variables: dict[str, Any], referer: str) -> Any:
    try:
        response = stash_requests.post(
            f"https://www.{site}.com/graphql",
            json={"query": query, "variables": {"site": site.upper(), **variables}},
            headers={"Content-Type": "application/json", "Referer": referer},
        )
        response.raise_for_status()
        return response.json().get("data")
    # py_common.proxy raises a bare Exception once every backend has failed
    except Exception as err:  # noqa: BLE001
        log.error(f"GraphQL query to {site} failed: {err}")
        return None


def site_and_slug(url: str) -> tuple[str, str] | None:
    host = (urlparse(url).hostname or "").split(".")
    path = urlparse(url).path.rstrip("/").split("/")
    if len(host) > 1 and host[-2] in SITES and len(path) > 2 and path[-2] == "videos":
        return host[-2], path[-1]
    return None


def largest_image(images: list[dict[str, Any]] | None) -> str | None:
    return max(images or [], key=lambda i: i["width"], default={}).get("src")


def upgrade_image(image_url: str) -> str:
    # The API lists 1920x1080 at most but the CDN keeps a bigger original
    bigger = re.sub(r"\d+x\d+", "5760x3240", image_url)
    if stash_requests.head(bigger).status_code == 200:
        return bigger
    return image_url


def to_seconds(run_length: str | None) -> int | None:
    if run_length and (match := re.fullmatch(r"(\d+):(\d+):(\d+)", run_length)):
        hours, minutes, seconds = map(int, match.groups())
        return hours * 3600 + minutes * 60 + seconds
    return None


def to_scene(video: dict[str, Any], site: str, image: str | None) -> ScrapedScene:
    scene: ScrapedScene = {
        "title": video["title"],
        "code": video["videoId"],
        "urls": [f"https://www.{site}.com/videos/{video['slug']}"],
        "studio": {"name": SITES[site], "parent": {"name": "Vixen Media Group"}},
    }
    if details := video.get("description"):
        scene["details"] = details
    if date := video.get("releaseDate"):
        scene["date"] = date.split("T")[0]
    if performers := video.get("models"):
        scene["performers"] = [{"name": p["name"]} for p in performers]
    if directors := video.get("directors"):
        scene["director"] = ", ".join(d["name"] for d in directors)
    if tags := [t["name"] for t in video.get("categories") or []] + SITE_TAGS.get(
        site, []
    ):
        scene["tags"] = [{"name": t} for t in tags]
    if image:
        scene["image"] = image
    if duration := to_seconds(video.get("runLength")):
        scene["duration"] = duration
    return scene


def scene_from_url(url: str, scene_id: str | None = None) -> ScrapedScene | None:
    if not (parsed := site_and_slug(url)):
        log.error(f"Not a Vixen Media Group scene URL: {url}")
        return None
    site, slug = parsed
    if not (
        video := dig(
            call_api(site, VIDEO_QUERY, {"videoSlug": slug}, url), "findOneVideo"
        )
    ):
        log.error(f"No scene found for {url}")
        return None
    image = largest_image(dig(video, "images", "poster"))
    scene = to_scene(video, site, image and upgrade_image(image))
    if scene_id and config.scrape_markers:
        add_markers(
            scene_id, dig(video, "chapters", "video") or [], scene.get("duration")
        )
    return scene


def sites_to_search(query: str) -> tuple[list[str], str]:
    "A site named in the query limits the search to it, unless the query starts with $"
    if query.startswith("$"):
        return list(SITES), query[1:].strip()
    # Longest first so 'Tushy Raw' isn't taken for 'Tushy'
    for site, name in sorted(SITES.items(), key=lambda s: len(s[0]), reverse=True):
        if match := re.search(rf"\b(?:{site}|{name})\b", query, re.IGNORECASE):
            return [site], (query[: match.start()] + query[match.end() :]).strip()
    return list(SITES), query.strip()


def scene_search(query: str) -> list[ScrapedScene]:
    sites, query = sites_to_search(query)
    log.debug(f"Searching {', '.join(sites)} for '{query}'")
    return [
        to_scene(node, site, largest_image(dig(node, "images", "listing")))
        for site in sites
        for edge in dig(
            call_api(
                site,
                SEARCH_QUERY,
                {"query": query, "first": 6},
                f"https://www.{site}.com",
            ),
            "searchVideos",
            "edges",
            default=[],
        )
        if (node := edge.get("node")) and node.get("slug")
    ]


def scene_from_fragment(fragment: dict[str, Any]) -> ScrapedScene | None:
    for url in fragment.get("urls") or []:
        if is_own_url(url) and (scene := scene_from_url(url, fragment.get("id"))):
            return scene
    if not (title := fragment.get("title")):
        log.error("Need a scene URL or title to scrape this fragment")
        return None

    def similarity(scene: ScrapedScene) -> float:
        return difflib.SequenceMatcher(
            None, title.lower(), scene["title"].lower()
        ).ratio()

    best = max(scene_search(f"${title}"), key=similarity, default=None)
    if best and similarity(best) >= config.minimum_similarity:
        return scene_from_url(best["urls"][0], fragment.get("id"))
    log.error(f"No scene matching '{title}'")
    return None


def add_markers(scene_id: str, chapters: list[dict[str, Any]], duration: int | None):
    stash = callGraphQL(
        "query FindScene($id: ID!) { findScene(id: $id) { files { duration } scene_markers { seconds } } allTags { id name aliases } }",
        {"id": scene_id},
    )
    if not stash or not (stash_scene := stash["findScene"]):
        log.error("Failed to get the scene from Stash, not adding markers")
        return
    file_duration = dig(stash_scene, "files", 0, "duration")
    if (
        duration
        and file_duration
        and abs(file_duration - duration) > config.marker_duration_tolerance
    ):
        log.info(
            "The file is a different length than the official scene, not adding markers"
        )
        return
    tags = {
        name.lower(): tag["id"]
        for tag in stash["allTags"]
        for name in [tag["name"], *tag["aliases"]]
    }
    existing = {m["seconds"] for m in stash_scene["scene_markers"]}
    for chapter in chapters:
        if chapter["seconds"] in existing:
            continue
        if not (tag_id := tags.get(chapter["title"].lower())):
            log.debug(f"No tag named '{chapter['title']}', skipping its marker")
            continue
        callGraphQL(
            "mutation SceneMarkerCreate($input: SceneMarkerCreateInput!) { sceneMarkerCreate(input: $input) { id } }",
            {
                "input": {
                    "scene_id": scene_id,
                    "title": chapter["title"],
                    "seconds": chapter["seconds"],
                    "primary_tag_id": tag_id,
                }
            },
        )


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
