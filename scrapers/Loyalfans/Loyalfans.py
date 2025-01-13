import sys
import json
import re

from py_common import log
from py_common.types import ScrapedScene
from py_common.util import scraper_args, dig
from py_common.deps import ensure_requirements

ensure_requirements("cloudscraper")
import cloudscraper  # noqa: E402

scraper = cloudscraper.create_scraper()
scraper.headers.update(
    {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.loyalfans.com",
        "Referer": "https://www.loyalfans.com",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    }
)
# Initial API request to get cookies
scraper.post("https://www.loyalfans.com/api/v2/system-status")


def to_scraped_scene(scene_from_api: dict) -> ScrapedScene:
    owner_slug = scene_from_api["owner"]["slug"]
    scene_slug = scene_from_api["slug"]
    scraped: ScrapedScene = {
        "title": scene_from_api["title"],
        "urls": [f"https://www.loyalfans.com/{owner_slug}/video/{scene_slug}"],
    }

    if content := dig(scene_from_api, "content"):
        details = content.replace("<br />", "")
        # Sometimes hashtags are included at the bottom of the description. This line strips all that junk out, as we're utilising the hashtags for the tags. Also tidies up ellipses.
        details = re.sub(r"#\w+\b", "", details).replace(". . .", "...").strip()
        scraped["details"] = details

    if image := dig(scene_from_api, "video_object", "poster"):
        scraped["image"] = image

    if studio_name := dig(scene_from_api, "owner", "display_name"):
        scraped["studio"] = {"name": studio_name}
        scraped["performers"] = [{"name": studio_name}]

    if date := dig(scene_from_api, "created_at", "date"):
        scraped["date"] = date.split(" ")[0]

    if tags := dig(scene_from_api, "hashtags"):
        scraped["tags"] = [{"name": tag.strip("#. ")} for tag in tags]

    # TODO: add duration to Stash scrapers
    # if duration := dig(scene_from_api, "video_object", "duration"):
    #     scraped["duration"] = duration

    return scraped


def scene_from_url(scene_url: str) -> dict:
    slug = scene_url.split("/")[-1]
    api_url = f"https://www.loyalfans.com/api/v1/social/post/{slug}"
    raw = scraper.get(api_url).json()
    return to_scraped_scene(raw["post"])


def scene_search(query: str) -> list[ScrapedScene]:
    query_body = {
        "q": query,
        "type": "videos",
        "limit": 10,
    }
    search_url = "https://www.loyalfans.com/api/v2/advanced-search?ngsw-bypass=true"
    raw = scraper.post(search_url, json=query_body).json()
    return [to_scraped_scene(scene) for scene in raw["data"]]


if __name__ == "__main__":
    op, args = scraper_args()

    result = None
    match op, args:
        case "scene-by-url" | "scene-by-query-fragment", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name)
        case _:
            log.error(
                f"Not implemented: Operation: {op}, arguments: {json.dumps(args)}"
            )
            sys.exit(1)

    print(json.dumps(result))
