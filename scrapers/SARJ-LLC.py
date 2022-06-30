import base64
import json
import sys
import re
from urllib.parse import urlparse, urlencode

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()


class Logger:
    levels = {
        "trace": b't'.decode(),
        "debug": b'd'.decode(),
        "info": b'i'.decode(),
        "warning": b'w'.decode(),
        "error": b'e'.decode(),
    }

    def __write(self, level: str, msg: str):
        if level == "" or level not in self.levels:
            return

        print(f"\x01{self.levels[level]}\x02{msg}\n", file=sys.stderr, flush=True)

    def trace(self, msg):
        self.__write("trace", msg)

    def debug(self, msg):
        self.__write("debug", msg)

    def info(self, msg):
        self.__write("info", msg)

    def warning(self, msg):
        self.__write("warning", msg)

    def error(self, msg):
        self.__write("error", msg)


log = Logger()


def scrape_url(url, type):
    parsed = urlparse(url)

    path = parsed.path.split('/')
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    if type == 'scene':
        try:
            index = path.index('movie')
            scraped = scrape_movie(base_url, path[index + 1], path[index + 2])
        except ValueError:
            log.error(f"scene scraping not supported for {url}")
            return None
    elif type == 'gallery':
        try:
            index = path.index('gallery')
            scraped = scrape_gallery(base_url, path[index + 1], path[index + 2])
        except ValueError:
            log.error(f"gallery scraping not supported for {url}")
            return None
    elif type == 'performer':
        try:
            index = path.index('model')
            scraped = scrape_model(base_url, path[index + 1])
        except ValueError:
            log.error(f"performer scraping not supported for {url}")
            return None
    else:
        return None

    return scraped


def query(fragment, type):
    if type == 'scene' or type == 'gallery':
        name = re.sub(r'\W', '_', fragment['title']).upper()
        date = fragment['date'].replace('-', '')

        scraper = globals()['scrape_' + ('movie' if type == 'scene' else type)]
        res = scraper('https://metartnetwork.com', date, name)
        if res is not None:
            return res


def search(type, name):
    search_type = {
        'scene': 'MOVIE',
        'gallery': 'GALLERY',
        'performer': 'model'
    }[type]
    page = 1
    page_size = 30
    args = {
        'searchPhrase': name,
        'pageSize': page_size,
        'sortBy': 'relevance'
    }

    if type == 'performer':
        def map_result(result):
            item = result['item']
            return {
                'name': item['name'],
                'url': f"https://www.metartnetwork.com{item['path']}",
            }
    elif type == 'scene':
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

    log.info(f"Searching for {type} '{name}'")
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


def fetch(base_url, type, arguments):
    url = f"{base_url}/api/{type}?{urlencode(arguments)}"
    log.debug(f"Fetching URL {url}")
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
        }, timeout=(3, 6))
    except requests.exceptions.RequestException as e:
        log.error(f"Error fetching URL {url}: {e.strerror}")
        return None

    if response.status_code >= 400:
        log.debug(f"Fetching URL {url} resulted in error status: {response.status_code}")
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
                    re.sub('\w\S*', lambda m: m.group(0).lower().capitalize(), p),
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
    url = ""
    studio_name = {'Name': ""}
    if studio is not None:
        studio_url = studio[1]
        url = f"https://www.{studio_url}{data['path']}"
        studio_name = {'Name': studio[0]}

    return {
        'Title': data['name'],
        'Details': data['description'],
        'URL': url,
        'Date': data['publishedAt'][0:data['publishedAt'].find('T')],
        'Tags': list(map(lambda t: {'Name': t}, data['tags'])),
        'Performers': list(map(lambda m: map_model(base_url, m), data['models'])),
        'Studio': studio_name
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
            except requests.exceptions.RequestException as e:
                log.error(f"Error fetching URL {res['Image']}: {e.strerror}")

            if response.status_code < 400:
                mime = 'image/jpeg'
                encoded = base64.b64encode(response.content).decode('utf-8')
                res['Image'] = 'data:{0};base64,{1}'.format(mime, encoded)
                break

            log.debug(f"Fetching URL {res['Image']} resulted in error status: {response.status_code}")
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

    def add_tag(key, format):
        nonlocal tags
        if key in model and model[key] != "":
            tags.append({
                'Name': format.format(model[key])
            })

    add_tag('hair', '{} hair')
    add_tag('pubicHair', '{} pussy')
    add_tag('eyes', '{} eyes')
    add_tag('breasts', '{} breasts')

    return {
        'Name': model.get("name"),
        'Gender': model.get("gender" or "").upper(),
        'URL': f"{base_url}{model.get('path')}",
        'Ethnicity': model.get("ethnicity"),
        'Country': model.get("country", {}).get("name"),
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
    'E6B595104E3411DF98790800200C9A66': ('Met Art', 'metart.com'),
    '5C38C84F55841824817C19987F5447B0': ('Met Art Intimate', 'metart.com'),
    'E7DFB70DF31C45B3B5E0BF10D733D349': ('Met Art X', 'metartx.com'),
    'D99236C04DD011E1B86C0800200C9A66': ('Rylsky Art', 'rylskyart.com'),
    '94DB3D0036FC11E1B86C0800200C9A66': ('Sex Art', 'sexart.com'),
    '3D345D1E156910B44DB5A80CDD746318': ('Straplez', 'straplez.com'),
    '18A2E47EAEFD45F29033A5FCAF1F5B91': ('Stunning 18', 'stunning18.com'),
    'FDAFDF209DC311E0AA820800200C9A66': ('The Life Erotic', 'thelifeerotic.com'),
    '4F23028982B542FA9C6DAAA747E9B5B3': ('Viv Thomas', 'vivthomas.com'),
}


def validate_url(url):
    if url is None or not re.match('^https?://', url):
        return False

    for (name, domain) in studios.values():
        if domain in url:
            return True

    if 'metartnetwork.com' in url:
        return True

    return False


def get_studio(siteUuid):
    return studios[siteUuid] if siteUuid in studios else None


input = sys.stdin.read()
i = json.loads(input)
log.debug(f"Started with input: {input}")

ret = {}
if sys.argv[1] == "scrape":
    ret = scrape_url(i['url'], sys.argv[2])
elif sys.argv[1] == "query":
    if 'url' in i and validate_url(i['url']):
        ret = scrape_url(i['url'], sys.argv[2])

    if ret is None or ret == {}:
        ret = query(i, sys.argv[2])
elif sys.argv[1] == 'search':
    ret = search(sys.argv[2], i['title'] if 'title' in i else i['name'])

if ret is not None:
    output = json.dumps(ret)
    print(output)
    # don't log the output since it has an image
    # log.debug(f"Send output: {output}")
