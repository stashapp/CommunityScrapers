import difflib
import json
import os
import pathlib
import re
import sys
from configparser import ConfigParser, NoSectionError
from datetime import datetime
from urllib.parse import urlparse

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    import py_common.config as stash_config
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

try:
    import requests
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
except ModuleNotFoundError:
    log.error(
        "You need to install the python modules mentioned in requirements.txt"
    )
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal from the directory the scraper is located: pip install -r requirements.txt"
    )
    sys.exit()

def stash_api_key():
    try:
        return stash_config.STASH.get("api_key")
    except:
        log.debug("No API_KEY found in py_common/config.py")
        return None

def sendRequest(url, head):
    try:
        response = requests.get(url, headers=head, timeout=6, verify=False)
    except requests.exceptions.SSLError:
        log.error("SSL Error on this site")
        return None
    except:
        log.error(f"Error while connecting to {url}")
        return None
    if response.content and response.status_code == 200:
        return response
    else:
        log.error(f"[REQUEST] Error, Status Code: {response.status_code}")
        if response.status_code == 429:
            log.error("[REQUEST] 429 Too Many Requests, You have sent too many requests in a given amount of time.")
    return None

def check_config(domain, api_key_file):
    if os.path.isfile(api_key_file):
        config = ConfigParser()
        config.read(api_key_file)
        try:
            today = datetime.today().strftime('%Y-%m-%d')
            config_date = datetime.strptime(config.get(domain, 'date'), '%Y-%m-%d')
            date_diff = datetime.strptime(today, '%Y-%m-%d') - config_date
            if date_diff.days == 0:
                # date is within 24 hours so using old instance
                token = config.get(domain, 'instance')
                return token
            else:
                pass
        except NoSectionError:
            pass
    return None

def write_config(url, token, api_key_file):
    log.debug("Writing config!")
    url_domain = re.sub(r"www\.|\.com", "", urlparse(url).netloc)
    config = ConfigParser()
    config.read(api_key_file)
    today = datetime.today().strftime('%Y-%m-%d')
    try:
        config.get(url_domain.lower(), 'url')
    except NoSectionError:
        config.add_section(url_domain.lower())
    config.set(url_domain, 'url', url)
    config.set(url_domain, 'instance', token)
    config.set(url_domain, 'date', today)
    # order by name before saving
    sorted_config = ConfigParser()
    sorted_sections = sorted(config._sections)
    for s in sorted_sections:
        sorted_config.add_section(s)
        items = sorted(config._sections[s].items())
        for i in items:
            sorted_config.set(s, i[0], i[1])
    with open(api_key_file, 'w') as configfile:
        sorted_config.write(configfile)
    return

def api_token_get(url, api_key_file, agent):
    url_domain = re.sub(r"www\.|\.com", "", urlparse(url).netloc)
    api_token = check_config(url_domain, api_key_file)
    if api_token is None:
        log.info("Need to get API Token")
        r = sendRequest(url,{'User-Agent': agent})
        if r:
            api_token = r.cookies.get_dict().get("instance_token")
        if r is None or api_token is None: # retry using the home page
            url_home = urlparse(url).scheme + "://" + urlparse(url).netloc
            log.debug(f"Fetching API token from main page:{url_home}")
            r = sendRequest(url_home,{'User-Agent': agent})
            if r:
                api_token = r.cookies.get_dict().get("instance_token")
        if api_token is None:
            log.error("Can't get an instance_token")
            sys.exit(1)
        # Writing new token in the config file
        write_config(url, api_token, api_key_file)
    api_headers = {
        'Instance': api_token,
        'User-Agent': agent,
        'Origin':'https://' + urlparse(url).netloc,
        'Referer': url
    }
    return api_headers

def save_json(api_json, scene_id, json_dir):
    try:
        if scene_id:
            try:
                os.makedirs(json_dir)
            except FileExistsError:
                pass  # Dir already exist
            filename = os.path.join(json_dir, scene_id + ".json")
            log.debug(f"writing file {filename}...\n")
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(api_json, file, ensure_ascii=False, indent=4)
    except IndexError:
        pass

def load_json(scene_id, json_dir):
    json_file = os.path.join(json_dir, scene_id+".json")
    if os.path.isfile(json_file):
        log.debug("Using local JSON...")
        use_local = 1
        with open(json_file, encoding="utf-8") as json_file:
            return json.load(json_file)
    return None