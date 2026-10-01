import json
import re
import sys
from typing import Any
from urllib.parse import unquote, urlparse

import requests

from py_common import log
from py_common.types import ScrapedPerformer, ScrapedScene
from py_common.util import dig, scraper_args

FIT18 = "https://fit18.com"
THICC18 = "https://thicc18.com"
THICC18_API = "https://thicc18.team18media.app/graphql"
THICC18_API_KEY = "0e36c7e9-8cb7-4fa1-9454-adbc2bad15f0"

THICC18_VIDEO_QUERY = """
query FindVideo($videoId: ID!) {
    video {
        find(input: { videoId: $videoId }) {
            result {
                title
                duration
                description { short long }
                talent { talent { name } }
            }
        }
    }
}
"""


def fit18_api(endpoint: str, options: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        response = requests.get(
            f"{FIT18}/api/{endpoint}",
            params={"options": json.dumps(options)},
            headers={"User-Agent": "stash-scraper/1.0"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Fit18 API request for {endpoint} failed: {e}")
        return []
    return dig(response.json(), "data", "data") or []


def fit18_by_slug(endpoint: str, slug: str) -> dict[str, Any] | None:
    if hits := fit18_api(endpoint, {"filters": {"slug": {"$eq": slug}}}):
        return hits[0]
    log.error(f"No Fit18 {endpoint} found for slug '{slug}'")
    return None


def largest_jpeg(media: dict[str, Any] | None) -> str | None:
    if sizes := dig(media or {}, "signedUrls", "jpeg"):
        return max(sizes, key=lambda s: s["width"])["url"]
    return None


def rich_text(blocks: list[dict[str, Any]] | None) -> str:
    return "\n\n".join(
        "".join(child.get("text", "") for child in block.get("children", []))
        for block in blocks or []
    )


def fit18_scene(slug: str) -> ScrapedScene | None:
    if not (video := fit18_by_slug("videos", slug)):
        return None

    scene: ScrapedScene = {
        "title": video["title"],
        "urls": [f"{FIT18}/video/{video['slug']}"],
        "studio": {"name": "Fit18", "urls": [FIT18]},
    }
    if release := video.get("release"):
        scene["date"] = release[:10]
    if details := rich_text(video.get("description")):
        scene["details"] = details
    if length := video.get("length"):
        scene["duration"] = length
    if image := largest_jpeg(video.get("poster")):
        scene["image"] = image
    if tags := video.get("tags"):
        scene["tags"] = [{"name": t["name"]} for t in tags]
    if models := video.get("models"):
        # scene hits carry model ids and names, but not the slugs their URLs need
        ids = [m["id"] for m in models]
        slugs = {
            m["id"]: m["slug"]
            for m in fit18_api("models", {"filters": {"id": {"$in": ids}}})
        }
        scene["performers"] = [
            scene_performer(m["name"], slugs.get(m["id"])) for m in models
        ]
    return scene


def scene_performer(name: str, slug: str | None) -> ScrapedPerformer:
    performer: ScrapedPerformer = {"name": name, "gender": "FEMALE"}
    if slug:
        performer["urls"] = [f"{FIT18}/model/{slug}"]
    return performer


def fit18_performer(slug: str) -> ScrapedPerformer | None:
    if not (model := fit18_by_slug("models", slug)):
        return None

    performer: ScrapedPerformer = {
        "name": model["name"],
        "gender": "FEMALE",
        "urls": [f"{FIT18}/model/{model['slug']}"],
    }
    if aliases := model.get("aliases"):
        performer["aliases"] = ", ".join(aliases)
    # a few models only have their height in the stats blurb
    if height := model.get("height") or (
        (m := re.search(r"Height:\s*(\d+)", rich_text(model.get("description"))))
        and m.group(1)
    ):
        performer["height"] = str(height)
    if weight := model.get("weight"):
        performer["weight"] = str(weight)
    if all(model.get(k) for k in ("cup", "waist", "hips")):
        performer["measurements"] = f"{model['cup']}-{model['waist']}-{model['hips']}"
    if image := largest_jpeg(model.get("portrait")):
        performer["images"] = [image]
    if tags := model.get("tags"):
        performer["tags"] = [{"name": t["name"]} for t in tags]
    return performer


def thicc18_scene(video_id: str, url: str) -> ScrapedScene | None:
    try:
        response = requests.post(
            THICC18_API,
            json={"query": THICC18_VIDEO_QUERY, "variables": {"videoId": video_id}},
            headers={
                "argonath-api-key": THICC18_API_KEY,
                "Origin": THICC18,
                "Referer": THICC18,
                "User-Agent": "stash-scraper/1.0",
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Thicc18 API request failed: {e}")
        return None

    if not (video := dig(response.json(), "data", "video", "find", "result")):
        log.error(f"No Thicc18 video found for '{video_id}'")
        return None

    scene: ScrapedScene = {
        "title": video["title"],
        "urls": [url],
        "studio": {"name": "Thicc18", "urls": [THICC18]},
    }
    if details := dig(video, "description", "long") or dig(
        video, "description", "short"
    ):
        scene["details"] = re.sub(r"^In 60FPS.\s*", "", re.sub(r" +", " ", details))
    if duration := video.get("duration"):
        scene["duration"] = duration
    if talent := video.get("talent"):
        scene["performers"] = [{"name": t["talent"]["name"]} for t in talent]
    return scene


def scene_from_url(url: str) -> ScrapedScene | None:
    parsed = urlparse(url)
    match parsed.hostname, unquote(parsed.path).strip("/").split("/"):
        case host, ["video", slug] if host and host.endswith("fit18.com"):
            return fit18_scene(slug)
        case host, ["videos", video_id] if host and host.endswith("thicc18.com"):
            return thicc18_scene(video_id, url)
    log.error(f"Unsupported URL: {url}")
    return None


def performer_from_url(url: str) -> ScrapedPerformer | None:
    match unquote(urlparse(url).path).strip("/").split("/"):
        case ["model" | "models", slug]:
            return fit18_performer(slug)
    log.error(f"Unsupported URL: {url}")
    return None


if __name__ == "__main__":
    op, args = scraper_args()
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
