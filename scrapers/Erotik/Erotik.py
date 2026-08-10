import sys
import requests
import re
import json
from py_common.util import scraper_args, dig
from py_common.types import ScrapedGroup, ScrapedTag
from py_common import log
from bs4 import BeautifulSoup

durationConvert = lambda x: f"{x//3600}:{(x%3600)//60}:{x%60}"

def get_group(inputurl) -> ScrapedGroup:
    # pull body
    body = requests.get(inputurl).text
    # search for meta id
    match = re.search(r'<meta name="id" content="([\w\d]+)">', body)
    if match:
        groupid = match.group(1)
    else:
        log.error('No ID found in URL.')
        sys.exit()
    # scrape from api
    api_res = requests.get(f"https://api.erotik.com/content/movies?idList[]={groupid}")
    api_data = api_res.json()[0]
    group: ScrapedGroup = {}
    group['name'] = dig(api_data, 'title', 'en')
    description = dig(api_data, 'description', 'en')
    soup = BeautifulSoup(description, 'html.parser')
    group['synopsis'] = soup.get_text()
    group['studio'] = {'name': dig(api_data, 'studio', 'name')}
    group['front_image'] = dig(api_data, 'image', 'default')
    directors = dig(api_data, 'directors')
    director_names = [dig(director, 'name') for director in directors]
    group['director'] = ', '.join(director_names)
    tags = dig(api_data, 'categories')
    tag_names: list[ScrapedTag] = [{"name": dig(tag, 'name', 'en')} for tag in tags if tag['sortOrder'] >= 0]
    group['tags'] = tag_names
    group['duration'] = durationConvert((dig(api_data, 'durationSeconds') or 0))
    group['rating'] = str(dig(api_data, 'rating') or 0)
    group['date'] = dig(api_data, 'releaseYear').__str__()
    # get urls from lang array
    group['urls'] = list(dig(api_data, 'url').values())

    return group

if __name__ == '__main__':
    op, args = scraper_args()
    result = None
    match op, args:
        case 'group-by-url', { "url": url } if url:
            result = get_group(url)
        case _:
            log.debug(f'Unknown operation {op} with arguments {args}')
            sys.exit(1)
    print(json.dumps(result))
