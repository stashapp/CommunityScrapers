import html
import json
import re
from datetime import datetime
from typing import Optional, TypedDict
from urllib.parse import quote

from py_common import cache, log
from py_common.deps import ensure_requirements
from py_common.graphql import configuration
from py_common.types import (
    PerformerSearchResult,
    SceneSearchResult,
    ScrapedPerformer,
    ScrapedScene,
    ScrapedStudio,
    ScrapedTag,
)
from py_common.util import dig, scraper_args

ensure_requirements("requests", "bs4:beautifulsoup4")

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402


class PerformerData(TypedDict):
    image: Optional[str]
    tags: list[ScrapedTag]


class StudioData(TypedDict):
    image: Optional[str]
    details: str


def parse_date(date_str: Optional[str]) -> str:
    """
    Parses a date string from Clips4Sale format (MM/DD/YY H:M AM/PM) to YYYY-MM-DD.
    """
    if not date_str:
        return ""
    try:
        # Format: "01/02/06 3:04 PM"
        dt = datetime.strptime(date_str, "%m/%d/%y %I:%M %p")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return ""


def clean_text(text: Optional[str]) -> str:
    """
    Cleans text by unescaping HTML entities, removing data attributes,
    converting <br> to newlines, and stripping whitespace.
    """
    if not text:
        return ""

    text = str(text)
    # Unescape HTML entities first (e.g. &lt;br&gt; -> <br>)
    text = html.unescape(text)
    text = re.sub(r'data-\w+="[^"]*"\s*', "", text)
    soup = BeautifulSoup(text, "html.parser")

    for br in soup.find_all("br"):
        br.replace_with("\n")

    return soup.get_text().strip()


def normalize_url(url: Optional[str]) -> Optional[str]:
    """
    Ensures a URL has the correct scheme and domain.
    """
    if url and not url.startswith("http"):
        return "https://www.clips4sale.com" + url
    return url


@cache.cache_to_disk(ttl=60)
def get_user_agent() -> str:
    default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    try:
        config = configuration()
        if config:
            return dig(config, "scraping", "scraperUserAgent") or default_ua
    except Exception:
        pass
    return default_ua


