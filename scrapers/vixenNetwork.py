import json
import os
import re
import sys
from urllib.parse import urlparse

try:
    import requests
except ModuleNotFoundError:
    print(
        "You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)",
        file=sys.stderr
    )
    print(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests",
        file=sys.stderr
    )
    sys.exit()

try:
    import py_common.log as log
    import py_common.graphql as graphql
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr
    )
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
        p = self.parse_search(r)
        return p

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

            date = data.get('releaseDate')
            if date:
                scene['date'] = date.split("T")[0]
            scene['performers'] = []
            if data.get('models'):
                for model in data['models']:
                    scene['performers'].append({"name": model['name']})

            scene['tags'] = []
            if data.get('tags'):
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
                        sc['studio'] = {"name": self.name}
                        date = scene.get('releaseDate')
                        if date:
                            sc['date'] = date.split("T")[0]
                        sc['performers'] = []
                        if scene.get('modelsSlugged'):
                            for model in scene['modelsSlugged']:
                                sc['performers'].append(
                                    {"name": model['name']}
                                )

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

    def length(self, studio):
        return len(studio.id)

    getVideoQuery = """
    query getVideo($videoSlug: String, $site: Site) {
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


# sort site dicts into a list
# by reverse id length
def sortByLength(sites):
    sorted = []
    for s in sites:
        sorted.append(s)
    sorted.sort(reverse=True, key=s.length)
    return sorted


studios = {
    Site('Blacked Raw'),
    Site('Blacked'),
    Site('Deeper'),
    Site('Tushy'),
    Site('Tushy Raw'),
    Site('Slayed'),
    Site('Vixen')
}

# Allows us to simply debug the script via CLI args
if len(sys.argv) > 2 and '-d' in sys.argv:
    stdin = sys.argv[sys.argv.index('-d') + 1]
else:
    stdin = sys.stdin.read()

frag = json.loads(stdin)
scene_id = frag.get("id")
search_query = frag.get("name")
url = frag.get("url")
if scene_id:
    scene_data = graphql.getScene(scene_id)
    if scene_data is None:
        filename = frag.get("title")
    else:
        filename = scene_data.get("path")
else:
    filename = scene_data = None

# sceneByURL
if url:
    for x in studios:
        if x.isValidURL(url):
            s = x.getScene(url)
            # log.debug(f"{json.dumps(s)}")
            print(json.dumps(s))
            sys.exit(0)
    if not filename:
        log.error(f"URL: {url} is not supported")
        print("{}")
        sys.exit(1)

return_scene = "sceneByFragment" in sys.argv


def extract_filter_from_query(str_query: str):
    filter = []
    #  Only search on specific site if the studio name is in the search query
    # ('Ariana Vixen Cecilia' will search only on Vixen)
    # if the first character is $, filter will be ignored.
    if str_query[0] != "$":
        # make sure longer matches are filtered first
        studios_sorted = sortByLength(studios)
        for x in studios_sorted:
            if x.id.lower() in str_query.lower():
                filter.append(x.id.lower())
                str_query = re.sub(
                    x.id, "", str_query, 0,
                    re.IGNORECASE | re.MULTILINE
                )
                continue
            # remove the studio from the search result
    else:
        str_query = str_query[1:]

    # if filter:
        # log.info(f"Filter: {filter} applied")

    if len(filter) > 0:
        return filter, str_query
    else:
        return None, str_query


def extract_date_from_filename(str_filename: str):
    # Here we will check if there's scene date in query, like: 20150125 which is 2015/01/15 actually.
    match = re.search(r"\d{8}", str_filename)
    if match:
        query_scene_date = match.group()
    else:
        query_scene_date = None
    if query_scene_date is None:
        # There were no scene date with yyyymmdd format in the query, let's try the yyyy/mm/dd or yyyy-mm-dd or yyyy.mm.dd format
        match = re.search(
            r"\d{4}([-./])\d{2}([-./])\d{2}", str_filename
        )
        if match:
            # There's a match to the format above but we need to remove the separator chars from the match.
            query_scene_date = str(match.group()).replace(
                '.', ''
            ).replace('-', '').replace('/', '')
        else:
            query_scene_date = None
    if query_scene_date is None:
        return None
    # we can have an accurate search as we there's scene date in query
    parsed_scene_date = f'{query_scene_date[:4]}-{query_scene_date[4:6]}-{query_scene_date[6:8]}'
    return parsed_scene_date


def remove_dates_from_str(str_input: str):
    str_input = re.sub(r"\d{8}", "", str_input, 0,
                       re.IGNORECASE | re.MULTILINE)
    str_input = re.sub(r"\d{4}([-./])\d{2}([-./])\d{2}",
                       "", str_input, 0, re.IGNORECASE | re.MULTILINE)
    return str_input


def return_the_scene(str_url: str):
    """
    Grabs the scene by its link and announces the scene data to stash then exit.

    Returns:
        None: Totally exit the scraper via sys.exit(0)
    """
    for studio in studios:
        if studio.isValidURL(str_url):
            scene_result = studio.getScene(str_url)
            if 'url' not in scene_result:
                scene_result['url'] = str_url
            print(json.dumps(scene_result))
            sys.exit(0)


def return_result(result):
    """
    If a scene is needed it will first fetch scene data with the url of the first item in search results
    and return to stash, Otherwise returns the search results (list) to stash.

    Returns:
        None: Totally exit the scraper via sys.exit(0)
    """
    try:
        if return_scene is True:
            return_the_scene(result[0]['url'])
        else:
            print(json.dumps(result))
            sys.exit(0)
    except Exception as err:
        log.error(f"Exception occurred during returning result: {err}")


def cleanup_str_for_title_match(str_input: str):
    # 'Daddy's Girl' to 'Daddys Girl'
    str_input = re.sub("('s)", "s", str_input.lower(),
                       0, re.IGNORECASE | re.MULTILINE)

    # 'Daddys.Girl' to 'Daddys Girl'
    str_input = re.sub("""[-,.'"~!@#$%^&*()_+|><]""", " ",
                       str_input, 0, re.IGNORECASE | re.MULTILINE)

    # ' Daddys  Girl   ' to ' Daddys Girl'
    str_input = re.sub(r"[\s\t]{2,}", " ", str_input,
                       0, re.IGNORECASE | re.MULTILINE)

    # ' Daddys Girl' to 'Daddys Girl'
    str_input = str_input.strip()

    return str_input


