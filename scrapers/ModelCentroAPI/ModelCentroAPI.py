import datetime
import json
import os
import pathlib
import re
import sys
from configparser import ConfigParser, NoSectionError
from urllib.parse import urlparse

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()


def debug(q):
    print(q, file=sys.stderr)


def sendRequest(url, headers):
    r = ""
    try:
        r = requests.get(url, headers=headers, timeout=(3, 5))
    except requests.exceptions.RequestException:
        debug("An error has occurred with Requests")
        debug("Request status: {}".format(r.status_code))
        debug("Check your ModelCentroAPI.log for more details")
        with open("ModelCentroAPI.log", 'w', encoding='utf-8') as f:
            f.write("Request:\n{}".format(r.text))
        sys.exit(1)
    return r


def check_config(timenow):
    if os.path.isfile(SET_FILE_URL):
        config = ConfigParser()
        config.read(SET_FILE_URL)
        try:
            ini_keys1 = config.get(DOMAIN_URL, 'keys1')
            ini_keys2 = config.get(DOMAIN_URL, 'keys2')
            ini_date = config.get(DOMAIN_URL, 'date')
            time_past = datetime.datetime.strptime(ini_date, '%Y-%m-%d %H:%M:%S.%f')
            # Key for 1 days
            if time_past.day - timenow == 0:
                debug("Using old API keys")
                return ini_keys1, ini_keys2
            else:
                debug("Need new API keys")
        except NoSectionError:
            pass
    return None, None


def write_config(keys1, keys2):
    config = ConfigParser()
    config.read(SET_FILE_URL)
    try:
        config.get(DOMAIN_URL, 'date')
    except NoSectionError:
        config.add_section(DOMAIN_URL)
    config.set(DOMAIN_URL, 'keys1', keys1)
    config.set(DOMAIN_URL, 'keys2', keys2)
    config.set(DOMAIN_URL, 'date', str(datetime.datetime.now()))
    with open(SET_FILE_URL, 'w') as configfile:
        config.write(configfile)
    return

FRAGMENT = json.loads(sys.stdin.read())
USERFOLDER_PATH = str(pathlib.Path(__file__).parent.parent.absolute())
SCENE_URL = FRAGMENT["url"]
DOMAIN_URL = urlparse(SCENE_URL).netloc
DIR_JSON = os.path.join(USERFOLDER_PATH, "scraperJSON", DOMAIN_URL)
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
SET_FILE_URL = "ModelCentroAPI.ini"

scene_id = re.search(r"/(\d+)/*", SCENE_URL).group(1)
if not scene_id:
    debug("Error with the ID ({})\nAre you sure that your URL is correct ?".format(SCENE_URL))
    sys.exit(1)

timenow = datetime.datetime.now()
api_key1, api_key2 = check_config(timenow.day)
if api_key1 is None:
    debug("Going to the URL...")
    headers = {
        'User-Agent': USER_AGENT
    }
    r = sendRequest(SCENE_URL, headers)
    page_html = r.text
    try:
        api_function = re.findall(
            r'_fox_init(.+)</script>', page_html, re.DOTALL | re.MULTILINE)[0]
        api_key1 = re.findall(
            r'ah":"([a-zA-Z0-9_-]+)"', api_function, re.MULTILINE)[0]
        api_key2 = re.findall(r'aet":(\d+),"', api_function, re.MULTILINE)[0]
        # Need to reverse this key
        api_key1 = api_key1[::-1]
        write_config(api_key1, api_key2)
    except IndexError:
        debug("There is a problem with getting API identification")
        sys.exit(1)

debug("Asking the Scene API...")
api_url = "https://{}/sapi/{}/{}/content.load?_method=content.load&tz=1&filter[id][fields][0]=id&filter[id][values][0]={}&transitParameters[v1]=ykYa8ALmUD&transitParameters[preset]=scene".format(
    DOMAIN_URL, api_key1, api_key2, scene_id)
headers = {
    'User-Agent': USER_AGENT,
    'Referer': SCENE_URL
}
r = sendRequest(api_url, headers)
try:
    scene_api_json = r.json()['response']['collection'][0]
except:
    debug("Error with Request API")
    sys.exit(1)

debug("Trying the Performer API...")
perf_list = []
api_url = "https://{}/sapi/{}/{}/model.getModelContent?_method=model.getModelContent&tz=1&fields[0]=modelId.stageName&transitParameters[contentId]={}".format(
    DOMAIN_URL, api_key1, api_key2, scene_id)
r = sendRequest(api_url, headers)
try:
    performer_api_json = r.json()['response']['collection']
    for perf_id in performer_api_json:
        for perf_id2 in performer_api_json[perf_id]['modelId']['collection']:
            performer_name=performer_api_json[perf_id]['modelId']['collection'][perf_id2]['stageName']
            perf_list.append({"name": performer_name})
except:
    debug("Performer API failed")
    pass
# Time to scrape all data
scrape = {}
scrape['title'] = scene_api_json.get('title')
date = datetime.datetime.strptime(scene_api_json['sites']['collection'][scene_id].get('publishDate'), '%Y-%m-%d %H:%M:%S')
scrape['date'] = str(date.date())
scrape['details'] = scene_api_json.get('description')
scrape['studio'] = {}
scrape['studio']['name'] = re.sub('www\.|\.com', '', DOMAIN_URL)
if perf_list:
    scrape['performers'] = perf_list
scrape['tags'] = [{"name": scene_api_json['tags']['collection'][x].get('alias')} for x in scene_api_json['tags']['collection']]
scrape['image'] = scene_api_json['_resources']['primary'][0]['url']
for key_name, key_value in scrape.items():
    debug('[{}]:{}'.format(key_name, key_value))

print(json.dumps(scrape))

# Last Updated March 01, 2021
