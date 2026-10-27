import json
import re
import sys
from typing import Any

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import ScrapedGroup
from py_common.util import dig, scraper_args

ensure_requirements("requests", "bs4:beautifulsoup4")
import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    if paragraphs := soup.find_all("p"):
        return "\n\n".join(t for p in paragraphs if (t := p.get_text().strip()))
    return soup.get_text().strip()


def to_scraped_group(movie: dict[str, Any]) -> ScrapedGroup:
    group: ScrapedGroup = {}
    if name := dig(movie, "name", ("en", "de")):
        group["name"] = name
    if (description := dig(movie, "description", ("en", "de"))) and (
        synopsis := html_to_text(description)
    ):
        group["synopsis"] = synopsis
    if studio := dig(movie, "studio", "name"):
        group["studio"] = {"name": studio}
    if directors := movie.get("directors"):
        group["director"] = ", ".join(d["name"] for d in directors)
    # Negative sort orders are the shop's own lists, like "Recommended"
    if tags := [
        name
        for c in movie.get("categories") or []
        if c.get("sortOrder", 0) >= 0 and (name := dig(c, "name", ("en", "de")))
    ]:
        group["tags"] = [{"name": t} for t in tags]
    if duration := movie.get("durationSeconds"):
        group["duration"] = str(duration)
    if rating := movie.get("rating"):
        group["rating"] = str(rating)
    if year := movie.get("releaseYear"):
        group["date"] = str(year)
    if urls := movie.get("url"):
        group["urls"] = list(urls.values())
    if image := dig(movie, "image", "default"):
        group["front_image"] = image
    return group


def group_from_url(url: str) -> ScrapedGroup | None:
    page = requests.get(url, timeout=30).text
    # Scene pages carry the movie's id with a scene suffix: MOV121915-1
    if not (match := re.search(r'<meta name="id" content="(MOV\d+)', page)):
        log.error(f"No movie id found on {url}")
        return None
    response = requests.get(
        "https://api.erotik.com/content/movies",
        params={"idList[]": match.group(1)},
        timeout=30,
    )
    if not (movies := response.json()):
        log.error(f"Movie {match.group(1)} not found in the API")
        return None
    return to_scraped_group(movies[0])


if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "group-by-url", {"url": url} if url:
            result = group_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