def search_method_1(str_filename: str):
    if str_filename is None:
        # We don't have the filename and this method depends on it.
        return None
    date_in_filename = extract_date_from_filename(
        str_filename=os.path.basename(str_filename))
    if date_in_filename is None:
        # There's no date in the filename and this method depends on it.
        return None

    query: str = os.path.splitext(os.path.basename(str_filename))[0]
    filter = extract_filter_from_query(str_query=query)
    query = filter[1]
    filter = filter[0]
    query = remove_dates_from_str(query)
    search_results = []
    for x in studios:
        if filter:
            if x.id.lower() not in filter:
                continue
        search_result = x.getSearchResult(query)
        search_results.extend(search_result)

    end_result = []

    for search_result in search_results:
        if search_result is None:
            continue
        if 'date' in search_result and search_result['date'] is not None and search_result['date'] == date_in_filename:
            # Date in search result's scene matches the date in the filename.
            if 'title' in search_result and search_result['title'] is not None and len(
                    search_result['title']
            ) > 0 and cleanup_str_for_title_match(
                    str_input=str(
                        search_result['title']
                    ).lower()) in cleanup_str_for_title_match(str_input=query.lower()):
                # Title in search result's scene exists in the filename.
                # It's a match in this method.
                end_result.append(search_result)

    return end_result


