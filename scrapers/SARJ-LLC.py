import json
import os
import sys
import re
import requests
from urllib.parse import urlparse, urlunparse, urlencode

def scrape_url(url, type):
    parsed = urlparse(url)

    path = parsed.path.split('/')
    baseUrl = f"{parsed.scheme}://{parsed.netloc}"
    if type == 'scene':
        index = path.index('movie')
        scraped = scrape_movie(baseUrl, path[index+1], path[index+2])
    elif type == 'gallery':
        index = path.index('gallery')
        scraped = scrape_gallery(baseUrl, path[index+1], path[index+2])
    elif type == 'performer':
        index = path.index('model')
        scraped = scrape_model(baseUrl, path[index+1])
    else:
        return None

    return scraped

def search(fragment, type):
    if type == 'scene' or type == 'gallery':
      name = re.sub(r'\W', '_', fragment['title']).upper()
      date = fragment['date'].replace('-', '')

      scraper = globals()['scrape_' + ('movie' if type == 'scene' else type)]
      res = scraper('https://metartnetwork.com', date, name)
      if res != None:
          return res

def fetch(baseUrl, type, arguments):
    url =f"{baseUrl}/api/{type}?{urlencode(arguments)}"
    try:
      response = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
      }, timeout=(3, 6))
    except requests.exceptions.RequestException as e:
      return None

    if response.status_code >= 400:
        return None

    data = response.json()
    return data

def scrape_model(baseUrl, name):
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
    data = fetch(baseUrl, 'model', {'name': transformed_name, 'order': 'DATE', 'direction': 'DESC'})
    if data == None:
        return None

    return map_model(baseUrl, data)

def map_media(data, studio, baseUrl):
    studioUrl = studio[1]

    return {
        'Title': data['name'],
        'Details': data['description'],
        'URL': f"https://www.{studioUrl}{data['path']}",
        'Date': data['publishedAt'][0:data['publishedAt'].find('T')],
        'Tags': list(map(lambda t: {'Name': t}, data['tags'])),
        'Performers': list(map(lambda m: map_model(baseUrl, m), data['models'])),
        'Studio': {'Name': studio[0]}
    }

def scrape_movie(baseUrl, date, name):
    data = fetch(baseUrl, 'movie', {'name':name, 'date': date})
    if data == None:
        return None

    studio = get_studio(data['media']['siteUUID'])
    res = map_media(data, studio, baseUrl)
    res['Image'] = f"https://www.{studio[1]}{data['splashImagePath'] if 'splashImagePath' in data else data['coverCleanImagePath'] if 'coverCleanImagePath' in data else data['coverImagePath']}"

    return res

def scrape_gallery(baseUrl, date, name):
    data = fetch(baseUrl, 'gallery', {'name':name, 'date': date})
    if data == None:
        return None

    studio = get_studio(data['siteUUID'])
    return map_media(data, studio, baseUrl)

def map_model(baseUrl, model):
    return {
        'Name': model['name'],
        'Gender': model['gender'].upper(),
        'URL': f"{baseUrl}{model['path']}",
        'Ethnicity': model['ethnicity'],
        'Country': model['country']['name'],
        'EyeColor': model['eyes'],
        'Height': str(model['height']),
        'Measurements': model['size'],
        'Image': f"{baseUrl}{model['headshotImagePath']}"
    }

studios = {
        '2163551D11D0439686AD9D291C8DFD71': ('ALS Scan', 'alsscan.com'),
        '5592E33324211E3FF640800200C93111': ('Erotic Beauty', 'eroticbeauty.com'),
        '15A9FFA04E3511DF98790800200C9A66': ('Errotica Archives', 'errotica-archives.com'),
        '706DF46B88884F7BB226097952427754': ('Eternal Desire', 'eternaldesire.com'),
        '5A68E1D7B6E69E7401226779D559A10A': ('Love Hairy', 'lovehairy.com'),
        'E6B595104E3411DF98790800200C9A66': ('Met Art', 'metart.com'),
        'E7DFB70DF31C45B3B5E0BF10D733D349': ('Met Art X', 'metartx.com'),
        'D99236C04DD011E1B86C0800200C9A66': ('Rylsky Art', 'rylskyart.com'),
        '94DB3D0036FC11E1B86C0800200C9A66': ('Sex Art', 'sexart.com'),
        '18A2E47EAEFD45F29033A5FCAF1F5B91': ('Stunning 18', 'stunning18.com'),
        'FDAFDF209DC311E0AA820800200C9A66': ('The Life Erotic', 'thelifeerotic.com'),
        '4F23028982B542FA9C6DAAA747E9B5B3': ('Viv Thomas', 'vivthomas.com'),
}

def validate_url(url):
    if url == None or not re.match('^https?://', url):
        return False

    for (name, domain) in studios.values():
        if domain in url:
            return True

    if 'metartnetwork.com' in url:
        return True

    return False

def get_studio(siteUuid):
    return studios[siteUuid] if siteUuid in studios else None

i = json.loads(sys.stdin.read())

ret = {}
if sys.argv[1] == "scrape":
    ret = scrape_url(i['url'], sys.argv[2])
elif sys.argv[1] == "query":
    if 'url' in i and validate_url(i['url']):
        ret = scrape_url(i['url'], sys.argv[2])
    else:
        ret = search(i, sys.argv[2])

print(json.dumps(ret))
# Last Updated May 15, 2021
