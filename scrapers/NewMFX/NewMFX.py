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
HOME_URL = urljoin(BASE_URL, "home")
SEARCH_URL = urljoin(BASE_URL, "search")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/152.0.0.0 Safari/537.36"
)

def new_session() -> requests.Session:
    """Create a NewMFX session and pass the Laravel age gate."""
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
    token_input = soup.select_one('form[method="post"] input[name="_token"]')
    if token_input is None or not token_input.get("value"):
        raise RuntimeError("Could not find NewMFX age-gate CSRF token")

    form = token_input.find_parent("form")
    action = form.get("action") if form else BASE_URL
    action_url = urljoin(BASE_URL, action or BASE_URL)

    log.debug(f"Submitting NewMFX age gate to {action_url}")
    response = session.post(
        action_url,
        data={"_token": token_input["value"]},
        headers={"Referer": BASE_URL},
        timeout=30,
        allow_redirects=True,
    )
    response.raise_for_status()

    log.debug(f"NewMFX age gate completed at {response.url}")
    return session

def clean_text(value: str | None) -> str:
    """Collapse whitespace in text extracted from HTML."""
    return " ".join(value.split()) if value else ""

def parse_date(value: str | None) -> str:
    """Convert NewMFX dates such as 'Oct 28, 2012' to '2012-10-28'."""
    if not value:
        return ""

    value = clean_text(value)
    try:
        return datetime.strptime(value, "%b %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        log.warning(f"Could not parse NewMFX date: {value}")
        return ""

def validate_scene_url(url: str) -> bool:
    """Return True only for HTTP(S) URLs hosted by newmfx.com."""
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
    """Scrape a complete NewMFX scene page."""
    if not validate_scene_url(url):
        log.error(f"Invalid NewMFX URL: {url}")
        return None

    session = new_session()
    log.debug(f"Fetching NewMFX scene: {url}")

    response = session.get(
        url,
        headers={"Referer": HOME_URL},
        timeout=30,
    )
    response.raise_for_status()

    log.debug(
        f"NewMFX scene response: HTTP {response.status_code}, final URL {response.url}"
    )

    soup = BeautifulSoup(response.text, "html.parser")
    title_element = soup.select_one(".box-title-video h1")
    if not title_element:
        log.error("Could not find NewMFX scene title after passing age gate")
        return None

    scene: ScrapedScene = {}

    title = clean_text(title_element.get_text())
    if title:
        scene["title"] = title

    scene["urls"] = [response.url]

    date_element = soup.select_one(".item-detail-video.date .info")
    if date_element:
        date = parse_date(date_element.get_text())
        if date:
            scene["date"] = date

    description = soup.select_one(".description-video p")
    if description:
        details = clean_text(description.get_text(" ", strip=True))
        if details:
            scene["details"] = details

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

    category = soup.select_one(".item-detail-video.category .info")
    if category:
        category_name = clean_text(category.get_text())
        if category_name:
            tags: list[ScrapedTag] = [{"name": category_name}]
            scene["tags"] = tags

    studio: ScrapedStudio = {
        "name": "NewMFX",
        "urls": [BASE_URL],
    }
    scene["studio"] = studio

    image = soup.select_one(".movie-image img")
    if image and image.get("src"):
        scene["image"] = urljoin(BASE_URL, image["src"])

    return scene
    
def parse_search_results(html: str) -> list[ScrapedScene]:
    """Parse scene metadata from a NewMFX search-results page."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[ScrapedScene] = []

    for card in soup.select(".item-list-video"):
        title_element = card.select_one(".content-thumb-video .title")
        scene_link = card.select_one("a.image[href]")
        if not title_element or not scene_link:
            continue

        title = clean_text(title_element.get_text())
        href = scene_link.get("href")
        if not title or not href:
            continue

        scene: ScrapedScene = {
            "title": title,
            "urls": [urljoin(BASE_URL, href)],
        }

        image = scene_link.select_one("img")
        if image and image.get("src"):
            scene["image"] = urljoin(BASE_URL, image["src"])

        date_element = card.select_one(".date-video")
        if date_element:
            date = parse_date(date_element.get_text())
            if date:
                scene["date"] = date

        performers: list[ScrapedPerformer] = []
        performer_container = card.select_one(".category.slidetext__content")
        if performer_container:
            for performer_link in performer_container.select('a[href*="/cast/"]'):
                name = clean_text(performer_link.get_text())
                if not name:
                    continue

                performer: ScrapedPerformer = {"name": name}
                performer_href = performer_link.get("href")
                if performer_href:
                    performer["urls"] = [urljoin(BASE_URL, performer_href)]
                performers.append(performer)

        if performers:
            scene["performers"] = performers

        category_link = card.select_one(".content-thumb-video > a.subtitle")
        if category_link:
            category_name = clean_text(category_link.get_text())
            if category_name:
                scene["tags"] = [{"name": category_name}]

        scene["studio"] = {"name": "NewMFX"}
        results.append(scene)

    return results

def perform_search(
    session: requests.Session,
    query: str,
) -> list[ScrapedScene]:
    """Perform one NewMFX search using an authenticated session."""
    log.debug(f"Searching NewMFX for: {query}")

    response = session.get(
        SEARCH_URL,
        params={"text": query},
        headers={"Referer": HOME_URL},
        timeout=30,
    )
    response.raise_for_status()

    results = parse_search_results(response.text)
    log.debug(f"Found {len(results)} NewMFX search results for: {query}")
    return results

def scene_search(query: str) -> list[ScrapedScene]:
    """Search NewMFX, retrying ASCII apostrophes as U+2019 when necessary."""
    session = new_session()

    results = perform_search(session, query)
    if results:
        return results

    # NewMFX search is punctuation-sensitive. Titles may use U+2019 RIGHT
    # SINGLE QUOTATION MARK where users naturally type an ASCII apostrophe.
    if "'" in query:
        alternate_query = query.replace("'", "\u2019")
        log.debug(
            "NewMFX search returned no results; retrying with "
            f"typographic apostrophe: {alternate_query}"
        )
        return perform_search(session, alternate_query)

    return results

if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    match op, args:
        case "scene-by-url", {"url": url}:
            result = scene_from_url(url)

        case "scene-by-name", {"name": name}:
            result = scene_search(name)

        case "scene-by-query-fragment", args:
            if url := args.get("url"):
                result = scene_from_url(url)
            else:
                log.error("scene-by-query-fragment received no URL")

        case _:
            log.error(f"Operation {op} not implemented")

    print(json.dumps(result))
# Last Updated September 17, 2026
