import difflib
import json
import os
import re
import sys
from configparser import ConfigParser, NoSectionError
from datetime import datetime
from urllib.parse import urlparse

import requests

#
# User variables
#
# Ratio to consider the scene to scrape (Ratio between Title and API Title)
SET_RATIO = 0.75
# Print debug message.
PRINT_DEBUG = True
# Print ratio message. (Show title find in search)
PRINT_MATCH = True
## File used to store key to connect the API.
STOCKAGE_FILE_APIKEY = "MindGeekAPI.ini"
# This file will be used for search by name. It can be useful if you only want to search on specific site. (Like only putting Parent studio and not Child)
# Copy MindGeekAPI.ini to another name (then put the name in the var below), then edit the file to remove the site  you don't want to search.
STOCKAGE_FILE_APIKEY_SEARCH = ""

# Tags you don't want to see in the Scraper window.
IGNORE_TAGS = ["Sex","Feature","HD","Big Dick"]
# Tags you want to add in the Scraper window.
FIXED_TAGS = ""
# Check the SSL Certificate.
CHECK_SSL_CERT = True

def debug(q):
    if "[DEBUG]" in q and PRINT_DEBUG == False:
        return
    if "[MATCH]" in q and PRINT_MATCH == False:
        return
    print(q, file=sys.stderr)

def sendRequest(url, head):
    #debug("[DEBUG] Request URL: {}".format(url))
    try:
        response = requests.get(url, headers=head, timeout=10, verify=CHECK_SSL_CERT)
    except requests.exceptions.SSLError:
        debug("[ERROR] SSL Error on this site. You can ignore this error with the 'CHECK_SSL_CERT' param inside the python file.")
        return None
    #debug("[DEBUG] Returned URL: {}".format(response.url))
    if response.content and response.status_code == 200:
        return response
    else:
        debug("[REQUEST] Error, Status Code: {}".format(response.status_code))
        if response.status_code == 429:
            debug("[REQUEST] 429 Too Many Requests, You have made too many requests in a given amount of time.")
    return None

# Config

def check_config(domain):
    if os.path.isfile(STOCKAGE_FILE_APIKEY):
        config = ConfigParser()
        config.read(STOCKAGE_FILE_APIKEY)
        try:
            config_date = datetime.strptime(config.get(domain, 'date'), '%Y-%m-%d')
            date_diff = datetime.strptime(DATE_TODAY, '%Y-%m-%d') - config_date
            if date_diff.days == 0:
                # date is within 24 hours so using old instance
                token = config.get(domain, 'instance')
                return token
            else:
                debug("[DEBUG] Old Config date: {}".format(config_date))
                pass
        except NoSectionError:
            pass
    return None


def write_config(url, token):
    debug("[DEBUG] Writing config!")
    url_domain = re.sub(r"www\.|\.com", "", urlparse(url).netloc)
    config = ConfigParser()
    config.read(STOCKAGE_FILE_APIKEY)
    try:
        config.get(url_domain, 'url')
    except NoSectionError:
        config.add_section(url_domain)
    config.set(url_domain, 'url', url)
    config.set(url_domain, 'instance', token)
    config.set(url_domain, 'date', DATE_TODAY)
    with open(STOCKAGE_FILE_APIKEY, 'w') as configfile:
        config.write(configfile)
    return

# API

def api_token_get(url):
    # API TOKEN
    url_domain = re.sub(r"www\.|\.com", "", urlparse(url).netloc)
    api_token = check_config(url_domain)
    if api_token is None:
        debug("[INFO] Need to get API Token")
        r = sendRequest(url,{'User-Agent': USER_AGENT})
        if r:
            api_token = r.cookies.get_dict().get("instance_token")
            if api_token is None:
                debug("[ERROR] Can't get the instance_token from the cookie.")
                sys.exit(1)
            # Writing new token in the config file
            write_config(url, api_token)
    debug("[DEBUG] Token: {}".format(api_token))
    api_headers = {
        'Instance': api_token,
        'User-Agent': USER_AGENT,
        'Origin':'https://' + urlparse(url).netloc,
        'Referer': url
    }
    return api_headers

