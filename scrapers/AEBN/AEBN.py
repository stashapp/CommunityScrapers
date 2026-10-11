import json
import re
import sys
import time
from functools import reduce
from urllib.parse import urljoin, urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedTag
from py_common.util import scraper_args

ensure_requirements("requests", "lxml")
import requests  # noqa: E402
from lxml import html  # noqa: E402

session = requests.Session()
session.cookies.set("ageGated", "true")


def fetch(url: str) -> html.HtmlElement | None:
    res = session.get(url, timeout=20)
    if res.status_code != 200:
        log.error(f"Failed to fetch {url}: {res.status_code}")
        return None
    return html.fromstring(res.text, base_url=res.url)


GENRES = {"101": "straight", "102": "gay"}


def movie_page_url(url: str) -> str | None:
    parsed = urlparse(url)
    if "aebn.com" in parsed.netloc and "/movies/" in parsed.path:
        return parsed._replace(fragment="").geturl()
    # AEBN storefronts like ManSurfer link to AEBN's own movie ids. AEBN
    # renders any movie under whichever genre host is asked, so the genre
    # must come from the storefront URL or every emitted URL is mislabelled
    if m := re.search(r"[?&]movieId=(\d+)", url):
        genre_id = g[1] if (g := re.search(r"[?&]genreId=(\d+)", url)) else ""
        genre = GENRES.get(genre_id, "straight")
        return f"https://{genre}.aebn.com/{genre}/movies/{m[1]}"
    return None


def first(tree: html.HtmlElement, xpath: str) -> str:
    return next((s for v in tree.xpath(xpath) if (s := str(v).strip())), "")


def texts(tree: html.HtmlElement, xpath: str) -> list[str]:
    return [s for e in tree.xpath(xpath) if (s := e.text_content().strip())]


def absolute(tree: html.HtmlElement, url: str) -> str:
    return urljoin(tree.base_url or "https://aebn.com", url)


def seconds(timestamp: str) -> int | None:
    if m := re.search(r"\d+(?::\d+)+", timestamp):
        return reduce(lambda total, part: total * 60 + int(part), m[0].split(":"), 0)
    return None


def parse_date(text: str) -> str | None:
    text = text.replace("Sept", "Sep")
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return time.strftime("%Y-%m-%d", time.strptime(text, fmt))
        except ValueError:
            continue
    return None


def production_date(tree: html.HtmlElement) -> str | None:
    if not (
        (link := first(tree, '//a[@id="footerMovieSpecific2257Link"]/@href'))
        and (m := re.search(r"/movies/(\d+)", link))
        and (page := fetch(f"https://m.aebn.net/movie/2257/{m[1]}"))
    ):
        return None
    return parse_date(
        first(
            page,
            '//div[contains(text(), "Production Date")]/span[@class="description"]/text()',
        )
    )


def to_performers(
    tree: html.HtmlElement, anchors: list[html.HtmlElement]
) -> list[ScrapedPerformer]:
    return [
        {"name": name, "urls": [absolute(tree, a.get("href"))]}
        for a in anchors
        if (name := a.text_content().strip())
    ]


def to_tags(names: list[str]) -> list[ScrapedTag]:
    return [{"name": name} for name in dict.fromkeys(names)]


def movie_fields(tree: html.HtmlElement) -> ScrapedScene:
    "Fields shared by the movie and each of its scenes"
    scene: ScrapedScene = {}
    if date := parse_date(
        first(tree, '//li[@class="section-detail-list-item-release-date"]/text()')
    ):
        scene["date"] = date
    if date := production_date(tree):
        scene["production_date"] = date
    if directors := texts(tree, '//li[@class="section-detail-list-item-director"]//a'):
        scene["director"] = ", ".join(directors)
    # Several studios share one comma-separated list of links
    if studio := first(
        tree, '//li[@class="section-detail-list-item-studio"]//a/text()'
    ):
        scene["studio"] = {"name": studio.rstrip(",")}
    return scene


