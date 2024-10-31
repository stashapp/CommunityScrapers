import datetime
import json
import os
import re
import sys
from configparser import ConfigParser, NoSectionError
from urllib.parse import urlparse

import requests
from py_common.deps import ensure_requirements
from py_common import log

ensure_requirements("cloudscraper")
import cloudscraper

ensure_requirements("lxml")
from lxml import html, etree

scraper = cloudscraper.create_scraper()

def base64_image(url) -> str:
    import base64
    b64img_bytes = base64.b64encode(scraper.get(url).content)
    return f"data:image/jpeg;base64,{b64img_bytes.decode('utf-8')}"

def scrape(url: str, retries=0):
    try:
        scraped = scraper.get(url, timeout=(3, 7))
    except requests.exceptions.Timeout as exc_time:
        log.debug(f"Timeout: {exc_time}")
        return scrape(url, retries + 1)
    except Exception as e:
        log.error(f"scrape error {e}")
        sys.exit(1)
    if scraped.status_code >= 400:
        log.error(f"HTTP Error: {scraped.status_code}")
        sys.exit(1)
    return html.fromstring(scraped.content)


def scene_title(tree):
    raw = tree.xpath("//meta[@property='og:title']/@content")
    if not raw or len(raw) < 1:
        return ""
    return raw[0].split('|')[0].strip()

def scene_date(tree):
    stash_date = "%Y-%m-%d"
    date_format = "%B %d, %Y"
    raw = tree.xpath("//div[contains(@class, 'video_info_wrapper')]//span[@id='release_date']/@title")[0]
    raw = re.sub(r'(\d)(st|nd|rd|th)', r'\1', raw)
    return datetime.datetime.strptime(raw, date_format).strftime(stash_date)

def scene_details(tree):
    rawDescription = tree.xpath("//*[contains(@class, 'video_description')]")
    details = rawDescription[0].text_content()

    songs = ""
    rawSong = tree.xpath("//a[contains(@class, 'song_link')]//span/text()")
    rawSongs = zip(rawSong[::2], rawSong[1::2])
    for (songTitle, songAuthor) in rawSongs:
        songs += "\n" + songAuthor + " - " + songTitle

    if songs != "":
        details = details + "\n\nSongs: " + songs
    return details

def scene_tags(tree):
    # Tags do not appear anymore on the site
    return []

def get_performers(tree):
    detailsUrl = tree.xpath("//*[@id='current-video']//button[contains(@class, 'btn-plus')]/@hx-get")
    if not detailsUrl or len(detailsUrl) < 1:
        return []
    
    scrapedPerformers = scrape("https://www.noodledude.io" + detailsUrl[0])
    performerList = scrapedPerformers.xpath("//a[contains(@class, 'performer_card')]//span[1]/text()")
    return [
        {
            "name" : performerName
        }
        for performerName in performerList
    ]

def scene_image(tree):
    rawUrl = tree.xpath("//video[@id='player']/@poster")[0]
    return base64_image(rawUrl)

def scene_from_tree(tree):
    return {
        "title": scene_title(tree),
        "date": scene_date(tree),
        "details": scene_details(tree),
        "tags" : scene_tags(tree),
        "image" : scene_image(tree),
        "studio": {
            "name" : "NoodleDudePMV"
        },
        "performers": get_performers(tree)
    }

if __name__ == "__main__":
    params = json.loads(sys.stdin.read())
    scraped = scrape(params["url"])
    result = {}
    result = scene_from_tree(scraped)
    result["url"] = params["url"]
    print(json.dumps(result))