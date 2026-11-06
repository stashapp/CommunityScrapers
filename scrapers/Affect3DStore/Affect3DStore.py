import base64
import json
import sys
from typing import Any
from urllib.parse import quote_plus

from py_common import log
from py_common.deps import ensure_requirements
from py_common.proxy import stash_requests
from py_common.types import ScrapedScene, ScrapedStudio
from py_common.util import is_own_url, scraper_args

ensure_requirements("lxml")
from lxml import html  # noqa: E402

STUDIO_MAPPER = {
    "Miro Affect3D": "Miro",
}

ATTRIBUTES = '//div[contains(@class, "info-details-xl")]//table[contains(@class, "additional-attributes")]'


def fetch(url: str) -> Any | None:
    # Cloudflare blocks plain requests, py_common.proxy falls back to FlareSolverr
    try:
        response = stash_requests.get(url)
    # py_common.proxy raises a bare Exception once every backend has failed
    except Exception as e:  # noqa: BLE001
        log.error(f"Failed to fetch {url}: {e}")
        return None
    if response.status_code != 200:
        log.error(f"HTTP {response.status_code} for {url}")
        return None
    return response


def fetch_tree(url: str) -> html.HtmlElement | None:
    if not (response := fetch(url)):
        return None
    return html.document_fromstring(response.text)


def image_data(url: str) -> str | None:
    # Stash can't get past Cloudflare to download the image itself, but the
    # clearance py_common.proxy got for the page works for the image too
    if not (response := fetch(url)):
        return None
    mime = response.headers.get("Content-Type", "").split(";")[0]
    if not mime.startswith("image/"):
        log.warning(f"{url} is not an image ({mime})")
        return None
    return f"data:{mime};base64,{base64.b64encode(response.content).decode()}"


def studio(artist: str) -> ScrapedStudio:
    return {"name": STUDIO_MAPPER.get(artist, artist)}


def scene_from_url(url: str) -> ScrapedScene | None:
    if (tree := fetch_tree(url)) is None:
        return None
    scene: ScrapedScene = {"urls": [url]}
    if title := tree.xpath("//h1/span"):
        scene["title"] = title[0].text_content()
    if year := tree.xpath(f'{ATTRIBUTES}//td[@data-th="Year Released"]'):
        scene["date"] = year[0].text_content()
    if description := tree.xpath(
        '//div[contains(@class, "info-details-xl")]//div[contains(@class, "description")]'
    ):
        # Older pages split the description into paragraphs, newer ones don't
        paragraphs = description[0].xpath(".//p") or description[:1]
        if details := "\n\n".join(p.text_content().strip() for p in paragraphs).strip():
            scene["details"] = details
    if artist := tree.xpath(
        '//div[@class="box-inner1"]//span[@class="artist_name_m"]//a/text()'
    ):
        scene["studio"] = studio(artist[0])
    if tags := tree.xpath(f'{ATTRIBUTES}//td[not(@data-th="Artist/Circle")]/a/text()'):
        scene["tags"] = [{"name": t.strip()} for t in tags]
    if (image := tree.xpath('//img[@alt="main product photo"]/@src')) and (
        data := image_data(image[0])
    ):
        scene["image"] = data
    return scene


def scene_search(name: str) -> list[ScrapedScene]:
    url = f"https://affect3dstore.com/catalogsearch/result/?q={quote_plus(name)}"
    if (tree := fetch_tree(url)) is None:
        return []
    results: list[ScrapedScene] = []
    for item in tree.xpath(
        '//div[contains(@class, "products-grid") and contains(@class, "wrapper")]//li[contains(@class, "product-item")]'
    ):
        scene: ScrapedScene = {}
        if link := item.xpath('.//a[contains(@class, "product-item-link")]'):
            scene["urls"] = [link[0].get("href")]
            if title := link[0].text_content().strip():
                scene["title"] = title
        # Later results' images are lazy-loaded and may not resolve
        if image := item.xpath(
            './/a[contains(@class, "product-item-photo")]//img/@src'
        ):
            scene["image"] = image[0]
        if artist := item.xpath('.//span[contains(@class, "artist_name_m")]/a/text()'):
            scene["studio"] = studio(artist[0])
        results.append(scene)
    return results


def scene_from_fragment(fragment: dict) -> ScrapedScene | None:
    for url in fragment.get("urls") or []:
        if is_own_url(url) and (scene := scene_from_url(url)):
            return scene
    if (title := fragment.get("title")) and (results := scene_search(title)):
        return results[0]
    return None


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
