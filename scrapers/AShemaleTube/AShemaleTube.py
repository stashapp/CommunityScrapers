import json
import re
import sys
import time
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer, ScrapedScene
from py_common.util import scraper_args

ensure_requirements("cloudscraper", "lxml")
import cloudscraper
from cloudscraper.exceptions import CloudflareException
from lxml import html
from requests import RequestException

BASE_URL = "https://www.ashemaletube.com"

NOT_TAGS = {"suggest", "suggest tag"}

scraper = cloudscraper.create_scraper()


def fetch(url: str) -> html.HtmlElement | None:
    try:
        res = scraper.get(url, timeout=30)
    except (RequestException, CloudflareException) as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None
    if res.status_code != 200:
        blocked = " (Cloudflare challenge)" if "Just a moment" in res.text else ""
        log.error(f"HTTP {res.status_code} for {url}{blocked}")
        return None
    return html.document_fromstring(res.text)


def first(tree: html.HtmlElement, xpath: str) -> str | None:
    return next((s for v in tree.xpath(xpath) if (s := str(v).strip())), None)


def info(tree: html.HtmlElement, label: str) -> str | None:
    return first(
        tree,
        f'//div[@class="info-box info"]/ul/li/span[text()="{label}:"]/../text()[2]',
    )


def video_object(tree: html.HtmlElement) -> dict[str, Any]:
    for script in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            data = json.loads(script)
        except json.JSONDecodeError:
            continue
        for node in data.get("@graph", [data]):
            if node.get("@type") == "VideoObject":
                return node
    return {}


def parse_date(date: str) -> str | None:
    try:
        return time.strftime("%Y-%m-%d", time.strptime(date, "%d %B %Y"))
    except ValueError:
        return None


def remove_query(url: str) -> str:
    return urlunparse(urlparse(url)._replace(query=""))


def scene_from_url(url: str) -> ScrapedScene | None:
    if (tree := fetch(url)) is None:
        return None
    video = video_object(tree)

    scene: ScrapedScene = {"urls": [video.get("mainEntityOfPage") or url]}
    if title := first(tree, "//h1//text()"):
        scene["title"] = title
    if uploaded := video.get("uploadDate"):
        scene["date"] = uploaded[:10]
    match video.get("thumbnailUrl"):
        case [image, *_] | str(image):
            scene["image"] = image
    if tags := [
        tag
        for tag in dict.fromkeys(tree.xpath('//a[contains(@class, "btn-tag")]/@title'))
        if tag.strip().lower() not in NOT_TAGS
    ]:
        scene["tags"] = [{"name": tag} for tag in tags]
    if actors := [a for a in video.get("actor", []) if a.get("name")]:
        scene["performers"] = [
            {"name": a["name"], **({"urls": [a["url"]]} if a.get("url") else {})}
            for a in actors
        ]
    return scene


def social_urls(tree: html.HtmlElement) -> list[str]:
    urls = []
    for link in tree.xpath('//a[starts-with(@class, " social-")]/@href'):
        try:
            urls.append(remove_query(scraper.get(urljoin(BASE_URL, link)).url))
        except (RequestException, CloudflareException) as e:
            log.warning(f"Could not resolve social link {link}: {e}")
    return urls


def performer_from_url(url: str) -> ScrapedPerformer | None:
    if (tree := fetch(url)) is None:
        return None
    if not (name := first(tree, "//h1//text()")):
        log.error(f"No performer name found at {url}")
        return None

    performer: ScrapedPerformer = {"name": name}
    if aliases := info(tree, "AKA"):
        performer["aliases"] = aliases
    if (birthdate := info(tree, "Date of Birth")) and (date := parse_date(birthdate)):
        performer["birthdate"] = date
    if (
        (status := info(tree, "Status"))
        and (match := re.search(r"\d{1,2} \w+ \d{4}", status))
        and (date := parse_date(match.group()))
    ):
        performer["death_date"] = date
    if country := info(tree, "Country"):
        performer["country"] = country
    if eye_color := info(tree, "Eye Color"):
        performer["eye_color"] = eye_color
    if hair_color := info(tree, "Hair Color"):
        performer["hair_color"] = hair_color
    if ethnicity := info(tree, "Ethnicity"):
        performer["ethnicity"] = ethnicity
    if (height := info(tree, "Height")) and (match := re.match(r"(\d+) cm", height)):
        performer["height"] = match.group(1)
    if tags := tree.xpath('//a[@class="tag-item"]/text()'):
        performer["tags"] = [{"name": tag.strip()} for tag in tags]
    if image := first(tree, '//div[@class="user-photo"]/img/@src'):
        performer["images"] = [image]
    websites = tree.xpath(
        '//div[@class="info-box info"]/ul/li/span[text()="Website:"]/following-sibling::a/@href'
    )
    performer["urls"] = [url, *social_urls(tree), *map(remove_query, websites)]
    return performer


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case "scene-by-url" | "scene-by-query-fragment", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-query-fragment", {"urls": [url, *_]} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
