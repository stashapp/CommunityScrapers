import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedScene
from py_common.util import scraper_args

ensure_requirements("requests", "lxml")

import requests  # noqa: E402
from lxml import html  # noqa: E402

BASE = "https://ifeelmyself.com/public/main.php"
SEARCH_PAGES = 30

# Artist ID and per-artist video index, as in cover names: /23922/f16642-15vg.jpg
FILE_ID = re.compile(r"(?<![a-z\d])([fm]\d{3,5})-(\d+)", re.IGNORECASE)
COVER = re.compile(r"/(\d+)/([fm]\d+)-\d+", re.IGNORECASE)

session = requests.Session()
session.headers["User-Agent"] = "stash-scraper/1.0"


def fetch(url: str, **params: Any) -> html.HtmlElement | None:
    try:
        res = session.get(url, params=params, timeout=20)
        res.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Request to {url} failed: {e}")
        return None
    # Served as ISO-8859-1, but the bytes are Windows-1252 (and some titles UTF-8)
    return html.fromstring(res.content.decode("cp1252", errors="replace"))


def utf8_as_cp1252(text: str) -> str:
    try:
        return text.encode("cp1252").decode("utf-8")
    except UnicodeError:
        return text


def text(el: html.HtmlElement, xpath: str) -> str | None:
    if (found := el.xpath(xpath)) and (value := found[0].text_content().strip()):
        return value
    return None


def covers(table: html.HtmlElement) -> list[str]:
    return table.xpath(
        './/img[contains(@src, "bcdn.ifeelmyself.com")]/@src | .//video/@poster'
    )


def media_and_artist_id(table: html.HtmlElement) -> tuple[str, str] | None:
    if (cover := covers(table)) and (ids := COVER.search(cover[0])):
        return ids[1], ids[2]
    if player := table.xpath('.//div[starts-with(@id, "player__")]/@id'):
        media_id, artist_id = player[0].removeprefix("player__").split("-", 1)
        return media_id, artist_id
    return None


def to_scene(table: html.HtmlElement) -> ScrapedScene:
    scene: ScrapedScene = {"studio": {"name": "I Feel Myself"}}
    heading = './/*[contains(@class, "entryHeading")]'

    if title := text(table, f"{heading}/a[1]"):
        scene["title"] = utf8_as_cp1252(title)
    if date := text(
        table, './/*[@class="blog-title-right" or @class="entryDatestamp"]'
    ):
        scene["date"] = time.strftime("%Y-%m-%d", time.strptime(date, "%d %b %Y"))
    if details := text(
        table, './/td[@class="blog_wide_new_text" or @class="entryBlurb"]'
    ):
        scene["details"] = utf8_as_cp1252(" ".join(details.split()))
    if tags := table.xpath('.//span[@class="tags-list-item-tag"]/text()'):
        scene["tags"] = [{"name": tag} for tag in tags]

    if cover := covers(table):
        scene["image"] = cover[0]

    ids = media_and_artist_id(table)
    if ids:
        media_id, artist_id = ids
        scene["urls"] = [
            f"{BASE}?page=flash_player&out=bkg&media_id={media_id}&artist_id={artist_id}"
        ]

    if performer := text(table, f"{heading}/a[2]"):
        scene["performers"] = [{"name": performer.replace("_", " ")}]
        if ids:
            scene["performers"][0]["urls"] = [
                f"{BASE}?page=artist_bio&artist_id={ids[1]}"
            ]

    return scene


def scene_from_url(url: str) -> ScrapedScene | None:
    if (page := fetch(url)) is not None and (
        tables := page.xpath('//table[contains(@class, "ppss-scene")]')
    ):
        return to_scene(tables[0])
    log.error(f"No scene found at {url}")
    return None


def scene_from_file_id(artist_id: str, index: str) -> ScrapedScene | None:
    cover = re.compile(rf"/{artist_id}-{index}[a-z]*\.jpg$", re.IGNORECASE)
    for offset in range(0, SEARCH_PAGES * 10, 10):
        page = fetch(
            BASE, page="quick_search", view_by="news", keyword=artist_id, offset=offset
        )
        if page is None or not (
            tables := page.xpath('//table[contains(@class, "ppss-scene")]')
        ):
            break
        for table in tables:
            if any(
                cover.search(src)
                for src in table.xpath(".//img/@src | .//video/@poster")
            ):
                return to_scene(table)
    log.error(f"No scene with cover {artist_id}-{index} among {artist_id}'s videos")
    return None


def scene_from_fragment(args: dict[str, Any]) -> ScrapedScene | None:
    urls = [args.get("url"), *(args.get("urls") or [])]
    if url := next((u for u in urls if u and "page=flash_player" in u), None):
        return scene_from_url(url)

    names = [Path(f["path"]).name for f in args.get("files") or []] + [
        args.get("title") or ""
    ]
    if match := next((m for name in names if (m := FILE_ID.search(name))), None):
        artist_id, index = match.groups()
        log.debug(f"Looking for video {index} by {artist_id}")
        return scene_from_file_id(artist_id.lower(), index)

    log.error(f"No IFM artist ID in {names}; expected a filename like f16642-15_hd.mp4")
    return None


if __name__ == "__main__":
    op, args = scraper_args()
    match op, args:
        case "scene-by-fragment", args:
            result = scene_from_fragment(args)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