def movie_categories(tree: html.HtmlElement) -> list[str]:
    return texts(
        tree, '//div[contains(@class,"dts-detail-movie-categories-content")]/a'
    )


def to_scraped_movie_scene(tree: html.HtmlElement, canonical: str) -> ScrapedScene:
    scene = movie_fields(tree)
    if title := first(tree, '//div[@class="dts-section-page-heading-title"]/h1/text()'):
        scene["title"] = title
    scene["urls"] = [canonical]
    if details := texts(
        tree, '//div[@class="dts-section-page-detail-description-body"]'
    ):
        scene["details"] = details[0]
    if duration := seconds(
        first(
            tree,
            '//li[@class="section-detail-list-item-duration"][contains(span,"Running Time")]/text()',
        )
    ):
        scene["duration"] = duration
    if performers := to_performers(
        tree,
        tree.xpath(
            '//div[contains(@class,"movie-meta-information")]//a[contains(@class,"dts-movie-star-wrapper")]'
        ),
    ):
        scene["performers"] = performers
    if tags := to_tags(movie_categories(tree)):
        scene["tags"] = tags
    if image := first(tree, '//img[contains(@class,"dts-modal-boxcover-front")]/@src'):
        scene["image"] = absolute(tree, image)
    return scene


def to_scraped_scene(
    tree: html.HtmlElement, section: html.HtmlElement, canonical: str
) -> ScrapedScene:
    scene = movie_fields(tree)
    movie_title = first(
        tree, '//div[@class="dts-section-page-heading-title"]/h1/text()'
    )
    label = first(section, './/span[@class="dts-panel-header-title-no-link"]/text()')
    if title := first(section, './/picture[@class="dts-primary-scene-image"]/img/@alt'):
        scene["title"] = title
    elif movie_title and label:
        scene["title"] = f"{movie_title}, {label}"
    scene["urls"] = [f"{canonical}#{section.get('id')}"]
    if duration := seconds(
        first(
            section, './/span[contains(@class,"dts-scene-title-metadata")]/span/text()'
        )
    ):
        scene["duration"] = duration
    if performers := to_performers(
        tree, section.xpath('.//a[contains(@class,"dts-movie-star-wrapper")]')
    ):
        scene["performers"] = performers
    if tags := to_tags(
        texts(section, './/div[@class="scene-strip-meta-data"]/div/a')
        + movie_categories(tree)
    ):
        scene["tags"] = tags
    if image := first(section, './/picture[@class="dts-primary-scene-image"]/img/@src'):
        # Without the size parameter the CDN serves the full-resolution still
        scene["image"] = absolute(tree, image).split("?")[0]
    if movie_title:
        scene["groups"] = [{"name": movie_title, "urls": [canonical]}]
    return scene


def find_scene(tree: html.HtmlElement, fragment: str) -> html.HtmlElement | None:
    sections = tree.xpath('//section[starts-with(@id, "scene-")]')
    match re.fullmatch(r"(scene-|rl_)(\d+)", fragment):
        case None:
            return None
        case m if m[1] == "scene-":
            return next((s for s in sections if s.get("id") == fragment), None)
        case m:
            # ManSurfer numbers scenes by position: #rl_1 is the first
            index = int(m[2]) - 1
            return sections[index] if 0 <= index < len(sections) else None


def scene_from_url(url: str) -> ScrapedScene | None:
    if not (page_url := movie_page_url(url)):
        log.error(f"Not an AEBN movie URL: {url}")
        return None
    if (tree := fetch(page_url)) is None:
        return None
    canonical = first(tree, '//link[@rel="canonical"]/@href') or page_url

    if not (fragment := urlparse(url).fragment):
        return to_scraped_movie_scene(tree, canonical)
    if (section := find_scene(tree, fragment)) is None:
        log.warning(f"No scene matching #{fragment}, scraping the whole movie")
        return to_scraped_movie_scene(tree, canonical)
    return to_scraped_scene(tree, section, canonical)


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
