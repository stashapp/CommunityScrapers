import datetime
import json
import os
import re
import sys
from configparser import ConfigParser, NoSectionError
from urllib.parse import urlparse

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
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

def sendRequest(url, req_headers):
    req = ""
    try:
        req = requests.get(url, headers=req_headers, timeout=(3, 5))
    except requests.exceptions.RequestException:
        log.error("An error has occurred with Requests")
        log.error("Check your ModelCentroAPI.log for more details")
        with open("ModelCentroAPI.log", 'w', encoding='utf-8') as log_file:
            log_file.write(f"Request:\n{req}")
        sys.exit(1)
    return req


def check_config(time_now):
    if os.path.isfile(SET_FILE_URL):
        config = ConfigParser()
        config.read(SET_FILE_URL)
        try:
            ini_keys1 = config.get(DOMAIN_URL, 'keys1')
            ini_keys2 = config.get(DOMAIN_URL, 'keys2')
            ini_date = config.get(DOMAIN_URL, 'date')
            time_past = datetime.datetime.strptime(ini_date, '%Y-%m-%d %H:%M:%S.%f')
            # Key for 1 days
            if time_past.day - time_now == 0:
                log.debug("Using old API keys")
                return ini_keys1, ini_keys2
            log.debug("Need new API keys")
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
    with open(SET_FILE_URL, 'w', encoding='utf-8') as configfile:
        config.write(configfile)

FRAGMENT = json.loads(sys.stdin.read())
SCENE_URL = FRAGMENT["url"]
DOMAIN_URL = urlparse(SCENE_URL).netloc
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
SET_FILE_URL = "ModelCentroAPI.ini"

scene_id = re.search(r"/(\d+)/*", SCENE_URL).group(1)
if not scene_id:
    log.error(f"Error with the ID ({SCENE_URL})\nAre you sure that your URL is correct ?")
    sys.exit(1)

timenow = datetime.datetime.now()
api_key1, api_key2 = check_config(timenow.day)
if api_key1 is None:
    log.debug("Going to the URL...")
    url_headers = {
        'User-Agent': USER_AGENT
    }
    r = sendRequest(SCENE_URL, url_headers)
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
        log.error("There is a problem with getting API identification")
        sys.exit(1)

log.debug("Asking the Scene API...")
api_url = f"https://{DOMAIN_URL}/sapi/{api_key1}/{api_key2}/content.load?_method=content.load&tz=1&filter[id][fields][0]=id&filter[id][values][0]={scene_id}&transitParameters[v1]=ykYa8ALmUD&transitParameters[preset]=scene"
headers = {
    'User-Agent': USER_AGENT,
    'Referer': SCENE_URL
}
r = sendRequest(api_url, headers)
try:
    scene_api_json = r.json()['response']['collection'][0]
except:
    log.error("Error with Request API")
    sys.exit(1)

log.debug("Trying the Performer API...")
perf_list = []
api_url = f"https://{DOMAIN_URL}/sapi/{api_key1}/{api_key2}/model.getModelContent?_method=model.getModelContent&tz=1&fields[0]=modelId.stageName&transitParameters[contentId]={scene_id}"
r = sendRequest(api_url, headers)
try:
    performer_api_json = r.json()['response']['collection']
    for perf_id in performer_api_json:
        for perf_id2 in performer_api_json[perf_id]['modelId']['collection']:
            performer_name=performer_api_json[perf_id]['modelId']['collection'][perf_id2]['stageName']
            perf_list.append({"name": performer_name})
except:
    log.error("Performer API failed")
# Time to scrape all data
scrape = {}
scrape['title'] = scene_api_json.get('title')
date = datetime.datetime.strptime(scene_api_json['sites']['collection'][scene_id].get('publishDate'), '%Y-%m-%d %H:%M:%S')
scrape['date'] = str(date.date())
scrape['details'] = scene_api_json.get('description')
scrape['studio'] = {}
scrape['studio']['name'] = re.sub(r'www\.|\.com', '', DOMAIN_URL)
if perf_list:
    scrape['performers'] = perf_list
scrape['tags'] = [{"name": scene_api_json['tags']['collection'][x].get('alias')} for x in scene_api_json['tags']['collection']]
scrape['image'] = scene_api_json['_resources']['primary'][0]['url']
for key_name, key_value in scrape.items():
    log.debug(f'[{key_name}]:{key_value}')

print(json.dumps(scrape))
