import json
import re
import sys
from datetime import datetime as dt

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import (
    ScrapedMovie,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedStudio,
    ScrapedTag,
)
from py_common.util import scraper_args

ensure_requirements("requests", "lxml")
import requests  # noqa: E402
from lxml import html  # noqa: E402

BASE_URL = "https://www.downloadpass.com"


def get_html_from_url(url: str, session: requests.Session) -> html.HtmlElement | None:
    try:
        res = session.get(url)
        res.raise_for_status()
    except Exception as ex:
        log.error(f"Error getting URL: {ex}")
    else:
        return html.fromstring(res.text)


def get_first_elem_text(root: html.HtmlElement, expression: str) -> str | None:
    try:
        el = root.xpath(expression)[0]
    except IndexError:
        log.warning(f"Element not found: {expression}")
        return None
    if isinstance(el, html.HtmlElement):
        return el.text
    return el


def urls_from_style(style_text: str) -> list[str]:
    return re.findall(r"(https?://\S+)\)", style_text)


def movie_from_url(url: str) -> ScrapedMovie:
    def get_table_text(tree: html.HtmlElement, header: str):
        return get_first_elem_text(tree, ".//li/span[text()='" + header + "']/parent::li/text()")

    sess = requests.Session()

    url = url.replace("heatwavepass.com", "downloadpass.com")
    tree = get_html_from_url(url, sess)
    if tree is None:
        sys.exit(1)

    try:
        info_el = tree.xpath("//div[contains(@class, 'dvd-info')]")[0]
    except IndexError:
        log.warning("Info element not found")
        sys.exit(1)

    group = ScrapedMovie()

    # Name
    name_text = get_first_elem_text(info_el, "./h1")
    if name_text:
        group["name"] = name_text
    # Date
    date_text = get_table_text(info_el, "Added")
    if date_text:
        group["date"] = dt.strptime(date_text, "%b %d, %Y").strftime("%Y-%m-%d")
    # Duration
    duration_text = get_table_text(info_el, "Duration")
    if duration_text:
        duration = 0
        duration_parts = re.findall(r"(\d+[h|m|s])", duration_text)
        for part in duration_parts:
            t_abbr = part[-1]
            t_val = int(part[:-1])
            match t_abbr:
                case "s":
                    t_mult = 1
                case "m":
                    t_mult = 60
                case "h":
                    t_mult = 60 * 60
            duration = duration + t_val * t_mult
        if duration:
            group["duration"] = str(duration)
    # Covers
    cover_map = {"front_image": "cover-front", "back_image": "cover-back"}
    for k, v in cover_map.items():
        cover_style_text = get_first_elem_text(info_el, f".//div[@id='{v}']/@style")
        try:
            cover_url = urls_from_style(cover_style_text)[0]
        except (TypeError, IndexError):
            pass
        else:
            group[k] = cover_url
    # URL
    group_url_text = get_first_elem_text(tree, "//link[@rel='canonical']/@href")
    if group_url_text:
        group["url"] = group_url_text

    return group


def scene_from_url(url: str) -> ScrapedScene:
    sess = requests.Session()

    tree = get_html_from_url(url, sess)
    if tree is None:
        sys.exit(1)

    scene = ScrapedScene()

    # Details
    try:
        scene["details"] = tree.xpath("//meta[@name='description']/@content")[0]
    except IndexError:
        log.error("Details element not found.")

    # URL
    try:
        scene["url"] = tree.xpath("//link[@rel='canonical']/@href")[0]
    except IndexError:
        log.error("Canonical link element not found.")

    try:
        player_el = tree.xpath("//div[@id='player_page']")[0]
    except IndexError:
        log.error("Player element not found.")
    else:
        # Title
        title_el = get_first_elem_text(player_el, ".//h1[@class='title']")
        if title_el:
            scene["title"] = title_el
        # Image
        image_text = get_first_elem_text(player_el, ".//div[@id='promo-shots']/div[1]/@style")
        if image_text:
            image_url = urls_from_style(image_text)[0]
            # Use the first thumbnail image name as scene image name. Naming convention happens to align.
            scene["image"] = re.sub(r"(.+)/images/(.+)/crop/\d+x\d+/(.+)", r"\1/sc/\2/\3", image_url)
        # Performers
        performer_els = player_el.xpath(".//div[contains(@class, 'starItem')]")
        performers = []
        for p_el in performer_els:
            p_name = get_first_elem_text(p_el, "./div[@class='name']/a")
            if p_name:
                performer = ScrapedPerformer(name=p_name)
                p_url = get_first_elem_text(p_el, "./div[@class='name']/a/@href")
                if p_url:
                    performer["urls"] = [BASE_URL + p_url]
                performers.append(performer)
        scene["performers"] = performers

    try:
        info_el = tree.xpath("//div[@id='info_container']")[0]
    except IndexError:
        log.error("Info element not found.")
    else:
        # Date
        date_text = get_first_elem_text(info_el, ".//span[text()='Added']/parent::p/text()")
        if date_text:
            scene["date"] = dt.strptime(date_text.replace("Added", "").strip(), "%B %d, %Y").strftime("%Y-%m-%d")
        # Groups
        group_title = get_first_elem_text(info_el, ".//span[text()='DVD Title']/parent::p/a")
        if group_title:
            group = ScrapedMovie(name=group_title)
            group_url = get_first_elem_text(tree, "//div[@id='right']/div[@class='dvd']/h4/a/@href")
            if group_url:
                group["url"] = BASE_URL + group_url
            scene["movies"] = [group]
        # Tags
        tag_els = info_el.xpath(".//span[text()='Tags']/parent::p/a")
        if tag_els:
            scene["tags"] = [ScrapedTag(name=t.text) for t in tag_els]

    # Studio
    studio_url = get_first_elem_text(tree, "//div[@id='right']/div[@class='dvd']/h4/a/@href")
    if studio_url:
        studio_tree = get_html_from_url(BASE_URL + studio_url, sess)
        if studio_tree is not None:
            studio_name = get_first_elem_text(
                studio_tree,
                "//div[@id='content']//div[contains(@class, 'dvd-info')]//li/span[text()='Studio']/parent::li/a",
            )
            if studio_name:
                scene["studio"] = ScrapedStudio(name=studio_name)

    return scene


def performer_from_url(url: str) -> ScrapedPerformer:
    sess = requests.Session()
    tree = get_html_from_url(url, sess)
    if tree is None:
        sys.exit(1)

    try:
        bio_elem = tree.xpath("//div[contains(@class, 'pornstar-bio')]")[0]
    except IndexError:
        log.error("Bio element not found.")
        sys.exit(1)

    p_id = re.findall(r".+?(\d+)", url)[0]
    performer = ScrapedPerformer(
        name=get_first_elem_text(bio_elem, "./h1"),
        image=f"https://images.downloadpass.com/images/headshots/{p_id[:1]}/{p_id}/crop/300.jpg",
    )

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
            log.error(f"Not Implemented: Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
