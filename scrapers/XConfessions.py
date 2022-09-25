import json
import os
import re
import sys
from typing import List
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

# Allows us to simply debug the script via CLI args
if len(sys.argv) > 2 and '-d' in sys.argv:
    stdin = sys.argv[sys.argv.index('-d') + 1]
else:
    stdin = sys.stdin.read()

frag = json.loads(stdin)
search_query = frag.get("name", frag.get('title'))
url = frag.get("url")


def return_result(result):
    """
    If a scene is needed it will first fetch scene data with the url of the first item in search results
    and return to stash, Otherwise returns the search results (list) to stash.

    Returns:
        None: Totally exit the scraper via sys.exit(0)
    """
    try:
        print(json.dumps(result))
        sys.exit(0)
    except Exception as err:
        log.error(f"Exception occurred during returning result: {err}")


class Site:

    def __init__(self, name: str):
        self.name = name
        self.id = name.replace(' ', '').upper()
        self.api = "https://api." + self.id.lower() + ".com/api"
        self.home = "https://www." + self.id.lower() + ".com"
        self.access_token: str = ''
        self.search_count = MAX_SCENES
        self.getAccessToken()

    def isValidURL(self, url: str):
        u = url.lower().rstrip("/")
        up = urlparse(u)
        if up.hostname is None:
            return False
        if up.hostname.lstrip("www.").lstrip("api.").rstrip(".com") == self.id.lower():
            splits = u.split("/")
            if len(splits) < 4:
                return False
            if splits[3] == "film":
                return True
        return False

    def getSlug(self, url: str):
        u = url.lower().rstrip("/")
        slug = u.split("/")[-1]
        return slug

    def getSearchResult(self, query: str):
        log.debug(f"Searching using {self.name} API")
        reqBody = {
            'query': query,
        }
        r = self.postAPI('/search', json=reqBody)
        p = self.parse_search(r)
        return p

    def getAPI(self, route: str, params: dict = None, attempt: int = 1):
        if route is None:
            return None
        if route.startswith('/') == False:
            route = '/' + route
        headers = {
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
            "DNT": "1",
            "X-Requested-With": "XMLHttpRequest",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
            'Authorization': f'Bearer {self.access_token}',
        }

        try:
            response = requests.get(
                self.api + route, params=params, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, dict) and result.get("error"):
                    for error in result["error"]["errors"]:
                        raise Exception(f"API GET error: {error}")
                return result
            elif response.status_code == 403 and attempt == 1:
                # The access token is not working probably.
                self.getAccessToken(force=True)
                return self.getAPI(route=route, params=params, attempt=attempt + 1)
            else:
                raise ConnectionError(
                    f"API GET query failed:{response.status_code} - {response.content}"
                )
        except Exception as err:
            log.error(f"API GET query failed {err}")
            return None

    def postAPI(self, route: str, json: dict = None, params: dict = None, attempt: int = 1):
        if route is None or json is None:
            return None
        if route.startswith('/') == False:
            route = '/' + route
        headers = {
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "DNT": "1",
            "X-Requested-With": "XMLHttpRequest",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
            'Authorization': f'Bearer {self.access_token}',
        }

        try:
            response = requests.post(
                self.api + route, params=params, json=json, headers=headers)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, dict) and result.get("error"):
                    for error in result["error"]["errors"]:
                        raise Exception(f"API POST error: {error}")
                return result
            elif response.status_code == 403 and attempt == 1:
                # The access token is not working probably.
                self.getAccessToken(force=True)
                return self.postAPI(route=route, json=json, params=params, attempt=attempt + 1)
            else:
                raise ConnectionError(
                    f"API POST query failed:{response.status_code} - {response.content}"
                )
        except Exception as err:
            log.error(f"API POST query failed {err}")
            return None

    def parse_search(self, response: dict):
        search_result = []

        if response is None:
            return search_result

        data = response if isinstance(response, list) else [response]
        if data:
            for item in data:
                model_type = item.get("model_type")
                if model_type != 'App\Models\Movie':
                    # Only Iterate over Movies, No Confession or Pereson
                    continue

                if item:
                    slug = item.get('slug')
                    # search results without a url are useless
                    # only add results with a slug present
                    if slug:
                        sc = {}
                        sc['title'] = item.get('title')
                        sc['url'] = f"https://www.{self.id.lower()}.com/film/{slug}"
                        sc['studio'] = {"name": 'XConfessions',
                                        'url': 'https://xconfessions.com/'}
                        date = item.get('release_date')
                        if date:
                            sc['date'] = date.split(' ')[0]
                        # sc['performers'] = []
                        # if item.get('modelsSlugged'):
                        #     for model in item['modelsSlugged']:
                        #         sc['performers'].append(
                        #             {"name": model['name']}
                        #         )

                        sc['image'] = item.get('poster_picture')
                    search_result.append(sc)
            return search_result
        return None

    def length(self, studio):
        return len(studio.id)

    def cacheAccessToken(self, access_token: str):
        cache_file_path = os.path.join(os.path.realpath(
            os.path.dirname(__file__)), f'{self.id}.accessToken')
        if access_token is None or len(access_token) < 10:
            return
        with open(cache_file_path, "w") as file:
            file.write(access_token)

    def cachedAccessToken(self):
        cache_file_path = os.path.join(os.path.realpath(
            os.path.dirname(__file__)), f'{self.id}.accessToken')
        if os.path.isfile(cache_file_path) == False:
            return ''
        with open(cache_file_path, encoding='utf8') as f:
            return f.readline()

    def getAccessToken(self, force: bool = False):
        if self.access_token is not None and len(self.access_token) > 10:
            return

        if force == False:
            self.access_token = self.cachedAccessToken()
            if self.access_token is not None and len(self.access_token) > 10:
                return

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'
        }

        response = requests.get('https://xconfessions.com/', headers=headers)
        if response.status_code == 200:
            body = response.text
            match = re.search('access_token="(.*?)";', body, re.MULTILINE)
            if match:
                self.access_token = match.group(1)
                self.cacheAccessToken(self.access_token)