# Final scraping 

def scraping_json(api_json, url=""):
    scrape = {}
    scrape['title'] = api_json.get('title')
    date = datetime.strptime(api_json.get('dateReleased'), '%Y-%m-%dT%H:%M:%S%z')
    scrape['date'] = str(date.date())
    scrape['details'] = api_json.get('description')
    # URL
    if url:
        scrape['url'] = url
    # Studio
    try:
        api_json['collections'][0].get('name') # If this creates an error it wont continue so no studio at all
        scrape['studio'] = {}
        scrape['studio']['name'] = api_json['collections'][0].get('name')
    except:
        debug("[WARN] No studio")
    # Perf
    if 'female_only' in sys.argv:
        perf = []
        for x in api_json.get('actors'):
            if x.get('gender') == "female":
                perf.append({"name": x.get('name'), "gender": x.get('gender')})
        scrape['performers'] = perf
    else:
        scrape['performers'] = [{"name": x.get('name'), "gender": x.get('gender')} for x in api_json.get('actors')]
    # Tags
    list_tag = []
    for x in api_json.get('tags'):
        tag_name = x.get('name')
        if tag_name in IGNORE_TAGS:
            continue
        if tag_name:
            list_tag.append({"name": x.get('name')})
    if FIXED_TAGS:
        list_tag.append({"name": FIXED_TAGS})
    scrape['tags'] = list_tag

    # Image can be poster or poster_fallback
    backup_image=None
    if type(api_json['images']['poster']) is list:
        for image_type in api_json['images']['poster']:
            try:
                if '/poster_fallback/' in image_type['xx'].get('url') and backup_image is None:
                    backup_image = image_type['xx'].get('url')
                    continue
                if '/poster/' in image_type['xx'].get('url'):
                    scrape['image'] = image_type['xx'].get('url')
                    break
            except TypeError:
                pass
    else:
        if type(api_json['images']['poster']) is dict:
            for _, img_value in api_json['images']['poster'].items():
                try:
                    if '/poster_fallback/' in img_value['xx'].get('url') and backup_image is None:
                        backup_image = img_value['xx'].get('url')
                        continue
                    if '/poster/' in img_value['xx'].get('url'):
                        scrape['image'] = img_value['xx'].get('url')
                        break
                except TypeError:
                    pass
    if scrape.get('image') is None and backup_image:
        debug("[INFO] Using alternate image")
        scrape['image'] = backup_image
    return scrape

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
DATE_TODAY = datetime.today().strftime('%Y-%m-%d')

FRAGMENT = json.loads(sys.stdin.read())
SEARCH_TITLE = FRAGMENT.get("name")
SCENE_ID = FRAGMENT.get("id")
SCENE_TITLE = FRAGMENT.get("title")
SCENE_URL = FRAGMENT.get("url")
scraped_json = None

if "validName" in sys.argv and SCENE_URL is None:
    sys.exit()

if SCENE_URL:
    # fixing old scene
    if 'brazzers.com/scenes/view/id/' in SCENE_URL:
        debug("[INFO] Probably an old url, need to redirect")
        try:
            r = requests.get(SCENE_URL, headers={'User-Agent': USER_AGENT}, timeout=(3, 5))
            SCENE_URL = r.url
        except:
            debug("[WARN] Redirect failed, result may be inaccurate.")
    # extract thing
    url_domain = re.sub(r"www\.|\.com", "", urlparse(SCENE_URL).netloc)
    debug("[DEBUG] Domain: {}".format(url_domain))
    url_check = re.sub('.+/', '', SCENE_URL)
    try:
        if url_check.isdigit():
            url_sceneid = url_check
        else:
            url_sceneid = re.search(r"/(\d+)/*", SCENE_URL).group(1)
    except:
        url_sceneid = None
    if url_sceneid is None:
        debug("[ERROR] Can't get the ID of the Scene. Are you sure that URL is from Mindgeek Network?")
        sys.exit()
    else:
        debug("[INFO] ID: {}".format(url_sceneid))


    # API ACCES
    api_headers = api_token_get(SCENE_URL)
    api_URL = 'https://site-api.project1service.com/v2/releases/{}'.format(url_sceneid)
    # EXPLORE API
    api_scene_json = sendRequest(api_URL, api_headers)
    try:
        if type(api_scene_json.json()) == list:
            api_scene_json = api_scene_json.json()[0].get('message')
            debug("[ERROR] API Error Message: {}".format(api_scene_json))
            sys.exit(1)
        else:
            api_scene_json = api_scene_json.json().get('result')
    except:
        debug("[ERROR] Failed to get the JSON from API")
        sys.exit(1)
    if api_scene_json:
        if api_scene_json.get('parent') is not None and api_scene_json['type'] != "scene":
            if api_scene_json['parent']['type'] == "scene":
                api_scene_json = api_scene_json.get('parent')
        scraped_json = scraping_json(api_scene_json, SCENE_URL)
    else:
        scraped_json = None