def search_method_2(str_filename: str):
    if str_filename is None:
        # We don't have the filename and this method depends on it.
        return None

    query: str = os.path.splitext(os.path.basename(str_filename))[0]
    filter = extract_filter_from_query(str_query=query)
    query = filter[1]
    filter = filter[0]
    query = remove_dates_from_str(query)
    search_results = []
    for x in studios:
        if filter:
            if x.id.lower() not in filter:
                continue
        search_result = x.getSearchResult(query)
        search_results.extend(search_result)

    end_result = []

    for search_result in search_results:
        if search_result is None:
            continue
        if 'title' in search_result and search_result['title'] is not None and len(
                search_result['title']
        ) > 0 and cleanup_str_for_title_match(
                str_input=str(
                    search_result['title']
                ).lower()) in cleanup_str_for_title_match(str_input=query.lower()):
            # Title in search result's scene exists in the filename.
            if 'performers' in search_result and len(search_result['performers']) > 0:
                # Only the first performer is checked because usually female performers are written first in both
                # filename and site.
                performer_name = search_result['performers'][0]['name']
                if performer_name is not None and len(performer_name) > 1:
                    # Replace the filename (query) space replacements (e.g. Hello.World)
                    # with space (results in: Hello World)
                    if cleanup_str_for_title_match(str_input=str(performer_name).lower()) in cleanup_str_for_title_match(
                            str_input=query.lower()):
                        # Performer name found in the filename. It's a match in this method.
                        end_result.append(search_result)
            else:
                # There's no performer in the scene result.
                continue

    return end_result


def search_method_3(query: str):
    if query is None or len(query) < 1:
        # We don't have the filename and this method depends on it.
        return None

    date_in_query = extract_date_from_filename(str_filename=query)

    filter = extract_filter_from_query(str_query=query)
    query = filter[1]
    filter = filter[0]
    query = remove_dates_from_str(query)
    search_results = []
    for x in studios:
        if filter:
            if x.id.lower() not in filter:
                continue
        search_result = x.getSearchResult(query)
        search_results.extend(search_result)

    end_result = []

    for search_result in search_results:
        if search_result is None:
            continue
        end_result.append(search_result)
        date_matches = False if date_in_query is None else \
            'date' in search_result and search_result['date'] is not None and search_result['date'] == date_in_query
        title_matches = 'title' in search_result and search_result['title'] is not None and len(
            search_result['title']
        ) > 0 and cleanup_str_for_title_match(
            str_input=str(
                search_result['title']
            ).lower()) in cleanup_str_for_title_match(str_input=query.lower())
        performer_matches = False
        if 'performers' in search_result and len(search_result['performers']) > 0:
            performer_name = search_result['performers'][0]['name']
            # Only the first performer is checked because usually female performers are written first in both
            # filename and site.
            performer_matches = performer_name is not None and len(performer_name) > 1 and \
                cleanup_str_for_title_match(
                    str_input=str(performer_name).lower(
                    )) in cleanup_str_for_title_match(str_input=query.lower())

        if (date_matches is True and title_matches is True) or (performer_matches is True and title_matches is True):
            # This is 99.9% the one and only true match.
            # we will only return this one result, so choosing it will be easier for the end user
            return [search_result]

    return end_result


for search_method in [
    "1. Search and match by date and title in scene's filename",
    "2. Search and match by scene title and one performer name in filename",
    "3. Input search query"
]:
    method: int = int(search_method[:1])
    try:
        if method == 1:
            result = search_method_1(str_filename=filename)
            if result is not None and len(result) > 0:
                # There's a result, pass to stash.
                return_result(result)
        elif method == 2:
            result = search_method_2(str_filename=filename)
            if result is not None and len(result) > 0:
                # There's a result, pass to stash.
                return_result(result)
        elif method == 3:
            result = search_method_3(query=search_query)
            if result is not None and len(result) > 0:
                # There's a result, pass to stash.
                return_result(result)
    except Exception as err:
        log.error(f"Exception occurred in search_method_{method}: {err}")

if return_scene is True:
    print('{}')
    sys.exit(0)
else:
    print(json.dumps([]))
    sys.exit(0)

# Last Updated June 24, 2022
