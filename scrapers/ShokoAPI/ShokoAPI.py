from urllib.request import Request, urlopen
import sys
import os
import json
import re
import urllib.error
import urllib.request

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
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit()

#user inputs start
SHOKO_API_KEY = ''  #leave empty it gets your Shoko api key with your shoko server username and password
STASH_API_KEY = ""  #your Stash api key
STASH_URL = "http://localhost:9999/graphql"  #your stash graphql url
SHOKO_URL = "http://localhost:8111"  #your shoko server url
SHOKO_USER = ""  #your shoko server username
SHOKO_PASS = ""  #your shoko server password
#user inputs end


def validate_user_inputs() -> bool:
    shoko = bool(re.search(r"^(http|https)://.+:\d+$", SHOKO_URL))
    if shoko is False:
        log.error("Shoko Url needs to be hostname:port and is currently " +
                  SHOKO_URL)
    stash = bool(re.match(r"^(http|https)://.+:\d+/graphql$", STASH_URL))
    if stash is False:
        log.error(
            "Stash Url needs to be hostname:port/graphql and is currently " +
            STASH_URL)
    return (shoko and stash)


def get_filename(scene_id: str) -> str:
    log.debug(f"stash sceneid: {scene_id}")
    headers = CaseInsensitiveDict()
    headers["ApiKey"] = STASH_API_KEY
    headers["Content-Type"] = "application/json"
    data = data = '{ \"query\": \" query { findScene (id: ' + scene_id + ' ) {path , id} }\" }'
    resp = requests.post(url=STASH_URL, headers=headers, data=data)
    if resp.status_code == 200:
        log.debug("Stash response was successful resp_code: " + str(resp.status_code))
    else:
        log.error("response from stash was not successful stash resp_code: " + str(resp.status_code))
        return None
    output = resp.json()
    path = output['data']['findScene']['path']
    log.debug("scene path in stash: " + str(path))
    pattern = "(^.+)([\\\\]|[/])"
    replace = ""
    filename = re.sub(pattern, replace, str(path))
    log.debug(f"encoded filename: {filename}")
    return filename


def find_scene_id(scene_id: str) -> (str, str):
    if SHOKO_API_KEY == "":
        apikey = get_apikey()
    else:
        apikey = SHOKO_API_KEY
    filename = get_filename(scene_id)
    return filename, apikey


def lookup_scene(scene_id: str, epnumber: str, apikey: str, date: str) -> dict:
    log.debug(epnumber)
    title, details, cover, tags = get_series(apikey, scene_id)  #, characters
    tags = tags + ["ShokoAPI"] + ["Hentai"]
    #characters_json = json.dumps(characters)
    #json_object = json.loads(characters_json)
    #character = json_object[0]['character']
    #log.info(str(character))
    res = {}
    res['title'] = title + " 0" + epnumber
    res['details'] = details
    res['image'] = cover
    res['date'] = date
    res['tags'] = [{"name": i} for i in tags]
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

    response_body = urlopen(request).read()
    json_object = json.loads(response_body.decode('utf-8'))
    log.debug("got series:\t" + str(json_object))
    title = json_object['name']
    details = json_object['summary']
    local_sizes = json_object['local_sizes']['Episodes']
    log.debug("number of episodes " + str(local_sizes))
    #characters = json_object['roles']
    cover = SHOKO_URL + json_object['art']['thumb'][0]['url']
    tags = json_object['tags']
    return title, details, cover, tags  #, characters


def query(fragment: dict) -> dict:
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


if __name__ == '__main__':
    main()
