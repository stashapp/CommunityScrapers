import json
import sys
import re
from urllib.parse import urlencode, urlparse
from py_common import log
from py_common.config import get_config
from py_common.deps import ensure_requirements
from py_common.types import ScrapedMovie, ScrapedScene
from py_common.util import scraper_args, is_valid_url

ensure_requirements("bs4:beautifulsoup4", "requests")

# Need to disable E402 since we can only import them after we've ensured they're installed

from bs4 import BeautifulSoup  # noqa: E402
import requests  # noqa: E402
from javlib_parser import scrape_movie  # noqa: E402

config = get_config(
    default="""# Preferred language: en, ja, cn, tw
language = en

# Find the `cf_clearance` cookie in your browser and put it here
cf_clearance = cookie_here
"""
)


base_url = urlparse("https://www.javlibrary.com")

if config.language in ("en", "ja", "cn", "tw"):
    lang = config.language
else:
    log.error(f"Config sets invalid language '{config.language}', defaulting to 'en'")
    lang = "en"


def abs_url(url: str) -> str:
    if url.startswith("http"):
        return url
    return base_url._replace(path=url.replace(".", lang, 1)).geturl()


session = requests.session()
log.debug(f"Using cookie {config.cf_clearance}")
session.cookies.update({"cf_clearance": config.cf_clearance})
session.headers.update(
    {
        "Referer": base_url.netloc,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    }
)


def get_better_image(url: str) -> str:
    """
    Attempts to find a higher resolution image associated with the digital release

    Returns the original URL if no better option is found
    """
    if not (match := re.search(r"(\d+)?([a-zA-Z]+)(\d+)([a-zA-Z]?)", url, re.I)):
        return url
    prefix, letters, numbers, postfix = match.groups()
    new_code = f"{prefix if prefix else ''}{letters}{numbers.zfill(5)}{postfix}"
    new_url = f"https://awsimgsrc.dmm.com/dig/digital/video/{new_code}/{new_code}pl.jpg"
    return new_url if is_valid_url(new_url) else url


def scene_from_url(url: str) -> ScrapedScene | None:
    log.debug(f"Scraping scene from {url}")
    response = session.get(url)
    if response.status_code not in range(200, 300):
        status_code, reason = response.status_code, response.reason
        log.error(f"Failed to fetch {url}: {status_code} {reason}")
        return None

    movie = scrape_movie(response.content.decode("utf-8"))
    scraped: ScrapedScene = {
        "title": movie.get("title", ""),
        "code": movie.get("code", ""),
        "date": movie.get("date", ""),
        "director": movie.get("director", ""),
        "performers": movie.get("cast", []),
    }

    if image := movie.get("cover"):
        better_image = get_better_image(image)
        if better_image != image:
            log.debug("Trying to get higher resolution cover image:")
            log.debug(f"Before: {image}")
            log.debug(f" After: {better_image}")
        scraped["image"] = better_image

    studio = movie.get("label")
    parent_studio = movie.get("maker")

    if studio:
        scraped["studio"] = {"name": studio}
        if parent_studio and studio != parent_studio:
            scraped["studio"]["parent"] = {"name": parent_studio}

    cleaned: ScrapedScene = {k: v for k, v in scraped.items() if v}  # type: ignore because narrowing is safe

    return cleaned


def movie_from_url(url: str) -> ScrapedMovie | None:
    log.debug(f"Scraping movie from {url}")
    response = session.get(url)
    if response.status_code not in range(200, 300):
        status_code, reason = response.status_code, response.reason
        log.error(f"Failed to fetch {url}: {status_code} {reason}")
        return None

    movie = scrape_movie(response.text)
    log.debug(json.dumps(movie))
    scraped: ScrapedMovie = {
        "name": movie.get("title", ""),
        "duration": movie.get("duration", ""),
        "date": movie.get("date", ""),
        "director": movie.get("director", ""),
    }

    if image := movie.get("cover"):
        better_image = get_better_image(image)
        if better_image != image:
            log.debug("Trying to get higher resolution cover image:")
            log.debug(f"Before: {image}")
            log.debug(f" After: {better_image}")
        scraped["front_image"] = better_image

    studio = movie.get("label")
    parent_studio = movie.get("maker")

    if studio:
        scraped["studio"] = {"name": studio}
        if parent_studio and studio != parent_studio:
            scraped["studio"]["parent"] = {"name": parent_studio}

    cleaned: ScrapedMovie = {k: v for k, v in scraped.items() if v}  # type: ignore because narrowing is safe

    return cleaned


def scene_search(code: str) -> list[ScrapedScene]:
    if match := re.search(r"([a-zA-Z]+-\d+[zZ]?[eE]?)(?:-pt)?(\d{1,2})?", code):
        log.info(f"Extracted code '{match.group(1)}' from '{code}")
        code = match.group(1)

    log.info(f"Searching for scene with code '{code}'")
    search_url = base_url._replace(
        path=f"{lang}/vl_searchbyid.php", query=urlencode({"keyword": code})
    ).geturl()

    log.debug(f"Fetching {search_url}")
    response = session.post(search_url)
    if response.status_code not in range(200, 300):
        status_code, reason = response.status_code, response.reason
        log.error(f"Failed to fetch {search_url}: {status_code} {reason}")
        log.error(response.text)
        return []

    soup = BeautifulSoup(response.content.decode("utf-8"), "html.parser")

    scenes = []
    for video in soup.find_all("div", class_="video"):
        link = video.find("a", href=True)
        title = link["title"]
        url = abs_url(link["href"])
        image = abs_url(video.find("img", src=True).get("src"))
        scenes.append(
            {
                "title": title,
                "url": url,
                "image": image,
            }
        )

    return scenes


def scene_from_fragment(args) -> ScrapedScene | None:
    # If the scene already has a JavLibrary URL we just use that
    for url in args.get("urls", []):
        if base_url.hostname in url:
            return scene_from_url(url)

    # Searching by code is the most reliable
    if (term := args.get("code")) and (scenes := scene_search(term)):
        return scene_from_url(scenes[0].get("url", ""))

    # Title can contain studio code, so it's the next best thing
    if (title := args.get("title")) and (scenes := scene_search(title)):
        return scene_from_url(scenes[0].get("url", ""))

    return None


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    match op, args:
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name)
        case "scene-by-fragment", args:
            result = scene_from_fragment(args)
        case "movie-by-url", {"url": url} if url:
            result = movie_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
