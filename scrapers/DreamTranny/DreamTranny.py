from datetime import datetime
import json
import re
import sys
from typing import Any

from py_common.deps import ensure_requirements
ensure_requirements("bs4:beautifulsoup4", "requests")
import py_common.log as log
from py_common.types import ScrapedGallery, ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag
from py_common.util import guess_nationality, scraper_args

import requests
from bs4 import BeautifulSoup as bs, Tag

STUDIO = ScrapedStudio(name="Dream Tranny", url="https://www.dreamtranny.com")

def url_to_absolute(base_url: str, url: str) -> str:
    if url.startswith("http"):
        log.debug(f"URL is already absolute: {url}")
        return url
    absolute_url = requests.compat.urljoin(base_url, url)
    log.debug(f"Converted URL to absolute: {absolute_url}")
    return absolute_url

def scrape_scene_date(date_elem: Tag):
    date_str = date_elem.get_text(strip=True)
    try:
        date_obj = datetime.strptime(date_str, "%b %d, %Y")
        return date_obj.strftime("%Y-%m-%d")
    except Exception as ex:
        log.warning(f"Error parsing date from search results: {ex}")
        return None

def scrape_performers(performer_links):
    performers: list[ScrapedPerformer] = []
    for el in performer_links:
        p_name = el.get_text(strip=True)
        p_url = el.get("href")
        if p_name and p_url:
            p_abs_url = url_to_absolute(STUDIO["url"], p_url)
            log.debug(f"Found performer: name={p_name}, url={p_abs_url}")
            performers.append(ScrapedPerformer(name=p_name, url=p_abs_url))
    return performers

def scene_from_url(url: str) -> ScrapedScene:
    sess = requests.Session()
    res = sess.get(url)
    res.raise_for_status()
    soup = bs(res.text, "html.parser")

    scene = ScrapedScene(studio=STUDIO)

    # title from xpath //div[@class="section-title"]/h4/text()
    if title_elem := soup.select_one("div.section-title > h4"):
        scene["title"] = title_elem.get_text(strip=True)
    else:
        log.warning("Title not found")

    # details from xpath //p[@class="read-more"]/text()
    details = None
    if details_elem := soup.select_one("p.read-more"):
        details = details_elem.get_text(strip=True)
        scene["details"] = details
    else:
        log.warning("Details not found")

    # date from xpath //small[@class="updated-at"]/text() with format "Jan 2, 2006"
    if date_elem := soup.select_one("small.updated-at"):
        scene["date"] = scrape_scene_date(date_elem)
    else:
        log.warning("Date not found")

    # performers from xpath //a[contains(@class, "model-name")] with name from text() and url from @href
    if performer_links := soup.select("a.model-name"):
        scene["performers"] = scrape_performers(performer_links)
    else:
        log.warning("Performers not found")

    # cover image from xpath:
    # //video[contains(@class,"video-js")]/@poster
    # or
    # //div[contains(@class,"model-player")]//img/@src
    # or
    # //video[contains(@class,"vjs")]/@poster
    cover_url = None
    if cover_url_elem := soup.select_one("video.video-js"):
        cover_url = cover_url_elem.get("poster")
        scene["image"] = url_to_absolute(url, cover_url)
    elif cover_url_elem := soup.select_one("div.model-player img"):
        cover_url = cover_url_elem.get("src")
        scene["image"] = url_to_absolute(url, cover_url)
    elif cover_url_elem := soup.select_one("video.vjs"):
        cover_url = cover_url_elem.get("poster")
        scene["image"] = url_to_absolute(url, cover_url)
    else:
        log.warning("Cover image not found")

    # tags from xpath //div[@class="model-categories"]/a/text()
    if tag_elements := soup.select("div.model-categories > a"):
        tags = [ScrapedTag(name=el.get_text(strip=True)) for el in tag_elements]
        scene["tags"] = tags
    else:
        log.warning("Tags not found")

    # url from xpath //script[contains(.,"API_VIEW_URLS")]/text()
    # with regex pattern .*/api(/update/\d+)/view_count.*
    if script_elements := soup.select("script"):
        for el in script_elements:
            if el.string and "API_VIEW_URLS" in el.string:
                match = re.search(r'.*/api(/update/(\d+)/)view_count.*', el.string)
                if match:
                    absolute_url = url_to_absolute(url, match.group(1))
                    scene["url"] = absolute_url
                    scene["urls"] = [absolute_url]
                    scene["code"] = match.group(2)
                    break
        if "url" not in scene:
            log.warning("Scene URL not found in scripts")
    else:
        log.warning("Script elements not found for URL extraction")

    return scene

