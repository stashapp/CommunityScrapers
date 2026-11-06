import csv
import difflib
import json
import re
import sys
from io import StringIO
from urllib.parse import urlparse

from py_common import log
from py_common.cache import cache_to_disk
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag
from py_common.util import is_own_url, scraper_args

ensure_requirements("requests", "lxml")
import requests  # noqa: E402
from lxml import html  # noqa: E402

NETWORK = "Nasty Club"
HUB = "nastyclub.com"
# Every domain renders every scene, so the URL's host doesn't say which channel
# a scene belongs to: each channel's own feed lists exactly its own scenes
CHANNELS = {
    "bangvan.com": "BangVan",
    "cuckold.xxx": "Cuckold XXX",
    "homemade.xxx": "Homemade XXX",
    "mature.club": "Mature Club",
    "pickup.club": "Pickup Club",
}
FEED_FIELDS = [
    "id",
    "link",
    "title",
    "description",
    "tags",
    "performers",
    "duration",
    "date",
    "image",
    "extra",
]

session = requests.Session()


def get(url: str) -> str | None:
    try:
        res = session.get(url, timeout=15)
    except requests.RequestException as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None
    if res.status_code != 200:
        log.debug(f"{url} returned {res.status_code}")
        return None
    return res.text


@cache_to_disk(ttl=600)
def fetch_feed(domain: str) -> list[dict[str, str]]:
    res = session.get(f"https://{domain}/api/feed", timeout=15)
    # Raises instead of returning [] so a failed fetch is never cached
    res.raise_for_status()
    return list(csv.DictReader(StringIO(res.text), fieldnames=FEED_FIELDS))


def feed(domain: str) -> list[dict[str, str]]:
    try:
        return fetch_feed(domain)
    except requests.RequestException as e:
        log.error(f"Failed to fetch the {domain} feed: {e}")
        return []


def slug_from_url(url: str) -> str | None:
    if match := re.search(r"/video/([^/?#]+)", url):
        return match[1]
    return None


def host(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.")


def channel_of(scene_id: str, preferred: str) -> str | None:
    # The URL's own channel is checked first: most URLs are on the right domain
    domains = sorted(CHANNELS, key=lambda domain: domain != preferred)
    return next(
        (d for d in domains if any(row["id"] == scene_id for row in feed(d))), None
    )


def split(value: str) -> list[str]:
    return [s for part in value.split(",") if (s := part.strip())]


def to_scraped_scene(row: dict[str, str], channel: str | None) -> ScrapedScene:
    slug = row["link"].rsplit("/", 1)[-1]
    studio: ScrapedStudio = (
        {"name": CHANNELS[channel], "parent": {"name": NETWORK}}
        if channel
        else {"name": NETWORK}
    )
    scene: ScrapedScene = {
        "urls": [f"https://{channel or HUB}/video/{slug}"],
        "studio": studio,
    }
    if title := row["title"].strip():
        scene["title"] = title
    if details := row["description"].strip():
        scene["details"] = details
    if date := row["date"][:10]:
        scene["date"] = date
    if row["duration"].isdigit():
        scene["duration"] = int(row["duration"])
    if image := row["image"].strip():
        scene["image"] = image
    if tags := [ScrapedTag(name=t) for t in split(row["tags"])]:
        scene["tags"] = tags
    if performers := [ScrapedPerformer(name=p) for p in split(row["performers"])]:
        scene["performers"] = performers
    return scene


def text_of(page: html.HtmlElement, xpath: str) -> str:
    return " ".join(page.xpath(f"string({xpath})").split())


def scene_from_page(url: str) -> ScrapedScene | None:
    "Scenes missing from the feed: the page has no date, tags, duration or channel"
    if not (text := get(url)):
        return None
    page = html.fromstring(text)
    if not (title := text_of(page, '//div[contains(@class,"tab-title")]')):
        return None
    scene: ScrapedScene = {"title": title, "urls": [url]}
    if channel := CHANNELS.get(host(url)):
        scene["studio"] = {"name": channel, "parent": {"name": NETWORK}}
    description = page.xpath('string(//div[contains(@class,"up_description")])')
    if details := "\n".join(
        " ".join(line.split()) for line in description.strip().split("\n")
    ):
        scene["details"] = details
    if image := page.xpath("string(//video[@id='video-player']/@poster)"):
        scene["image"] = image
    if performers := [
        ScrapedPerformer(name=name)
        for a in page.xpath('//div[contains(@class,"up_starring")]/a')
        if (name := a.text_content().strip())
    ]:
        scene["performers"] = performers
    return scene


def scene_from_url(url: str) -> ScrapedScene | None:
    if not (slug := slug_from_url(url)):
        log.error(f"No scene slug in {url}")
        return None
    if row := next(
        (row for row in feed(HUB) if row["link"].endswith(f"/video/{slug}")), None
    ):
        return to_scraped_scene(row, channel_of(row["id"], host(url)))
    log.warning(f"'{slug}' is not in the feed, falling back to the scene page")
    return scene_from_page(url)


def similarity(query: str, title: str) -> float:
    return difflib.SequenceMatcher(None, query.lower(), title.lower()).ratio()


def scene_search(query: str) -> list[ScrapedScene]:
    rows = sorted(feed(HUB), key=lambda row: similarity(query, row["title"]))
    matches = [
        row
        for row in reversed(rows)
        if query.lower() in row["title"].lower()
        or similarity(query, row["title"]) > 0.5
    ][:10]
    return [to_scraped_scene(row, channel_of(row["id"], "")) for row in matches]


def scene_from_fragment(fragment: dict[str, object]) -> ScrapedScene | None:
    urls = fragment.get("urls")
    for url in urls if isinstance(urls, list) else []:
        if (
            isinstance(url, str)
            and is_own_url(url)
            and slug_from_url(url)
            and (scene := scene_from_url(url))
        ):
            return scene
    if not isinstance(title := fragment.get("title"), str) or not title:
        return None
    if (
        best := max(
            feed(HUB), key=lambda row: similarity(title, row["title"]), default=None
        )
    ) and similarity(title, best["title"]) >= 0.9:
        return to_scraped_scene(best, channel_of(best["id"], ""))
    log.info(f"No scene in the feed matches '{title}'")
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
