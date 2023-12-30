import os
import json
import sys
import requests
import random
import time
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

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    from py_common import log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

#bugfix for socks5 proxies, due to pySocks implementation incompatibility with Stash
proxy = os.environ.get('HTTPS_PROXY', '')
if proxy != "" and proxy.startswith("socks5://"):
    proxy = proxy.replace("socks5://", "socks5h://")
    os.environ['HTTPS_PROXY'] = proxy
    os.environ['HTTP_PROXY'] = proxy

URL_XPATH = '//meta[@property="og:video:url"]/@content'
URL_XPATH_2 = '//meta[@property="og:video:secure_url"]/@content'
IMAGE_XPATH = '//meta[@property="og:image"]/@content'

def getHTML(url, retries=0):
    scraper = cloudscraper.create_scraper()
    
    try:
        scraped = scraper.get(url)
    except requests.exceptions.Timeout as exc_time:
        log.debug(f"Timeout: {exc_time}")
        return getHTML(url, retries + 1)
    except Exception as e:
        log.error(f"scrape error {e}")
        sys.exit(1)
    if scraped.status_code >= 400:
        if retries < 10:
            wait_time = random.randint(1, 4)
            log.debug(f"HTTP Error: {scraped.status_code}, waiting {wait_time} seconds")
            time.sleep(wait_time)
            return getHTML(url, retries + 1)
        log.error(f"HTTP Error: {scraped.status_code}, giving up")
        sys.exit(1)

    return html.fromstring(scraped.text)

def getXPATH(pageTree, XPATH):
    res = pageTree.xpath(XPATH)
    if res:
        return res[0]
    return ""

def getData(sceneId):
    try:
        req = requests.post("https://pmvhaven.com/api/v2/videoInput", json={
            "video": sceneId,
            "mode": "InitVideo",
            "view": True
        })
    except Exception as e:
        log.error(f"scrape error {e}")
        sys.exit(1)
    return req.json()

def getURL(pageTree):
    url = getXPATH(pageTree, URL_XPATH)
    if not url:
        return getXPATH(pageTree, URL_XPATH_2)
    return url

def getIMG(data):
    for item in data['thumbnails']:
        if item.startswith("https://storage.pmvhaven.com/"):
            return item
    return ""

def main():
    params = json.loads(sys.stdin.read())
    if not params['url']:
        log.error('No URL entered.')
        sys.exit(1)
    
    tree = getHTML(params['url'])
    data = getData(getURL(tree).split('_')[-1])['video'][0]

    tags = data['tags'] + data['categories']

    ret = {
        'title': data['title'],
        'image': getIMG(data),
        'date': data['isoDate'].split('T')[0],
        'details': data['description'],
        'studio': {
            'Name': data['creator']
        },
        'tags':[
            {
                'name': x.strip()
            } for x in tags
        ],
        'performers': [
            {
                'name': x.strip()
            } for x in data['stars']
        ]
    }
    print(json.dumps(ret))

if __name__ == "__main__":
    main()
