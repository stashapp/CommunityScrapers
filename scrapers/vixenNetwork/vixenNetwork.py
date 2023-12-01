import json
import os
import sys
from urllib.parse import urlparse

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

# Max number of scenes that a site can return for the search.
MAX_SCENES = 6


class Site:

    def __init__(self, name: str):
        self.name = name
        self.id = name.replace(' ', '').upper()
        self.api = "https://www." + self.id.lower() + ".com/graphql"
        self.home = "https://www." + self.id.lower() + ".com"
        self.search_count = MAX_SCENES

    def isValidURL(self, url: str):
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

    def getSlug(self, url: str):
        u = url.lower().rstrip("/")
        slug = u.split("/")[-1]
        return slug

    def getScene(self, url: str):
        log.debug(f"Scraping using {self.name} graphql API")
        q = {
            'query': self.getVideoQuery,
            'operationName': "getVideo",
            'variables': {
                "site": self.id,
                "videoSlug": self.getSlug(url)
            }
        }
        r = self.callGraphQL(query=q, referer=url)
        return self.parse_scene(r)

    def getSearchResult(self, query: str):
        log.debug(f"Searching using {self.name} graphql API")
        q = {
            'query': self.getSearchQuery,
            'operationName': "getSearchResults",
            'variables': {
                "site": self.id,
                "query": query,
                "first": self.search_count
            }
        }
        r = self.callGraphQL(query=q, referer=self.home)
        return self.parse_search(r)

    def callGraphQL(self, query: dict, referer: str):
        headers = {
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Referer": referer,
            "DNT": "1",
        }
        if not query:
            return None

        try:
            response = requests.post(self.api, json=query, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if result.get("error"):
                    for error in result["error"]["errors"]:
                        raise Exception(f"GraphQL error: {error}")
                return result
            else:
                raise ConnectionError(
                    f"GraphQL query failed:{response.status_code} - {response.content}"
                )
        except Exception as err:
            log.error(f"GraphqQL query failed {err}")
            return None

    def parse_scene(self, response):
        scene = {}
        if response is None or response.get('data') is None:
            return scene

        data = response['data'].get('findOneVideo')
        if data:
            scene['title'] = data.get('title')
            scene['details'] = data.get('description')
            scene['studio'] = {"name": self.name}
            scene['code'] = data.get('videoId')
            director = data.get("directors")
            if director is not None:
                scene["director"] = ", ".join(d["name"] for d in data.get("directors", []))

            date = data.get('releaseDate')
            if date:
                scene['date'] = date.split("T")[0]
            scene['performers'] = []
            if data.get('models'):
                for model in data['models']:
                    scene['performers'].append({"name": model['name']})

            scene['tags'] = []
            tags = data.get('tags')
            categories = data.get('categories')
            if tags == [] and categories:
                for tag in data['categories']:
                    scene['tags'].append({"name": tag['name']})
            elif tags:
                for tag in data['tags']:
                    scene['tags'].append({"name": tag})

            if data.get('images'):
                if data['images'].get('poster'):
                    maxWidth = 0
                    for image in data['images']['poster']:
                        if image['width'] > maxWidth:
                            scene['image'] = image['src']
                        maxWidth = image['width']
            if url:
                scene["url"] = url
            return scene
        return None

    def parse_search(self, response):
        search_result = []

        if response is None or response.get('data') is None:
            return search_result

        data = response['data'].get('searchVideos')
        if data:
            for scene in data["edges"]:
                scene = scene.get("node")
                if scene:
                    slug = scene.get('slug')
                    # search results without a url are useless
                    # only add results with a slug present
                    if slug:
                        sc = {}
                        sc['title'] = scene.get('title')
                        sc['details'] = scene.get('description')
                        sc['url'] = f"https://www.{self.id.lower()}.com/videos/{slug}"
                        sc['code'] = scene.get('videoId')
                        sc['studio'] = {"name": self.name}
                        date = scene.get('releaseDate')
                        if date:
                            sc['date'] = date.split("T")[0]
                        sc['performers'] = []
                        if scene.get('modelsSlugged'):
                            for model in scene['modelsSlugged']:
                                sc['performers'].append(
                                    {"name": model['name']})
                        if scene.get('images'):
                            if scene['images'].get('listing'):
                                maxWidth = 0
                                for image in scene['images']['listing']:
                                    if image['width'] > maxWidth:
                                        sc['image'] = image['src']
                                    maxWidth = image['width']
                        search_result.append(sc)
            return search_result
        return None

    @property
    def length(self):
        return len(self.id)

    getVideoQuery = """
    query getVideo($videoSlug: String, $site: Site) {
        findOneVideo(input: {slug: $videoSlug, site: $site}) {
            title
            description
            releaseDate
            models {
                name
            }
            videoId
            directors {
                name
            }
            images {
                poster {
                    src
                    width
                }
            }
            tags
            categories {
                name
            }
        }
    }
    """
    getSearchQuery = """
    query getSearchResults($query: String!, $site: Site!, $first: Int) {
        searchVideos(input: { query: $query, site: $site, first: $first }) {
            edges {
                node {
                    description
                    title
                    slug
                    releaseDate
                    modelsSlugged: models {
                        name
                        slugged: slug
                    }
                    videoId
                    images {
                        listing {
                            src
                            width
                        }
                    }
                }
            }
        }
    }
  """


studios = {
    Site('Blacked Raw'),
    Site('Blacked'),
    Site('Deeper'),
    Site('Milfy'),
    Site('Tushy'),
    Site('Tushy Raw'),
    Site('Slayed'),
    Site('Vixen')
}

frag = json.loads(sys.stdin.read())
search_query = frag.get("name")
url = frag.get("url")

#sceneByURL
if url:
    for x in studios:
        if x.isValidURL(url):
            s = x.getScene(url)
            #log.debug(f"{json.dumps(s)}")
            print(json.dumps(s))
            sys.exit(0)
    log.error(f"URL: {url} is not supported")
    print("{}")
    sys.exit(1)

#sceneByName
if search_query and "search" in sys.argv:
    search_query = search_query.lower()
    lst = []
    wanted = []

    #  Only search on specific site if the studio name is in the search query
    # ('Ariana Vixen Cecilia' will search only on Vixen)

    # if the first character is $, filter will be ignored.
    if search_query[0] != "$":
        # make sure longer matches are filtered first
        studios_sorted = sorted(studios, reverse=True, key=lambda s: s.length)
        for x in studios_sorted:
            if x.id.lower() in search_query:
                wanted.append(x.id.lower())
                continue
            # remove the studio from the search result
            search_query = search_query.replace(x.id.lower(), "")
    else:
        search_query = search_query[1:]

    if wanted:
        log.info(f"Filter: {wanted} applied")

    log.debug(f"Query: '{search_query}'")

    for x in studios:
        if wanted:
            if x.id.lower() not in wanted:
                log.debug(f"[Filter] ignoring {x.id}")
                continue
        s = x.getSearchResult(search_query)
        # merge all list into one
        if s:
            lst.extend(s)
    #log.debug(f"{json.dumps(lst)}")
    print(json.dumps(lst))
    sys.exit(0)
