import json
import re
import sys
import time

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    ScrapedGroup,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedStudio,
)
from py_common.util import scraper_args

ensure_requirements("requests", "lxml")
import requests
from lxml import html

BASE_URL = "https://www.downloadpass.com"

# Used as the meta description of scenes that have no description of their own
BOILERPLATE_DETAILS = "Download full-length Porn DVDs at Download Pass"

session = requests.Session()


def fetch(url: str) -> html.HtmlElement | None:
    try:
        res = session.get(url, timeout=30)
        res.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Error getting URL: {e}")
        return None
    return html.fromstring(res.text)


def first(root: html.HtmlElement, xpath: str) -> str | None:
    "Text of the first match, whether the XPath selects elements or strings"
    for match in root.xpath(xpath):
        text = match.text if isinstance(match, html.HtmlElement) else str(match)
        if text and (text := text.strip()):
            return text
    return None


def url_from_style(style: str | None) -> str | None:
    return (
        m.group(1) if style and (m := re.search(r"(https?://\S+)\)", style)) else None
    )


def parse_date(text: str, fmt: str) -> str | None:
    try:
        return time.strftime("%Y-%m-%d", time.strptime(text, fmt))
    except ValueError:
        return None


def parse_duration(text: str) -> int:
    "Durations are written like '1h, 26m, 29s'"
    units = {"h": 3600, "m": 60, "s": 1}
    return sum(int(n) * units[u] for n, u in re.findall(r"(\d+)([hms])", text))


def dvd_studio(dvd: html.HtmlElement) -> ScrapedStudio | None:
    xpath = "//div[contains(@class, 'dvd-info')]//li/span[text()='Studio']/parent::li/a"
    return {"name": name} if (name := first(dvd, xpath)) else None


def movie_from_url(url: str) -> ScrapedGroup | None:
    url = url.replace("heatwavepass.com", "downloadpass.com")
    if (tree := fetch(url)) is None:
        return None
    if not (info := tree.xpath("//div[contains(@class, 'dvd-info')]")):
        log.error("Info element not found")
        return None
    info = info[0]

    def field(label: str) -> str | None:
        return first(info, f".//li/span[text()='{label}']/parent::li/text()")

    group: ScrapedGroup = {}
    if name := first(info, "./h1"):
        group["name"] = name
    if (added := field("Added")) and (date := parse_date(added, "%b %d, %Y")):
        group["date"] = date
    if (length := field("Duration")) and (duration := parse_duration(length)):
        group["duration"] = str(duration)
    if front := url_from_style(first(info, ".//div[@id='cover-front']/@style")):
        group["front_image"] = front
    if back := url_from_style(first(info, ".//div[@id='cover-back']/@style")):
        group["back_image"] = back
    if studio := dvd_studio(tree):
        group["studio"] = studio
    if canonical := first(tree, "//link[@rel='canonical']/@href"):
        group["urls"] = [canonical]
    return group


def scene_from_url(url: str) -> ScrapedScene | None:
    if (tree := fetch(url)) is None:
        return None

    scene: ScrapedScene = {}
    if (details := first(tree, "//meta[@name='description']/@content")) and (
        details != BOILERPLATE_DETAILS
    ):
        scene["details"] = details
    if canonical := first(tree, "//link[@rel='canonical']/@href"):
        scene["urls"] = [canonical]

    if player := tree.xpath("//div[@id='player_page']"):
        player = player[0]
        if title := first(player, ".//h1[@class='title']"):
            scene["title"] = title
        style = first(player, ".//div[@id='promo-shots']/div[1]/@style")
        if thumb := url_from_style(style):
            # The first thumbnail's name matches the scene image's naming convention
            scene["image"] = re.sub(
                r"(.+)/images/(.+)/crop/\d+x\d+/(.+)", r"\1/sc/\2/\3", thumb
            )
        scene["performers"] = [
            {
                "name": name,
                **({"urls": [BASE_URL + href]} if href else {}),
            }
            for star in player.xpath(".//div[contains(@class, 'starItem')]")
            if (name := first(star, "./div[@class='name']/a"))
            for href in [first(star, "./div[@class='name']/a/@href")]
        ]

    if info := tree.xpath("//div[@id='info_container']"):
        info = info[0]
        if (added := first(info, ".//span[text()='Added']/parent::p/text()")) and (
            date := parse_date(added.replace("Added", "").strip(), "%B %d, %Y")
        ):
            scene["date"] = date
        if (length := first(info, ".//span[text()='Duration']/parent::p/text()")) and (
            duration := parse_duration(length)
        ):
            scene["duration"] = duration
        if tags := [t.text for t in info.xpath(".//span[text()='Tags']/parent::p/a")]:
            scene["tags"] = [{"name": tag} for tag in tags if tag]

    dvd_path = first(tree, "//div[@id='right']/div[@class='dvd']/h4/a/@href")
    if dvd_title := first(
        tree, "//div[@id='info_container']//span[text()='DVD Title']/parent::p/a"
    ):
        group: ScrapedGroup = {"name": dvd_title}
        if dvd_path:
            group["urls"] = [BASE_URL + dvd_path]
        scene["groups"] = [group]
    # The studio is only listed on the scene's DVD page
    if (
        dvd_path
        and (dvd := fetch(BASE_URL + dvd_path)) is not None
        and (studio := dvd_studio(dvd))
    ):
        scene["studio"] = studio

    return scene


def performer_from_url(url: str) -> ScrapedPerformer | None:
    if (tree := fetch(url)) is None:
        return None
    if not (name := first(tree, "//div[contains(@class, 'pornstar-bio')]/h1")):
        log.error("Performer name not found")
        return None
    performer: ScrapedPerformer = {"name": name, "urls": [url]}
    if p_id := re.search(r"(\d+)", url.rsplit("/", 1)[-1]):
        pid = p_id.group(1)
        performer["images"] = [
            f"https://images.downloadpass.com/images/headshots/{pid[:1]}/{pid}/crop/300.jpg"
        ]
    return performer


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
