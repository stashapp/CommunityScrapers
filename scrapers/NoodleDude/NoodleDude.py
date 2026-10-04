import json
import re
import sys
from datetime import UTC, datetime
from typing import Any

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag
from py_common.util import scraper_args

ensure_requirements("requests", "lxml")
import requests  # noqa: E402
from lxml import html  # noqa: E402

BASE_URL = "https://www.noodledude.io"
STUDIO: ScrapedStudio = {"name": "NoodleDudePMV"}

session = requests.Session()


def fetch(url: str) -> html.HtmlElement | None:
    try:
        response = session.get(url, timeout=(3, 10))
    except requests.RequestException as e:
        log.error(f"Failed to fetch '{url}': {e}")
        return None
    if response.status_code != 200:
        log.error(f"Fetching '{url}' returned status {response.status_code}")
        return None
    return html.fromstring(response.content)


def decode_prop(value: Any) -> Any:
    "Astro serializes island props as [type, value] pairs: 0 is a plain value, 1 an array"
    match value:
        case [0, dict() as obj]:
            return {k: decode_prop(v) for k, v in obj.items()}
        case [0, plain]:
            return plain
        case [1, list() as items]:
            return [decode_prop(item) for item in items]
    return value


def island_props(tree: html.HtmlElement, component: str) -> dict[str, Any]:
    for island in tree.xpath("//astro-island[@props]"):
        if f"/{component}." in island.get("component-url", ""):
            return {
                k: decode_prop(v) for k, v in json.loads(island.get("props")).items()
            }
    return {}


def text_from_html(fragment: str) -> str:
    root = html.fromstring(f"<div>{fragment}</div>")
    if blocks := root.xpath("./*"):
        text = "\n\n".join(block.text_content().strip() for block in blocks)
    else:
        text = root.text_content()
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def to_scraped_performer(performer: dict[str, Any]) -> ScrapedPerformer:
    scraped: ScrapedPerformer = {
        "name": performer["name"],
        "urls": [
            f"{BASE_URL}/creators/{performer['slug']}",
            *performer.get("social_urls", []),
        ],
    }
    if aliases := performer.get("aliases"):
        scraped["aliases"] = ", ".join(aliases)
    if image := performer.get("image"):
        scraped["images"] = [image]
    if birthdate := performer.get("date_of_birth"):
        scraped["birthdate"] = birthdate
    return scraped


def scene_details(video: dict[str, Any]) -> str:
    parts = []
    if (description := video.get("description")) and (
        text := text_from_html(description)
    ):
        parts.append(text)
    if songs := video.get("songs"):
        parts.append(
            "Songs:\n" + "\n".join(f"{s['artist']} - {s['name']}" for s in songs)
        )
    return "\n\n".join(parts)


def to_scraped_scene(video: dict[str, Any], title: str | None) -> ScrapedScene:
    scene: ScrapedScene = {"studio": STUDIO}
    if title := title or video.get("name"):
        scene["title"] = title
    if released := video.get("release_date"):
        # milliseconds since the epoch
        scene["date"] = datetime.fromtimestamp(released / 1000, tz=UTC).strftime(
            "%Y-%m-%d"
        )
    if details := scene_details(video):
        scene["details"] = details
    if image := video.get("thumbnail"):
        scene["image"] = image
    if (length := video.get("length")) and length >= 10:
        scene["duration"] = length
    if tags := video.get("tags"):
        scene["tags"] = [ScrapedTag(name=t["name"]) for t in tags]
    if performers := video.get("performers"):
        scene["performers"] = [to_scraped_performer(p) for p in performers]
    return scene


def scene_from_url(url: str) -> ScrapedScene | None:
    if (tree := fetch(url)) is None:
        return None
    if not (video := island_props(tree, "Player").get("initialVideo")):
        log.error(f"No video data found on '{url}'")
        return None
    # "Let Me Keep My Socks On - A Socks & Skirts PMV | NoodleDude PMVs"
    title = next(
        (
            t.rsplit(" | ", 1)[0]
            for t in tree.xpath("//meta[@property='og:title']/@content")
        ),
        None,
    )
    return to_scraped_scene(video, title)


def performer_from_url(url: str) -> ScrapedPerformer | None:
    if (tree := fetch(url)) is None:
        return None
    if not (info := tree.xpath("//div[contains(@class, 'performer-main-info')]")):
        log.error(f"No performer found on '{url}'")
        return None
    info = info[0]
    performer: ScrapedPerformer = {
        "name": info.xpath("string(h1)").strip(),
        "urls": [url, *info.xpath("div[@class='performer-links']/a/@href")],
    }
    # "Aliases: Lili • hot404found", the label and separators are child spans
    if aliases := [
        a.strip()
        for a in info.xpath("span[contains(@class, 'fs-s')]/text()")
        if a.strip()
    ]:
        performer["aliases"] = ", ".join(aliases)
    if birthdate := info.xpath("span/span[@title]/@title"):
        performer["birthdate"] = birthdate[0]
    if details := tree.xpath(
        "string(//div[contains(@class, 'performer-description')]/p)"
    ).strip():
        performer["details"] = details
    if images := tree.xpath("//img[contains(@class, 'performer-image')]/@src"):
        performer["images"] = images
    return performer


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