def get_scraper() -> requests.Session:
    """
    Creates and configures a requests Session with necessary headers and cookies
    for Clips4Sale.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": get_user_agent()})
    cookies = {
        "iAgreeWithUpdatedTerms": "true",
        "contentPreference": "%5B0%5D",
        "i18nextLng": "en",
    }
    for name, value in cookies.items():
        session.cookies.set(name, value, domain=".clips4sale.com", path="/")

    return session


@cache.cache_to_disk(ttl=600)
def fetch_studio_data(studio_id: str, studio_slug: str) -> StudioData:
    """
    Fetches additional studio data (image, details) from the studio page.
    Cached for 10 minutes.
    """
    scraper = get_scraper()
    url = f"https://www.clips4sale.com/studio/{studio_id}/{studio_slug}?_data=routes%2F%28%24lang%29.studio.%24id_.%24studioSlug.%24"
    try:
        response = scraper.get(url)
        if response.ok:
            # Response is newline delimited JSON
            first_line = response.text.splitlines()[0]
            data = json.loads(first_line)
            return {
                "image": dig(data, "avatarSrc"),
                "details": clean_text(dig(data, "description")),
            }
    except Exception as e:
        log.error(f"Error fetching studio data: {e}")
    return {"image": None, "details": ""}


@cache.cache_to_disk(ttl=600)
def fetch_performer_data(performer_id: str, performer_slug: str) -> PerformerData:
    """
    Fetches additional performer data (image) from the performer page.
    Cached for 10 minutes.
    """
    scraper = get_scraper()
    encoded_slug = quote(performer_slug)
    url = f"https://www.clips4sale.com/performers/{performer_id}/{encoded_slug}?_data=routes%2F%28%24lang%29.performers.%24performerId.%28%24performerSlug%29"
    try:
        response = scraper.get(url)
        if response.ok:
            # Response is newline delimited JSON
            first_line = response.text.splitlines()[0]
            data = json.loads(first_line)
            performer_data = dig(data, "performer")
            image = dig(performer_data, "avatars", "original", "url")
            tags: list[ScrapedTag] = []
            if related_categories := dig(data, "relatedCategories"):
                tags = [
                    {"name": cat.get("name")}
                    for cat in related_categories
                    if cat.get("name")
                ]
            return {"image": image, "tags": tags}
    except Exception as e:
        log.error(f"Error fetching performer data: {e}")
    return {"image": None, "tags": []}


def to_scraped_scene(
    clip: dict, detailed: bool = False
) -> ScrapedScene | SceneSearchResult:
    """
    Converts a raw clip dictionary from the API into a ScrapedScene object.
    """
    title = clean_text(dig(clip, "title"))

    studio_name = dig(clip, "studio", "name")
    studio_link = normalize_url(dig(clip, "studio", "link"))
    studio_id = dig(clip, "studio", "id")

    studio_data = {}
    if studio_link:
        # Attempt to extract ID and slug from link like /studio/12345/some-studio-name
        match = re.search(r"/studio/(\d+)/([^/?]+)", studio_link)
        if match:
            if not studio_id:
                studio_id = match.group(1)
            studio_slug = match.group(2)

            if detailed:
                studio_data = fetch_studio_data(studio_id, studio_slug)

    date_str = dig(clip, "date_display")
    date = parse_date(date_str)

    link = normalize_url(dig(clip, "link"))

    image = dig(clip, "cdn_previewlg_link") or dig(clip, "previewLink")

    performers: list[ScrapedPerformer] = []
    raw_performers = dig(clip, "performers") or []
    for p in raw_performers:
        p_name = dig(p, "stage_name")
        p_id = dig(p, "id")

        if p_name:
            performer: ScrapedPerformer = {"name": p_name}

            p_slug = dig(p, "slug") or p_name
            encoded_slug = quote(p_slug)
            performer_url = (
                f"https://www.clips4sale.com/performers/{p_id}/{encoded_slug}"
            )

            if detailed:
                performer["urls"] = [performer_url]
                p_data = fetch_performer_data(str(p_id), p_slug)
                if p_img := p_data.get("image"):
                    performer["images"] = [p_img]
                if p_tags := p_data.get("tags"):
                    performer["tags"] = p_tags
            else:
                performer["urls"] = [performer_url]

            performers.append(performer)

    unique_tags = {}
    potential_tags = []

    if category := dig(clip, "category_name"):
        potential_tags.append(category)

    if related := dig(clip, "related_category_links"):
        potential_tags.extend([r.get("category") for r in related if r.get("category")])

    if keywords := dig(clip, "keyword_links"):
        potential_tags.extend([k.get("keyword") for k in keywords if k.get("keyword")])

    for tag_name in potential_tags:
        if not tag_name:
            continue

        original = tag_name.strip()
        lower = original.lower()

        if lower not in unique_tags:
            unique_tags[lower] = original
        else:
            # Prefer the version with more uppercase letters
            current_upper = sum(1 for c in original if c.isupper())
            stored_upper = sum(1 for c in unique_tags[lower] if c.isupper())

            if current_upper > stored_upper:
                unique_tags[lower] = original

    tags: list[ScrapedTag] = [{"name": t} for t in unique_tags.values()]

    # Construct studio object
    studio_obj: ScrapedStudio = {"name": studio_name}

    if studio_link and detailed:
        studio_obj["urls"] = [studio_link]

    if studio_img := studio_data.get("image"):
        studio_obj["image"] = studio_img

    if studio_details := clean_text(studio_data.get("details")):
        studio_obj["details"] = studio_details

    if studio_id:
        studio_obj["aliases"] = str(studio_id)

    if not detailed:
        # Return SceneSearchResult
        res: SceneSearchResult = {
            "title": title,
            "url": link or "",
            "studio": studio_obj,
        }
        if date:
            res["date"] = date
        if image:
            res["image"] = image
        if tags:
            res["tags"] = tags
        if performers:
            res["performers"] = performers
        return res

    clip_id = dig(clip, "id")

    scene: ScrapedScene = {}

    if title:
        scene["title"] = title

    if clip_id:
        scene["code"] = str(clip_id)

    if date:
        scene["date"] = date

    if link:
        scene["urls"] = [link]

    if image:
        scene["image"] = image

    if performers:
        scene["performers"] = performers

    if tags:
        scene["tags"] = tags

    if details := clean_text(dig(clip, "description")):
        scene["details"] = details

    scene["studio"] = studio_obj

    return scene


def scene_search(
    query: str, detailed: bool = False, limit: Optional[int] = None
) -> list[ScrapedScene] | list[SceneSearchResult]:
    """
    Searches for scenes by query string.
    """
    scraper = get_scraper()
    encoded_query = quote(query)
    url = f"https://www.clips4sale.com/clips/search/{encoded_query}/category/0/storesPage/1/clipsPage/1?_data=routes%2F%28%24lang%29.clips.search.%24"

    log.debug(f"Searching URL: {url}")
    try:
        response = scraper.get(url)
        if not response.ok:
            log.error(f"Search failed with status code {response.status_code}")
            return []

        data = response.json()
    except Exception as e:
        log.error(f"Error fetching or parsing JSON: {e}")
        return []

    clips = dig(data, "clips") or []
    results = []

    for clip in clips:
        if limit and len(results) >= limit:
            break
        res = to_scraped_scene(clip, detailed=detailed)
        results.append(res)

    return results


def scene_from_url(url: str) -> Optional[ScrapedScene | SceneSearchResult]:
    """
    Scrapes a single scene from a direct URL.
    """
    scraper = get_scraper()

    # Example: https://www.clips4sale.com/studio/23235/22576135/interviewing-thew-new-maid-part-one-interview-only-4k-mp4-vid0541a
    match = re.search(r"/studio/(\d+)/(\d+)/([^/?]+)", url)
    if match:
        studio_id = match.group(1)
        clip_id = match.group(2)
        slug = match.group(3)

        data_url = f"https://www.clips4sale.com/studio/{studio_id}/{clip_id}/{slug}?_data=routes%2F%28%24lang%29.studio.%24id_.%24clipId.%24clipSlug"
        log.debug(f"Fetching direct scene data from: {data_url}")

        try:
            response = scraper.get(data_url)
            if response.ok:
                # Response is newline delimited JSON, first line is what we want
                first_line = response.text.splitlines()[0]
                data = json.loads(first_line)

                if clip_data := dig(data, "clip"):
                    return to_scraped_scene(clip_data, detailed=True)
        except Exception as e:
            log.error(f"Error fetching direct scene data: {e}")

    # Fallback to search by Title/Slug
    match = re.search(r"/studio/\d+/(\d+)/([^/?]+)", url)
    if match:
        clip_id = match.group(1)
        slug = match.group(2)
        search_query = slug.replace("-", " ")
        log.debug(f"Extracted slug: {slug}, searching for: {search_query}")

        results = scene_search(search_query, detailed=True)

        for res in results:
            # Check if res is ScrapedScene (has code)
            if "code" in res and res.get("code") == clip_id:
                return res

        if results:
            return results[0]

    log.error("Could not extract clip info for fallback search")
    return None


def performer_search(
    query: str, detailed: bool = False, limit: Optional[int] = None
) -> list[ScrapedPerformer] | list[PerformerSearchResult]:
    """
    Searches for performers by query string using the Clips4Sale API.
    """
    scraper = get_scraper()
    encoded_query = quote(query)
    url = f"https://www.clips4sale.com/api/performer-list?keyword={encoded_query}&sort=top_100&_data=routes%2Fapi.performer-list"

    log.debug(f"Searching Performer URL: {url}")
    try:
        response = scraper.get(url)
        if not response.ok:
            log.error(
                f"Performer search failed with status code {response.status_code}"
            )
            return []

        data = response.json()
    except Exception as e:
        log.error(f"Error fetching or parsing performer-list JSON: {e}")
        return []

    performers_data = dig(data, "performers") or []
    results = []

    for p in performers_data:
        if limit and len(results) >= limit:
            break

        p_id = dig(p, "id")
        p_name = dig(p, "stage_name")

        if not p_id or not p_name:
            continue

        p_slug = dig(p, "slug") or p_name
        encoded_slug = quote(p_slug)

        performer_url = f"https://www.clips4sale.com/performers/{p_id}/{encoded_slug}"

        if not detailed:
            res: PerformerSearchResult = {"name": p_name, "url": performer_url}
            results.append(res)
            continue

        performer: ScrapedPerformer = {"name": p_name, "urls": [performer_url]}

        if detailed:
            p_data = fetch_performer_data(str(p_id), p_slug)
            if p_img := p_data.get("image"):
                performer["images"] = [p_img]

        if "images" not in performer:
            if img := dig(p, "avatars", "original"):
                performer["images"] = [img]

        results.append(performer)

    return results


def performer_from_url(url: str) -> Optional[ScrapedPerformer]:
    """
    Scrapes a single performer from a direct URL.
    """
    scraper = get_scraper()

    # Example: https://www.clips4sale.com/performers/12345/performer-name
    match = re.search(r"/performers/(\d+)/([^/?]+)", url)
    if not match:
        return None

    p_id = match.group(1)
    p_slug = match.group(2)

    encoded_slug = quote(p_slug)
    api_url = f"https://www.clips4sale.com/performers/{p_id}/{encoded_slug}?_data=routes%2F%28%24lang%29.performers.%24performerId.%28%24performerSlug%29"

    try:
        response = scraper.get(api_url)
        if response.status_code == 200:
            # Response is newline delimited JSON
            first_line = response.text.splitlines()[0]
            data = json.loads(first_line)

            p_data = dig(data, "performer")
            if not p_data:
                return None

            # Performer page API uses "name", not "stage_name"
            name = dig(p_data, "name")
            if not name:
                return None

            performer: ScrapedPerformer = {
                "name": name,
                "urls": [url],
            }

            # avatars is nested: {"original": {"url": "..."}}
            if img := dig(p_data, "avatars", "original", "url"):
                performer["images"] = [img]

            if related_categories := dig(data, "relatedCategories"):
                tags: list[ScrapedTag] = [
                    {"name": cat.get("name")}
                    for cat in related_categories
                    if cat.get("name")
                ]
                if tags:
                    performer["tags"] = tags

            return performer

    except Exception as e:
        log.error(f"Error fetching performer from URL: {e}")

    return None


def main():
    try:
        op, args = scraper_args()
        log.debug(f"Operation: {op}, Args: {args}")
        output = {}

        match op, args:
            case "scene-by-name", {"name": name}:
                output = scene_search(name, detailed=False)
            case "scene-by-url", {"url": url}:
                output = scene_from_url(url)
            case "scene-by-fragment" | "scene-by-query-fragment", args:
                if url := args.get("url"):
                    output = scene_from_url(url)
                elif title := args.get("title"):
                    # Stash expects a single object for fragment scraping in some contexts
                    results = scene_search(title, detailed=True, limit=1)
                    output = results[0] if results else {}
                elif name := args.get("name"):
                    results = scene_search(name, detailed=True, limit=1)
                    output = results[0] if results else {}
            case "performer-by-name", {"name": name}:
                output = performer_search(name, detailed=False)
            case "performer-by-url", {"url": url}:
                output = performer_from_url(url)
            case "performer-by-fragment", args:
                if url := args.get("url"):
                    output = performer_from_url(url)
                elif name := args.get("name"):
                    results = performer_search(name, detailed=True, limit=1)
                    output = results[0] if results else {}
            case _:
                log.error(f"Operation {op} not implemented")

        log.debug(f"Output: {output}")
        print(json.dumps(output or {}))
    except Exception as e:
        log.error(f"Error running scraper: {e}")


if __name__ == "__main__":
    main()
