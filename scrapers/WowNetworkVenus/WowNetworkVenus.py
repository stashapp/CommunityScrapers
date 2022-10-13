import base64
import json
import os
import re
import sys
import urllib.parse
from itertools import chain, zip_longest

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()
try:
    import requests
except ModuleNotFoundError:
    log.error(
        "You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)"
    )
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests"
    )
    sys.exit()

try:
    from lxml import etree, html
except ModuleNotFoundError:
    log.error(
        "You need to install the lxml module. (https://lxml.de/installation.html#installation)"
    )
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml"
    )
    sys.exit()


STUDIOS = {"Ultra Films": None, "All Fine Girls": 24,
           "WowGirls": 32, "WowPorn": 36}
PROXIES = {}
TIMEOUT = 10


class WowVenus:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"}
        )
        self.session.proxies.update(PROXIES)
        self.search_results = {}

    def count_results_pages(self, studio_name):
        try:
            return len(self.search_results.get(studio_name))
        except:
            return 0

    def wow_sub_studio_filter_toggle(self, studio_key, studio_name):
        query_studio_name = studio_name.replace(" ", "").lower()
        data = f"__operation=toggle&__state=sites%3D{studio_key}"
        scraped = None
        try:
            scraped = self.session.post(
                f"https://venus.{query_studio_name}.com/search/cf", data=data
            )
        except:
            log.error("scrape error")
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
                page_content = html.fromstring(
                    self.pageNu_scrape(studio_name, pageNu))
                self.search_results[studio_name].append(page_content)

    def GET_req(self, url):
        scraped = None
        try:
            scraped = self.session.get(url, timeout=TIMEOUT)
        except:
            log.error("scrape error")
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
            scraped = self.session.post(url, data=data, timeout=TIMEOUT)
        except:
            log.error("scrape error")
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
            scraped = self.session.post(url, data=data, timeout=TIMEOUT)
        except:
            log.error("scrape error")
        if scraped.status_code >= 400:
            log.error(f"HTTP Error: {scraped.status_code}")
        scraped = scraped.content.decode("utf-8")
        return scraped

    def output_json(self, title, tags, url, b64img, studio, performers):
        return {
            "title": title,
            "tags": [{"name": x} for x in tags],
            "url": url,
            "image": "data:image/jpeg;base64," + b64img.decode("utf-8"),
            "studio": {"name": studio},
            "performers": [{"name": x.strip()} for x in performers],
        }

    def scene_card_parse(self, scene_card):
        title = scene_card.xpath('./a[@class="title"]/text()')[0].strip()
        imgurl = scene_card.xpath(".//img[@title]/@src")[0]
        if URL:
            imgurl = re.sub("_\w*", "_1280x720", imgurl)
        img = self.GET_req(imgurl)
        b64img = base64.b64encode(img)
        performers = scene_card.xpath('.//*[@class="models"]/a/text()')
        tags = scene_card.xpath('.//span[@class="genres"]/a/text()')
        return title, b64img, performers, tags

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
                    title, b64img, performers, tags = self.scene_card_parse(
                        scene_card)
                    if not parsed_scenes.get(query_studio_name):
                        parsed_scenes[query_studio_name] = []
                    parsed_scenes[query_studio_name].append(
                        self.output_json(title, tags, url,
                                         b64img, studio_name, performers)
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
                    title, b64img, performers, tags = self.scene_card_parse(
                        scene_card)
                    return self.output_json(
                        title, tags, url, b64img, studio_name, performers
                    )

    def search(self, query_title, studio_name, studio_key):
        query_studio_name = studio_name.replace(" ", "").lower()
        url = f"https://venus.{query_studio_name}.com/search/?query={query_title}"
        self.GET_req(url)   # send search request, needed for session data
        # set 'video only' filter for results
        scraped = self.set_video_filter(query_studio_name)
        page_content = html.fromstring(scraped)
        if studio_key:  # use studio_key to filter search results by sub studio
            scraped = self.wow_sub_studio_filter_toggle(
                studio_key, query_studio_name)  # toggle on
            page_content = html.fromstring(scraped)
        self.scrape_all_results_pages(page_content, studio_name)
        if studio_key:
            self.wow_sub_studio_filter_toggle(
                studio_key, query_studio_name)  # toggle off
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
    a = [s for s in string if s.isalnum() or s.isspace() or s == "-" or s == "'"]
    string = "".join(a)
    return urllib.parse.quote(string)


FRAGMENT = json.loads(sys.stdin.read())

NAME = FRAGMENT.get("name")
URL = FRAGMENT.get("url")
scraper = WowVenus()
ret = {}


if NAME:
    log.debug(f'Searching for "{NAME}"')
    query_title = search_query_prep(NAME)
    for studio_name, studio_key in STUDIOS.items():
        scraper.search(query_title, studio_name, studio_key)
    parsed_scenes = scraper.parse_results()
    ret = interleave_results(parsed_scenes)
elif URL:
    query_title = URL.split("/")[-1].replace("-", " ")
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
