import json
import re
import sys
from urllib.parse import urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.util import scraper_args
from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag

ensure_requirements("requests")

import requests  # noqa: E402

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
)

STUDIOS = {
    "en.kin8tengoku.com": "Kinpatsutengoku",
    "enasianmusume.kin8tengoku.com": "Exotic Babes",
    "enexbabes.kin8tengoku.com": "Exotic Babes",
}

RSC_CHUNK_RE = re.compile(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', re.DOTALL)

MOVIE_ID_RE = re.compile(r"/moviepages/(\d+)/index\.html|/movie/(\d+)|/(\d+)/?$")


def _movie_id_from_url(url: str) -> str | None:
    if m := MOVIE_ID_RE.search(urlparse(url).path):
        return next(g for g in m.groups() if g)
    return None


def _fetch_movie_page(host: str, movie_id: str) -> str | None:
    # The site's URL scheme differs per sub-brand (en.kin8tengoku.com uses
    # /movie/{id}, sibling sites use a bare /{id}), so just try both
    for path in (f"/movie/{movie_id}", f"/{movie_id}"):
        url = f"https://{host}{path}"
        log.debug(f"Fetching '{url}'")
        response = session.get(url, timeout=(3, 6))
        if response.status_code == 200:
            return response.text
    log.error(f"Could not find a working page for movie {movie_id} on {host}")
    return None


def _extract_movie_data(html: str) -> dict | None:
    for m in RSC_CHUNK_RE.finditer(html):
        try:
            decoded = json.loads('"' + m.group(1) + '"')
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        if '"movie":{' not in decoded:
            continue

        try:
            data = json.loads(decoded[decoded.index(":") + 1 :])
            return data[0][3]["movie"]
        except (json.JSONDecodeError, IndexError, KeyError, TypeError):
            continue

    return None


def _strip_rsc_date(value: str | None) -> str | None:
    # RSC serializes dates as '$D2010-12-22T00:00:00.000Z'
    if not value:
        return None
    return value.removeprefix("$D").split("T")[0]


def scene_from_url(url: str) -> ScrapedScene:
    host = urlparse(url).netloc

    if not (movie_id := _movie_id_from_url(url)):
        log.error(f"Could not find a movie ID in '{url}'")
        sys.exit(1)

    if not (html := _fetch_movie_page(host, movie_id)):
        sys.exit(1)

    if not (movie := _extract_movie_data(html)):
        log.error(f"Could not extract movie data from '{url}'")
        sys.exit(1)

    scraped: ScrapedScene = {
        "urls": [url],
        "studio": ScrapedStudio(name=STUDIOS.get(host, host)),
    }

    if title := movie.get("name_en"):
        scraped["title"] = title

    if code := movie.get("movie_id"):
        scraped["code"] = str(code)

    if date := _strip_rsc_date(movie.get("ecp_start_date")):
        scraped["date"] = date

    if details := movie.get("detail", {}).get("memo_utf8"):
        scraped["details"] = details

    if duration := movie.get("detail", {}).get("duration"):
        scraped["duration"] = duration

    if performer := movie.get("act_en"):
        scraped["performers"] = [ScrapedPerformer(name=performer)]

    scraped["tags"] = [
        ScrapedTag(name=c["category_name_en"])
        for c in movie.get("categories", [])
        if c.get("category_name_en") and not c.get("category_key_name")
    ]

    if image := re.search(r'<meta property="og:image" content="([^"]+)"', html):
        scraped["image"] = image.group(1)

    return scraped


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
