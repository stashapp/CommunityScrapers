import html
import json
import re
import sys
import time
from typing import Any

import requests

from py_common import log
from py_common.types import ScrapedPerformer, ScrapedScene
from py_common.util import scraper_args

BASE_URL = "https://joeschmoevideos.com"
STUDIO = {"name": "Joe Schmoe Videos", "urls": [BASE_URL]}

# The site does not publish a director field, but IAFD credits "Joe Schmoe" as
# director on every one of this studio's releases, so it is set unconditionally.
DIRECTOR = "Joe Schmoe"

# The site is a Next.js app: every page embeds the data it renders as JSON.
# Parsing that is far more reliable than scraping the DOM. The /_next/data/
# endpoint is deliberately avoided because its URL contains a build id that
# changes on every deploy.
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
    re.DOTALL,
)


def _next_data(path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    url = f"{BASE_URL}{path}"
    try:
        response = requests.get(
            url,
            params=params,
            headers={"User-Agent": "stash-scraper/1.0"},
            timeout=(5, 15),
        )
        response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None

    if not (match := NEXT_DATA_RE.search(response.text)):
        log.error(f"No __NEXT_DATA__ found on {url}")
        return None

    try:
        return json.loads(match.group(1))["props"]["pageProps"]
    except (json.JSONDecodeError, KeyError) as e:
        log.error(f"Could not parse page data from {url}: {e}")
        return None


def _text(value: str | None) -> str | None:
    """Model bios arrive HTML-escaped (&#039;, &quot;)."""
    return html.unescape(value) if value else value


def _absolute(url: str | None) -> str | None:
    """Image URLs come back protocol-relative (//cdn.example/...)."""
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"{BASE_URL}{url}"
    return url


def _image(scene: dict[str, Any]) -> str | None:
    if thumb := scene.get("thumbnail"):
        return _absolute(thumb)
    # Fall back to the predictable CDN path built from the scene code
    cdn, code = scene.get("cdn_thumbs_url"), scene.get("scene_code")
    if cdn and code:
        return _absolute(f"{cdn}/jsp/largethumbs/{code}.jpg")
    for extra in scene.get("extra_thumbnails") or []:
        if extra:
            return _absolute(extra)
    return None


def _date(scene: dict[str, Any]) -> str | None:
    # e.g. "2025/05/27 00:00:00"
    if not (raw := scene.get("publish_date")):
        return None
    try:
        return time.strftime("%Y-%m-%d", time.strptime(raw[:10], "%Y/%m/%d"))
    except ValueError:
        log.debug(f"Unrecognised publish_date: {raw}")
        return None


def to_scraped_scene(scene: dict[str, Any]) -> ScrapedScene:
    scraped: ScrapedScene = {"studio": STUDIO, "director": DIRECTOR}

    if title := scene.get("title"):
        scraped["title"] = _text(title)
    if slug := scene.get("slug"):
        scraped["urls"] = [f"{BASE_URL}/scenes/{slug}"]
    if date := _date(scene):
        scraped["date"] = date
    if description := scene.get("description"):
        scraped["details"] = _text(description)
    if code := scene.get("scene_code"):
        scraped["code"] = code
    if image := _image(scene):
        scraped["image"] = image
    # models_slugs is richer than models, but either may be present
    if models := scene.get("models_slugs"):
        scraped["performers"] = [
            {"name": _text(m["name"]), "urls": [f"{BASE_URL}/models/{m['slug']}"]}
            for m in models
            if m.get("name")
        ]
    elif models := scene.get("models"):
        scraped["performers"] = [{"name": _text(name)} for name in models if name]
    if tags := scene.get("tags"):
        scraped["tags"] = [{"name": tag} for tag in tags if tag]

    return scraped


def scene_by_url(url: str) -> ScrapedScene | None:
    if not (match := re.search(r"/scenes/([^/?#]+)", url)):
        log.error(f"Not a Joe Schmoe Videos scene URL: {url}")
        return None

    if not (props := _next_data(f"/scenes/{match.group(1)}")):
        return None
    if not (scene := props.get("content")):
        log.error(f"No scene data on {url}")
        return None

    return to_scraped_scene(scene)


def scene_by_name(name: str) -> list[ScrapedScene]:
    if not (props := _next_data("/", {"search": name})):
        return []

    results = (props.get("contents") or {}).get("data") or []
    if not results:
        log.debug(f"No results for '{name}'")
    return [to_scraped_scene(scene) for scene in results]


def to_scraped_performer(model: dict[str, Any]) -> ScrapedPerformer:
    performer: ScrapedPerformer = {"gender": "MALE"}

    if name := model.get("name"):
        performer["name"] = _text(name)
    if slug := model.get("slug"):
        performer["urls"] = [f"{BASE_URL}/models/{slug}"]
    # The bio field is capitalised in the site's payload
    if details := model.get("Bio") or model.get("details"):
        performer["details"] = _text(details)
    if image := _absolute(model.get("thumbnail")):
        performer["images"] = [image]

    return performer


def performer_by_url(url: str) -> ScrapedPerformer | None:
    if not (match := re.search(r"/models/([^/?#]+)", url)):
        log.error(f"Not a Joe Schmoe Videos model URL: {url}")
        return None

    if not (props := _next_data(f"/models/{match.group(1)}")):
        return None
    if not (model := props.get("model")):
        log.error(f"No model data on {url}")
        return None

    return to_scraped_performer(model)


def performer_by_name(name: str) -> list[ScrapedPerformer]:
    if not (props := _next_data("/models", {"search": name})):
        return []

    results = (props.get("models") or {}).get("data") or []
    if not results:
        log.debug(f"No performers matching '{name}'")
    return [to_scraped_performer(model) for model in results]


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_by_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_by_name(name)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            if url := args.get("url"):
                result = scene_by_url(url)
            elif title := args.get("title"):
                matches = scene_by_name(title)
                result = matches[0] if matches else None
        case "performer-by-url", {"url": url} if url:
            result = performer_by_url(url)
        case "performer-by-name", {"name": name} if name:
            result = performer_by_name(name)
        case "performer-by-fragment", args:
            if url := args.get("url"):
                result = performer_by_url(url)
            elif name := args.get("name"):
                matches = performer_by_name(name)
                result = matches[0] if matches else None
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
