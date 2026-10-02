import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

from py_common import log
from py_common.config import get_config
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer, ScrapedScene
from py_common.util import scraper_args

ensure_requirements("requests", "lxml")

import requests  # noqa: E402
from lxml import html  # noqa: E402

config = get_config(
    default="""
# javlibrary sits behind a Cloudflare challenge that only a real browser can solve:
# run FlareSolverr (https://github.com/FlareSolverr/FlareSolverr) and point this at it
flaresolverr_url = http://localhost:8191/v1
# Site language: en, ja, tw or cn
language = ja
"""
)

BASE = "https://www.javlibrary.com"
LANGUAGE = config.language
# Cloudflare's clearance cookie only works together with the user agent that earned it
CLEARANCE_FILE = Path(__file__).with_name("clearance.json")

IGNORE_TAGS = {
    "Features Actress",
    "Hi-Def",
    "Beautiful Girl",
    "Blu-ray",
    "Featured Actress",
    "VR Exclusive",
    "MOODYZ SALE 4",
}
# The English site lists 微乳 as "Tits"
OBFUSCATED_TAGS = {"Tits": "Small Tits"}
# Latin names are listed family name first: Aoi Tsukasa -> Tsukasa Aoi
IGNORE_NAME_REVERSE = {"Lily Heart"}

# Blu-ray editions duplicate the DVD release under the same code
BLU_RAY = re.compile(r"\(Blu-ray|（ブルーレイ")
CODE = re.compile(r"(?<![a-z])([a-z]{2,8})-?(\d{2,5})(?!\d)", re.IGNORECASE)

session = requests.Session()


def use_clearance(clearance: dict[str, Any]) -> None:
    session.headers["User-Agent"] = clearance["userAgent"]
    session.cookies.update(clearance["cookies"])


def solve_challenge(url: str) -> None:
    log.info(
        f"Solving Cloudflare's challenge with FlareSolverr ({config.flaresolverr_url})"
    )
    try:
        res = requests.post(
            config.flaresolverr_url,
            json={"cmd": "request.get", "url": url, "maxTimeout": 60000},
            timeout=90,
        ).json()
    except requests.RequestException as e:
        log.error(
            f"FlareSolverr is unreachable at {config.flaresolverr_url}: javlibrary"
            " can't be scraped without it, see JavLibrary_python/config.ini"
        )
        log.debug(str(e))
        sys.exit(1)
    if res.get("status") != "ok":
        log.error(f"FlareSolverr failed to solve the challenge: {res.get('message')}")
        sys.exit(1)

    solution = res["solution"]
    clearance = {
        "userAgent": solution["userAgent"],
        "cookies": {c["name"]: c["value"] for c in solution["cookies"]},
    }
    CLEARANCE_FILE.write_text(json.dumps(clearance), encoding="utf-8")
    use_clearance(clearance)


def fetch(url: str) -> tuple[html.HtmlElement, str] | None:
    url = re.sub(r"^https?://(www\.)?javlib(rary)?\.com", BASE, url)
    for attempt in range(2):
        res = session.get(url, timeout=20)
        if res.status_code == 403 and "Just a moment" in res.text and not attempt:
            solve_challenge(url)
            continue
        if "maintenance" in res.url:
            log.error("javlibrary is down for maintenance")
            return None
        if not res.ok:
            log.error(f"Failed to fetch {url}: {res.status_code} {res.reason}")
            return None
        return html.fromstring(res.content), res.url
    log.error(f"Still challenged by Cloudflare after solving it for {url}")
    return None


def localized(url: str, language: str = LANGUAGE) -> str:
    return re.sub(r"/(en|ja|tw|cn)/", f"/{language}/", url)


def texts(tree: html.HtmlElement, xpath: str) -> list[str]:
    return [
        value.strip()
        for node in tree.xpath(xpath)
        if (value := node if isinstance(node, str) else node.text_content())
        and value.strip()
    ]


def text(tree: html.HtmlElement, xpath: str) -> str | None:
    return next(iter(texts(tree, xpath)), None)


def performer_name(name: str) -> str:
    if name in IGNORE_NAME_REVERSE:
        return name
    return re.sub(r"^([a-zA-Z]+) ([a-zA-Z]+)$", r"\2 \1", name)


def japanese_names(page_url: str) -> dict[str, str]:
    "Maps each cast member's link to their name on the Japanese version of the page"
    if not (page := fetch(localized(page_url, "ja"))):
        return {}
    tree, _ = page
    cast = tree.xpath('//div[@id="video_cast"]//span[@class="cast"]/span/a')
    return {a.get("href"): a.text_content().strip() for a in cast}


