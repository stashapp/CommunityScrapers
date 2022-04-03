import base64
import datetime
import json
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
    from lxml import html
except ModuleNotFoundError:
    print("You need to install the lxml module. (https://lxml.de/installation.html#installation)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml", file=sys.stderr)
    sys.exit()

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

lang = 'en'

if len(sys.argv) > 1:
    if sys.argv[1] == 'fr':
        lang = 'fr'

frag = json.loads(sys.stdin.read())
if not frag['url']:
    log.error('No URL entered.')
    sys.exit(1)

url = frag["url"]
scraper = cloudscraper.create_scraper()
try:
    cookies = {'lang': lang}
    scraped = scraper.get(url, cookies=cookies)
except:
    log.error("scrape error")
    sys.exit(1)

if scraped.status_code >= 400:
    log.error(f'HTTP Error: {scraped.status_code}')
    sys.exit(1)

tree = html.fromstring(scraped.text)

title = None
title_res = tree.xpath("//h1/text()")
if title_res:
    title = title_res[0]
date = None
dt = tree.xpath("//span[@class='video-detail__date']/text()")
if dt:
    f, *m, l = dt[0].split()
    log.debug(f"found date: {l}")
    if l:
        if lang == 'fr':
            date = datetime.datetime.strptime(l,
                                              "%d/%m/%Y").strftime("%Y-%m-%d")
        else:
            # en
            date = datetime.datetime.strptime(l,
                                              "%m/%d/%Y").strftime("%Y-%m-%d")
desc = tree.xpath("//meta[@property='og:description']/@content")
details = ""
if desc:
    details = desc[0]
tags = tree.xpath("//a[@class='video-detail__tag-list__link']/text()")
imgurl_res = tree.xpath("//video[@id='video-player']/@poster")
datauri = None
if imgurl_res:
    imgurl = imgurl_res[0]
    img = scraper.get(imgurl).content
    b64img = base64.b64encode(img)
    datauri = "data:image/jpeg;base64,"

ret = {
    'title': title,
    'tags': [{
        'name': x.strip()
    } for x in tags],
    'date': date,
    'details': details,
    'image': datauri + b64img.decode('utf-8'),
    'studio': {
        'name': 'Jacquie Et Michel TV'
    },
}

print(json.dumps(ret))
