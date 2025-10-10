import json
import re
import sys
from datetime import datetime # birthday formatting

import cloudscraper
from lxml import html

# for image
import base64

import py_common.log as log
from py_common.util import scraper_args
from py_common.types import ScrapedPerformer, PerformerSearchResult, Ethnicity, EyeColor, HairColor

scraper = cloudscraper.create_scraper()

def fetch_as_base64(url: str) -> str | None:
  return base64.b64encode(scraper.get(url).content).decode('utf-8')

def biography_xpath_test(tree, html_name: str, selector: str) -> str | None:
  elem = tree.xpath(f'//span[contains(text(), "{html_name}")]/following-sibling::span{selector}/text()')
  return elem[0].strip() if elem else None

def sanitize_ethnicity(str) -> Ethnicity:
    str = str.upper()
    if str in ["CAUCASIAN","BLACK","ASIAN","INDIAN","LATIN","MIDDLE_EASTERN","MIXED","OTHER"]:
        return str
    # catch mixed-race
    if "Mixed" in str.lower():
        return str
    return "Other" # type: ignore

def sanitize_eye_color(str) -> EyeColor | None:
    str = str.upper()
    if str in ["Blue","Brown","Green","Grey","Hazel","Red"]:
        return str
    return None

def sanitize_hair_color(str) -> HairColor:
    str = str.upper()
    if str in ["Blonde","Brunette","Black","Red","Auburn","Grey","Bald","Various","Other"]:
        return str
    # brown to brunette
    if str.lower() == "brown":
        return "Brunette" # type: ignore
    return "Other" # type: ignore

def performer_from_url(url) -> ScrapedPerformer:
    scraped = scraper.get(url)
    scraped.raise_for_status()
    tree = html.fromstring(scraped.text)

    performer: ScrapedPerformer = {
        "name": tree.xpath('//h1[@id="babename"]')[0].text.strip(),
        "urls": [url],
        # fixed gender
        "gender": 'FEMALE'
    }
    aliases = tree.xpath('//h2[@id="aka"][1]/text()')
    if aliases:
        performer['aliases'] = ", ".join(aliases[0].split(" - "))
    # get birthdate
    birth_container = tree.xpath('//span[contains(text(), "Born:")]/following-sibling::span/a')
    if birth_container:
        if len(birth_container) == 2:
            birth_text = map(lambda x: x.text_content().strip(), birth_container)
            birth_date = " ".join(birth_text)
            clean_birth_date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', birth_date) # remove suffix
            birthdate = datetime.strptime(f"{clean_birth_date}", "%d of %B %Y").date()
            performer['birthdate'] = birthdate.isoformat()
        elif len(birth_container) == 1:
            birth_year = birth_container[0].text_content().strip()
            performer['birthdate'] = birth_year
    # get death date
    death_date = biography_xpath_test(tree, "Died", "")
    if death_date:
        clean_death_date = re.sub(r'\w+ (\d+)(?:st|nd|rd|th) of (\w+) (\d+) \(.+\)', r'\1 \2 \3', death_date) # remove prefix, date
        deathdate = datetime.strptime(f"{clean_death_date}", "%d %B %Y").date()
        performer['death_date'] = deathdate.isoformat()
    # get career length
    career = biography_xpath_test(tree, "Years active", "")
    if (career):
        years = career.split(" ", 1)[0]
        start, end = years.split("-")
        if end == "Present":
            performer["career_length"] = f"{start}-"
        else:
            performer["career_length"] = f"{start} - {end}"
    # get country
    country = biography_xpath_test(tree, "Nationality", "")
    if country:
       performer['country'] = country.strip("() ")
    # get ethnicity
    ethnicity = biography_xpath_test(tree, "Ethnicity", "/a")
    if ethnicity:
        performer['ethnicity'] = sanitize_ethnicity(ethnicity)
    # get eye color
    eye_color = biography_xpath_test(tree, "Eye color", "/a")
    if eye_color:
        eye_color_str = sanitize_eye_color(eye_color)
        if eye_color_str:
            performer['eye_color'] = eye_color_str
    # get hair color
    hair_color = biography_xpath_test(tree, "Hair color", "/a")
    if hair_color:
        performer['hair_color'] = sanitize_hair_color(hair_color)
    # get height
    height = biography_xpath_test(tree, "Height", "")
    if height:
        cm_height = re.search(r'(\d+) cm', height)
        if cm_height:
            performer['height'] = cm_height[1]
    # get weight
    weight = biography_xpath_test(tree, "Weight", "")
    if weight:
        kg_weight = re.search(r'(\d+) kg', weight)
        if kg_weight:
            performer['weight'] = kg_weight[1]
    # get measurements
    measurements = biography_xpath_test(tree, "Measurements", "")
    cup_size = biography_xpath_test(tree, "Bra/cup size", "")
    if measurements and cup_size:
        measurements_split = measurements.split("-")
        performer['measurements'] = f"{cup_size}-{measurements_split[1]}-{measurements_split[2]}"
    if measurements and not cup_size:
        performer['measurements'] = measurements
    # get fake/naturals
    breast_type = biography_xpath_test(tree, "Boobs", "/a")
    if breast_type:
        real_breasts = breast_type == "Real/Natural"
        performer['fake_tits'] = str(not real_breasts)
    # get tattoos
    tattoos = biography_xpath_test(tree, "Tattoos", "")
    if tattoos and tattoos != "None":
        performer['tattoos'] = tattoos # not split
    # get piercings
    piercings = biography_xpath_test(tree, "Piercings", "")
    if piercings and piercings != "None":
        performer["piercings"] = piercings
    # get bio
    bio = tree.xpath('//p[@id="biotext"]')
    if bio:
        performer["details"] = bio[0].text_content().strip()
    # get images
    img_url = tree.xpath('//div[@id="profimg"]/a/@href')
    if img_url:
        b64img = fetch_as_base64(f"https://www.babepedia.com/{img_url[0]}")
        performer['images'] = [f"data:image/jpg;base64,{b64img}"]
    return performer

def map_performer_search(performer) -> PerformerSearchResult:
    result: PerformerSearchResult = {
       "name": performer['label'],
       "url": f"https://www.babepedia.com/babe/{performer['value']}"
    }
    return result

def performer_by_name(name) -> list[PerformerSearchResult]:
    url = f"https://www.babepedia.com/ajax-search.php?term={name}"
    scraped = scraper.get(url)
    scraped.raise_for_status()
    data = scraped.json()
    return list(map(map_performer_search,data))

if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "performer-by-url", {"url": url} if url:
            result = performer_from_url(url)
        case "performer-by-name", {"name": name} if name:
            result = performer_by_name(name)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
    print(json.dumps(result))
