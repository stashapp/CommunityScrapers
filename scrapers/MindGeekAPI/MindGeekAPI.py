import difflib
import json
import os
import re
import sys
from configparser import ConfigParser, NoSectionError
from datetime import datetime
from urllib.parse import urlparse

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

#
# User variables
#
# Ratio to consider the scene to scrape (Ratio between Title and API Title)
SET_RATIO = 0.75
## File used to store key to connect the API.
STOCKAGE_FILE_APIKEY = "MindGeekAPI.ini"
# This file will be used for search by name. It can be useful if you only want to search on specific site. (Like only putting Parent studio and not Child)
# Copy MindGeekAPI.ini to another name (then put the name in the var below), then edit the file to remove the site  you don't want to search.
STOCKAGE_FILE_APIKEY_SEARCH = ""

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
# Check the SSL Certificate.
CHECK_SSL_CERT = True
# Local folder with JSON inside (Only used if scene isn't found from the API)
LOCAL_PATH = r""


SERVER_IP = "http://localhost:9999"
# API key (Settings > Configuration > Authentication)
STASH_API = ""

def sendRequest(url, head):
    #log.debug("Request URL: {}".format(url))
    try:
        response = requests.get(url, headers=head, timeout=10, verify=CHECK_SSL_CERT)
    except requests.exceptions.SSLError:
        log.error("SSL Error on this site. You can ignore this error with the 'CHECK_SSL_CERT' param inside the python file.")
        return None
    #log.debug("Returned URL: {}".format(response.url))
    if response.content and response.status_code == 200:
        return response
    else:
        log.error("[REQUEST] Error, Status Code: {}".format(response.status_code))
        if response.status_code == 429:
            log.error("[REQUEST] 429 Too Many Requests, You have sent too many requests in a given amount of time.")
    return None

