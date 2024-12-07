import json
import re
import sys
import urllib.parse
from itertools import chain, zip_longest
from difflib import SequenceMatcher
import array as arr


import py_common.log as log
import requests

from lxml import html

PROXIES = {}
TIMEOUT = 10

STUDIOS = {
    "Ultra Films": None,
    "All Fine Girls": 24,
    "WowGirls": 32,
    "WowPorn": 36,
}

session = requests.Session()
session.proxies.update(PROXIES)


class WowVenus:
    def __init__(self):
        self.search_results = {}

    def count_results_pages(self, studio_name):
        return len(self.search_results.get(studio_name, []))

    def wow_sub_studio_filter_toggle(self, studio_key, studio_name):
        query_studio_name = studio_name.replace(" ", "").lower()
        data = f"__operation=toggle&__state=sites%3D{studio_key}"
        scraped = None
        try:
            scraped = session.post(
                f"https://venus.{query_studio_name}.com/search/cf", data=data
            )
        except Exception as ex:
            log.error(f"scrape error: {ex}")
            return None
        if scraped.status_code >= 400:
            log.error(f"HTTP Error: {scraped.status_code}")
        scraped = scraped.content.decode("utf-8")
        return scraped

    def scrape_all_results_pages(self, page_content, studio_name):
        if not page_content.xpath('//div[@class="no_results"]'):
            if not self.search_results.get(studio_name):
                self.search_results[studio_name] = []
            self.search_results[studio_name].append(page_content)
            pagignator = page_content.xpath(
                "//div[@class='paginator']/div[@class='pages']//text()"
            )
            for pageNu in pagignator[1:]:
                page_content = html.fromstring(self.pageNu_scrape(studio_name, pageNu))
                self.search_results[studio_name].append(page_content)

    def GET_req(self, url):
        scraped = None
        try:
            scraped = session.get(url, timeout=TIMEOUT)
        except Exception as ex:
            log.error(f"scrape error: {ex}")
            return None
        if scraped.status_code >= 400:
            log.error(f"HTTP Error: {scraped.status_code}")
            return None
        return scraped.content

    def set_video_filter(self, studio_name):
        query_studio_name = studio_name.replace(" ", "").lower()
        url = f"https://venus.{query_studio_name}.com/search/cf"
        data = "__state=contentTypes%3D%5Bvideo%5D"
        scraped = None
        try:
            scraped = session.post(url, data=data, timeout=TIMEOUT)
        except Exception as ex:
            log.error(f"scrape error: {ex}")
            return None
        if scraped.status_code >= 400:
            log.error(f"HTTP Error: {scraped.status_code}")
            return None
        scraped = scraped.content.decode("utf-8")
        return scraped

    def pageNu_scrape(self, studio_name, pageNu):
        query_studio_name = studio_name.replace(" ", "").lower()
        url = f"https://venus.{query_studio_name}.com/search/cf"
        data = f"__state=paginator.page%3D{pageNu}"
        try:
            scraped = session.post(url, data=data, timeout=TIMEOUT)
        except Exception as ex:
            log.error(f"scrape error: {ex}")
        if scraped.status_code >= 400:
            log.error(f"HTTP Error: {scraped.status_code}")
        scraped = scraped.content.decode("utf-8")
        return scraped

    def output_json(self, title, tags, url, img, studio, performers):
        return {
            "title": title,
            "tags": [{"name": x} for x in tags],
            "url": url,
            "image": img,
            "studio": {"name": studio},
            "performers": [{"name": x.strip()} for x in performers],
        }

    def scene_card_parse(self, scene_card):
        title = scene_card.xpath('./a[@class="title"]/text()')[0].strip()
        imgurl = scene_card.xpath(".//img[@title]/@src")[0]
        if URL:
            imgurl = re.sub(r"_\w*", "_1280x720", imgurl)
        performers = scene_card.xpath('.//*[@class="models"]/a/text()')
        tags = scene_card.xpath('.//span[@class="genres"]/a/text()')
        return title, imgurl, performers, tags

    def parse_results(self):  # parse all scene elements, return all
        parsed_scenes = {}
        for studio_name, pages in self.search_results.items():
            query_studio_name = studio_name.replace(" ", "").lower()
            for page in pages:
                scene_cards = page.xpath(
                    '//div[contains(@class, "ct_video")]//img[@title]/ancestor::div'
                )
                for scene_card in scene_cards:
                    url = (
                        f"https://venus.{query_studio_name}.com"
                        + scene_card.xpath("./a/@href")[0]
                    )
                    title, img, performers, tags = self.scene_card_parse(scene_card)
                    if not parsed_scenes.get(query_studio_name):
                        parsed_scenes[query_studio_name] = []
                    parsed_scenes[query_studio_name].append(
                        self.output_json(title, tags, url, img, studio_name, performers)
                    )
        return parsed_scenes

    def get_scene_with_id(
        self, scene_ID
    ):  # parse all scene elements, return single with matched id
        for studio_name, pages in self.search_results.items():
            query_studio_name = studio_name.replace(" ", "").lower()
            for page in pages:
                scene_cards_with_ID = page.xpath(
                    f'//div[contains(@class, "ct_video")]//a[contains(@href,"{scene_ID}")]/ancestor::div'
                )
                if scene_cards_with_ID:
                    scene_card = scene_cards_with_ID[0]
                    url = (
                        f"https://venus.{query_studio_name}.com"
                        + scene_card.xpath("./a/@href")[0]
                    )
                    title, b64img, performers, tags = self.scene_card_parse(scene_card)
                    return self.output_json(
                        title, tags, url, b64img, studio_name, performers
                    )

    def search(self, query_title, studio_name, studio_key):
        query_studio_name = studio_name.replace(" ", "").lower()
        url = f"https://venus.{query_studio_name}.com/search/?query={query_title}"
        self.GET_req(url)  # send search request, needed for session data
        # set 'video only' filter for results
        scraped = self.set_video_filter(query_studio_name)
        page_content = html.fromstring(scraped)
        if studio_key:  # use studio_key to filter search results by sub studio
            scraped = self.wow_sub_studio_filter_toggle(
                studio_key, query_studio_name
            )  # toggle on
            page_content = html.fromstring(scraped)
        self.scrape_all_results_pages(page_content, studio_name)
        if studio_key:
            self.wow_sub_studio_filter_toggle(
                studio_key, query_studio_name
            )  # toggle off
        log.debug(
            f"Searched {studio_name}, found {self.count_results_pages(studio_name)} pages"
        )


