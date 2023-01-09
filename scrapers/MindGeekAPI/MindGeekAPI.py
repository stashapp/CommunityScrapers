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
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

import mg_utils
import mg_graphql
import mg_default_config

try:
    import mg_config # override default config options with user specified ones
    for k in mg_config.SETTINGS:
        mg_default_config.SETTINGS[k] = mg_config.SETTINGS[k]
except Exception as exception_error: # on error skip, keeping the default values
    log.debug(exception_error)
    pass

# Load User variables
SET_RATIO = mg_default_config.SETTINGS["SET_RATIO"]
STOCKAGE_FILE_APIKEY = mg_default_config.SETTINGS["STOCKAGE_FILE_APIKEY"]
STOCKAGE_FILE_APIKEY_SEARCH = mg_default_config.SETTINGS["STOCKAGE_FILE_APIKEY_SEARCH"]
CREATE_MARKER = mg_default_config.SETTINGS["CREATE_MARKER"]
MARKER_DURATION_MATCH = mg_default_config.SETTINGS["MARKER_DURATION_MATCH"]
MARKER_DURATION_UNSURE = mg_default_config.SETTINGS["MARKER_DURATION_UNSURE"]
MARKER_SEC_DIFF = mg_default_config.SETTINGS["MARKER_SEC_DIFF"]
FIXED_TAG = mg_default_config.SETTINGS["FIXED_TAG"]
MG_SAVE_JSON = mg_default_config.SETTINGS["MG_SAVE_JSON"]
USER_AGENT = mg_default_config.SETTINGS["USER_AGENT"]
FEMALE_ONLY = mg_default_config.SETTINGS["FEMALE_ONLY"]

# API key (Settings > Configuration > Authentication)
STASH_API = mg_utils.stash_api_key()

USERFOLDER_PATH = str(pathlib.Path(__file__).parent.parent.absolute())
DIR_JSON = os.path.join(USERFOLDER_PATH, "scraperJSON","MindGeekAPI")

def load_json(scene_id):
    if MG_SAVE_JSON: # try to load the scene from the local JSON
        return mg_utils.load_json(scene_id, DIR_JSON)
    return None

# Final scraping 

def scraping_json(api_json, url=""):
    scrape = {}
    scrape['title'] = api_json.get('title')
    date = datetime.strptime(api_json.get('dateReleased'), '%Y-%m-%dT%H:%M:%S%z')
    scrape['date'] = str(date.date())
    scrape['details'] = api_json.get('description')
    if api_json.get('id'):
        scrape['code'] = str(api_json['id'])
    orientation = api_json.get('sexualOrientation')
    global saved_json
    # URL
    if url:
        scrape['url'] = url
    # Studio
    try:
        api_json['collections'][0].get('name') # If this creates an error it wont continue so no studio at all
        scrape['studio'] = {}
        scrape['studio']['name'] = api_json['collections'][0].get('name')
    except:
        log.warning("No studio, trying brand name")
        if api_json.get('brandMeta'):
            scrape['studio'] = { "name": api_json['brandMeta'].get('displayName') }
    # Perf
    if FEMALE_ONLY: # only scrape the female performers
        perf = []
        for x in api_json.get('actors'):
            if x.get('gender') == "female":
                perf.append({"name": x.get('name'), "gender": x.get('gender')})
        scrape['performers'] = perf
    else:
        scrape['performers'] = [{"name": x.get('name'), "gender": x.get('gender')} for x in api_json.get('actors')]
    # Tags
    list_tag = []
    if orientation:
        list_tag.append({"name": "Sexual Orientation - " + orientation.title()})
    for x in api_json.get('tags'):
        tag_name = x.get('name')
        if tag_name:
            list_tag.append({"name": x.get('name')})
    if FIXED_TAG:
        list_tag.append({"name": FIXED_TAG})
    scrape['tags'] = list_tag

    # Image can be poster or poster_fallback
    backup_image=None
    if type(api_json['images']) is dict:
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
        log.debug("Using alternate image")
        scrape['image'] = backup_image

    if SCENE_ID and STASH_API and CREATE_MARKER:
        if api_json.get("timeTags"):
            stash_scene_info = mg_graphql.getScene(SCENE_ID)
            api_scene_duration = None
            if api_json.get("videos"):
                if api_json["videos"].get("mediabook"):
                    api_scene_duration = api_json["videos"]["mediabook"].get("length")
            if MARKER_DURATION_MATCH and api_scene_duration is None:
                log.info("No duration given by the API.")
            else:
                log.debug(f"Stash Len: {stash_scene_info['duration']}| API Len: {api_scene_duration}")
                if (MARKER_DURATION_MATCH and api_scene_duration-MARKER_SEC_DIFF <= stash_scene_info["duration"] <= api_scene_duration+MARKER_SEC_DIFF) or (api_scene_duration in [0,1] and MARKER_DURATION_UNSURE):
                    for marker in api_json["timeTags"]:
                        if stash_scene_info.get("marker"):
                            if marker.get("startTime") in stash_scene_info["marker"]:
                                log.debug(f"Ignoring marker ({marker.get('startTime')}) because already have with same time.")
                                continue
                        try:
                            mg_graphql.createMarker(SCENE_ID, marker.get("name"), marker.get("name"), marker.get("startTime"))
                        except:
                            log.error("Marker failed to create")
                else:
                    log.info("The duration (API) of this scene doesn't match the one from stash (DB).")
        else:
            log.info("No offical marker for this scene")
    saved_json = api_json
    return scrape

