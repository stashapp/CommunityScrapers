import base64
import json
import re
import sys
from datetime import datetime
from typing import Any

from py_common import log
from py_common.config import get_config
from py_common.deps import ensure_requirements
from py_common.proxy import StashRequests
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedTag
from py_common.util import is_own_url, scraper_args

ensure_requirements("lxml")
from lxml import html  # noqa: E402

config = get_config(
    default="""
# Scene pages are members-only: paste the "Cookie:" request header from your
# browser's network tools while logged in, only pcar%5fUmVzdHJpY3RlZA%3d%3d is used
COOKIES =
"""
)

COOKIE_NAME = "pcar%5fUmVzdHJpY3RlZA%3d%3d"

# Performer pages are named after first names only, these were identified by face
PERFORMER_NAMES = {
    # Guys
    "chrism2": "Chris Cock",
    "dick": "Dick James",
    "dirk": "Dirk Huge",
    "donny": "Donny Sins",
    "isiah": "Isiah Maxwell",
    "jason": "Jason Amalfi",
    "john": "John Janiero",
    "lawson": "Lawson Jones",
    "marlon": "Marlon Tesoro",
    "randy": "Randy Rodman",
    "randyd": "Randy Denmark",
    "ray": "Ray Black",
    "rico": "Rico Reyes",
    "rion": "Rion King",
    "robby": "Robby Apples",
    # Girls
    "aja": "Aja Cummings",
    "alanna": "Alana Thomas",
    "alicia": "Alicia Daniels",
    "amanda": "Amanda Ryder",
    "cathy": "Cathy Craving",
    "chanell": "Chanell Heart",
    "darian": "Darians Fire",
    "fallon": "Fallon West",
    "janey": "Janey Web",
    "lily": "Lilly Lixx",
    "lilyf": "Lilly Lit",
    "mia": "Mia Knight",
}

requests = StashRequests()


def cookies() -> dict[str, str] | None:
    for part in str(config.COOKIES or "").split(";"):
        name, _, value = part.partition("=")
        if name.strip() == COOKIE_NAME and (value := value.strip()):
            return {COOKIE_NAME: value}
    log.error(f"Set the {COOKIE_NAME} cookie in CathysCraving's config.ini")
    return None


def fetch(url: str) -> Any | None:
    if not (jar := cookies()):
        return None
    try:
        response = requests.get(url, cookies=jar, timeout=10)
        response.raise_for_status()
    # py_common.proxy raises a bare Exception once every backend has failed
    except Exception as e:  # noqa: BLE001
        log.error(f"Failed to fetch {url}: {e}")
        return None
    return response


def fetch_tree(url: str) -> html.HtmlElement | None:
    if not (response := fetch(url)):
        return None
    tree = html.fromstring(response.content)
    tree.make_links_absolute(base_url=url)
    return tree


def line_text(element: html.HtmlElement) -> str:
    for br in element.xpath(".//br"):
        br.tail = " " + (br.tail or "")
    return " ".join(element.text_content().split())


def multiline_text(element: html.HtmlElement) -> str:
    "Keeps <br> as line breaks, so <br><br> still separates paragraphs"
    # A private-use character marks each <br>: lxml rejects control characters
    for br in element.xpath(".//br"):
        br.tail = "" + (br.tail or "")
    lines = element.text_content().split("")
    return "\n".join(" ".join(line.split()) for line in lines).strip()


def title(tree: html.HtmlElement) -> str | None:
    # The title sits on its own page, shown in an iframe
    frames = (
        src
        for src in tree.xpath("//iframe/@src")
        if re.search(r"/iframe-\d+\.html$", src)
    )
    if not (frame := next(frames, None)) or (frame_tree := fetch_tree(frame)) is None:
        return None
    parts = [
        line_text(span)
        for cls in ("scene", "title")
        for span in frame_tree.xpath(f"(//span[contains(@class, '{cls}')])[1]")
    ]
    return ": ".join(part for part in parts if part) or None


def release_date(tree: html.HtmlElement, url: str) -> str | None:
    # Dates are only listed next to the scene's "View Scene" link on the scene index
    if not (
        index_url := tree.xpath("string(//a[contains(text(), 'SCENE INDEX')]/@href)")
    ):
        return None
    if (index := fetch_tree(index_url)) is None or not (
        entry := index.xpath(
            f"(//a[normalize-space()='View Scene' and @href='{url}']/ancestor::table[1])[1]"
        )
    ):
        log.warning(f"{url} not found on the scene index")
        return None
    for label, parse, show in (
        ("Added -", "%m-%d-%Y", "%Y-%m-%d"),
        # Older scenes only give the month
        ("When -", "%B %Y", "%Y-%m"),
    ):
        if (
            value := entry[0]
            .xpath(f"string(.//span[contains(., '{label}')]/b)")
            .strip()
        ):
            try:
                return datetime.strptime(value, parse).strftime(show)
            except ValueError:
                log.warning(f"Unexpected date '{value}'")
    return None


def details(tree: html.HtmlElement) -> str | None:
    # Picture download links share the class, the description comes first
    if spans := tree.xpath("//span[contains(@class, 'description')]"):
        return multiline_text(spans[0]) or None
    return None


def performer_name(link: html.HtmlElement) -> str:
    name = link.text_content().strip()
    if page := re.search(r"/([a-zA-Z0-9]+)\.html", link.get("href") or ""):
        return PERFORMER_NAMES.get(page.group(1), name)
    return name


def performers(tree: html.HtmlElement) -> list[ScrapedPerformer]:
    links = tree.xpath(
        "//a[contains(@href, '/girls+guys/') and not(contains(@href, '/girls+guys/girls.html'))]"
    )
    return [{"name": name} for link in links if (name := performer_name(link))]


def tags(tree: html.HtmlElement) -> list[ScrapedTag]:
    return [
        {"name": name}
        for link in tree.xpath(
            "//span[contains(@class, 'keywords')]//a[contains(@href, 'categories')]"
        )
        if (name := link.text_content().strip())
    ]


def image(tree: html.HtmlElement) -> str | None:
    # The image needs the member cookie too, so it's passed on as a data URL
    if not (src := tree.xpath("//img/@src")) or not (response := fetch(src[0])):
        return None
    mime = (
        response.headers.get("Content-Type", "").split(";")[0].strip() or "image/jpeg"
    )
    return f"data:{mime};base64,{base64.b64encode(response.content).decode()}"


def scene_from_url(url: str) -> ScrapedScene | None:
    if (tree := fetch_tree(url)) is None:
        return None
    if not (name := title(tree)):
        log.error(f"No title found for {url}")
        return None
    scene: ScrapedScene = {
        "title": name,
        "urls": [url],
        "studio": {"name": "Cathy's Craving"},
    }
    if code := re.match(r"Scene\s+(\d+):", name):
        scene["code"] = code.group(1)
    if date := release_date(tree, url):
        scene["date"] = date
    if description := details(tree):
        scene["details"] = description
    if cast := performers(tree):
        scene["performers"] = cast
    if categories := tags(tree):
        scene["tags"] = categories
    if cover := image(tree):
        scene["image"] = cover
    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-query-fragment", args:
            result = next(
                (
                    scene
                    for url in args.get("urls") or []
                    if is_own_url(url) and (scene := scene_from_url(url))
                ),
                None,
            )
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
