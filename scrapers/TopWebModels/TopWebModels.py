import json
import os
import re
import sys

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()
# make sure to install below modules if needed
try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    print("You need to install the BeautifulSoup module. (https://pypi.org/project/beautifulsoup4/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install beautifulsoup4", file=sys.stderr)
    sys.exit()

def get_from_url(url_to_parse):
    m = re.match(r'https?://tour\.((\w+)\.com)/scenes/(\d+)/([a-z0-9-]+)', url_to_parse)
    if m is None:
        return None, None, None, None
    return m.groups()


def make_request(request_url, origin_site):
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
    requests.packages.urllib3.disable_warnings()

    try:
        requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += 'HIGH:!DH:!aNULL'
    except AttributeError:
        # no pyopenssl support used / needed / available
        pass

    try:
        r = requests.get(request_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
            'Origin': origin_site,
            'Referer': request_url
        }, timeout=(3, 6), verify=False)
    except requests.exceptions.RequestException as e:
        return None, e

    if r.status_code == 200:
        return r.text, None
    return None, f"HTTP Error: {r.status_code}"

def fetch_page_json(page_html):
        matches = re.findall(r'window\.__DATA__ = (.+)$', page_html, re.MULTILINE)
        return json.loads(matches[0]) if matches else None

def main():
    stdin = sys.stdin.read()
    log.debug(stdin)
    fragment = json.loads(stdin)

    if not fragment['url']:
        log.error('No URL entered.')
        sys.exit(1)
    url = fragment['url'].strip()
    site, studio, sid, slug = get_from_url(url)
    if site is None:
        log.error('The URL could not be parsed')
        sys.exit(1)
    response, err = make_request(url, f"https://{site}")
    if err is not None:
        log.error('Could not fetch page HTML', err)
        sys.exit(1)
    j = fetch_page_json(response)
    if j is None:
        log.error('Could not find JSON on page')
        sys.exit(1)
    if 'video' not in j['data']:
        log.error('Could not locate scene within JSON')
        sys.exit(1)

    scene = j["data"]["video"]

    if scene.get('id'):
        if str(scene['id']) != sid:
            log.error('Wrong scene within JSON')
            sys.exit(1)
        log.info(f"Scene {sid} found")
    scrape = {}
    if scene.get('title'):
        scrape['title'] = scene['title']
    if scene.get('release_date'):
        scrape['date'] = scene['release_date'][:10]
    if scene.get('description'):
        details = BeautifulSoup(scene['description'], "html.parser").get_text()
        scrape['details'] = details
    if scene.get('sites'):
        scene_studio = scene['sites'][0]['name']
        scrape['studio'] = {'name': scene_studio}
    if scene.get('models'):
        models = []
        for m in scene['models']:
           models.extend([x.strip() for x in m['name'].split("&") ])
        scrape['performers'] = [{'name': x} for x in models]
    if scene.get('tags'):
        scrape['tags'] = [{'name': x['name']} for x in scene['tags']]
    if j['data'].get('file_poster'):
        scrape['image'] = j['data']['file_poster']
    print(json.dumps(scrape))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log.error(e)
