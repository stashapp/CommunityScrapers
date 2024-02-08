import base64
import os
import json
import sys
import re
from urllib.parse import urlparse, urlencode

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    from py_common import log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

def scrape_url(url, scrape_type):
    parsed = urlparse(url)

    path = parsed.path.split('/')
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    if scrape_type == 'scene':
        try:
            index = path.index('movie')
            scraped = scrape_movie(base_url, path[index + 1], path[index + 2])
        except ValueError:
            log.error(f"scene scraping not supported for {url}")
            return None
    elif scrape_type == 'gallery':
        try:
            index = path.index('gallery')
            scraped = scrape_gallery(base_url, path[index + 1], path[index + 2])
            if scraped and (director := scraped.pop("Director", None)):
                scraped["Photographer"] = director
        except ValueError:
            log.error(f"gallery scraping not supported for {url}")
            return None
    elif scrape_type == 'performer':
        try:
            index = path.index('model')
            scraped = scrape_model(base_url, path[index + 1])
        except ValueError:
            log.error(f"performer scraping not supported for {url}")
            return None
    else:
        return None

    return scraped


def query(fragment, query_type):
    res = None
    if query_type in ('scene', 'gallery'):
        name = re.sub(r'\W', '_', fragment['title']).upper()
        if fragment.get('date') is None:
            log.error("Date is a required field when scraping by fragment")
            return None
        date = fragment['date'].replace('-', '')

        scraper = globals()['scrape_' + ('movie' if query_type == 'scene' else query_type)]
        res = scraper('https://metartnetwork.com', date, name)
    return res

def search(s_type, name):
    search_type = {
        'scene': 'MOVIE',
        'gallery': 'GALLERY',
        'performer': 'model'
    }[s_type]
    page = 1
    page_size = 30
    args = {
        'searchPhrase': name,
        'pageSize': page_size,
        'sortBy': 'relevance'
    }

    if s_type == 'performer':
        def map_result(result):
            item = result['item']
            return {
                'name': item['name'],
                'url': f"https://www.metartnetwork.com{item['path']}",
            }
    elif s_type == 'scene':
        def map_result(result):
            item = result['item']
            studio = get_studio(item['siteUUID'])
            if studio:
                image = f"https://www.{studio[1]}{item['thumbnailCoverPath']}"
            return {
                'title': item['name'],
                'url': f"https://www.metartnetwork.com{item['path']}",
                'date': item['publishedAt'][0:item['publishedAt'].find('T')],
                'performers': list(map(lambda m: {'name': m['name']}, item['models'])),
                'image': image,
            }
    else:
        return []

    results = []

    log.info(f"Searching for {s_type} '{name}'")
    while True:
        args['page'] = page
        response = fetch("https://metartnetwork.com", "search-results", args)

        results += list(
            map(
                map_result,
                filter(
                    lambda r: r['type'] == search_type,
                    response['items']
                )
            )
        )

        if page * page_size > response['total'] or len(response['items']) == 0:
            break

        page += 1

    return results


def fetch(base_url, fetch_type, arguments):
    url = f"{base_url}/api/{fetch_type}?{urlencode(arguments)}"
    log.debug(f"Fetching URL {url}")
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
        }, timeout=(3, 6))
    except requests.exceptions.RequestException as req_ex:
        log.error(f"Error fetching URL {url}: {req_ex}")
        return None

    if response.status_code >= 400:
        log.info(f"Fetching URL {url} resulted in error status: {response.status_code}")
        return None

    data = response.json()
    return data


def scrape_model(base_url, name):
    transformed_name = str.join(
        ' ',
        list(
            map(
                lambda p:
                re.sub(
                    '[_-]',
                    ' ',
                    re.sub(r'\w\S*', lambda m: m.group(0).lower().capitalize(), p),
                ),
                name.split('-')
            )
        )
    )
    log.info(f"Scraping model '{name}' as '{transformed_name}'")
    data = fetch(base_url, 'model', {'name': transformed_name, 'order': 'DATE', 'direction': 'DESC'})
    if data is None:
        return None

    return map_model(base_url, data)


def map_media(data, studio, base_url):
    urls = []
    studio_code = data["UUID"]
    studio_name = {'Name': ""}
    if studio is not None:
        studio_url = studio[1]
        urls = [f"https://www.{studio_url}{data['path']}"]
        studio_name = {'Name': studio[0]}

    director = None
    directors = []

    # director seems to be included in `photographers` and `crew` section
    if data.get("photographers"):
        for director in data['photographers']:
            directors.append(director.get('name').strip())
    if data.get('crew') and studio_name["Name"] not in ("Sex Art", "ALS Scan"):
                                # some sites only use the `photograpers`` section for director
        for crew in data['crew']:
            if crew.get('role') == "Still Photographer":
                for crew_name in crew.get('names'):
                    name = crew_name.strip()
                    if name not in directors:
                        directors.append(name)
    director = ", ".join(directors)

    return {
        'Title': data['name'],
        'Details': data['description'],
        'URLs': urls,
        'Date': data['publishedAt'][0:data['publishedAt'].find('T')],
        'Tags': list(map(lambda t: {'Name': t}, data['tags'])),
        'Performers': list(map(lambda m: map_model(base_url, m), data['models'])),
        'Studio': studio_name,
        'Code': studio_code,
        "Director": director
    }