def scene_search(name: str) -> list[ScrapedScene]:
    sess = requests.Session()
    search_url = f"https://www.dreamtranny.com/updates/?q={requests.utils.quote(name)}"
    res = sess.get(search_url)
    res.raise_for_status()
    soup = bs(res.text, "html.parser")

    scenes: list[ScrapedScene] = []
    # scene items from xpath //div[contains(@class, "video-item")]
    if scene_results := soup.select("div.video-item"):
        for el in scene_results:
            scene = ScrapedScene(studio=STUDIO)
            # scene link from relative xpath //div[@class="item-content"]//a[contains(@href, "/update/")]/text()
            if scene_link := el.select_one('div.item-content a[href*="/update/"]'):
                if scene_url := scene_link.get("href"):
                    log.debug(f"Found scene URL in search results: {scene_url}")
                    scene["url"] = url_to_absolute(search_url, scene_url)
                if scene_title := scene_link.get_text(strip=True):
                    scene["title"] = scene_title
            # cover image from relative xpath //a[@class="item-thumb"]/img/@src
            if cover_img := el.select_one('a.item-thumb img'):
                if cover_url := cover_img.get("src"):
                    scene["image"] = url_to_absolute(search_url, cover_url)
            # date from relative xpath //div[@class="item-content"]/div[2]/p
            if date_elem := el.select_one("div.item-content > div:nth-child(2) > p"):
                scene["date"] = scrape_scene_date(date_elem)
            # performers from relative xpath //div[@class="item-content"]//a[contains(@href, "/models/")] with name from text() and url from @href
            if performer_links := el.select('div.item-content a[href*="/models/"]'):
                scene["performers"] = scrape_performers(performer_links)
            scenes.append(scene)
    else:
        log.warning("Scene links not found in search results")

    return scenes

def scene_from_fragment(args: dict[str, Any]) -> list[ScrapedScene]:
    # if url is provided, call scene_from_url
    if url := args.get("url"):
        log.debug(f"Extracting scene from URL fragment: {url}")
        return scene_from_url(url)

    # if name is provided, call scene_search
    if name := args.get("name"):
        log.debug(f"Searching for scene by name fragment: {name}")
        if search_results := scene_search(name):
            log.debug(f"Found {len(search_results)} search results for name: {name}")
            return search_results[0]
        else:
            log.warning(f"No search results found for name: {name}")
            return None

    log.error(f"No valid fragment provided in arguments: {args}")
    return None

def gallery_from_url(url: str) -> ScrapedGallery:
    # reuse scene_from_url to get gallery info since the page structure is the same
    if scene := scene_from_url(url):
        gallery = ScrapedGallery(
            title=scene.get("title", ""),
            details=scene.get("details"),
            date=scene.get("date"),
            tags=scene.get("tags", []),
            performers=scene.get("performers", []),
            studio=scene.get("studio"),
            url=scene.get("url", ""),
            code=scene.get("code", ""),
        )
        return gallery
    return None

def gallery_from_fragment(args: dict[str, Any]) -> ScrapedGallery:
    # if url is provided, call gallery_from_url
    if url := args.get("url"):
        log.debug(f"Extracting gallery from URL fragment: {url}")
        return gallery_from_url(url)
    
    # if name is provided, call scene_search and convert first result to gallery
    if name := args.get("name"):
        log.debug(f"Searching for gallery by name fragment: {name}")
        if search_results := scene_search(name):
            log.debug(f"Found {len(search_results)} search results for name: {name}")
            first_result = search_results[0]
            gallery = ScrapedGallery(
                title=first_result.get("title", ""),
                details=first_result.get("details"),
                date=first_result.get("date"),
                tags=first_result.get("tags", []),
                performers=first_result.get("performers", []),
                studio=first_result.get("studio"),
                url=first_result.get("url", ""),
                code=first_result.get("code", ""),
            )
            return gallery
        else:
            log.warning(f"No search results found for name: {name}")
            return None

    log.error(f"No valid fragment provided for gallery extraction in arguments: {args}")
    return None