def interleave_results(parsed_scenes):  # interleave search results by studio
    interleaved = [
        x
        for x in chain.from_iterable(zip_longest(*parsed_scenes.values()))
        if x is not None
    ]
    return interleaved


def search_query_prep(string: str):
    string = string.replace("’", "'")
    a = [s for s in string if s.isalpha() or s.isspace() or s == "-" or s == "'"]
    string = "".join(a)
    return urllib.parse.quote(string)

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def isSingleLetterEnglishWord(word: str):
    word = word.lower()
    return (word == "a" or word == "i")

def commonWordFixes(word: str):
    word = word.lower()
    if word == "cant":
        return "can't"
    else:
        return word

def unCamelCase(string: str):
    substring = ""
    resultstring = ""
    for i, v in enumerate(string):
        if v.isupper() or v.isnumeric():
            if len(substring) > 1 or isSingleLetterEnglishWord(substring):
                resultstring = resultstring + commonWordFixes(substring) + " "
                substring = ""
        substring = substring + v
    
    return resultstring + substring

def parseFilename(string: str):
    list = string.split("_")
    if(len(list) > 2):
        name = list[-3]
        name = unCamelCase(name)
        
        artists = list[0:-3]
        artists = [unCamelCase(artist) for artist in artists]

        return {
            "parseable": True,
            "name": name,
            "artists": artists
        }
    else:
        return {
            "parseable": False,
            "name": string,
            "artists": []
        }