def scrape_movie(base_url, date, name):
    log.info(f"Scraping movie '{name}' released on {date}")
    data = fetch(base_url, 'movie', {'name': name, 'date': date})
    if data is None:
        return None

    studio = get_studio(data['media']['siteUUID'])
    res = map_media(data, studio, base_url)
    image_types = ['splashImagePath', 'coverCleanImagePath', 'coverImagePath']
    for image_type in image_types:
        if image_type in data:
            image_part = data[image_type]
            res['Image'] = f"https://cdn.metartnetwork.com/{data['media']['siteUUID']}/{image_part}"
            try:
                response = requests.get(res['Image'], headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
                }, timeout=(3, 6))
                if response and response.status_code < 400:
                    mime = 'image/jpeg'
                    encoded = base64.b64encode(response.content).decode('utf-8')
                    res['Image'] = f'data:{mime};base64,{encoded}'
                    break
            except requests.exceptions.RequestException as req_ex:
                log.info(f"Error fetching URL {res['Image']}: {req_ex}")
            res['Image'] = None

    return res


def scrape_gallery(base_url, date, name):
    log.info(f"Scraping gallery '{name}' released on {date}")
    data = fetch(base_url, 'gallery', {'name': name, 'date': date})
    if data is None:
        return None

    studio = get_studio(data['siteUUID'])
    return map_media(data, studio, base_url)


def map_model(base_url, model):
    tags = list(map(lambda t: {'Name': t}, model['tags']))

    def add_tag(key, tag_format):
        nonlocal tags
        if key in model and model[key] != "":
            tags.append({
                'Name': tag_format.format(model[key])
            })

    add_tag('hair', '{} hair')
    add_tag('pubicHair', '{} pussy')
    add_tag('eyes', '{} eyes')
    add_tag('breasts', '{} breasts')

    country_name = model.get("country", {}).get("name")
    # Unknown is not parsable by stash, convert to None
    if country_name and country_name == "Unknown":
        country_name = None

    return {
        'Name': model.get("name"),
        'Gender': model.get("gender" or "").upper(),
        'URL': f"{base_url}{model.get('path')}",
        'Ethnicity': model.get("ethnicity"),
        'Country': country_name,
        'Height': str(model.get("height")),
        'Weight': str(model.get("weight")),
        'Measurements': model.get("size"),
        'Details': model.get("biography"),
        'hair_color': model.get("hair" or "").capitalize(),
        'eye_color': model.get("eyes" or "").capitalize(),
        'Image': f"https://cdn.metartnetwork.com/{model.get('siteUUID')}{model.get('headshotImagePath')}",
        'Tags': tags
    }


studios = {
    '2163551D11D0439686AD9D291C8DFD71': ('ALS Scan', 'alsscan.com'),
    'D0E7E33329311E3BB6E0800200C93255': ('Domai', 'domai.com'),
    'FDA021004E3411DF98790800200C9A66': ('Erotic Beauty', 'eroticbeauty.com'),
    '15A9FFA04E3511DF98790800200C9A66': ('Errotica Archives', 'errotica-archives.com'),
    '706DF46B88884F7BB226097952427754': ('Eternal Desire', 'eternaldesire.com'),
    '5592E33324211E3FF640800200C93111': ('Goddess Nudes', 'goddessnudes.com'),
    '5A68E1D7B6E69E7401226779D559A10A': ('Love Hairy', 'lovehairy.com'),
    'E6B595104E3411DF98790800200C9A66': ('MetArt', 'metart.com'),
    '5C38C84F55841824817C19987F5447B0': ('MetArt Intimate', 'metart.com'),
    'E7DFB70DF31C45B3B5E0BF10D733D349': ('MetArt X', 'metartx.com'),
    'D99236C04DD011E1B86C0800200C9A66': ('Rylsky Art', 'rylskyart.com'),
    '94DB3D0036FC11E1B86C0800200C9A66': ('SexArt', 'sexart.com'),
    '3D345D1E156910B44DB5A80CDD746318': ('Straplez', 'straplez.com'),
    '18A2E47EAEFD45F29033A5FCAF1F5B91': ('Stunning 18', 'stunning18.com'),
    'FDAFDF209DC311E0AA820800200C9A66': ('The Life Erotic', 'thelifeerotic.com'),
    '4F23028982B542FA9C6DAAA747E9B5B3': ('Viv Thomas', 'vivthomas.com'),
}


def validate_url(url):
    if url is None or not re.match('^https?://', url):
        return False

    for (_, domain) in studios.values():
        if domain in url:
            return True

    if 'metartnetwork.com' in url:
        return True

    return False


def get_studio(site_uuid):
    return studios[site_uuid] if site_uuid in studios else None


scraper_input = sys.stdin.read()
i = json.loads(scraper_input)
log.debug(f"Started with input: {scraper_input}")

ret = {}
if sys.argv[1] == "scrape":
    ret = scrape_url(i['url'], sys.argv[2])
elif sys.argv[1] == "query":
    if 'url' in i and validate_url(i['url']):
        ret = scrape_url(i['url'], sys.argv[2])

    if ret is None or ret == {}:
        ret = query(i, sys.argv[2])
elif sys.argv[1] == 'search':
    if i.get('title') is not None or i.get('name') is not None:
        ret = search(sys.argv[2], i['title'] if 'title' in i else i['name'])

if ret is not None:
    output = json.dumps(ret)
    print(output)
else:
    print("{}")
    # log.debug(f"Send output: {output}")
