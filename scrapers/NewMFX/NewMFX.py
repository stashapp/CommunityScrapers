import json
from datetime import datetime
from urllib.parse import urljoin, urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag
from py_common.util import scraper_args

ensure_requirements("requests", "bs4:beautifulsoup4")

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402


BASE_URL = "https://newmfx.com/"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/152.0.0.0 Safari/537.36"
)


def new_session() -> requests.Session:
    """Create a NewMFX session and pass the site's age gate."""

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    log.debug("Fetching NewMFX age-gate page")

    response = session.get(BASE_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # NewMFX's age gate is:
    #
    # <form action="https://newmfx.com" method="post">
    #   <input type="hidden" name="_token" value="...">
    #   <button type="submit">Enter Page</button>
    # </form>

    token_input = soup.select_one('form[method="post"] input[name="_token"]')

    if token_input is None or not token_input.get("value"):
        raise RuntimeError("Could not find NewMFX age-gate CSRF token")

    token = token_input["value"]

    form = token_input.find_parent("form")
    action = form.get("action") if form else BASE_URL
    action_url = urljoin(BASE_URL, action or BASE_URL)

    log.debug(f"Submitting NewMFX age gate to {action_url}")

    response = session.post(
        action_url,
        data={"_token": token},
        headers={"Referer": BASE_URL},
        timeout=30,
        allow_redirects=True,
    )
    response.raise_for_status()

    log.debug(f"NewMFX age gate completed at {response.url}")

    return session


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split())


def parse_date(value: str | None) -> str:
    if not value:
        return ""

    value = clean_text(value)

    try:
        return datetime.strptime(value, "%b %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        log.warning(f"Could not parse NewMFX date: {value}")
        return ""


def validate_scene_url(url: str) -> bool:
    """Only allow NewMFX URLs to be fetched."""

    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    return (
        parsed.scheme in ("http", "https")
        and parsed.hostname is not None
        and (
            parsed.hostname == "newmfx.com"
            or parsed.hostname.endswith(".newmfx.com")
        )
    )


def scene_from_url(url: str) -> ScrapedScene | None:
    if not validate_scene_url(url):
        log.error(f"Invalid NewMFX URL: {url}")
        return None

    session = new_session()

    log.debug(f"Fetching NewMFX scene: {url}")

    response = session.get(
        url,
        headers={"Referer": "https://newmfx.com/home"},
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title_element = soup.select_one(".box-title-video h1")

    if not title_element:
        log.error(
            "Could not find scene title. "
            "The NewMFX age gate may not have been successfully passed."
        )
        return None

    scene: ScrapedScene = {}

    # Title
    title = clean_text(title_element.get_text())
    if title:
        scene["title"] = title

    # URL
    scene["urls"] = [url]

    # Date
    date_element = soup.select_one(".item-detail-video.date .info")
    if date_element:
        date = parse_date(date_element.get_text())
        if date:
            scene["date"] = date

    # Description
    description = soup.select_one(".description-video p")
    if description:
        details = clean_text(description.get_text(" ", strip=True))
        if details:
            scene["details"] = details

    # Performers
    performers: list[ScrapedPerformer] = []

    for performer_link in soup.select(".box-title-video .subtitle a"):
        name = clean_text(performer_link.get_text())

        if not name:
            continue

        performer: ScrapedPerformer = {"name": name}

        href = performer_link.get("href")
        if href:
            performer["urls"] = [urljoin(BASE_URL, href)]

        performers.append(performer)

    if performers:
        scene["performers"] = performers

    # Category -> tag
    tags: list[ScrapedTag] = []

    category = soup.select_one(".item-detail-video.category .info")
    if category:
        category_name = clean_text(category.get_text())

        if category_name:
            tags.append({"name": category_name})

    if tags:
        scene["tags"] = tags

    # Studio
    studio: ScrapedStudio = {
        "name": "NewMFX",
        "urls": [BASE_URL],
    }
    scene["studio"] = studio

    # Main image
    image = soup.select_one(".movie-image img")
    if image and image.get("src"):
        scene["image"] = urljoin(BASE_URL, image["src"])

    return scene


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    match op, args:
        case "scene-by-url", {"url": url}:
            result = scene_from_url(url)

        case _:
            log.error(f"Operation {op} not implemented")

    print(json.dumps(result))