def sortBySimilarity(originalName, originalPerformers, options):
    scores = arr.array('d', [])

    originalName_lowercase = originalName.lower()
    originalPerformers_lowercase = [x.lower() for x in originalPerformers]

    for scene in options:
        optionName = scene["title"]
        optionName_lowercase = optionName.lower()

        optionPerformers = [artist["name"] for artist in scene["performers"]]
        optionPerformers_lowercase = [x.lower() for x in optionPerformers]

        nameSimilarity = similar(originalName_lowercase, optionName_lowercase)
        performersSimilarity = similar(sorted(originalPerformers_lowercase), sorted(optionPerformers_lowercase))

        log.debug("similarity between \"" + str(originalName) + "\" and \"" + str(optionName) + "\" is: " + str(nameSimilarity * 100) + "%")
        log.debug("similarity between " + str(originalPerformers) + " and " + str(optionPerformers) + " is: " + str(performersSimilarity * 100) + "%")

        this_similarity = ((nameSimilarity + performersSimilarity) / 2)

        log.debug("score: "+ str(this_similarity))

        scores.append(this_similarity)
        
    zipped = zip(scores, options)

    sortedScenes = [scene for _, scene in sorted(zipped, reverse=True, key = lambda x: x[0])]

    log.debug(sortedScenes)

    return sortedScenes

FRAGMENT = json.loads(sys.stdin.read())

URL = FRAGMENT.get("url")
scraper = WowVenus()

log.debug(sys.argv[1]);

if sys.argv[1] == "url" or sys.argv[1] == "fragment":
    ret = {}
    
    query_title = URL.split("/")[-1].replace("-", " ")
    query_title = ''.join([i for i in query_title if not i.isdigit()]) #remove numbers from string, because searches that contain numbers will get no results
    query_title = urllib.parse.unquote(query_title)
    scene_ID = URL.split("/")[4]
    log.debug(f'Searching for "{query_title}"')
    for studio_name, studio_key in STUDIOS.items():
        scraper.search(query_title, studio_name, studio_key)
        if ret := WowVenus.get_scene_with_id(scraper, scene_ID):
            log.debug("Scene found!")
            break
    if not ret:
        log.error(
            "Scene not found!\nSome scenes do not appear in search results unless you are logged in!"
        )
        sys.exit()
    
    print(json.dumps(ret))
elif sys.argv[1] == "query":
    parsedFilename = parseFilename(FRAGMENT.get('title'))

    NAME = parsedFilename["name"]
    ARTISTS = parsedFilename["artists"]

    log.debug("set NAME from title: " + NAME)

    if NAME:
        log.debug(f'Searching for "{NAME}"')
        query_title = search_query_prep(NAME)
        for studio_name, studio_key in STUDIOS.items():
            scraper.search(query_title, studio_name, studio_key)
        parsed_scenes = scraper.parse_results()
        interleaved = interleave_results(parsed_scenes)
        if(len(interleaved) > 0):
            sortedBySimilarity = sortBySimilarity(NAME, ARTISTS, interleaved)

            print(json.dumps(sortedBySimilarity[0]))
else:
    parsedFilename = parseFilename(FRAGMENT.get("name"))

    NAME = parsedFilename["name"]
    ARTISTS = parsedFilename["artists"]

    ret = {}

    if NAME:
        log.debug("set NAME from name: " + NAME)

        log.debug(f'Searching for "{NAME}"')
        query_title = search_query_prep(NAME)
        for studio_name, studio_key in STUDIOS.items():
            scraper.search(query_title, studio_name, studio_key)
        parsed_scenes = scraper.parse_results()

        interleaved = interleave_results(parsed_scenes)
        sortedBySimilarity = sortBySimilarity(NAME, ARTISTS, interleaved)

        ret = sortedBySimilarity

    print(json.dumps(ret))
