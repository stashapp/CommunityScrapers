from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import os
import re
import sys
from typing import Any

from py_common.deps import ensure_requirements
ensure_requirements("bs4:beautifulsoup4", "requests")
import py_common.log as log
from py_common.types import ScrapedGallery, ScrapedGroup, ScrapedPerformer, ScrapedScene, ScrapedStudio, ScrapedTag
from py_common.util import dig, guess_nationality, scraper_args

import requests
from bs4 import BeautifulSoup as bs

STUDIO = ScrapedStudio(name="Dream Tranny", url="https://www.dreamtranny.com")

def relative_url_to_absolute(base_url: str, relative_url: str) -> str:
    log.debug(f"Converting relative URL to absolute: base_url={base_url}, relative_url={relative_url}")
    if relative_url.startswith("http"):
        return relative_url
    return requests.compat.urljoin(base_url, relative_url)

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
        date_str = date_elem.get_text(strip=True)
        try:
            # parse string to a datetime object
            date_obj = datetime.strptime(date_str, "%b %d, %Y")
            # format date as "YYYY-MM-DD"
            scene["date"] = date_obj.strftime("%Y-%m-%d")
        except Exception as ex:
            log.warning(f"Error parsing date: {ex}")
    else:
        log.warning("Date not found")

    # performers from xpath //a[contains(@class, "model-name")] with name from text() and url from @href
    if performer_links := soup.select("a.model-name"):
        performers: list[ScrapedPerformer] = []
        for el in performer_links:
            p_name = el.get_text(strip=True)
            p_url = el.get("href")
            if p_name and p_url:
                log.debug(f"Found performer: name={p_name}, url={p_url}")
                performers.append(ScrapedPerformer(name=p_name, url=p_url))
        # male performers are often mentions in the description
        # so we can try to extract them from there using a regex pattern for likely full names
        if details and (description_performers := re.findall("([A-Z][a-z]+ [A-Z][a-z]+)", details, re.DOTALL)):
            for dp in description_performers:
                if not any(dp == p["name"] for p in performers):
                    log.debug(f"Adding performer from description: {dp}")
                    performers.append(ScrapedPerformer(name=dp))
        scene["performers"] = performers
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
        scene["image"] = relative_url_to_absolute(url, cover_url)
    elif cover_url_elem := soup.select_one("div.model-player img"):
        cover_url = cover_url_elem.get("src")
        scene["image"] = relative_url_to_absolute(url, cover_url)
    elif cover_url_elem := soup.select_one("video.vjs"):
        cover_url = cover_url_elem.get("poster")
        scene["image"] = relative_url_to_absolute(url, cover_url)
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
                    absolute_url = relative_url_to_absolute(url, match.group(1))
                    log.debug(f"Extracted scene URL: {absolute_url}")
                    scene["url"] = absolute_url
                    scene["urls"] = [absolute_url]
                    scene["code"] = match.group(2)
                    break
        if "url" not in scene:
            log.warning("Scene URL not found in scripts")
    else:
        log.warning("Script elements not found for URL extraction")

    return scene

if __name__ == "__main__":
    op, args = scraper_args()

    log.debug(f"args: {args}")
    match op, args:
        # case "gallery-by-url", {"url": url} if url:
        #     result = gallery_from_url(url)
        # case "gallery-by-fragment", args:
        #     result = gallery_from_fragment(args)
        # case "group-by-url", {"url": url} if url:
        #     result = group_from_url(url)
        case "scene-by-url", {"url": url} if url:
            result = scene_from_url(url)
        # case "scene-by-name", {"name": name} if name:
        #     result = scene_search(name)
        # case "scene-by-fragment" | "scene-by-query-fragment", args:
        #     result = scene_from_fragment(args)
        # case "performer-by-url", {"url": url}:
        #     result = performer_from_url(url)
        # case "performer-by-fragment", args:
        #     result = performer_from_fragment(args)
        # case "performer-by-name", {"name": name} if name:
        #     result = performer_search(name)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))