def performers(tree: html.HtmlElement, page_url: str) -> list[ScrapedPerformer]:
    cast = tree.xpath('//div[@id="video_cast"]//span[@class="cast"]/span/a')
    aliases = japanese_names(page_url) if cast and LANGUAGE != "ja" else {}
    result: list[ScrapedPerformer] = []
    for a in cast:
        href, name = a.get("href"), performer_name(a.text_content().strip())
        performer: ScrapedPerformer = {"name": name, "urls": [urljoin(page_url, href)]}
        if (alias := aliases.get(href)) and alias != name:
            performer["aliases"] = alias
        result.append(performer)
    return result


def to_scene(tree: html.HtmlElement, page_url: str) -> ScrapedScene:
    scene: ScrapedScene = {}
    if title := text(tree, '//div[@id="video_title"]/h3/a'):
        scene["title"] = title
    if code := text(tree, '//div[@id="video_id"]//td[@class="text"]'):
        scene["code"] = code
    if date := text(tree, '//div[@id="video_date"]//td[@class="text"]'):
        scene["date"] = date
    if minutes := text(tree, '//div[@id="video_length"]//span[@class="text"]'):
        scene["duration"] = int(minutes) * 60
    if director := text(tree, '//div[@id="video_director"]//span[@class="director"]/a'):
        scene["director"] = director
    if url := text(tree, '//meta[@property="og:url"]/@content'):
        scene["urls"] = [urljoin(page_url, url)]
    if studio := text(tree, '//div[@id="video_maker"]//span[@class="maker"]/a'):
        scene["studio"] = {"name": studio}
    if tags := [
        {"name": OBFUSCATED_TAGS.get(tag, tag)}
        for tag in texts(tree, '//div[@id="video_genres"]//span[@class="genre"]/a')
        if tag not in IGNORE_TAGS
    ]:
        scene["tags"] = tags
    if cast := performers(tree, page_url):
        scene["performers"] = cast
    if (image := text(tree, '//div[@id="video_jacket"]/img/@src')) and not re.search(
        r"now_printing|noimage", image
    ):
        scene["image"] = urljoin(page_url, image)
    return scene


def scene_from_url(url: str) -> ScrapedScene | None:
    if page := fetch(localized(url)):
        return to_scene(*page)
    return None


def search(
    keyword: str,
) -> tuple[list[ScrapedScene], tuple[html.HtmlElement, str] | None]:
    """
    Returns the search results, or the scene page itself when javlibrary
    redirects a search with a single result straight to it
    """
    if not (
        page := fetch(f"{BASE}/{LANGUAGE}/vl_searchbyid.php?keyword={quote(keyword)}")
    ):
        return [], None
    tree, page_url = page
    if "vl_searchbyid" not in page_url:
        return [], page

    results: list[ScrapedScene] = []
    for video in tree.xpath('//div[@class="videos"]/div[@class="video"]'):
        link = video.find("a")
        if link is None or BLU_RAY.search(link.get("title", "")):
            continue
        result: ScrapedScene = {
            "title": link.get("title"),
            "urls": [urljoin(page_url, link.get("href"))],
        }
        if code := text(video, './/div[@class="id"]'):
            result["code"] = code
        if image := text(video, ".//img/@src"):
            result["image"] = urljoin(page_url, image)
        results.append(result)
    return results, None


def scene_search(name: str) -> list[ScrapedScene]:
    results, scene_page = search(name)
    if scene_page:
        return [to_scene(*scene_page)]
    return results


def scene_from_code(name: str) -> ScrapedScene | None:
    if not (match := CODE.search(name)):
        log.error(f"No JAV code found in '{name}'")
        return None
    code = f"{match[1]}-{match[2]}".upper()
    results, scene_page = search(code)
    if scene_page:
        return to_scene(*scene_page)
    if not (best := next((r for r in results if r.get("code") == code), None)):
        log.error(f"No javlibrary result for {code}")
        return None
    return scene_from_url(best["urls"][0])


def scene_from_fragment(args: dict[str, Any]) -> ScrapedScene | None:
    urls = [args.get("url"), *(args.get("urls") or [])]
    if url := next(
        (u for u in urls if u and re.search(r"javlib(rary)?\.com", u)), None
    ):
        return scene_from_url(url)
    names = [Path(f["path"]).stem for f in args.get("files") or []]
    names += [args.get("code") or "", args.get("title") or ""]
    if name := next((n for n in names if CODE.search(n)), None):
        return scene_from_code(name)
    log.error(f"No javlibrary URL or JAV code in {names}")
    return None


if __name__ == "__main__":
    op, args = scraper_args()
    if CLEARANCE_FILE.exists():
        use_clearance(json.loads(CLEARANCE_FILE.read_text(encoding="utf-8")))

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
