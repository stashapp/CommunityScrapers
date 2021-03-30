import base64
import datetime
import json
import string
import sys
from urllib.parse import urlparse
# extra modules below need to be installed
# Node.js >= 10 also may be needed by cfscrape
import cfscrape
from lxml import html
import requests


def log(*s):
    print(*s, file=sys.stderr)
    ret_null = {}
    print(json.dumps(ret_null))
    sys.exit(1)


def strip_end(text, suffix):
    if suffix and text.endswith(suffix):
        return text[:-len(suffix)]
    return text


frag = json.loads(sys.stdin.read())
if not frag['url']:
    log('No URL entered.')

url = frag["url"]
scraper = cfscrape.create_scraper()
try:
    scraped = scraper.get(url)
except:
    log("scrape error")

if scraped.status_code >= 400:
    log('HTTP Error: %s' % scraped.status_code)

tree = html.fromstring(scraped.content)

title = tree.xpath("//h1/text()")[0]
date = tree.xpath("//span[@class='publication']/text()")[0]
details = tree.xpath("//div[@class='video-description']/p")[0]
tags = tree.xpath("//span[@class='categories']/a/strong/text()")
imgurl = tree.xpath("//video[@id='video-player']/@poster")[0]
img = scraper.get(imgurl).content
b64img = base64.b64encode(img)
datauri = "data:image/jpeg;base64,"

ret = {
    'title': title,
    'tags': [{
        'name': strip_end(x, ', ')
    } for x in tags],
    'date': datetime.datetime.strptime(date, "%m/%d/%Y").strftime("%Y-%m-%d"),
    'details': details.text_content(),
    'image': datauri + b64img.decode('utf-8'),
    'studio': {
        'name': 'Jacquie Et Michel TV'
    },
}

print(json.dumps(ret))