elif SCENE_TITLE:
    SCENE_TITLE = re.sub(r'[-._\']', ' ', os.path.splitext(SCENE_TITLE)[0])
    # Remove resolution
    SCENE_TITLE = re.sub(r'\sXXX|\s1080p|720p|2160p|KTR|RARBG|\scom\s|\[|]|\sHD|\sSD|', '', SCENE_TITLE)
    # Remove Date
    SCENE_TITLE = re.sub(r'\s\d{2}\s\d{2}\s\d{2}|\s\d{4}\s\d{2}\s\d{2}', '', SCENE_TITLE)
    debug("[INFO] Title: {}".format(SCENE_TITLE))
    # Reading config
    if os.path.isfile(STOCKAGE_FILE_APIKEY):
        config = ConfigParser()
        config.read(STOCKAGE_FILE_APIKEY)
        dict_config = dict(config.items())
    else:
        debug("[ERROR] Can't search for the scene ({} is missing)\nYou need to scrape 1 URL from the network, to be enable to search with your title on this network.".format(STOCKAGE_FILE_APIKEY))
        sys.exit(1)
    # Loop the config
    scraped_json = None
    ratio_record = 0
    for config_section in dict_config:
        if config_section == "DEFAULT":
            continue
        config_url = config.get(config_section, 'url')
        config_domain = re.sub(r"www\.|\.com", "", urlparse(config_url).netloc)
        debug("[INFO] Searching on: {}".format(config_domain))

        # API ACCESS
        api_headers = api_token_get(config_url)
        search_url = 'https://site-api.project1service.com/v2/releases?title={}&type=scene'.format(SCENE_TITLE)
        api_search_json = sendRequest(search_url, api_headers)
        try:
            if type(api_search_json.json()) == list:
                api_search_error = api_search_json.json()[0]['message']
                debug("[ERROR] API Error Message: {}".format(api_search_error))
                sys.exit(1)
            else:
                api_search_json = api_search_json.json()['result']
        except:
            debug("[ERROR] Failed to get the JSON from API")
            sys.exit(1)
        
        ratio_scene = None
        making_url = None
        for result in api_search_json:
            title_filename = None
            try:
                api_filename = result['videos']['mediabook']['files']["320p"]['urls']['download']
                title_filename = re.sub(r'^.+filename=', '', api_filename)
                title_filename = re.sub(r'_.+$', '', title_filename)
            except:
                pass
            if title_filename:
                making_url = re.sub(r'/\d+/*.+', '/' + str(result.get("id")) + "/" + title_filename, config_url)
            else:
                making_url = re.sub(r'/\d+/*.+', '/' + str(result.get("id")) + "/", config_url)
            ratio = round(difflib.SequenceMatcher(None, SCENE_TITLE.lower(), result["title"].lower()).ratio(), 3)
            debug("[MATCH] Title: {} | Ratio: {}".format(result.get('title'), ratio))
            if ratio > ratio_record:
                ratio_record = ratio
                ratio_scene = result
        if ratio_record > SET_RATIO:
            debug("[INFO] Found scene {}".format(ratio_scene["title"]))
            scraped_json = scraping_json(ratio_scene, making_url)
            break
    if scraped_json is None:
        debug("[ERROR] API Search Error. No scenes found")
        sys.exit(1)