def performer_from_url(url: str) -> ScrapedPerformer:
    performer = ScrapedPerformer(gender="TRANSGENDER_FEMALE")
    sess = requests.Session()
    res = sess.get(url)
    res.raise_for_status()
    soup = bs(res.text, "html.parser")

    # remove query parameters from URL and store as performer URL
    performer["url"] = url.split("?")[0]

    # name from xpath //h1[@class="model-title"]/text()
    if name_elem := soup.select_one("h1.model-title"):
        performer["name"] = name_elem.get_text(strip=True)
    else:
        log.warning("Performer name not found")
    
    # image from xpath //div[@class="model-img"]/a/img[@class="img"]/@src
    if img_elem := soup.select_one("div.model-img a img.img"):
        if img_url := img_elem.get("src"):
            performer["image"] = url_to_absolute(url, img_url)
    else:
        log.warning("Performer image not found")
    
    if model_content := soup.select_one('div.model-content'):
        for p_tag in model_content.find_all('p'):
            spans = p_tag.find_all('span')
            for i, span in enumerate(spans):
                # country from relative xpath /p/span[text()="NATIONALITY"]/following-sibling::span[1]
                # the text values on the site are inconsistent, sometimes it can be "Brazil", other times "Brazilian"
                if span.get_text(strip=True) == "NATIONALITY" and i + 1 < len(spans):
                    country = spans[i + 1].get_text(strip=True)
                    performer["country"] = guess_nationality(country)
                # birthdate from relative xpath /p/span[text()="DATE OF BIRTH"]/following-sibling::span[1]
                if span.get_text(strip=True) == "DATE OF BIRTH" and i + 1 < len(spans):
                    birthdate_elem = spans[i + 1]
                    birthdate = birthdate_elem.get_text(strip=True)
                    # remove ordinal suffixes from birthdate (e.g. "2nd" -> "2")
                    birthdate = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", birthdate)
                    # convert birthdate from format "January 2, 2006" to "2006-01-02"
                    try:
                        birthdate_obj = datetime.strptime(birthdate, "%B %d, %Y")
                        performer["birthdate"] = birthdate_obj.strftime("%Y-%m-%d")
                    except Exception as ex:
                        log.warning(f"Error parsing performer birthdate: {ex}")
    else:
        log.warning("Performer model-content not found")

    return performer

def performer_search(name: str) -> list[ScrapedPerformer]:
    # the scene search results also include performer links, so we can reuse scene_search to find performers by name
    if search_results := scene_search(name):
        performers = []
        for scene in search_results:
            if "performers" in scene:
                performers.extend(scene["performers"])
        log.debug(f"Extracted {len(performers)} performers from search results for name: {name}")
        # deduplicate performers by name and url
        unique_performers = {}
        for performer in performers:
            key = (performer.get("name"), performer.get("url"))
            if key not in unique_performers:
                unique_performers[key] = performer
        log.debug(f"Deduplicated performers to {len(unique_performers)} unique entries for name: {name}")
        # only return performers that contain the search name (case-insensitive)
        filtered_performers = [p for p in unique_performers.values() if name.lower() in p.get("name", "").lower()]
        log.debug(f"Found {len(filtered_performers)} performers matching search name: {name}")
        return filtered_performers
    else:
        log.warning(f"No search results found for performer name: {name}")
    return []

def performer_from_fragment(args: dict[str, Any]) -> list[ScrapedPerformer]:
    # if url is provided, call performer_from_url
    if url := args.get("url"):
        log.debug(f"Extracting performer from URL fragment: {url}")
        return performer_from_url(url)

    # if name is provided, call performer_search and return results
    if name := args.get("name"):
        log.debug(f"Searching for performer by name fragment: {name}")
        return performer_search(name)

    log.error(f"No valid fragment provided for performer extraction in arguments: {args}")
    return []

if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        case "gallery-by-url", {"url": url} if url:
            result = gallery_from_url(url)
        case "gallery-by-fragment", args:
            result = gallery_from_fragment(args)
        # case "group-by-url", {"url": url} if url:
        #     result = group_from_url(url)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        case "scene-by-name", {"name": name} if name:
            result = scene_search(name)
        case "scene-by-fragment" | "scene-by-query-fragment", args:
            result = scene_from_fragment(args)
        case "performer-by-url", {"url": url}:
            result = performer_from_url(url)
        case "performer-by-fragment", args:
            result = performer_from_fragment(args)
        case "performer-by-name", {"name": name} if name:
            result = performer_search(name)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))