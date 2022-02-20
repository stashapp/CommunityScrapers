import base64
import datetime
import json
import re
import string
import sys
from urllib.parse import urlparse
# extra modules below need to be installed
try:
    import cloudscraper
except ModuleNotFoundError:
    print("You need to install the cloudscraper module. (https://pypi.org/project/cloudscraper/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install cloudscraper", file=sys.stderr)
    sys.exit()
    
try:
    from lxml import html, etree
except ModuleNotFoundError:
    print("You need to install the lxml module. (https://lxml.de/installation.html#installation)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml", file=sys.stderr)
    sys.exit()

STUDIO_MAP = {
    'https://static-cdn-perfectgonzo.explicithd.com/assets/img/favicon_perfectgonzo.com.ico': 'Perfect Gonzo',
    'https://static-cdn-perfectgonzo.explicithd.com/assets/img/favicon_allinternal.com.ico': 'All Internal',
    'https://static-cdn-perfectgonzo.explicithd.com/assets/img/favicon_asstraffic.com.ico': 'Ass Traffic',
    'https://static-cdn-perfectgonzo.explicithd.com/assets/img/favicon_cumforcover.com.ico': 'Cum For Cover',
    'https://static-cdn-sapphix.explicithd.com/assets/img/favicon_fistflush.com.png': 'Fist Flush',
    'https://static-cdn-perfectgonzo.explicithd.com/assets/img/favicon_milfthing.com.ico': 'Milf Thing',
    'https://static-cdn-perfectgonzo.explicithd.com/assets/img/favicon_primecups.com.ico': 'Prime Cups',
    'https://static-cdn-perfectgonzo.explicithd.com/assets/img/favicon_purepov.com.ico': 'Pure POV',
    'https://static-cdn-perfectgonzo.explicithd.com/assets/img/favicon_spermswap.com.ico': 'Sperm Swap',
    'https://static-cdn-perfectgonzo.explicithd.com/assets/img/favicon_tamedteens.com.ico': 'Tamed Teens'
}

def log(*s):
    print(*s, file=sys.stderr)
    ret_null = {}
    print(json.dumps(ret_null))
    sys.exit(1)

frag = json.loads(sys.stdin.read())

if not frag['url']:
    log('No URL entered.')

url = frag["url"]
scraper = cloudscraper.create_scraper()
try:
    scraped = scraper.get(url)
except:
    log("scrape error")

if scraped.status_code >= 400:
    log('HTTP Error: %s' % scraped.status_code)

tree = html.fromstring(scraped.content)

title = tree.xpath('//div[@class="row"]//h2/text()')[0].strip()
date = tree.xpath('//div[@class="row"]//span/text()')[0]
date = re.sub("Added\s*", "", date)
details = tree.xpath('//p[@class="mg-md"]')[0]
imgurl = tree.xpath('//video[@id="video"]/@poster | //div[@id="video-hero"]//img/@src')[0]
img = scraper.get(imgurl).content
b64img = base64.b64encode(img)
datauri = "data:image/jpeg;base64,"
studio = tree.xpath('//link[@type="image/ico"]/@href | //link[@type="image/png"]/@href')[0]
studio = STUDIO_MAP[studio]
performers = tree.xpath('//div[contains(h4,"Featured model")]//a/text()')
tags = []
if studio == 'Fist Flush':
    tags = [x.replace('/movies?tag[]=', '').replace('&nats=', '') for x in tree.xpath('//div[contains(h4,"Tags:")]//a/@href')]
else:
    tag_nodes = tree.xpath("//div[contains(@class, 'tag-container')]/node()")
    tag_category = ''
    for node in tag_nodes:
        if not type(node) is etree._ElementUnicodeResult:
            tag_name = node.text_content().strip()
            if tag_name == 'Tags:':
                continue
            tags.append(f'{tag_category} - {tag_name}')
        elif node.strip():
            tag_category = node.strip()

ret = {
    'title': title,
    'tags': [{
        'name': x
    } for x in tags],
    'date': datetime.datetime.strptime(date, "%B %d, %Y").strftime("%Y-%m-%d"),
    'details': details.text_content().strip(),
    'image': datauri + b64img.decode('utf-8'),
    'studio': {
        'name': studio
    },
    'performers': [{
        'name': x.strip()
    } for x in performers]
}

print(json.dumps(ret))
