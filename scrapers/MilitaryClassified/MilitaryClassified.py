import base64
import json
import re
import sys
from typing import Any
from urllib.parse import quote

from py_common import log
from py_common.deps import ensure_requirements
from py_common.proxy import stash_requests
from py_common.types import ScrapedScene
from py_common.util import scraper_args

ensure_requirements("lxml")
from lxml import html  # noqa: E402

BASE_URL = "https://militaryclassified.com"

# Names the site writes in capitals that aren't just a first name to title-case
SPECIAL_PERFORMER_NAMES = ["TJ", "JJ"]


def fetch(url: str) -> Any | None:
    try:
        response = stash_requests.get(url, timeout=10)
    # py_common.proxy raises a bare Exception once every backend has failed
    except Exception as e:  # noqa: BLE001
        log.error(f"Failed to fetch {url}: {e}")
        return None
    if response.status_code != 200:
        log.error(f"HTTP {response.status_code} for {url}")
        return None
    return response


def extract_performers(slug: str) -> list[str]:
    "Performer names from a movie slug like DOMINIC7, TJ-BOOKER2 or D-MONEY"
    # Group scenes don't credit anyone in the slug
    if "BUKAKKE" in slug.upper():
        return []
    # A single-letter prefix is part of one name, not a separate performer
    if match := re.match(r"^([A-Z])-([A-Za-z]+)\d*$", slug):
        return [f"{match.group(1)}-{match.group(2).capitalize()}"]
    performers = []
    for part in slug.split("-"):
        if match := re.search(r"([A-Za-z]+)\d*", part):
            name = match.group(1)
            performers.append(
                name.upper()
                if name.upper() in SPECIAL_PERFORMER_NAMES
                else name.capitalize()
            )
    return performers


def format_title(search_result: str, performers: list[str], slug: str) -> str:
    "'Name 7: Descriptive Part' from a search result like 'DOMINIC7 / BLOWJOB-FEET'"
    parts = search_result.split("/")
    descriptive = parts[1] if len(parts) > 1 else parts[0]
    description = " ".join(
        word.capitalize() for part in descriptive.split("-") for word in part.split()
    )
    if not performers:
        return description
    if len(performers) == 1:
        cast = performers[0]
    else:
        cast = ", ".join(performers[:-1]) + f" & {performers[-1]}"
    # The episode number only makes sense for a single performer's series
    if len(performers) == 1 and (number := re.search(r"[A-Za-z]+(\d+)", slug)):
        return f"{cast} {number.group(1)}: {description}"
    return f"{cast}: {description}"


def title_from_search(slug: str) -> str:
    "The movie page only has the slug, the search results add a description"
    if not (
        response := fetch(
            f"{BASE_URL}/dt/classic/ClassicSearch.pl?search={quote(slug)}"
        )
    ):
        return slug
    results = [
        text.strip()
        for text in html.fromstring(response.content).xpath(
            "//div[contains(@class, 'RecruitBox')]/div[contains(@class, 'RecruitBoxText')]/text()"
        )
    ]
    if not results:
        log.warning(f"No search results found for {slug}")
        return slug
    exact = next(
        (r for r in results if r.split("/")[0].strip().upper() == slug.upper()), None
    )
    return format_title(exact or results[0], extract_performers(slug), slug)


def image(tree: html.HtmlElement) -> str | None:
    if not (poster := tree.xpath("//video/@poster")):
        return None
    url = f"{BASE_URL}{poster[0]}"
    # The image is passed on as data, so it works even when the page needed a bypass
    if not (response := fetch(url)):
        return url
    return f"data:image/jpeg;base64,{base64.b64encode(response.content).decode()}"


def scene_from_url(url: str) -> ScrapedScene | None:
    if not (response := fetch(url)):
        return None
    tree = html.fromstring(response.content)
    scene: ScrapedScene = {
        "urls": [url],
        "studio": {"name": "Military Classified"},
        # Every scene is filmed and narrated by the site's owner
        "director": "Rob Navarro",
    }
    if slug := next(
        (t.strip() for t in tree.xpath('//div[@id="BodyContainer"]//h4/text()')), ""
    ):
        scene["title"] = title_from_search(slug)
        if performers := extract_performers(slug):
            scene["performers"] = [{"name": name} for name in performers]
    if date := next(
        (
            match.group()
            for text in tree.xpath(
                '//div[@class="MovieBlurb"]/div[@class="Right"]/text()'
            )
            if (match := re.search(r"\d{4}-\d{2}-\d{2}", text))
        ),
        None,
    ):
        scene["date"] = date
    if details := [
        text.strip()
        for text in tree.xpath(
            "//h4[contains(text(), 'HOW IT WENT DOWN')]/following-sibling::p/text()"
        )
        if text.strip()
    ]:
        scene["details"] = "\n\n".join(details)
    if cover := image(tree):
        scene["image"] = cover
    return scene


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
