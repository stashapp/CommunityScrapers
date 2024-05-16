import json
import os
import sys
from urllib.parse import urlparse
from datetime import datetime, timedelta

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

# Marker
# If you want to create a marker while Scraping.
CREATE_MARKER = False
# Only create marker if the durations match (API vs Stash)
MARKER_DURATION_MATCH = True
# Sometimes the API duration is 0/1, so we can't really know if this matches. True if you want to create anyways
MARKER_DURATION_UNSURE = True
# Max allowed difference (seconds) in scene length between Stash & API.
MARKER_SEC_DIFF = 10

# Tags you don't want to see in the Scraper window.
IGNORE_TAGS = ["Sex","Feature","HD","Big Dick"]
# Tags you want to add in the Scraper window.
FIXED_TAGS = ""
# Add studio default tags to scenes (eg, "Anal Sex" for "Tushy")
USE_STUDIO_DEFAULT_TAGS = True
# Check the SSL Certificate.
CHECK_SSL_CERT = True
# Local folder with JSON inside (Only used if scene isn't found from the API)
LOCAL_PATH = r""

SERVER_IP = "http://localhost:9999"
# API key (Settings > Configuration > Authentication)
STASH_API = ""

# Automatically reattempt GraphQL queries to Vixen sites which fail with a 403 response 
MAX_403_REATTEMPTS = 20

SERVER_URL = SERVER_IP + "/graphql"

