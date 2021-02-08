import json
import os
import re
import requests
import sys
from urllib.parse import urlparse


def log(*s):
    print(*s, file=sys.stderr)


def get_from_url(url_to_parse):
    p = urlparse(url_to_parse)
    return p.netloc, p.netloc[4:-4], p.path[1:]


def make_request(request_url, origin_site):
    r = requests.get(request_url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
        'Origin': origin_site,
        'Referer': request_url
    })
    if r.status_code == 200:
        return r.text
    return None


def fetch_page_json(page_html):
    matches = re.findall(r'window\.__APOLLO_STATE__ = (.+);$', page_html, re.MULTILINE)
    return None if len(matches) == 0 else json.loads(matches[0])


def save_json(scraped_json, video_id):
    try:
        os.makedirs('VixenNetwork_JSON')
    except FileExistsError:
        pass
    filename = os.path.join('VixenNetwork_JSON', '%s.json' % video_id)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(scraped_json, f, ensure_ascii=False, indent=4)


def main():
    stdin = sys.stdin.read()
    log(stdin)
    fragment = json.loads(stdin)
    
    if not fragment['url']:
        log('No URL entered.')
        sys.exit(1)
    url = fragment['url']
    site, studio, path = get_from_url(url)
    response = make_request(url, 'https://%s' % site)
    if response is None:
        log('Could not fetch page HTML')
        sys.exit(1)
    j = fetch_page_json(response)
    if j is None:
        log('Could not find JSON on page')
        sys.exit(1)
    scene_id = 'Video:%s:%s' % (studio, path)
    if scene_id not in j:
        log('Could not locate scene within JSON')
        sys.exit(1)
    scene = j[scene_id]
    scrape = {
        'title': scene['title'],
        'date': scene['releaseDate'][:10],
        'details': scene['description'],
        'url': 'https:%s' % scene['absoluteUrl'],
        'studio': {
            'name': studio
        },
        'performers': [{'name': x['name']} for x in scene['models']],
        'tags': [{'name': x['name']} for x in scene['categories']],
        'image': scene['images']['poster'][len(scene['images']['poster']) - 1]['src'],
    }
    save_json(j, scene['videoId'])
    print(json.dumps(scrape))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log(e)
