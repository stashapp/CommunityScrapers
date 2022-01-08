import base64
import datetime
import json
import string
import sys
import re
from urllib.parse import urlparse
# extra modules below need to be installed
import cloudscraper
from lxml import html

class Scraper:
    def set_value(self,value):
        if value:
            if not re.match(r'(?i)no data', value[0]):
                    return value[0]
        return None

    def set_stripped_value(self,value):
        if value:
            return value[0].strip("\n ")
        return None

    def set_concat_value(self,sep,values):
        if values:
            return sep.join(values)
        return None

    def set_named_value(self, name, value):
        if value:
            attr = { name: value[0] }
            return attr
        return None

    def set_named_values(self, name, values):
        res = []
        for v in values:
            r = { name: v }
            res.append(r)
        return res

    def print(self):
        for a in dir(self):
            if not a.startswith('__') and not callable(getattr(self, a)) :
                if vars(self)[a]:
                    print("%s: %s" % (a , vars(self)[a] ) )

    def to_json(self):
        for a in dir(self):
            if not a.startswith('__') and not callable(getattr(self, a)) :
                if not vars(self)[a]:
                    del vars(self)[a]
        return json.dumps(self.__dict__)

# Log messages are transmitted via stderr and are
# encoded with a prefix consisting of special character SOH, then the log
# level (one of t, d, i, w, e - corresponding to trace, debug, info,
# warning and error levels respectively), then special character
# STX.
#
# The LogTrace, LogDebug, LogInfo, LogWarning, and LogError methods, and their equivalent
# formatted methods are intended for use by script scraper instances to transmit log
# messages.
#

def __prefix(levelChar):
    startLevelChar = b'\x01'
    endLevelChar = b'\x02'

    ret = startLevelChar + levelChar + endLevelChar
    return ret.decode()

def __log(levelChar, s):
    if levelChar == "":
        return

    print(__prefix(levelChar) + s + "\n", file=sys.stderr, flush=True)

def LogTrace(s):
    __log(b't', s)

def LogDebug(s):
    __log(b'd', s)

def LogInfo(s):
    __log(b'i', s)

def LogWarning(s):
    __log(b'w', s)

def LogError(s):
    __log(b'e', s)

def strip_end(text, suffix):
    if suffix and text.endswith(suffix):
        return text[:-len(suffix)]
    return text

def scrape(url):
    scraper = cloudscraper.create_scraper()
    try:
        scraped = scraper.get(url, timeout=(3,7))
    except Exception as e:
        LogError("scrape error %s" % e)
        sys.exit(1)
    if scraped.status_code >= 400:
        LogError('HTTP Error: %s' % scraped.status_code)
        sys.exit(1)
    return html.fromstring(scraped.content)

def scrape_image(url):
    scraper = cloudscraper.create_scraper()
    try:
        scraped = scraper.get(url, timeout=(3,7))
    except Exception as e:
        LogWarning("scrape error %s" %e )
        return None
    if scraped.status_code >= 400:
        LogWarning('HTTP Error: %s' % scraped.status_code)
        return None
    b64img = base64.b64encode(scraped.content)
    return "data:image/jpeg;base64," + b64img.decode('utf-8')

def scene_from_tree(tree):
    s = Scraper()

    scene_title = tree.xpath('//div[contains(@class,"info")]/h1/text()')
    s.title = s.set_stripped_value(scene_title)

    scene_details = tree.xpath('//div[contains(@class,"info")]/p/text()')
    s.details = s.set_value(scene_details)

    scene_studio = ["Fit18"]
    s.studio = s.set_named_value("name",scene_studio)

    scene_performers = tree.xpath('//div[contains(@class,"info")]//span[contains(span,"model")]/a/text()')
    s.performers = s.set_named_values("name", scene_performers)

    scene_image_url = tree.xpath('//main/div/a/img/@src')
    if scene_image_url:
        try:
           LogDebug("downloading image from %s" % scene_image_url[0] )
           s.image = scrape_image(scene_image_url[0])
        except Exception as e:
           LogDebug("error downloading image %s" %e)

    res = s.to_json()
    print(res)
    sys.exit(0)

frag = json.loads(sys.stdin.read())

if not frag['url']:
    LogWarning('No URL entered.')

url = frag["url"]
LogInfo("scraping %s" % url)
tree = scrape(url)

scene_from_tree(tree)

#Last Updated August 22, 2021
