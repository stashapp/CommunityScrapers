import json
import sys
from urllib.parse import urlparse

import requests

import py_common.log as log

class Site:
  def __init__(self, name):
    self.name = name
    self.id = name.replace(' ', '').upper()
    self.api = "https://www." + self.id.lower() + ".com/graphql"

  def isValidURL(self, url):
    u = url.lower().rstrip("/")
    up = urlparse(u)
    if up.hostname is None:
      return False
    if up.hostname.lstrip("www.").rstrip(".com") == self.id.lower():
      splits = u.split("/")
      if len(splits) < 4:
        return False
      if splits[-2] == "videos":
           return True
    return False

  def getSlug(self, url):
    u = url.lower().rstrip("/")
    slug = u.split("/")[-1]
    return slug

  def getScene(self, url):
    log.debug(f"Scraping using {self.name} graphql API")
    v = {
      "site": self.id,
      "videoSlug": self.getSlug(url)
    }
    r = self.callGraphQL(v)
    return self.parse_scene(r)

  def callGraphQL(self, variables):
    headers = {
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": url,
        "DNT": "1",
    }

    j = { 'query': self.getVideoQuery,
        'operationName': "getVideo"
    }
    if variables is None:
        return None
    j["variables"] = variables

    try:
        response = requests.post(self.api, json=j, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result.get("error"):
                for error in result["error"]["errors"]:
                    raise Exception(f"GraphQL error: {error}")
            return result
        else:
           raise ConnectionError(f"GraphQL query failed:{response.status_code} - {response.content}")
    except Exception as err:
        log.error(f"GraphqQL query failed {err}")
        return None

  def parse_scene(self,response):
        scene = {}
        if response is None or response.get('data') is None:
          return scene

        data = response['data'].get('findOneVideo')
        if data:
          scene['title'] = data.get('title')
          scene['details'] = data.get('description')
          scene['studio'] = {"name": self.name}

          date = data.get('releaseDate')
          if date:
            scene['date']=date.split("T")[0]
          scene['performers'] = []
          if data.get('models'):
            for model in data['models']:
              scene['performers'].append({"name": model['name']})

          scene['tags'] = []
          if data.get('tags'):
            for tag in data['tags']:
                scene['tags'].append({"name": tag})

          if data.get('images') and data['images'].get('poster'):
            maxWidth = 0
            for image in data['images']['poster']:
              if image['width'] > maxWidth:
                scene['image'] = image['src']
              maxWidth = image['width']

          return scene

  getVideoQuery = """query getVideo($videoSlug: String, $site: Site) {
    findOneVideo(input: {slug: $videoSlug, site: $site}) {
      title
      description
      releaseDate
      models {
        name
      }
      images {
        poster {
          src
          width
        }
      }
      tags
  }
  }
  """

studios = {
        Site('Blacked'),
        Site('Blacked Raw'),
        Site('Deeper'),
        Site('Tushy'),
        Site('Tushy Raw'),
        Site('Slayed'),
        Site('Vixen')
}

frag = json.loads(sys.stdin.read())
url = frag.get("url")
if url is None:
  log.error(f"No URL given")
  print("{}")
  sys.exit(1)

for x in studios:
  if x.isValidURL(url):
    s = x.getScene(url)
    #log.debug(f"{json.dumps(s)}")
    print(json.dumps(s))
    sys.exit(0)

log.error(f"URL: {url} is not supported")
print("{}")
sys.exit(1)
