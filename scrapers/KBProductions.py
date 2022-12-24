import json
import os
import re
import sys

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

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
    m = re.match(
        r'https?:\/\/(?:www\.)?((\w+)\.com)(?:\/tour)?\/(?:videos|upcoming|models)\/?(\d+)?\/([a-z0-9-]+)',
        url_to_parse)
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
        r = requests.get(
            request_url,
            headers={
                'User-Agent':
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
                'Origin': origin_site,
                'Referer': request_url
            },
            timeout=(3, 6),
            verify=False)
    except requests.exceptions.RequestException as e:
        return None, e

    if r.status_code == 200:
        return r.text, None
    return None, f"HTTP Error: {r.status_code}"


def fetch_page_json(page_html):
    matches = re.findall(r'window\.__DATA__ = (.+)$', page_html, re.MULTILINE)
    return json.loads(matches[0]) if matches else None


def scrape_scene(page_json, studio):
    if page_json.get("video") is None:
        log.error('Could not find  scene in JSON data')
        sys.exit(1)

    scene = page_json["video"]

    scrape = {}
    scrape['studio'] = {'name': studio}
    if scene.get('title'):
        scrape['title'] = scene['title']
    if scene.get('release_date'):
        scrape['date'] = scene['release_date'][:10]
    if scene.get('description'):
        details = BeautifulSoup(scene['description'], "html.parser").get_text()
        scrape['details'] = details
    if scene.get('models'):
        models = []
        for m in scene['models']:
            if m.get('name'):
                models.append(m['name'])
        scrape['performers'] = [{'name': x} for x in models]
    if scene.get('tags'):
        tags = []
        for t in scene['tags']:
            if t.get('name'):
                tags.append(t['name'])
        scrape['tags'] = [{'name': x} for x in tags]
    if scene.get('extra_thumbs'):
        # available image endings
        # ================
        #_player.jpg
        #_playermobile.jpg
        #_portrait1.jpg
        #_portrait2.jpg
        #_scene.jpg
        #_scenemobile.jpg
        img = None
        for i in scene['extra_thumbs']:
            if i.endswith("_player.jpg"):
                image = i
                break
        if img is None:
            img = scene['extra_thumbs'][0]
        scrape['image'] = img
    print(json.dumps(scrape))


def get_dict_value(d: dict, v: str):
    if d.get(v):
        return d[v]
    return None


def scrape_performer(page_json):
    if page_json.get("model") is None:
        log.error('Could not find performer in JSON data')
        sys.exit(1)

    performer = page_json["model"]
    scrape = {}

    scrape['name'] = get_dict_value(performer, 'name')
    scrape['gender'] = get_dict_value(performer, 'gender')
    scrape['image'] = get_dict_value(performer, 'thumb')

    if performer.get('attributes'):
        pa = performer['attributes']
        if pa.get('bio'):
            scrape['details'] = get_dict_value(pa['bio'], 'value')
        if pa.get('birthdate'):
            scrape['birthdate'] = get_dict_value(pa['birthdate'], 'value')
        if pa.get('measurements'):
            scrape['measurements'] = get_dict_value(pa['measurements'],
                                                    'value')
        if pa.get('eyes'):
            scrape['eye_color'] = get_dict_value(pa['eyes'], 'value')
        if pa.get('height'):
            height_ft = get_dict_value(pa['height'], 'value')
            if height_ft:
                h = re.match(r'(\d+)\D(\d+).+', height_ft)
                if h:
                    h_int = int(
                        round((float(h.group(1)) * 12 + float(h.group(2))) *
                              2.54))  # ft'inches to cm
                    scrape['height'] = f"{h_int}"
        if pa.get('weight'):
            weight_lb = get_dict_value(pa['weight'], 'value')
            if weight_lb:
                w = re.match(r'(\d+)\slbs', weight_lb)
                if w:
                    w_int = int(round(float(w.group(1)) / 2.2046))  # lbs to kg
                    scrape['weight'] = f"{w_int}"
        if pa.get('hair'):
            scrape['hair_color'] = get_dict_value(pa['hair'], 'value')
    print(json.dumps(scrape))


def main():
    stdin = sys.stdin.read()
    log.debug(stdin)
    fragment = json.loads(stdin)

    if not fragment['url']:
        log.error('No URL entered.')
        sys.exit(1)
    url = fragment['url'].strip()

    site, studio, el_id, slug = get_from_url(url)
    if site is None:
        log.error('The URL could not be parsed')
        sys.exit(1)

    response, err = make_request(url, f"https://{site}")
    if err is not None:
        log.error(f"Could not fetch page HTML: {err}")
        sys.exit(1)

    j = fetch_page_json(response)
    if j is None:
        log.error('Could not find JSON on page')
        sys.exit(1)

    if len(sys.argv) == 0 or sys.argv[1] == "scene":
        scrape_scene(page_json=j, studio=studio)
    elif sys.argv[1] == "performer":
        scrape_performer(j)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log.error(e)