FRAGMENT = json.loads(sys.stdin.read())
SEARCH_TITLE = FRAGMENT.get("name")
SCENE_ID = FRAGMENT.get("id")
SCENE_TITLE = FRAGMENT.get("title")
SCENE_URL = FRAGMENT.get("url")
scraped_json = None
saved_json = None
using_local = False

if ("validName" in sys.argv or "validURL" in sys.argv) and SCENE_URL is None:
    sys.exit()

if SCENE_URL:
    # fixing old scene
    if 'brazzers.com/scenes/view/id/' in SCENE_URL:
        log.info("Probably an old url, need to redirect")
        try:
            r = mg_utils.sendRequest(SCENE_URL, headers={'User-Agent': USER_AGENT})
            SCENE_URL = r.url
        except:
            log.warning("Redirect failed, result may be inaccurate.")
    # extract thing
    url_domain = re.sub(r"www\.|\.com", "", urlparse(SCENE_URL).netloc)
    log.debug(f"Domain: {url_domain}")
    url_check = re.sub('.+/', '', SCENE_URL)
    try:
        if url_check.isdigit():
            url_sceneid = url_check
        else:
            url_sceneid = re.search(r"/(\d+)/*", SCENE_URL).group(1)
    except:
        url_sceneid = None
    
    if url_sceneid is None:
        log.error("Can't get the ID of the Scene. Are you sure that the URL is from Mindgeek Network?")
        sys.exit()
    else:
        log.info(f"ID: {url_sceneid}")


    # API ACCESS
    api_headers = mg_utils.api_token_get(SCENE_URL, STOCKAGE_FILE_APIKEY, USER_AGENT)
    api_URL = f'https://site-api.project1service.com/v2/releases/{url_sceneid}'
    # EXPLORE API
    api_scene_json = load_json(url_sceneid) # load json from local file if enabled/available
    if api_scene_json is None:
        api_scene_json = mg_utils.sendRequest(api_URL, api_headers)
        try:
            if type(api_scene_json.json()) == list:
                api_scene_json = api_scene_json.json()[0].get('message')
                log.error(f"API Error Message: {api_scene_json}")
                sys.exit(1)
            else:
                api_scene_json = api_scene_json.json().get('result')
        except:
            log.error("Failed to get the JSON from API")
            sys.exit(1)
    else:
        using_local = True
        log.debug("Using existing local JSON file for scraping")

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
    log.info(f"Title: {SCENE_TITLE}")
    # Reading config
    if os.path.isfile(STOCKAGE_FILE_APIKEY):
        config = ConfigParser()
        config.read(STOCKAGE_FILE_APIKEY)
        dict_config = dict(config.items())
    else:
        log.error(f"Can't search for the scene ({STOCKAGE_FILE_APIKEY} is missing)\nYou need to scrape 1 URL from the network, to be enable to search with your title on this network.")
        sys.exit(1)
    # Loop the config
    scraped_json = None
    ratio_record = 0
    for config_section in dict_config:
        if config_section == "DEFAULT":
            continue
        config_url = config.get(config_section, 'url')
        config_domain = re.sub(r"www\.|\.com", "", urlparse(config_url).netloc)
        log.info(f"Searching on: {config_domain}")

        # API ACCESS
        api_headers = mg_utils.api_token_get(config_url, STOCKAGE_FILE_APIKEY, USER_AGENT)
        search_url = f'https://site-api.project1service.com/v2/releases?title={SCENE_TITLE}&type=scene'
        api_search_json = mg_utils.sendRequest(search_url, api_headers)
        try:
            if type(api_search_json.json()) == list:
                api_search_error = api_search_json.json()[0]['message']
                log.error(f"API Error Message: {api_search_error}")
                sys.exit(1)
            else:
                api_search_json = api_search_json.json()['result']
        except:
            log.error("Failed to get the JSON from API")
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
            log.info(f"[MATCH] Title: {result.get('title')} | Ratio: {ratio}")
            if ratio > ratio_record:
                ratio_record = ratio
                ratio_scene = result
        if ratio_record > SET_RATIO:
            log.info(f"[INFO] Found scene {ratio_scene['title']}")
            scraped_json = scraping_json(ratio_scene, making_url)
            break
    if scraped_json is None:
        log.error("API Search Error. No scenes found")
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
        log.error(f"Can't search for the scene ({config_file_used} is missing)\nYou need to scrape 1 URL from the network, to be enable to search with your title on this network.")
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
        match_filter = re.match(r"{.+}", SEARCH_TITLE.lower())
        if match_filter:
            filter_domain = re.sub(r"[{}]","", match_filter.group(0))
            filter_domain = filter_domain.split(",")
            if config_domain not in filter_domain:
                log.info(f"Ignore {config_domain} (Filter query)")
                continue
        log.info(f"Searching on: {config_domain}")
        # API ACCESS
        api_headers = mg_utils.api_token_get(config_url, STOCKAGE_FILE_APIKEY, USER_AGENT)
        search_query = re.sub(r"{.+}\s*", "", SEARCH_TITLE)
        search_url = f'https://site-api.project1service.com/v2/releases?title={search_query}&type=scene&limit=40'
        api_search_json = mg_utils.sendRequest(search_url, api_headers)
        if api_search_json is None:
            log.error("Request failed")
            continue
        try:
            if type(api_search_json.json()) == list:
                api_search_error = api_search_json.json()[0]['message']
                log.error(f"API Error Message: {api_search_error}")
                continue
            else:
                api_search_json = api_search_json.json()['result']
        except:
            log.error(f"Failed to get the JSON from API ({config_domain})")
            continue
        
        ratio_scene = None
        making_url = None
        for result in api_search_json:
            search = {}
            try:
                result['collections'][0].get('name') # If this errors out it won't continue so no studio at all
                search['studio'] = {}
                search['studio']['name'] = result['collections'][0].get('name')
            except:
                log.warning("No studio")
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
        log.debug("[ERROR] API Search Error. No scenes found")
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
    if saved_json and not using_local:
        if saved_json.get("id") and MG_SAVE_JSON:
            mg_utils.save_json(saved_json, str(saved_json["id"]), DIR_JSON)
    print(json.dumps(scraped_json))