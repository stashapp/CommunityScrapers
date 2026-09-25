import json
import re
import sys
from urllib.parse import urlparse

from py_common import log
from py_common.deps import ensure_requirements
from py_common.types import PerformerSearchResult, SceneSearchResult
from py_common.util import scraper_args

ensure_requirements("requests", "lxml")
import lxml.html  # noqa: E402
import requests  # noqa: E402

session = requests.Session()
session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like"
            " Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
)
session.cookies.set("accessAgeDisclaimerPH", "1", domain=".pornhub.com")


def get_token() -> str | None:
    try:
        result = session.get("https://www.pornhub.com", timeout=15)
    except Exception as e:
        log.error(f"Failed to fetch Pornhub token page: {e}")
        return None
    # regex extract
    data_token = re.search(r'data-token="([^"]+)"', result.text)
    return data_token.group(1) if data_token else None


def performer_by_name(name: str) -> list[PerformerSearchResult]:
    token = get_token()
    if not token:
        log.warning("Failed to retrieve token for performer search")
        return []

    try:
        response = session.get(
            "https://www.pornhub.com/api/v1/video/search_autocomplete",
            params={
                "q": name,
                "token": token,
                "pornstars": "true",
                "alt": 0,  # hardcoded
            },
            timeout=15,
        )
        data = response.json()
    except Exception as e:
        log.warning(f"Failed to fetch or parse Pornhub performer autocomplete: {e}")
        return []

    results: list[PerformerSearchResult] = []
    for model in data.get("models", []):
        results.append(
            {
                "name": model.get("name"),
                "url": f"https://www.pornhub.com/model/{model.get('slug')}",
            }
        )
    for pornstar in data.get("pornstars", []):
        results.append(
            {
                "name": pornstar.get("name"),
                "url": f"https://www.pornhub.com/pornstar/{pornstar.get('slug')}",
            }
        )
    # sort by alphabetical
    results.sort(key=lambda x: x["name"].lower())
    return results


def clean_search_query(name: str) -> str:
    cleaned = re.sub(r"[\W_]+", " ", name)
    return " ".join(cleaned.split())


def parse_scene_search_results(html_content: str) -> list[SceneSearchResult]:
    if not html_content or not html_content.strip():
        return []

    try:
        tree = lxml.html.fromstring(html_content)
    except Exception as e:
        log.error(f"Failed to parse Pornhub HTML: {e}")
        return []

    results: list[SceneSearchResult] = []

    # Match search video list items excluding bottom recommendations
    items = tree.xpath(
        '//ul[contains(@class, "search-video-thumbs") and not(@id="bottomVideos")]/li[contains(@class, "pcVideoListItem") or contains(@class, "videoBox")]'
    )
    if not items:
        items = tree.xpath(
            '//ul[contains(@class, "search-video-thumbs") and not(@id="bottomVideos")]/li'
        )

    for item in items:
        # Title & URL
        title_nodes = item.xpath(
            './/div[contains(@class, "thumbnail-info-wrapper")]//span[@class="title"]/a'
        )
        if not title_nodes:
            title_nodes = item.xpath(
                './/span[contains(@class, "title")]/a | .//a[contains(@class, "linkVideoThumb")]'
            )
        if not title_nodes:
            continue

        title_el = title_nodes[0]
        href = title_el.get("href", "")
        if not href or "viewkey=" not in href:
            continue

        video_url = f"https://www.pornhub.com{href}" if href.startswith("/") else href
        title = title_el.get("title") or title_el.text_content().strip()
        if not title:
            continue

        # Image
        image_nodes = item.xpath('.//div[contains(@class, "phimage")]//img')
        image_url = None
        if image_nodes:
            img = image_nodes[0]
            image_url = (
                img.get("data-mediumthumb")
                or img.get("data-thumb_url")
                or img.get("data-image")
                or img.get("src")
            )
            if image_url and image_url.startswith("//"):
                image_url = f"https:{image_url}"

        # Studio / Channel / Model
        studio_nodes = item.xpath(
            './/div[contains(@class, "thumbnail-info-wrapper")]//div[contains(@class, "usernameWrap")]/a'
        )
        studio_name = None
        if studio_nodes:
            studio_href = studio_nodes[0].get("href", "")
            if re.search(r"/(channels|model|pornstar)/", studio_href):
                studio_name = studio_nodes[0].text_content().strip()

        scene_res: SceneSearchResult = {
            "title": title,
            "url": video_url,
        }
        if image_url:
            scene_res["image"] = image_url
        if studio_name:
            scene_res["studio"] = {"name": studio_name}

        results.append(scene_res)

    return results


def scene_by_name(name: str) -> list[SceneSearchResult]:
    clean_name = clean_search_query(name)
    if not clean_name:
        log.warning(f"No alphanumeric characters found in search query: {name!r}")
        return []

    log.info(
        f"Searching Pornhub for scenes with cleaned query: {clean_name!r}"
        f" (original: {name!r})"
    )

    try:
        response = session.get(
            "https://www.pornhub.com/video/search",
            params={"search": clean_name},
            timeout=15,
        )
    except Exception as e:
        log.error(f"Failed to query Pornhub search: {e}")
        return []

    if response.status_code != 200:
        log.warning(f"Pornhub search returned status code {response.status_code}")
        return []

    parsed_url = urlparse(response.url)
    if parsed_url.path in ("", "/"):
        log.warning(
            f"Pornhub search was redirected to homepage: {response.url}"
        )
        return []

    return parse_scene_search_results(response.text)


def main():
    op, args = scraper_args()
    result = None
    match op, args:
        case "performer-by-name", {"name": name} if name:
            result = performer_by_name(name)
        case "scene-by-name", {"name": name} if name:
            result = scene_by_name(name)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
