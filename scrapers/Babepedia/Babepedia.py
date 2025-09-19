import json
import re
import os
import sys
import cloudscraper
import urllib

from py_common import log
from py_common.util import scraper_args

scraper = cloudscraper.create_scraper()

def performerName(_name: str, _site: str):
    myHeaders = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'}
    url = "https://www.babepedia.com/ajax-search.php?term=" + urllib.parse.quote(_name)
    results = scraper.get(url, headers=myHeaders)
    data = results.json()
    
    ret = []
    for hit in data:
        p = {}
        p['name'] = hit['label']
        pUrl = "https://www.babepedia.com/babe/" + hit['value'].replace(' ', '_')
        p['url'] = pUrl
        ret.append(p)
    
    return ret

if __name__ == "__main__" or __name__.endswith("Babepedia"):
    op, args = scraper_args()

    match op, args:
        case "performer-by-name", {"name": name, "extra": extra} if name and extra:
            log.debug(f"Name is: {name} and extra is: {extra}")
            sites = extra
            ret = performerName(name, sites)
            print(json.dumps(ret))
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)
