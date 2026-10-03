import json
import re
import sys
from pathlib import PurePath
from urllib.parse import urljoin, urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import SceneSearchResult, ScrapedScene, ScrapedStudio
from py_common.util import scraper_args

ensure_requirements("requests", "lxml")
import requests  # noqa: E402
from lxml import html  # noqa: E402

BASE_URL = "https://www.milky-cat.com/movie/indexe.php"
STUDIO: ScrapedStudio = {"name": "Milky-Cat"}

session = requests.Session()


def fetch(url: str, **params) -> html.HtmlElement | None:
    try:
        res = session.get(url, params=params, timeout=15)
        res.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None
    return html.fromstring(res.content, base_url=res.url)


def text_with_breaks(el: html.HtmlElement) -> str:
    # <br> is the only line break the browser renders; source newlines are just indentation
    for br in el.iter("br"):
        br.tail = "\ue000" + (br.tail or "")
    text = re.sub(r"\s+", " ", el.text_content())
    return re.sub(" ?\ue000 ?", "\n", text).strip()


def product_table(tree: html.HtmlElement) -> dict[str, str]:
    return {
        label.text_content().strip().rstrip("："): value.text_content().strip()
        for row in tree.xpath("//div[@class='product_2']//tr")
        if len(cells := row.xpath("./td")) == 2
        for label, value in [cells]
    }


def cover(tree: html.HtmlElement, movie_id: str) -> str | None:
    # The linked full-size jacket is missing on newer titles and misnamed on some
    # older ones (dmc36 links dmcr36f.jpg, but the file is dmc36f.jpg)
    candidates = [
        *tree.xpath("//a[@class='jacket']/@href"),
        urljoin(BASE_URL, f"parts/package/{movie_id}f.jpg"),
        *tree.xpath("//a[@class='jacket']/img/@src"),
    ]
    return next(
        (url for url in dict.fromkeys(candidates) if session.head(url, timeout=15).ok),
        None,
    )


def scene_from_url(url: str) -> ScrapedScene | None:
    if not (movie_id := urlparse(url).query):
        log.error(f"No movie id in {url}")
        return None
    # Japanese and Chinese pages use translated table labels
    canonical = f"{BASE_URL}?{movie_id}"
    if (tree := fetch(canonical)) is None:
        return None
    if not (title := tree.xpath("string(//p[@class='title_p'])").strip()):
        log.error(f"No title found at {canonical}")
        return None

    scene: ScrapedScene = {
        "title": title,
        "urls": [canonical],
        "studio": STUDIO,
    }
    table = product_table(tree)
    if code := table.get("title No"):
        scene["code"] = code
    if (date := table.get("update")) and (
        m := re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", date)
    ):
        scene["date"] = f"{m[1]}-{int(m[2]):02}-{int(m[3]):02}"
    if (length := table.get("total time")) and (m := re.match(r"(\d+)\s*min", length)):
        scene["duration"] = int(m[1]) * 60
    paragraphs = tree.xpath(
        "//p[contains(@class, 'main_p')]"
        "[not(contains(@class, 'd_cn') or contains(@class, 'd_fr'))]"
    )
    if details := "\n\n".join(filter(None, map(text_with_breaks, paragraphs))):
        scene["details"] = details
    if image := cover(tree, movie_id):
        scene["image"] = image
    return scene


def search_result(link: html.HtmlElement) -> SceneSearchResult | None:
    if not (names := link.xpath("./p[@class='title_name']")):
        return None
    result: SceneSearchResult = {
        "title": text_with_breaks(names[0]).replace("\n", " "),
        "url": urljoin(BASE_URL, link.get("href")),
        "studio": STUDIO,
    }
    if image := link.xpath("string(./img/@src)"):
        result["image"] = image
    return result


def search(query: str) -> list[SceneSearchResult]:
    if (tree := fetch(BASE_URL, q=query)) is None:
        return []
    links = tree.xpath("//div[@class='MCtitle']/a[@class='title_link']")
    return list(filter(None, map(search_result, links)))


def code_in(text: str) -> str | None:
    if m := re.search(
        r"(?<![a-z])([a-z]{2,4})[-_ ]?(\d{2,4})(?!\d)", text, re.IGNORECASE
    ):
        return f"{m[1]}-{m[2]}".upper()
    return None


def scene_from_fragment(fragment: dict) -> ScrapedScene | None:
    if url := next(iter(fragment.get("urls") or []), None) or fragment.get("url"):
        return scene_from_url(url)

    sources = [
        fragment.get("title") or "",
        *(PurePath(f["path"]).stem for f in fragment.get("files") or []),
    ]
    if not (code := next(filter(None, map(code_in, sources)), None)):
        log.info(f"No title code in {sources}")
        return None
    match search(code):
        case [result]:
            return scene_from_url(result["url"])
        case results:
            log.info(f"{len(results)} search results for {code}, expected exactly one")
            return None


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name} if name:
            result = search(name)
        case "scene-by-query-fragment", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-fragment" | "scene-by-query-fragment", _:
            result = scene_from_fragment(args)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
