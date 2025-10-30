import base64
import os
import json
import sys
import re
from typing import Any
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


def scrape_url(url: str, scrape_type: str) -> dict[str, Any] | None:
    parsed = urlparse(url)

    *_, date, name = parsed.path.split('/')
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    scraped = None
    if scrape_type == 'scene':
        scraped = scrape_movie(base_url, date, name)
    elif scrape_type == 'gallery':
        scraped = scrape_gallery(base_url, date, name)
        if scraped and (director := scraped.pop("Director", None)):
            scraped["Photographer"] = director
    elif scrape_type == 'performer':
        scraped = scrape_model(base_url, name)

    return scraped


def query(fragment: dict[str, Any], query_type: str) -> dict[str, Any] | None:
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


def capitalize_word(match: re.Match[str]) -> str:
    """Helper function to capitalize words"""
    return match.group(0).lower().capitalize()


def transform_name_part(part: str) -> str:
    """Transform a name part by replacing underscores/hyphens and capitalizing"""
    cleaned = re.sub('[_-]', ' ', part)
    return re.sub(r'\w\S*', capitalize_word, cleaned)


def search(s_type: str, name: str) -> list[dict[str, Any]]:
    search_type = {
        'scene': 'MOVIE',
        'gallery': 'GALLERY',
        'performer': 'model'
    }[s_type]
    page = 1
    page_size = 30
    args: dict[str, str | int] = {
        'searchPhrase': name,
        'pageSize': page_size,
        'sortBy': 'relevance'
    }
    
    if s_type == 'performer':
        def map_result(result: dict[str, Any]) -> dict[str, Any]:
            item = result['item']
            return {
                'name': item['name'].strip(),
                'url': f"https://www.metartnetwork.com{item['path']}",
            }
    elif s_type == 'scene':
        def map_result(result: dict[str, Any]) -> dict[str, Any]:
            item = result['item']
            studio = get_studio(item['siteUUID'])
            image = ""
            if studio:
                image = f"https://www.{studio[1]}{item['thumbnailCoverPath']}"
            return {
                'title': item['name'].strip(),
                'url': f"https://www.metartnetwork.com{item['path']}",
                'date': item['publishedAt'][0:item['publishedAt'].find('T')],
                'performers': [{'name': m['name'].strip()} for m in item['models']],
                'image': image,
            }
    else:
        return []

    results: list[dict[str, Any]] = []

    log.info(f"Searching for {s_type} '{name}'")
    while True:
        args['page'] = page
        response = fetch("https://metartnetwork.com", "search-results", args)
        
        if response is None:
            break

        # Filter results by type and map them
        filtered_results = [
            map_result(r) for r in response['items']
            if r['type'] == search_type
        ]
        results += filtered_results

        if page * page_size > response['total'] or len(response['items']) == 0:
            break

        page += 1

    return results


def fetch(base_url: str, fetch_type: str, arguments: dict[str, str | int]) -> dict[str, Any] | None:
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

    data: dict[str, Any] = response.json()
    return data


def scrape_model(base_url: str, name: str) -> dict[str, Any] | None:
    # Transform the name by splitting on hyphens and processing each part
    name_parts = name.split('-')
    transformed_parts = [transform_name_part(part) for part in name_parts]
    transformed_name = ' '.join(transformed_parts)
    
    log.info(f"Scraping model '{name}' as '{transformed_name}'")
    data = fetch(base_url, 'model', {'name': transformed_name, 'order': 'DATE', 'direction': 'DESC'})
    if data is None:
        return None

    return map_model(base_url, data)


def map_media(data: dict[str, Any], studio: tuple[str, str] | None, base_url: str) -> dict[str, Any]:
    urls: list[str] = []
    studio_code = data["UUID"].strip()
    studio_name: dict[str, str] = {'Name': ""}
    
    # Sites that never put directors in the "crew" section
    # this eliminates picking up "still photographer" as an additional director
    directors_not_in_crew = ("SexArt", "ALS Scan")
    
    if studio is not None:
        studio_url = studio[1]
        urls = [f"https://www.{studio_url}{data['path']}"]
        studio_name = {'Name': studio[0].strip()}

    director: str | None = None
    directors: list[str] = []

    # director seems to be included in `photographers` and `crew` section
    if data.get("photographers"):
        for director in data['photographers']:
            directors.append(director.get('name').strip())
    if data.get('crew') and studio_name["Name"] not in directors_not_in_crew:
        # some sites only use the `photograpers`` section for director
        for crew in data['crew']:
            if crew.get('role') == "Still Photographer":
                for crew_name in crew.get('names'):
                    name = crew_name.strip()
                    if name not in directors:
                        directors.append(name)
    director = ", ".join(directors).strip()

    return {
        'Title': data['name'].strip(),
        'Details': data.get('description', "").strip() or None,
        'URLs': urls,
        'Date': data['publishedAt'][0:data['publishedAt'].find('T')],
        'Tags': [{'Name': t.strip()} for t in data['tags']],
        'Performers': [map_model(base_url, m) for m in data['models']],
        'Studio': studio_name,
        'Code': studio_code,
        "Director": director
    }


def scrape_movie(base_url: str, date: str, name: str) -> dict[str, Any] | None:
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


def scrape_gallery(base_url: str, date: str, name: str) -> dict[str, Any] | None:
    log.info(f"Scraping gallery '{name}' released on {date}")
    data = fetch(base_url, 'gallery', {'name': name, 'date': date})
    if data is None:
        # try fetching from movie
        log.info(f"Gallery '{name}' not found, trying to fetch as movie")
        data = fetch(base_url, 'movie', {'name': name, 'date': date})
    if data is None:
        log.error(f"Gallery '{name}' not found")
        return None

    studio = get_studio(data['siteUUID'])
    return map_media(data, studio, base_url)


def map_model(base_url: str, model: dict[str, Any]) -> dict[str, Any]:
    # Convert tags list to dictionary format
    tags: list[dict[str, str]] = [{'Name': t.strip()} for t in model['tags']]

    def add_tag(key: str, tag_format: str) -> None:
        nonlocal tags
        if key in model and model[key] != "":
            tags.append({
                'Name': tag_format.format(model[key]).strip()
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
        'Name': model.get("name", "").strip(),
        'Gender': model.get("gender", "").upper().strip(),
        'URL': f"{base_url}{model.get('path')}",
        'Ethnicity': model.get("ethnicity", "").strip() or None,
        'Country': country_name,
        'Height': str(model.get("height", "")).strip(),
        'Weight': str(model.get("weight", "")).strip(),
        'Measurements': model.get("size", "").strip() or None,
        'Details': model.get("biography", "").strip() or None,
        'hair_color': model.get("hair", "").capitalize().strip(),
        'eye_color': model.get("eyes", "").capitalize().strip(),
        'Image': f"https://cdn.metartnetwork.com/{model.get('siteUUID')}{model.get('headshotImagePath')}",
        'Tags': tags
    }


studios: dict[str, tuple[str, str]] = {
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


def validate_url(url: str | None) -> bool:
    if url is None or not re.match('^https?://', url):
        return False

    for (_, domain) in studios.values():
        if domain in url:
            return True

    if 'metartnetwork.com' in url:
        return True

    return False


def get_studio(site_uuid: str) -> tuple[str, str] | None:
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