elif SEARCH_TITLE:
    if not STOCKAGE_FILE_APIKEY_SEARCH:
        config_file_used = STOCKAGE_FILE_APIKEY
    else:
        config_file_used = STOCKAGE_FILE_APIKEY_SEARCH
    if os.path.isfile(config_file_used):
        config = ConfigParser()
        config.read(config_file_used)
        dict_config = dict(config.items())
    else:
        debug("[ERROR] Can't search for the scene ({} is missing)\nYou need to scrape 1 URL from the network, to be enable to search with your title on this network.".format(config_file_used))
        sys.exit(1)
    # Loop the config
    scraped_json = None
    result_search = []
    list_domain = []
    for config_section in dict_config:
        if config_section == "DEFAULT":
            continue
        config_url = config.get(config_section, 'url')
        config_domain = re.sub(r"www\.|\.com", "", urlparse(config_url).netloc)
        list_domain.append(config_domain)
        match_filter = re.match(r"{.+}", SEARCH_TITLE)
        if match_filter:
            filter_domain = re.sub(r"[{}]","", match_filter.group(0))
            filter_domain = filter_domain.split(",")
            if config_domain not in filter_domain:
                debug("[INFO] Ignore {} (Filter query)".format(config_domain))
                continue
        debug("[INFO] Searching on: {}".format(config_domain))
        # API ACCESS
        api_headers = api_token_get(config_url)
        search_url = 'https://site-api.project1service.com/v2/releases?title={}&type=scene&limit=40'.format(re.sub(r"{.+}\s*", "", SEARCH_TITLE))
        api_search_json = sendRequest(search_url, api_headers)
        if api_search_json is None:
            debug("[ERROR] Request fail")
            continue
        try:
            if type(api_search_json.json()) == list:
                api_search_error = api_search_json.json()[0]['message']
                debug("[ERROR] API Error Message: {}".format(api_search_error))
                continue
            else:
                api_search_json = api_search_json.json()['result']
        except:
            debug("[ERROR] Failed to get the JSON from API ({})".format(config_domain))
            continue
        
        ratio_scene = None
        making_url = None
        for result in api_search_json:
            search = {}
            try:
                result['collections'][0].get('name') # If this create a error it wont continue so no studio at all
                search['studio'] = {}
                search['studio']['name'] = result['collections'][0].get('name')
            except:
                debug("[WARN] No studio")
            search['title'] = result.get('title')
            title_filename = None
            try:
                api_filename = result['videos']['mediabook']['files']["320p"]['urls']['download']
                title_filename = re.sub(r'^.+filename=', '', api_filename)
                title_filename = re.sub(r'_.+$', '', title_filename)
            except:
                pass
            if title_filename:
                making_url = re.sub(r'/\d+/*.+', '/' + str(result.get("id")) + "/" + title_filename, config_url)
            else:
                making_url = re.sub(r'/\d+/*.+', '/' + str(result.get("id")) + "/", config_url)
            try:
                search['image'] = result['images']['poster']['0']["xl"]['url']
            except:
                pass
            try:
                search['performers'] = [{"name": x.get('name')} for x in result.get('actors')]
            except:
                pass
            search['url'] = making_url
            result_search.append(search)
    if not result_search:
        debug("[ERROR] API Search Error. No scenes found")
        scraped_json = {"title":"No scenes found. (Hover to see everything)"}
        scraped_json["details"] = """
        Be sure to have site(s) in the config file (.ini). To add a site in the config, you need to scrape 1 url from the site.
        Example: get a url from Brazzers -> use 'Scrape With...' -> now you can search on brazzers.
        \nYou can also filter your search with '{site} query'. 
        You can use a multiple site filter, just separate sites with a comma.
        (site = domain without www/com)
        \nAvailable sites are shown in the tags.
        """
        scraped_json['tags'] = [{"name": x} for x in list_domain]
        scraped_json = [scraped_json]
    else:
        scraped_json = result_search

if scraped_json:
    print(json.dumps(scraped_json))