def callGraphQL(query, variables=None):
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "DNT": "1",
        "ApiKey": STASH_API
    }
    json = {'query': query}
    if variables is not None:
        json['variables'] = variables
    try:
        response = requests.post(SERVER_URL, json=json, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result.get("error"):
                for error in result["error"]["errors"]:
                    raise Exception("GraphQL error: {}".format(error))
            if result.get("data"):
                return result.get("data")
        elif response.status_code == 401:
            log.error("[GraphQL] HTTP Error 401, Unauthorised.")
            return None
        else:
            raise ConnectionError("GraphQL query failed:{} - {}".format(response.status_code, response.content))
    except Exception as err:
        log.error(err)
        return None

def graphql_findTagbyName(name):
    query = """
        query {
            allTags {
                id
                name
                aliases
            }
        }
    """
    result = callGraphQL(query)
    normalized_name = name.lower().strip()
    for tag in result["allTags"]:
        if tag["name"].lower() == normalized_name:
            return tag["id"]
        if tag.get("aliases"):
            for alias in tag["aliases"]:
                if alias.lower() == normalized_name:
                    return tag["id"]
    return None

def graphql_createMarker(scene_id, title, main_tag, seconds, tags=[]):
    main_tag_id = graphql_findTagbyName(main_tag)
    if main_tag_id is None:
        log.warning("The 'Primary Tag' don't exist ({}), marker won't be created.".format(main_tag))
        return None
    log.info("Creating Marker: {}".format(title))
    query = """
    mutation SceneMarkerCreate($title: String!, $seconds: Float!, $scene_id: ID!, $primary_tag_id: ID!, $tag_ids: [ID!] = []) {
        sceneMarkerCreate(
            input: {
            title: $title
            seconds: $seconds
            scene_id: $scene_id
            primary_tag_id: $primary_tag_id
            tag_ids: $tag_ids
            }
        ) {
            ...SceneMarkerData
        }
    }
    fragment SceneMarkerData on SceneMarker {
        id
        title
        seconds
        stream
        preview
        screenshot
        scene {
            id
        }
        primary_tag {
            id
            name
            aliases
        }
        tags {
            id
            name
            aliases
        }
    }
    """
    variables = {
        "primary_tag_id": main_tag_id,
        "scene_id":	scene_id,
        "seconds":	seconds,
        "title": title,
        "tag_ids": tags
    }
    result = callGraphQL(query, variables)
    return result

def graphql_getMarker(scene_id):
    query = """
    query FindScene($id: ID!, $checksum: String) {
        findScene(id: $id, checksum: $checksum) {
            scene_markers {
                seconds
            }
        }
    }
    """
    variables = {
        "id": scene_id
    }
    result = callGraphQL(query, variables)
    if result:
        if result["findScene"].get("scene_markers"):
            return [x.get("seconds") for x in result["findScene"]["scene_markers"]]
    return None

def graphql_getScene(scene_id):
    query = """
    query FindScene($id: ID!, $checksum: String) {
        findScene(id: $id, checksum: $checksum) {
            files {
                duration
            }
            scene_markers {
                seconds
            }
        }
    }
    """
    variables = {
        "id": scene_id
    }
    result = callGraphQL(query, variables)
    if result:
        return_dict = {}
        return_dict["duration"] = result["findScene"]["files"][0]["duration"]
        if result["findScene"].get("scene_markers"):
            return_dict["marker"] = [x.get("seconds") for x in result["findScene"]["scene_markers"]]
        else:
            return_dict["marker"] = None
        return return_dict
    return None

def parse_duration_to_seconds(duration):
    if duration is None:
        return None
    t = datetime.strptime(duration,"%H:%M:%S")
    delta = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
    return delta.seconds

def process_chapters(scene_id, api_json):
    if scene_id and STASH_API and CREATE_MARKER and api_json != {}:
        log.debug(f"Processing markers: {json.dumps(api_json.get('markers'))}")
        markers = api_json.get("markers")
        if markers:
            stash_scene_info = graphql_getScene(scene_id)
            api_scene_duration = None
            if api_json.get("runLength"):                
                api_scene_duration = api_json.get("runLength")
            
            log.debug(f"API Duration: {api_scene_duration}")
            if MARKER_DURATION_MATCH and api_scene_duration is None:
                log.info("No duration given by the API.")
            else:
                log.debug("Stash Len: {}| API Len: {}".format(stash_scene_info["duration"], api_scene_duration))
                if (MARKER_DURATION_MATCH and api_scene_duration-MARKER_SEC_DIFF <= stash_scene_info["duration"] <= api_scene_duration+MARKER_SEC_DIFF) or (api_scene_duration in [0,1] and MARKER_DURATION_UNSURE):
                    for marker in markers:
                        if stash_scene_info.get("marker"):
                            if marker.get("seconds") in stash_scene_info["marker"]:
                                log.debug("Ignoring marker ({}) because already have with same time.".format(marker.get("seconds")))
                                continue
                        try:
                            graphql_createMarker(scene_id, marker.get("title"), marker.get("title"), marker.get("seconds"))
                        except:
                            log.error("Marker failed to create")
                else:
                    log.info("The duration of this scene don't match the duration of stash scene.")
        else:
            log.info("No offical marker for this scene")

class Site:

    def __init__(self, name: str, deftags: list):
        self.name = name
        self.deftags = deftags
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0",
        }
        if not query:
            return None

        reattempts = 0
        while True:
            try:
                response = requests.post(self.api, json=query, headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("error"):
                        for error in result["error"]["errors"]:
                            raise Exception(f"GraphQL error: {error}")
                    if reattempts > 0:
                        log.debug(f"Successful query after attempt #{reattempts}")
                    return result
                elif response.status_code == 403:
                    log.error("GraphQL query recieved a 403 status response")
                    if reattempts < MAX_403_REATTEMPTS:
                        log.debug(f"403 Reattempt {reattempts}/{MAX_403_REATTEMPTS}")
                    else:
                        log.error(f"Reached max 403 errors for GraphQL query")
                        return {}
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
            if USE_STUDIO_DEFAULT_TAGS:
                for tag in self.deftags:
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

            scene['runLength'] = parse_duration_to_seconds(data.get("runLength"))
            
            markers = data.get('chapters', {}).get('video')
            if markers:
                scene["markers"] = markers

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
            runLength
            chapters {
                video {
                    title
                    seconds
                }
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
    Site('Blacked Raw',['Black Male']),
    Site('Blacked',['Black Male']),
    Site('Deeper',[]),
    Site('Milfy',['MILF']),
    Site('Tushy',['Anal Sex']),
    Site('Tushy Raw',['Anal Sex']),
    Site('Slayed',['Lesbian Sex']),
    Site('Vixen',[])
}

frag = json.loads(sys.stdin.read())
search_query = frag.get("name")
url = frag.get("url")
scene_id = frag.get("id")

def check_alternate_urls(site):
    for u in frag.get("urls", []):
        if site.isValidURL(u):
            return u
    return None

#sceneByURL
if url:
    for x in studios:
        proper_url = None
        if x.isValidURL(url):
            proper_url = url
        else:
            proper_url = check_alternate_urls(site=x)

        if proper_url != None:
            s = x.getScene(proper_url)
            # log.info(f"{json.dumps(s)}")
            process_chapters(scene_id=scene_id, api_json=s)

            # drop unwanted keys from json result
            s.pop('runLength', None)
            s.pop('markers', None)

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
