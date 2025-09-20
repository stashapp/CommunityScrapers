import json
import re
import sys
from datetime import datetime # birthday formatting
from urllib import parse

import cloudscraper
from lxml import html

# for image
import base64
import requests

import py_common.log as log
from py_common.util import scraper_args
from py_common.types import ScrapedPerformer

scraper = cloudscraper.create_scraper()

FIREFOX_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0"

def fetch_as_base64(url: str) -> str | None:
  return base64.b64encode(requests.get(url, headers={ 'User-Agent': FIREFOX_UA }).content).decode('utf-8')

def biography_xpath_test(tree, html_name: str, selector: str) -> str | None:
  elem = tree.xpath(f'//span[contains(text(), "{html_name}")]/following-sibling::span{selector}/text()')
  return elem[0].strip() if elem else None

def performer_from_url(url) -> ScrapedPerformer:
    scraped = scraper.get(url)
    scraped.raise_for_status()
    tree = html.fromstring(scraped.text)

    performer: ScrapedPerformer = {}
    performer['urls'] = [url]
    performer['name'] = tree.xpath('//h1[@id="babename"]')[0].text.strip()
    # fixed geneder
    performer['gender'] = 'FEMALE'
    aliases = tree.xpath('//h2[@id="aka"][1]/text()')
    if aliases:
      performer['aliases'] = ", ".join(aliases[0].split(" - "))
    # get birthdate
    birth_container = tree.xpath('//span[contains(text(), "Born:")]/following-sibling::span')
    if birth_container:
      birth_container = birth_container[0]
      birth_year = birth_container.getchildren()[1].text_content().strip()
      birth_date = birth_container.getchildren()[0].text_content().strip()
      clean_birth_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', birth_date) # remove suffix
      birthdate = datetime.strptime(f"{clean_birth_date} {birth_year}", "%d of %B %Y").date()
      performer['birthdate'] = birthdate.isoformat()
    # get nationality
    nationality = biography_xpath_test(tree, "Nationality", "")
    if nationality:
      performer['country'] = nationality.strip("() ")
    # get ethnicity
    ethnicity = biography_xpath_test(tree, "Ethnicity", "/a")
    if ethnicity:
      performer['ethnicity'] = ethnicity.upper()
    # get eye color
    eye_color = biography_xpath_test(tree, "Eye color", "/a")
    if eye_color:
      performer['eye_color'] = eye_color
    # get hair color
    hair_color = biography_xpath_test(tree, "Hair color", "/a")
    if hair_color:
      performer['hair_color'] = hair_color
    # get height
    height = biography_xpath_test(tree, "Height", "")
    if height:
      cm_height = re.search(r'(\d+) cm', height)[1]
      performer['height'] = cm_height
    # get measurements
    measurements = biography_xpath_test(tree, "Measurements", "")
    cup_size = biography_xpath_test(tree, "Bra/cup size", "")
    if measurements and cup_size:
      measurements_split = measurements.split("-")
      performer['measurements'] = f"{measurements_split[0]}{cup_size}-{measurements_split[1]}-{measurements_split[2]}"
    if measurements and not cup_size:
      performer['measurements'] = measurements
    # get fake/naturals
    breast_type = biography_xpath_test(tree, "Boobs", "/a")
    if breast_type:
      real_breasts = breast_type == "Real/Natural"
      performer['fake_tits'] = str(not real_breasts)
    # get images
    img_url = tree.xpath('//div[@id="profimg"]/a/@href')
    if img_url:
      b64img = fetch_as_base64(f"https://www.babepedia.com/{img_url[0]}")
      performer['images'] = [f"data:image/jpg;base64,{b64img}"]
    return performer

if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))
