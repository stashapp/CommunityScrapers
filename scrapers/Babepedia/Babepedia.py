import json
import re
import sys
from datetime import datetime # birthday formatting

from py_common.proxy import StashRequests
from lxml import html

# for image
import base64

import py_common.log as log
from py_common.util import scraper_args
from py_common.types import ScrapedPerformer, PerformerSearchResult, Ethnicity, EyeColor, HairColor

scraper = StashRequests(cloudflare=True)

def fetch_as_base64(url: str) -> str | None:
  data = base64.b64encode(scraper.get(url).content).decode('utf-8')
  return f"data:image/jpg;base64,{data}"

def biography_xpath_test(tree, html_name: str, selector: str) -> str | None:
  elem = tree.xpath(f'//span[contains(text(), "{html_name}")]/following-sibling::span{selector}/text()')
  return elem[0].strip() if elem else None

def sanitize_ethnicity(str) -> Ethnicity:
    str_upper = str.upper()
    if str_upper in ["CAUCASIAN","BLACK","ASIAN","INDIAN","LATIN","MIDDLE_EASTERN","MIXED","OTHER"]:
        return str_upper
    # catch mixed-race
    if "MIXED" in str_upper:
        return str_upper
    return str # type: ignore

def sanitize_eye_color(str) -> EyeColor | None:
    str_upper = str.upper()
    if str_upper in ["Blue","Brown","Green","Grey","Hazel","Red"]:
        return str_upper
    return str

def sanitize_hair_color(str) -> HairColor:
    # brown to brunette
    if str.lower() == "brown":
        return "BRUNETTE"
    return str

def sanitize_fake_tits(value: str) -> str | None:
    # Maps Babepedia's breast type labels to Stash's valid fake_tits values:
    # "Fake", "Natural", or "Na". We never return "Na" here — if Babepedia
    # has no data, it's cleaner to leave the field unset than to store "Na".
    mapping = {
        "fake/enhanced": "Fake",    # observed on Babepedia
        "real/natural":  "Natural", # observed on Babepedia
        "fake":          "Fake",    # defensive
        "enhanced":      "Fake",    # defensive
        "augmented":     "Fake",    # defensive
        "natural":       "Natural", # defensive
        "real":          "Natural", # defensive
    }
    # Anything unrecognised returns None, which the caller treats as no data.
    return mapping.get(value.lower().strip())

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
        performer['aliases'] = ", ".join(aliases[0].strip().split(" - "))
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
    # get country - extract ISO code from flag icon class (first nationality only)
    nationality_flags = tree.xpath('//span[contains(text(), "Nationality")]/following-sibling::span//span[contains(@class, "fi-")]/@class')
    if nationality_flags:
        match = re.search(r'fi fi-([a-z]{2})', nationality_flags[0])
        if match:
            performer['country'] = match.group(1).upper()
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
        breast_type_str = "Natural" if "Real" in breast_type else "Fake" if "Fake" in breast_type else None
        if breast_type_str:
            performer['fake_tits'] = breast_type_str
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
    # get social/website URLs
    # Babepedia proxies some links as relative paths (e.g. /onlyfans/username)
    # rather than linking to the external site directly. Map known patterns;
    # log any unrecognised relative URLs so they can be added later.
    # Babepedia proxies some links through their own domain, both as relative
    # paths (/onlyfans/username) and absolute URLs
    # (https://www.babepedia.com/onlyfans/username). Map both forms.
    proxy_url_map = {
        "https://www.babepedia.com/onlyfans/": "https://onlyfans.com/",
        "/onlyfans/": "https://onlyfans.com/",
    }
    social_urls = tree.xpath('//div[@id="socialicons"]/a/@href')
    for href in social_urls:
        matched = False
        for prefix, replacement in proxy_url_map.items():
            if href.startswith(prefix):
                performer["urls"].append(href.replace(prefix, replacement, 1))
                matched = True
                break
        if not matched:
            if href.startswith("http"):
                performer["urls"].append(href)
            else:
                log.warning(f"Unrecognised relative URL skipped: {href}")
    # get images - collect all from main gallery, then user uploads
    # Returns URLs so Stash can present a picker when multiple images exist.
    base_url = "https://www.babepedia.com"
    main_imgs = tree.xpath('//div[@id="profbox2"]//a[@class="img"]/@href')
    user_imgs = tree.xpath('//div[contains(@class,"useruploads2")]//a[@class="img"]/@href')
    all_imgs = [
        fetch_as_base64(href if href.startswith("http") else f"{base_url}{href}")
        for href in main_imgs + user_imgs
    ]
    if all_imgs:
        performer["images"] = all_imgs
    return performer

def map_performer_search(performer) -> PerformerSearchResult:
    result: PerformerSearchResult = {
       "name": performer['label'],
       "url": f"https://www.babepedia.com/babe/{performer['value'].replace(' ', '_')}"
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