# graphql

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
    for tag in result["allTags"]:
        if tag["name"] == name:
            return tag["id"]
        if tag.get("aliases"):
            for alias in tag["aliases"]:
                if alias == name:
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
            file {
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
        return_dict["duration"] = result["findScene"]["file"]["duration"]
        if result["findScene"].get("scene_markers"):
            return_dict["marker"] = [x.get("seconds") for x in result["findScene"]["scene_markers"]]
        else:
            return_dict["marker"] = None
        return return_dict
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
                log.debug("Old Config date: {}".format(config_date))
                pass
        except NoSectionError:
            pass
    return None


def write_config(url, token):
    log.debug("Writing config!")
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
        log.info("Need to get API Token")
        r = sendRequest(url,{'User-Agent': USER_AGENT})
        if r:
            api_token = r.cookies.get_dict().get("instance_token")
            if api_token is None:
                log.error("Can't get the instance_token from the cookie.")
                sys.exit(1)
            # Writing new token in the config file
            write_config(url, api_token)
    log.debug("Token: {}".format(api_token))
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
        log.warning("No studio")
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
        log.info("Using alternate image")
        scrape['image'] = backup_image

    if SCENE_ID and STASH_API and CREATE_MARKER:
        if api_json.get("timeTags"):
            stash_scene_info = graphql_getScene(SCENE_ID)
            api_scene_duration = None
            if api_json.get("videos"):
                if api_json["videos"].get("mediabook"):
                    api_scene_duration = api_json["videos"]["mediabook"].get("length")
            if MARKER_DURATION_MATCH and api_scene_duration is None:
                log.info("No duration given by the API.")
            else:
                log.debug("Stash Len: {}| API Len: {}".format(stash_scene_info["duration"], api_scene_duration))
                if (MARKER_DURATION_MATCH and api_scene_duration-MARKER_SEC_DIFF <= stash_scene_info["duration"] <= api_scene_duration+MARKER_SEC_DIFF) or (api_scene_duration in [0,1] and MARKER_DURATION_UNSURE):
                    for marker in api_json["timeTags"]:
                        if stash_scene_info.get("marker"):
                            if marker.get("startTime") in stash_scene_info["marker"]:
                                log.debug("Ignoring marker ({}) because already have with same time.".format(marker.get("startTime")))
                                continue
                        try:
                            graphql_createMarker(SCENE_ID, marker.get("name"), marker.get("name"), marker.get("startTime"))
                        except:
                            log.error("Marker failed to create")
                else:
                    log.info("The duration of this scene don't match the duration of stash scene.")
        else:
            log.info("No offical marker for this scene")
    return scrape


USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'
DATE_TODAY = datetime.today().strftime('%Y-%m-%d')
SERVER_URL = SERVER_IP + "/graphql"

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
        log.info("Probably an old url, need to redirect")
        try:
            r = requests.get(SCENE_URL, headers={'User-Agent': USER_AGENT}, timeout=(3, 5))
            SCENE_URL = r.url
        except:
            log.warning("Redirect failed, result may be inaccurate.")
    # extract thing
    url_domain = re.sub(r"www\.|\.com", "", urlparse(SCENE_URL).netloc)
    log.debug("Domain: {}".format(url_domain))
    url_check = re.sub('.+/', '', SCENE_URL)
    try:
        if url_check.isdigit():
            url_sceneid = url_check
        else:
            url_sceneid = re.search(r"/(\d+)/*", SCENE_URL).group(1)
    except:
        url_sceneid = None
    if url_sceneid is None:
        log.error("Can't get the ID of the Scene. Are you sure that URL is from Mindgeek Network?")
        sys.exit()
    else:
        log.debug("ID: {}".format(url_sceneid))


    # API ACCES
    api_headers = api_token_get(SCENE_URL)
    api_URL = 'https://site-api.project1service.com/v2/releases/{}'.format(url_sceneid)
    # EXPLORE API
    api_scene_json = sendRequest(api_URL, api_headers)
    try:
        if type(api_scene_json.json()) == list:
            api_scene_json = api_scene_json.json()[0].get('message')
            log.error("API Error Message: {}".format(api_scene_json))
            sys.exit(1)
        else:
            api_scene_json = api_scene_json.json().get('result')
    except:
        log.error("Failed to get the JSON from API")
        local_tmp_path = os.path.join(LOCAL_PATH,url_sceneid + ".json")
        if os.path.exists(local_tmp_path):
            log.info("Using local file ({})".format(url_sceneid + ".json"))
            with open(local_tmp_path, "r", encoding="utf8") as file:
                api_scene_json = json.load(file)
        else:
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
    log.debug("Title: {}".format(SCENE_TITLE))
    # Reading config
    if os.path.isfile(STOCKAGE_FILE_APIKEY):
        config = ConfigParser()
        config.read(STOCKAGE_FILE_APIKEY)
        dict_config = dict(config.items())
    else:
        log.error("Can't search for the scene ({} is missing)\nYou need to scrape 1 URL from the network, to be enable to search with your title on this network.".format(STOCKAGE_FILE_APIKEY))
        sys.exit(1)
    # Loop the config
    scraped_json = None
    ratio_record = 0
    for config_section in dict_config:
        if config_section == "DEFAULT":
            continue
        config_url = config.get(config_section, 'url')
        config_domain = re.sub(r"www\.|\.com", "", urlparse(config_url).netloc)
        log.info("Searching on: {}".format(config_domain))

        # API ACCESS
        api_headers = api_token_get(config_url)
        search_url = 'https://site-api.project1service.com/v2/releases?title={}&type=scene'.format(SCENE_TITLE)
        api_search_json = sendRequest(search_url, api_headers)
        try:
            if type(api_search_json.json()) == list:
                api_search_error = api_search_json.json()[0]['message']
                log.error("API Error Message: {}".format(api_search_error))
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
            log.debug("[MATCH] Title: {} | Ratio: {}".format(result.get('title'), ratio))
            if ratio > ratio_record:
                ratio_record = ratio
                ratio_scene = result
        if ratio_record > SET_RATIO:
            log.info("Found scene {}".format(ratio_scene["title"]))
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
        log.error("Can't search for the scene ({} is missing)\nYou need to scrape 1 URL from the network, to be enable to search with your title on this network.".format(config_file_used))
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
                log.info("Ignore {} (Filter query)".format(config_domain))
                continue
        log.info("Searching on: {}".format(config_domain))
        # API ACCESS
        api_headers = api_token_get(config_url)
        search_url = 'https://site-api.project1service.com/v2/releases?title={}&type=scene&limit=40'.format(re.sub(r"{.+}\s*", "", SEARCH_TITLE))
        api_search_json = sendRequest(search_url, api_headers)
        if api_search_json is None:
            log.error("Request fail")
            continue
        try:
            if type(api_search_json.json()) == list:
                api_search_error = api_search_json.json()[0]['message']
                log.error("API Error Message: {}".format(api_search_error))
                continue
            else:
                api_search_json = api_search_json.json()['result']
        except:
            log.error("Failed to get the JSON from API ({})".format(config_domain))
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
        log.error("API Search Error. No scenes found")
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