studios: List[Site] = [Site('XConfessions')]


def remove_dates_from_str(str_input: str):
    str_input = re.sub(r"\d{8}", "", str_input, 0,
                       re.IGNORECASE | re.MULTILINE)
    str_input = re.sub(r"\d{4}([-./])\d{2}([-./])\d{2}",
                       "", str_input, 0, re.IGNORECASE | re.MULTILINE)
    return str_input


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


def search_method_1(query: str):
    if query is None or len(query) < 1:
        # If the search query is empty, exit.
        return None

    query = remove_dates_from_str(query)
    search_results = []
    for x in studios:
        search_result = x.getSearchResult(query)
        search_results.extend(search_result)

    end_results = []
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
            end_results.append(search_result)

    return end_results


def search_method_2(query: str):
    if query is None or len(query) < 1:
        # If the search query is empty, exit.
        return None

    query = remove_dates_from_str(query)
    search_results = []
    for x in studios:
        search_result = x.getSearchResult(query)
        search_results.extend(search_result)

    return search_results


for search_method in [
    "1. Search for query and match the title with search result title",
    "2. Input search query",
]:
    method: int = int(search_method[:1])
    try:
        if method == 1:
            result = search_method_1(query=search_query)
            if result is not None and len(result) > 0:
                # There's a result, pass to stash.
                return_result(result)
        elif method == 2:
            result = search_method_2(query=search_query)
            if result is not None and len(result) > 0:
                # There's a result, pass to stash.
                return_result(result)
    except Exception as err:
        log.error(f"Exception occurred in search_method_{method}: {err}")

print(json.dumps([]))
sys.exit(0)

# Last Updated September 25, 2022
