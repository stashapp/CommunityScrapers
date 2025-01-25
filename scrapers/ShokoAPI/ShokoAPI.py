import os
import sys
import json
import re
import unicodedata  # For Unicode normalization
from urllib.parse import quote  # For URL encoding
from urllib.request import Request, urlopen  # For HTTP requests
import urllib.error  # For handling URL-related errors

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from ther

try:
    import requests
    from requests.utils import requote_uri
    from requests.structures import CaseInsensitiveDict
except ModuleNotFoundError:
    print(
        "You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)",
        file=sys.stderr)
    print(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests",
        file=sys.stderr)
    sys.exit()

try:
    from py_common import log
    import py_common.graphql as graphql
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit()
    
import config

SHOKO_API_KEY = ''  #leave empty it gets your Shoko api key with your shoko server username and password
SHOKO_URL = config.SHOKO.get("url", "")
SHOKO_USER = config.SHOKO.get("user", "")
SHOKO_PASS = config.SHOKO.get("pass", "")


def validate_user_inputs() -> bool:
    shoko = bool(re.search(r"^(http|https)://.+:\d+$", SHOKO_URL))
    if shoko is False:
        log.error("Shoko Url needs to be hostname:port and is currently " +
                  SHOKO_URL)
    return (shoko)


def get_filename(scene_id: str) -> str:
    log.debug(f"stash sceneid: {scene_id}")
    log.debug(graphql.getScene(scene_id))
    data = graphql.getScene(scene_id)
    path = data['files'][0]['path']
    log.debug("scene path in stash: " + str(path))
    pattern = "(^.+)([\\\\]|[/])"
    replace = ""
    filename = re.sub(pattern, replace, str(path))
    normalized_filename = unicodedata.normalize('NFC', filename)
    encoded_filename = quote(normalized_filename, safe='')
    log.debug(f"encoded filename: {encoded_filename}")
    return encoded_filename


def find_scene_id(scene_id: str) -> (str, str):
    if SHOKO_API_KEY == "":
        apikey = get_apikey()
    else:
        apikey = SHOKO_API_KEY
    filename = get_filename(scene_id)
    return filename, apikey


def lookup_scene(scene_id: str, epnumber: str, apikey: str, date: str) -> dict:
    log.debug(epnumber)
    title, details, cover, tags, studio, studio_id = get_series(apikey, scene_id)  #, characters
    tags = tags + ["ShokoAPI"] + ["Hentai"]
    res = {}
    res['title'] = title + " 0" + epnumber
    res['details'] = details
    res['image'] = cover
    res['date'] = date
    res['tags'] = [{"name": i} for i in tags]
    
    if studio is None or studio_id is None:
        log.info("No studio information found. Skipping studio.")
    else:
        # Convert the string to a ScrapedStudio instance
        studio: ScrapedStudio = {
            "name": studio,  # Map the string to the required `name` field
            "image": f"{SHOKO_URL}/api/v3/Image/AniDB/Staff/{studio_id}" 
        }
    
        res['studio'] = studio
        
    log.debug("sceneinfo from Shoko: " + str(res))
    return res


def get_apikey() -> str:
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"

    values = '{"user": "' + SHOKO_USER + '","pass": "' + SHOKO_PASS + '","device": "Stash Scan"}'

    resp = requests.post(SHOKO_URL + '/api/auth', data=values, headers=headers)
    if resp.status_code == 200:
        log.debug("got Shoko's apikey: ")
        apikey = str(resp.json()['apikey'])
        return apikey
    elif resp.status_code == 401:
      log.error("check if your shoko server username/password is correct")
      return None
    else:
        log.error("response from Shoko was not successful stash resp_code: " + str(resp.status_code))
        return None


def find_scene(apikey: str, filename: str):
    headers = CaseInsensitiveDict()
    headers["apikey"] = apikey
    url_call = requote_uri(SHOKO_URL + '/api/ep/getbyfilename?filename=' + filename)
    log.debug(f"using url: {url_call}")
    request = Request(url_call, headers=headers)

    try:
        response_body = urlopen(request).read()
    except urllib.error.HTTPError as http_error:
        if http_error.code == 404:
            log.info(f"the file: {filename} is not matched on shoko")
    except urllib.error.URLError as url_error:
        # Not an HTTP-specific error (e.g. connection refused)
        # ...
        log.error(f'URLError: {url_error.reason}')
    else:
        # 200
        log.info(f"the file: {filename} is matched on shoko")
        json_object = json.loads(response_body.decode('utf-8'))
        log.debug("found scene\t" + str(json_object))
        scene_id = json_object['id']
        epnumber = str(json_object['epnumber']) + ' ' + str(json_object['name'])
        date = json_object['air']
        return scene_id, epnumber, date


def get_series(apikey: str, scene_id: str):
    headers = CaseInsensitiveDict()
    headers["apikey"] = apikey
    request = Request(SHOKO_URL + '/api/serie/fromep?id=' + scene_id, headers=headers)

    try:
        response_body = urlopen(request).read()
        json_object = json.loads(response_body.decode('utf-8'))
    except Exception as e:
        log.error(f"Failed to fetch series details: {e}")
        return None, None, None, None, None, None

    log.debug("got series:\t" + str(json_object))
    title = json_object.get('name', None)
    details = json_object.get('summary', None)
    local_sizes = json_object.get('local_sizes', {}).get('Episodes', 0)
    log.debug("number of episodes " + str(local_sizes))
    cover = SHOKO_URL + json_object['art']['thumb'][0]['url']
    tags = json_object.get('tags', [])

    series_id = json_object.get('id')

    try:
        response = requests.get(
            f'{SHOKO_URL}/api/v3/Series/{series_id}/Cast?roleType=Studio', 
            headers=headers
        )
        response.raise_for_status()
        json_response = response.json()
    except requests.RequestException as e:
        log.error(f"Failed to fetch studio data: {e}")
        json_response = []
          
    # Handle cases where there are no studios
    if json_response:
        studio = json_response[0].get('Staff', {}).get('Name', None)
        studio_id = json_response[0].get('Staff', {}).get('ID', None)
    else:
        studio = None
        studio_id = None

    return title, details, cover, tags, studio, studio_id  #, characters


def query(fragment: dict) -> dict:
    if fragment['title'] == "":
        scene_id = fragment['id']
        query = """query findScene($scene_id:ID!){findScene(id:$scene_id){files{basename}}}"""
        variables = {'scene_id': scene_id}
        result = call_graphql(query, variables)
        basename = result['findScene']['files'][0]['basename']
    filename, apikey = find_scene_id(fragment['id'])
    try:
        findscene_scene_id, findscene_epnumber, find_date = find_scene(apikey, filename)
    except:
        return None
    scene_id = str(findscene_scene_id)
    epnumber = str(findscene_epnumber)
    date = str(find_date)
    apikey = str(apikey)
    log.debug(f"Found scene id: {scene_id}")
    result = lookup_scene(scene_id, epnumber, apikey, date)
    return result


def main():
    mode = sys.argv[1]
    fragment = json.loads(sys.stdin.read())
    log.debug(str(fragment))
    data = None
    check_input = validate_user_inputs()
    if check_input is True:
        if mode == 'query':
            data = query(fragment)
    print(json.dumps(data))

def call_graphql(query, variables=None):
    return graphql.callGraphQL(query, variables)


if __name__ == '__main__':
    main()
