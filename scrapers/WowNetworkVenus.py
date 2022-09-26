import base64
import json
import re
import sys
import urllib.parse
from itertools import chain, zip_longest
# extra modules below need to be installed

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()
try:
    import requests
except ModuleNotFoundError:
    log.error("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)")
    log.error("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests")
    sys.exit()
    
try:
    from lxml import html, etree
except ModuleNotFoundError:
    log.error("You need to install the lxml module. (https://lxml.de/installation.html#installation)")
    log.error("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml")
    sys.exit()



def search_query_prep(string):
    string = string.replace("’", "'")
    a = [s for s in string if s.isalnum() or s.isspace() or s=='-' or s=="'"]
    string = "".join(a)
    return urllib.parse.quote(string)

def search(title):
    query_title = search_query_prep(title)
    for studio in MAIN_STUDIOS:
        query_studio = studio.replace(" ", "").lower()
        url = f'https://venus.{query_studio}.com/search/?query={query_title}'
        rGET(url) #send search request
        scraped = set_video_filter(query_studio) #set 'video only' filter for results
        if studio == 'Ultra Films':
            page_content = html.fromstring(scraped)
            scrape_all_results_pages(page_content, studio)
            log.debug(f'Searched {studio}, found {count_results_pages(studio)} pages')
        else: # filter results by wowgirls substudios
            for studio_key, studio in WOW_SUB_STUDIO_MAP.items():
                scraped = wow_sub_studio_filter_toggle(studio_key, query_studio)
                page_content = html.fromstring(scraped)
                scrape_all_results_pages(page_content, studio)
                wow_sub_studio_filter_toggle(studio_key, query_studio)
                log.debug(f'Searched {studio}, found {count_results_pages(studio)} pages')

def count_results_pages(studio):
    try:
        return len(search_results.get(studio))
    except:
        return 0

def wow_sub_studio_filter_toggle(studio_key, studio):
    query_studio = studio.replace(" ", "").lower()
    data = f'__operation=toggle&__state=sites%3D{studio_key}'
    try:
        scraped = s.post(f'https://venus.{query_studio}.com/search/cf', data=data)
    except:
        log.error("scrape error")
    if scraped.status_code >= 400:
        log.error(f"HTTP Error: {scraped.status_code}")
    scraped = scraped.content.decode('utf-8')
    return scraped

def scrape_all_results_pages(page_content, studio):
    if not page_content.xpath('//div[@class="no_results"]'):
        if not search_results.get(studio):
            search_results[studio] = []
        search_results[studio].append(page_content)
        pagignator = page_content.xpath("//div[@class='paginator']/div[@class='pages']//text()")
        for pageNu in pagignator[1:]:
            page_content = html.fromstring(pageNu_scrape(studio,pageNu))
            search_results[studio].append(page_content)

def rGET(url):
    try:
        scraped = s.get(url, timeout=TIMEOUT)
    except:
        log.error("scrape error")
    if scraped.status_code >= 400:
        log.error(f"HTTP Error: {scraped.status_code}")
    return scraped.content

def set_video_filter(studio):
    query_studio = studio.replace(" ", "").lower()
    url = f"https://venus.{query_studio}.com/search/cf"
    data = "__state=contentTypes%3D%5Bvideo%5D"
    try:
        scraped = s.post(url, data=data, timeout=TIMEOUT)
    except:
        log.error("scrape error")
    if scraped.status_code >= 400:
        log.error(f"HTTP Error: {scraped.status_code}")
    scraped = scraped.content.decode('utf-8')
    return scraped

def pageNu_scrape(studio,pageNu):
    query_studio = studio.replace(" ", "").lower()
    url = f"https://venus.{query_studio}.com/search/cf"
    data = f"__state=paginator.page%3D{pageNu}"
    try:
        scraped = s.post(url, data=data, timeout=TIMEOUT)
    except:
        log.error("scrape error")
    if scraped.status_code >= 400:
        log.error(f"HTTP Error: {scraped.status_code}")
    scraped = scraped.content.decode("utf-8")
    return scraped

