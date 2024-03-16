import re
import sys
import requests
import json
from datetime import datetime
from urllib.parse import urlparse

try:
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit(1)

try:
    from lxml import html
except ModuleNotFoundError:
    print("You need to install the lxml module. (https://lxml.de/installation.html#installation)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml",
          file=sys.stderr)
    sys.exit()

session = requests.session()


def get_scraped(inp):
    if not inp['url']:
        log.error('No URL Entered')
        return None

    scraped = session.get(inp['url'])
    if scraped.status_code >= 400:
        log.error('HTTP Error: %s' % scraped.status_code)
        return None
    log.trace('Scraped the url: ' + inp["url"])
    return scraped


def performer_by_url():
    inp = json.loads(sys.stdin.read())
    scraped = get_scraped(inp)
    if not scraped:
        return {}

    tree = html.fromstring(scraped.content)
    image = tree.xpath('//div[contains(@class, "model_picture")]/img/@src0_3x')[0].strip()
    image = '{uri.scheme}://{uri.netloc}/{img}'.format(uri=urlparse(scraped.url), img=image[1:])
    name = tree.xpath('//meta[@name="keywords"]/@content')[0].strip().capitalize()
    birthdate = re.search("([0-9]{2})", "".join(tree.xpath('//div[@class="model_bio"]/text()'))).group(0)
    birthdate = datetime.now().replace(year=datetime.now().year - int(birthdate)).replace(month=1, day=1).strftime(
        '%Y-%m-%d')

    return {
        "Image": image,
        "Name": name,
        "Disambiguation": "Broken Latina Whores",
        "Gender": "Female",
        "Birthdate": birthdate,
        "Ethnicity": "Latin"
    }


if sys.argv[1] == "performerByURL":
    print(json.dumps(performer_by_url()))
else:
    log.error("Unknown argument passed: " + sys.argv[1])
    print("{}")

# Last Updated March 16, 2024