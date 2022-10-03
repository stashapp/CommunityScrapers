import base64
import json
import re
import sys
from urllib.parse import quote, unquote
import html as htmlparser
from itertools import chain, zip_longest

# extra modules below need to be installed

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
    from lxml import html, etree
except ModuleNotFoundError:
    log.error(
        "You need to install the lxml module. (https://lxml.de/installation.html#installation)"
    )
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml"
    )
    sys.exit()

MAIN_STUDIOS = ["WowGirls", "Ultra Films"]
WOW_SUB_STUDIO_MAP = {24: "All Fine Girls", 32: "WowGirls", 36: "WowPorn"}
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

    def search_query_prep(self, string: str):
        string = string.replace("’", "'")
        a = [s for s in string if s.isalnum() or s.isspace() or s == "-" or s == "'"]
        string = "".join(a)
        return quote(string)

    def search(self, title):
        query_title = self.search_query_prep(title)
        for studio in MAIN_STUDIOS:
            query_studio = studio.replace(" ", "").lower()
            url = f"https://venus.{query_studio}.com/search/?query={query_title}"
            self.rGET(url)  # send search request, needed for session data
            scraped = self.set_video_filter(
                query_studio
            )  # set 'video only' filter for results
            if scraped is None:
                continue
            if studio == "Ultra Films":
                page_content = html.fromstring(scraped)
                self.scrape_all_results_pages(page_content, studio)
                log.debug(
                    f"Searched {studio}, found {self.count_results_pages(studio)} pages"
                )
                if (
                    URL
                ):  # when searching by url, check for scene with id after scraping each studio
                    ret = self.get_scene_with_id(sceneID)
                    if ret:
                        log.debug("scene found!")
                        return ret
            else:  # search WowGirls substudios one by one
                for studio_key, studio in WOW_SUB_STUDIO_MAP.items():
                    scraped = self.wow_sub_studio_filter_toggle(
                        studio_key, query_studio
                    )
                    if scraped is None:
                        continue
                    page_content = html.fromstring(scraped)
                    self.scrape_all_results_pages(page_content, studio)
                    self.wow_sub_studio_filter_toggle(studio_key, query_studio)
                    log.debug(
                        f"Searched {studio}, found {self.count_results_pages(studio)} pages"
                    )
                    if (
                        URL
                    ):  # when searching by url, check for scene with id after scraping each studio
                        ret = self.get_scene_with_id(sceneID)
                        if ret:
                            log.debug("scene found!")
                            return ret
        return None

    def count_results_pages(self, studio):
        try:
            return len(self.search_results.get(studio))
        except:
            return 0

    def wow_sub_studio_filter_toggle(self, studio_key, studio):
        query_studio = studio.replace(" ", "").lower()
        data = f"__operation=toggle&__state=sites%3D{studio_key}"
        scraped = None
        try:
            scraped = self.session.post(
                f"https://venus.{query_studio}.com/search/cf", data=data
            )
        except:
            log.error("scrape error")
            return None
        if scraped.status_code >= 400:
            log.error(f"HTTP Error: {scraped.status_code}")
        scraped = scraped.content.decode("utf-8")
        return scraped

    def scrape_all_results_pages(self, page_content, studio):
        if not page_content.xpath('//div[@class="no_results"]'):
            if not self.search_results.get(studio):
                self.search_results[studio] = []
            self.search_results[studio].append(page_content)
            pagignator = page_content.xpath(
                "//div[@class='paginator']/div[@class='pages']//text()"
            )
            for pageNu in pagignator[1:]:
                page_content = html.fromstring(self.pageNu_scrape(studio, pageNu))
                self.search_results[studio].append(page_content)

    def rGET(self, url):
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

    def set_video_filter(self, studio):
        query_studio = studio.replace(" ", "").lower()
        url = f"https://venus.{query_studio}.com/search/cf"
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

    def pageNu_scrape(self, studio, pageNu):
        query_studio = studio.replace(" ", "").lower()
        url = f"https://venus.{query_studio}.com/search/cf"
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
        imgurl = re.sub("_\w*", "_1280x720", imgurl)
        img = self.rGET(imgurl)
        b64img = base64.b64encode(img)
        performers = scene_card.xpath('.//*[@class="models"]/a/text()')
        tags = scene_card.xpath('.//span[@class="genres"]/a/text()')
        return title, b64img, performers, tags

    def parse_results(self):  # parse all scene elements, return all
        parsed_scenes = {}
        for studio, pages in self.search_results.items():
            query_studio = studio.replace(" ", "").lower()
            for page in pages:
                scene_cards = page.xpath(
                    '//div[contains(@class, "ct_video")]//img[@title]/ancestor::div'
                )
                for scene_card in scene_cards:
                    url = (
                        f"https://venus.{query_studio}.com"
                        + scene_card.xpath("./a/@href")[0]
                    )
                    title, b64img, performers, tags = self.scene_card_parse(scene_card)
                    if not parsed_scenes.get(query_studio):
                        parsed_scenes[query_studio] = []
                    parsed_scenes[query_studio].append(
                        self.output_json(title, tags, url, b64img, studio, performers)
                    )
        return parsed_scenes

    def get_scene_with_id(
        self, sceneID
    ):  # parse all scene elements, return single with matched id
        for studio, pages in self.search_results.items():
            query_studio = studio.replace(" ", "").lower()
            for page in pages:
                scene_cards_with_ID = page.xpath(
                    f'//div[contains(@class, "ct_video")]//a[contains(@href,"{sceneID}")]/ancestor::div'
                )
                if scene_cards_with_ID:
                    scene_card = scene_cards_with_ID[0]
                    url = (
                        f"https://venus.{query_studio}.com"
                        + scene_card.xpath("./a/@href")[0]
                    )
                    title, b64img, performers, tags = self.scene_card_parse(scene_card)
                    return self.output_json(
                        title, tags, url, b64img, studio, performers
                    )


def interleave_results(parsed_scenes):  # interleave search results by studio
    interleaved = [
        x
        for x in chain.from_iterable(zip_longest(*parsed_scenes.values()))
        if x is not None
    ]
    return interleaved

FRAGMENT = json.loads(sys.stdin.read())
NAME = FRAGMENT.get("name")
URL = FRAGMENT.get("url")

scraper = WowVenus()
ret = {}

if NAME:
    scraper.search(NAME)
    parsed_scenes = scraper.parse_results()
    ret = interleave_results(parsed_scenes)
elif URL:
    query_title = URL.split("/")[-1].replace("-", " ")
    query_title = unquote(query_title)
    sceneID = URL.split("/")[4]
    ret = scraper.search(query_title)
    if not ret:
        log.error(
            "Scene not found!\nSome scenes do not appear in search results unless you are logged in!"
        )
        sys.exit()
print(json.dumps(ret))