def output_json(title,tags,url,b64img,studio,performers):
    return {
    'title': title,
    'tags': [{
        'name': x
    } for x in tags],
    'url': url,
    'image': "data:image/jpeg;base64," + b64img.decode('utf-8'),
    'studio': {
        'name': studio
    },
    'performers': [{
        'name': x.strip()
    } for x in performers]
}

def scene_card_parse(scene_card):
    title = scene_card.xpath('./a[@class="title"]/text()')[0].strip()
    imgurl = scene_card.xpath('.//img[@title]/@src')[0]
    imgurl= re.sub("_\w*", "_1280x720", imgurl)
    img = rGET(imgurl)
    b64img = base64.b64encode(img)
    performers = scene_card.xpath('.//*[@class="models"]/a/text()')
    tags = scene_card.xpath('.//span[@class="genres"]/a/text()')
    return title, b64img, performers, tags

def get_all_results(): #parse all scene elements, return all
    parsed_scenes = []
    for studio, pages in search_results.items():
        query_studio = studio.replace(" ", "").lower()
        for page in pages:
            scene_cards = page.xpath('//div[contains(@class, "ct_video")]//img[@title]/ancestor::div')
            for scene_card in scene_cards:
                url = f'https://venus.{query_studio}.com'+scene_card.xpath('./a/@href')[0]
                title, b64img, performers, tags = scene_card_parse(scene_card)
                parsed_scenes.append(output_json(title,tags,url,b64img,studio,performers))
    return parsed_scenes

def get_scene_with_id(sceneID): #parse all scene elements, return single with matched id
    for studio, pages in search_results.items():
        query_studio = studio.replace(" ", "").lower()
        for page in pages:
            scene_cards_with_ID = page.xpath(f'//div[contains(@class, "ct_video")]//a[contains(@href,"{sceneID}")]/ancestor::div')
            if scene_cards_with_ID:
                scene_card=scene_cards_with_ID[0]
                url = f'https://venus.{query_studio}.com' + scene_card.xpath('./a/@href')[0]
                title, b64img, performers, tags = scene_card_parse(scene_card)
                return output_json(title,tags,url,b64img,studio,performers)
    log.error('Scene not found!\nSome scenes does not appear is search results unless you are logged in!')
    sys.exit()

def interleave_results(parsed_scenes): #interleave search results by studio
    def interleave(*args):
        sorted = []
        for list in args:
            sorted = [x for x in chain(*zip_longest(list, sorted)) if x is not None]
        return sorted
    ultra = []
    wowg = []
    afg = []
    wowp = []
    for result in parsed_scenes:
        if 'ultrafilms' in result["url"]:
            ultra.append(result)
        elif 'wowgirls' in result["url"]:  
            wowg.append(result)
        elif 'allfinegirls' in result["url"]:
            afg.append(result)
        elif 'wowporn' in result["url"]:
            wowp.append(result)
    return interleave(ultra,wowg,afg,wowp)

MAIN_STUDIOS = ['WowGirls','Ultra Films']
WOW_SUB_STUDIO_MAP = {
    24 : 'All Fine Girls',
    32 : 'WowGirls',
    36 : 'WowPorn'
    }
PROXIES = {}
TIMEOUT = 10


FRAGMENT = json.loads(sys.stdin.read())
NAME = FRAGMENT.get("name")
URL = FRAGMENT.get("url")


search_results = {}
s = requests.Session()
s.headers.update({'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'})
s.proxies.update(PROXIES)


if NAME:
    search(NAME)
    parsed_scenes = get_all_results()
    ret = interleave_results(parsed_scenes)
elif URL:
    query_title = URL.split("/")[-1].replace('-',' ')
    query_title = urllib.parse.unquote(query_title)
    sceneID = URL.split("/")[4]
    search(query_title)
    ret = get_scene_with_id(sceneID)
print(json.dumps(ret))
