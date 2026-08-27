import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import TypedDict
from urllib.parse import quote

from py_common import cache, log
from py_common.deps import ensure_requirements
from py_common.graphql import configuration
from py_common.types import (
    PerformerSearchResult,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedStudio,
    ScrapedTag,
)
from py_common.util import dig, scraper_args

ensure_requirements("requests", "bs4:beautifulsoup4")

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

# Clips4Sale's search silently 404s if the query contains certain words
BANNED_WORDS = {
    word.lower()
    for line in (Path(__file__).parent / "banned_words.txt")
    .read_text(encoding="utf-8")
    .splitlines()
    if (word := line.strip()) and not word.startswith("#")
}


def clean_search_query(query: str) -> str:
    def strip_banned(match: re.Match[str]) -> str:
        word = match.group(0)
        if word.lower() in BANNED_WORDS:
            log.debug(f"Removed banned search word '{word}' from query")
            return ""
        return word

    cleaned = re.sub(r"\w+", strip_banned, query)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


class PerformerData(TypedDict):
    image: str | None
    tags: list[ScrapedTag]


class StudioData(TypedDict):
    image: str | None
    details: str


def parse_date(date_str: str | None) -> str:
    """Clips4Sale date format: "01/02/06 3:04 PM" -> "2006-01-02" """
    if not date_str:
        return ""
    try:
        return datetime.strptime(date_str, "%m/%d/%y %I:%M %p").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def clean_text(text: str | None) -> str:
    if not text:
        return ""

    # Unescape HTML entities first (e.g. &lt;br&gt; -> <br>)
    text = html.unescape(text)
    text = re.sub(r'data-\w+="[^"]*"\s*', "", text)
    soup = BeautifulSoup(text, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")

    return soup.get_text().strip()


def normalize_url(url: str | None) -> str | None:
    if not url or url.startswith("http"):
        return url
    return "https://www.clips4sale.com" + url


def first_json_line(response: requests.Response) -> dict | None:
    if not (lines := response.text.splitlines()):
        return None
    return json.loads(lines[0])


@cache.cache_to_disk(ttl=60)
def get_user_agent() -> str:
    default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    try:
        config = configuration() or {}
    except Exception:
        return default_ua
    return dig(config, "scraping", "scraperUserAgent") or default_ua


scraper = requests.Session()
scraper.headers.update({"User-Agent": get_user_agent()})
for _name, _value in {
    "iAgreeWithUpdatedTerms": "true",
    "contentPreference": "%5B0%5D",
    "i18nextLng": "en",
}.items():
    scraper.cookies.set(_name, _value, domain=".clips4sale.com", path="/")


def fetch(url: str) -> requests.Response:
    """
    Clips4Sale's Remix-based routes signal a redirect to a canonical URL
    (e.g. a differently-cased or unhyphenated performer slug) via
    x-remix-redirect/x-remix-status response headers alongside a 204 body,
    instead of a normal 3xx status - a plain HTTP client won't follow that
    automatically, so retry once ourselves
    """
    response = scraper.get(url)
    if not (redirect := response.headers.get("x-remix-redirect")):
        return response

    query = url.partition("?")[2]
    redirect_url = f"https://www.clips4sale.com{redirect}"
    log.debug(f"Following remix redirect to {redirect_url}")
    return scraper.get(f"{redirect_url}?{query}" if query else redirect_url)


@cache.cache_to_disk(ttl=600)
def fetch_studio_data(studio_id: str, studio_slug: str) -> StudioData:
    url = f"https://www.clips4sale.com/studio/{studio_id}/{studio_slug}?_data=routes%2F%28%24lang%29.studio.%24id_.%24studioSlug.%24"
    response = fetch(url)
    if not response.ok or not (data := first_json_line(response)):
        log.warning(f"Failed to fetch studio data from {url}: {response.status_code}")
        return {"image": None, "details": ""}

    return {
        "image": dig(data, "avatarSrc"),
        "details": clean_text(dig(data, "description")),
    }


@cache.cache_to_disk(ttl=600)
def fetch_performer_data(performer_id: str, performer_slug: str) -> PerformerData:
    url = f"https://www.clips4sale.com/performers/{performer_id}/{quote(performer_slug)}?_data=routes%2F%28%24lang%29.performers.%24performerId.%28%24performerSlug%29"
    response = fetch(url)
    if not response.ok or not (data := first_json_line(response)):
        log.warning(
            f"Failed to fetch performer data from {url}: {response.status_code}"
        )
        return {"image": None, "tags": []}

    performer_data = dig(data, "performer")
    tags: list[ScrapedTag] = []
    if related_categories := dig(data, "relatedCategories"):
        tags = [
            {"name": name} for cat in related_categories if (name := cat.get("name"))
        ]

    return {
        "image": dig(performer_data, "avatars", "original", "url"),
        "tags": tags,
    }


def to_scraped_scene(clip: dict, detailed: bool = False) -> ScrapedScene:
    title = clean_text(dig(clip, "title"))

    studio_name = dig(clip, "studio", "name")
    studio_link = normalize_url(dig(clip, "studio", "link"))
    studio_id = dig(clip, "studio", "id")

    studio_data: StudioData = {"image": None, "details": ""}
    if studio_link and (match := re.search(r"/studio/(\d+)/([^/?]+)", studio_link)):
        studio_id = studio_id or match.group(1)
        if detailed:
            studio_data = fetch_studio_data(studio_id, match.group(2))

    performers: list[ScrapedPerformer] = []
    for p in dig(clip, "performers") or []:
        p_name = dig(p, "stage_name")
        p_id = dig(p, "id")
        if not p_name:
            continue

        p_slug = dig(p, "slug", default=p_name)
        performer: ScrapedPerformer = {
            "name": p_name,
            "urls": [f"https://www.clips4sale.com/performers/{p_id}/{quote(p_slug)}"],
        }
        if detailed:
            p_data = fetch_performer_data(str(p_id), p_slug)
            if p_img := p_data.get("image"):
                performer["images"] = [p_img]
            if p_tags := p_data.get("tags"):
                performer["tags"] = p_tags

        performers.append(performer)

    potential_tags = [dig(clip, "category_name")]
    potential_tags.extend(
        r.get("category") for r in dig(clip, "related_category_links") or []
    )
    potential_tags.extend(k.get("keyword") for k in dig(clip, "keyword_links") or [])

    unique_tags: dict[str, str] = {}
    for tag_name in potential_tags:
        if not (original := (tag_name or "").strip()):
            continue
        lower = original.lower()
        stored = unique_tags.get(lower)
        if not stored or sum(c.isupper() for c in original) > sum(
            c.isupper() for c in stored
        ):
            unique_tags[lower] = original
    tags: list[ScrapedTag] = [{"name": t} for t in unique_tags.values()]

    studio: ScrapedStudio = {"name": studio_name}
    if studio_link and detailed:
        studio["urls"] = [studio_link]
    if studio_img := studio_data.get("image"):
        studio["image"] = studio_img
    if studio_details := clean_text(studio_data.get("details")):
        studio["details"] = studio_details
    if studio_id:
        studio["aliases"] = str(studio_id)

    scene: ScrapedScene = {"studio": studio}
    if title:
        scene["title"] = title
    if clip_id := dig(clip, "id"):
        scene["code"] = str(clip_id)
    if date := parse_date(dig(clip, "date_display")):
        scene["date"] = date
    if link := normalize_url(dig(clip, "link")):
        scene["urls"] = [link]
    if image := (dig(clip, "cdn_previewlg_link") or dig(clip, "previewLink")):
        scene["image"] = image
    if performers:
        scene["performers"] = performers
    if tags:
        scene["tags"] = tags
    if details := clean_text(dig(clip, "description")):
        scene["details"] = details

    return scene


def dedupe_by_title(results: list[ScrapedScene]) -> list[ScrapedScene]:
    """
    Clips4Sale search results often include the same clip multiple times,
    once per quality/format variant it was uploaded in. Keep only the first
    (highest-ranked) result per distinct title
    """
    seen_titles: set[str] = set()
    deduped: list[ScrapedScene] = []
    for scene in results:
        title = scene.get("title", "").strip().lower()
        if title:
            if title in seen_titles:
                continue
            seen_titles.add(title)
        deduped.append(scene)
    return deduped


def scene_search(
    query: str, detailed: bool = False, limit: int | None = None
) -> list[ScrapedScene]:
    encoded_query = quote(clean_search_query(query))
    url = f"https://www.clips4sale.com/clips/search/{encoded_query}/category/0/storesPage/1/clipsPage/1?_data=routes%2F%28%24lang%29.clips.search.%24"
    log.debug(f"Searching URL: {url}")

    response = fetch(url)
    if not response.ok:
        log.error(f"Search failed with status code {response.status_code}")
        return []

    clips = dig(response.json(), "clips") or []
    if limit:
        clips = clips[:limit]

    scenes = [to_scraped_scene(clip, detailed=detailed) for clip in clips]
    return dedupe_by_title(scenes)


def scene_from_url(url: str) -> ScrapedScene | None:
    # Example: https://www.clips4sale.com/studio/23235/22576135/interviewing-thew-new-maid-part-one-interview-only-4k-mp4-vid0541a
    if not (match := re.search(r"/studio/(\d+)/(\d+)/([^/?]+)", url)):
        log.error(f"Could not extract clip info from URL: {url}")
        return None

    studio_id, clip_id, slug = match.groups()
    data_url = f"https://www.clips4sale.com/studio/{studio_id}/{clip_id}/{slug}?_data=routes%2F%28%24lang%29.studio.%24id_.%24clipId.%24clipSlug"
    log.debug(f"Fetching direct scene data from: {data_url}")

    response = fetch(data_url)
    if (
        response.ok
        and (data := first_json_line(response))
        and (clip_data := dig(data, "clip"))
    ):
        return to_scraped_scene(clip_data, detailed=True)

    # Fallback to search by title/slug
    search_query = slug.replace("-", " ")
    log.debug(f"Direct fetch failed, searching for: {search_query}")
    results = scene_search(search_query, detailed=True)
    for res in results:
        if dig(res, "code") == clip_id:
            return res
    return results[0] if results else None


def performer_search(
    query: str, detailed: bool = False, limit: int | None = None
) -> list[ScrapedPerformer] | list[PerformerSearchResult]:
    url = f"https://www.clips4sale.com/api/performer-list?keyword={quote(query)}&sort=top_100&_data=routes%2Fapi.performer-list"
    log.debug(f"Searching Performer URL: {url}")

    response = fetch(url)
    if not response.ok:
        log.error(f"Performer search failed with status code {response.status_code}")
        return []

    performers_data = dig(response.json(), "performers") or []
    if limit:
        performers_data = performers_data[:limit]

    if not detailed:
        return [
            {
                "name": name,
                "url": f"https://www.clips4sale.com/performers/{dig(p, 'id')}/{quote(name)}",
            }
            for p in performers_data
            if (name := dig(p, "stage_name")) and dig(p, "id")
        ]

    results: list[ScrapedPerformer] = []
    for p in performers_data:
        p_id = dig(p, "id")
        p_name = dig(p, "stage_name")
        if not p_id or not p_name:
            continue

        p_slug = dig(p, "slug") or p_name
        performer: ScrapedPerformer = {
            "name": p_name,
            "urls": [f"https://www.clips4sale.com/performers/{p_id}/{quote(p_slug)}"],
        }

        p_data = fetch_performer_data(str(p_id), p_slug)
        if p_img := p_data.get("image"):
            performer["images"] = [p_img]
        elif img := dig(p, "avatars", "original"):
            performer["images"] = [img]

        results.append(performer)

    return results


def performer_from_url(url: str) -> ScrapedPerformer | None:
    # Example: https://www.clips4sale.com/performers/12345/performer-name
    if not (match := re.search(r"/performers/(\d+)/([^/?]+)", url)):
        return None

    p_id, p_slug = match.groups()
    api_url = f"https://www.clips4sale.com/performers/{p_id}/{p_slug}?_data=routes%2F%28%24lang%29.performers.%24performerId.%28%24performerSlug%29"

    response = fetch(api_url)
    if not response.ok or not (data := first_json_line(response)):
        log.error(f"Failed to fetch performer from URL: {url} ({response.status_code})")
        return None

    if not (p_data := dig(data, "performer")):
        return None

    # Performer page API uses "name", not "stage_name"
    if not (name := dig(p_data, "name")):
        return None

    performer: ScrapedPerformer = {"name": name, "urls": [url]}

    if img := dig(p_data, "avatars", "original", "url"):
        performer["images"] = [img]

    if related_categories := dig(data, "relatedCategories"):
        tags: list[ScrapedTag] = [
            {"name": n} for cat in related_categories if (n := cat.get("name"))
        ]
        if tags:
            performer["tags"] = tags

    return performer


if __name__ == "__main__":
    op, args = scraper_args()
    result = None

    match op, args:
        case "scene-by-name", {"name": name}:
            result = scene_search(name, detailed=False)
        case "scene-by-url", {"url": url}:
            result = scene_from_url(url)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            if url := args.get("url"):
                result = scene_from_url(url)
            elif title := args.get("title"):
                results = scene_search(title, detailed=True, limit=1)
                result = results[0] if results else None
            elif name := args.get("name"):
                results = scene_search(name, detailed=True, limit=1)
                result = results[0] if results else None
        case "performer-by-name", {"name": name}:
            result = performer_search(name, detailed=False)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            if url := args.get("url"):
                result = performer_from_url(url)
            elif name := args.get("name"):
                results = performer_search(name, detailed=True, limit=1)
                result = results[0] if results else None
        case _:
            log.error(f"Operation {op} not implemented")

    print(json.dumps(result))
