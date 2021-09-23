import datetime
import difflib
import json
import os
import re
import sqlite3
import sys
from urllib.parse import urlparse

import requests

#
# User variable
#
SERVER_IP = "http://localhost:9999"
# STASH API (Settings > Configuration > Authentication)
STASH_API = ""
# Print debug message.
PRINT_DEBUG = True
# Print ratio message. (Show title find in search)
PRINT_MATCH = True
# File used to store key to connect the API.
STOCKAGE_FILE_APIKEY = "Adultime_key.txt"
# Tags you don't want to see appear in Scraper window.
IGNORE_TAGS = ["Sex","Feature"]
# Tag you always want in Scraper window.
FIXED_TAGS = ""

def debug(q):
    q = str(q)
    if "[DEBUG]" in q and PRINT_DEBUG == False:
        return
    if "[MATCH]" in q and PRINT_MATCH == False:
        return
    print(q, file=sys.stderr)

# Setup

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
            debug("[ERROR][GraphQL] HTTP Error 401, Unauthorised.")
            return None
        else:
            raise ConnectionError("GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(response.status_code, response.content, query, variables))
    except Exception as err:
        debug(err)
        return None


def graphql_configdb():
    query = """
    query Configuration {
        configuration {
            general {
                databasePath
            }
        }
    }
    """
    result = callGraphQL(query)
    if result:
        return result["configuration"]["general"]["databasePath"]
    return None


def graphql_getscene(scene_id):
    query = """
    query FindScene($id: ID!, $checksum: String) {
        findScene(id: $id, checksum: $checksum) {
            file {
                size
                duration
                video_codec
                audio_codec
                width
                height
                framerate
                bitrate
            }
        }
    }
    """
    variables = {
        "id": scene_id
    }
    result = callGraphQL(query, variables)
    if result:
        return result.get('findScene')
    return None


def check_db(DB_PATH, SCENE_ID):
    try:
        sqliteConnection = sqlite3.connect("file:" + DB_PATH + "?mode=ro", uri=True)
        debug("[DEBUG] Database successfully connected to SQLite")
    except:
        debug("[Error] Fail to connect to the database")
        return None, None, None
    cursor = sqliteConnection.cursor()
    cursor.execute("SELECT size,duration,height from scenes WHERE id=?;",[SCENE_ID])
    record = cursor.fetchall()
    database = {}
    database["size"] = int(record[0][0])
    database["duration"] = int(record[0][1])
    database["height"] = str(record[0][2])
    cursor.close()
    sqliteConnection.close()
    return database

# General

def sendRequest(url, head, json=""):
    #debug("[DEBUG] Request URL: {}".format(url))
    response = requests.post(url, headers=head,json=json, timeout=10)
    #debug("[DEBUG] Returned URL: {}".format(response.url))
    if response.content and response.status_code == 200:
        return response
    else:
        debug("[REQUEST] Error, Status Code: {}".format(response.status_code))
        #print(response.text, file=open("request.html", "w", encoding='utf-8'))
    return None




# API Authentification
def apikey_check(time):
    if (os.path.isfile(STOCKAGE_FILE_APIKEY) == True):
        with open(STOCKAGE_FILE_APIKEY) as f:
            list_f = f.read().split("|")
        time_past = datetime.datetime.strptime(list_f[0], '%Y-%m-%d %H:%M:%S.%f')
        if time_past.hour-1 < time.hour < time_past.hour+1 and (time - time_past).days == 0:
            debug("[DEBUG] Using old api keys")
            application_id = list_f[1]
            api_key = list_f[2]
            return application_id, api_key
        else:
            debug("[INFO] Need new api key: [{}|{}|{}]".format(time.hour,time_past.hour,(time - time_past).days))
    return None, None


def apikey_get(site_url,time):
    r = sendRequest(site_url, ADULTIME_HEADERS)
    if r is None:
        return None, None
    script_html = fetch_page_json(r.text)
    if script_html is not None:
        application_id = script_html['api']['algolia']['applicationID']
        api_key = script_html['api']['algolia']['apiKey']
        # Write key into a file
        print("{}|{}|{}".format(time, application_id,api_key), file=open(STOCKAGE_FILE_APIKEY, "w"))
        debug("[INFO] New API keys: {}".format(api_key))
        return application_id, api_key
    else:
        debug("[Error] Can't retrieve API keys from the html ({})".format(site_url))
        return None, None


def fetch_page_json(page_html):
    matches = re.findall(r'window.env\s+=\s(.+);', page_html, re.MULTILINE)
    return None if len(matches) == 0 else json.loads(matches[0])


# API Search Data

def api_search_req(type_search,query,api_url):
    api_request = None
    if type_search == "query":
        api_request = api_search_query(query,api_url)
    if type_search == "id":
        api_request = api_search_id(query,api_url)
    if api_request:
        api_search = api_request.json()["results"][0].get("hits")
        if api_search:
            return api_search
    return None


def api_search_id(url_id,api_url):
    clip_id = ["clip_id:{}".format(url_id)]
    request_api = {
        "requests": [
            {
                "indexName": "all_scenes_latest_desc",
                "params": "query=&hitsPerPage=20&page=0",
                "facetFilters": clip_id
            }
        ]
    }
    r = sendRequest(api_url, ADULTIME_HEADERS, request_api)
    return r


def api_search_query(query, api_url):
    request_api = {
        "requests": [
            {
                "indexName": "all_scenes_latest_desc",
                "params": "query=" + query + "&hitsPerPage=40&page=0"
            }
        ]
    }
    r = sendRequest(api_url, ADULTIME_HEADERS, request_api)
    return r


# Searching Result

def json_parser(search_json, range_duration=60, single=False):
    result_dict = {}
    # Just for not printing the full JSON in log...
    debug_dict = {}
    for scene in search_json:
        r_match = match_result(scene, range_duration, single)
        if r_match["info"]:
            if result_dict.get(r_match["info"]):
                # Url should be more accurate than the title
                if r_match["url"] > result_dict[r_match["info"]]["url"]:
                    result_dict[r_match["info"]] = {"title": r_match["title"],"url": r_match["url"],"json": scene}
                    debug_dict[r_match["info"]] = {"title": r_match["title"],"url": r_match["url"],"scene": scene["title"]}
                elif r_match["title"] > result_dict[r_match["info"]]["title"] and r_match["title"] > result_dict[r_match["info"]]["url"]:
                    result_dict[r_match["info"]] = {"title": r_match["title"],"url": r_match["url"],"json": scene}
                    debug_dict[r_match["info"]] = {"title": r_match["title"],"url": r_match["url"],"scene": scene["title"]}
            else:
                result_dict[r_match["info"]] = {"title": r_match["title"],"url": r_match["url"],"json": scene}
                debug_dict[r_match["info"]] = {"title": r_match["title"],"url": r_match["url"],"scene": scene["title"]}
    # Engine whoaaaaa
    # A = ByID/Most likely | S = Size | D = Duration | N = Network | R = Only Ratio
    debug("[INFO] --- BEST RESULT ---")
    for key,item in debug_dict.items():
        debug("[INFO][{}] Title: {}; Ratio Title: {} - URL: {}".format(key,item["scene"],round(item["title"],3),round(item["url"],3)))
    debug("[INFO] --------------")
    #
    if result_dict.get("ASDN"):
        return result_dict["ASDN"]["json"]
    elif result_dict.get("ASD"):
        return result_dict["ASD"]["json"]
    elif result_dict.get("ASN"):
        return result_dict["ASN"]["json"]
    elif result_dict.get("ADN"):
        return result_dict["ADN"]["json"]
    elif result_dict.get("AS"):
        return result_dict["AS"]["json"]
    elif result_dict.get("AD"):
        return result_dict["AD"]["json"]
    elif result_dict.get("AN"):
        if result_dict["AN"]["title"] > 0.5 or result_dict["AN"]["url"] > 0.5:
            return result_dict["AN"]["json"]
    elif result_dict.get("A"):
        if result_dict["A"]["title"] > 0.7 or result_dict["A"]["url"] > 0.7:
            return result_dict["A"]["json"]
    # 
    elif result_dict.get("SDN"):
        return result_dict["SDN"]["json"]
    elif result_dict.get("SD"):
        return result_dict["SD"]["json"]
    elif result_dict.get("SN"):
        if result_dict["SN"]["title"] > 0.5 or result_dict["SN"]["url"] > 0.5:
            return result_dict["SN"]["json"]
    elif result_dict.get("DN"):
        if result_dict["DN"]["title"] > 0.5 or result_dict["DN"]["url"] > 0.5:
            return result_dict["DN"]["json"]
    elif result_dict.get("S"):
        if result_dict["S"]["title"] > 0.7 or result_dict["S"]["url"] > 0.7:
            return result_dict["S"]["json"]
    elif result_dict.get("D"):
        if result_dict["D"]["title"] > 0.7 or result_dict["D"]["url"] > 0.7:
            return result_dict["D"]["json"]
    #
    elif result_dict.get("N"):
        if result_dict["N"]["title"] > 0.7 or result_dict["N"]["url"] > 0.7:
            return result_dict["N"]["json"]
    elif result_dict.get("R"):
        if result_dict["R"]["title"] > 0.8 or result_dict["R"]["url"] > 0.8:
            return result_dict["R"]["json"]
    return None
    

def match_result(api_scene, range_duration=60, single=False):
    api_title = api_scene.get("title")
    api_duration = int(api_scene.get("length"))
    api_filesize = None
    match_duration = False
    match_size = False
    # Using database
    if database_dict:
        db_duration = int(database_dict["duration"])
        db_height = str(database_dict["height"])
        db_size = int(database_dict["size"])
        if api_scene.get("download_file_sizes"):
            if db_height == "2160":
                api_filesize = api_scene["download_file_sizes"].get("4k")
            else:
                api_filesize = api_scene["download_file_sizes"].get(db_height+"p")
            if api_filesize:
                api_filesize = int(api_filesize)
        if api_filesize is None:
            api_filesize = api_scene.get("index_size")
            if api_filesize:
                api_filesize = int(api_filesize)
        if db_duration - range_duration <= api_duration <= db_duration + range_duration:
            match_duration = True
        db_size_max = db_size + (db_size/100)
        db_size_min = db_size - (db_size/100)
        if api_filesize:
            if db_size_min <= api_filesize <= db_size_max:
                match_size = True
    # Post process things
    match_domain = False
    if url_domain:
        if api_scene.get("sitename"):
            #debug("[DEBUG] API Sitename: {}".format(api_scene["sitename"]))
            if api_scene["sitename"] == url_domain:
                match_domain = True
        if api_scene.get("network_name"):
            #debug("[DEBUG] API Network: {}".format(api_scene["network_name"]))
            if api_scene["network_name"] == url_domain:
                match_domain = True

    # Matching ratio
    if SCENE_TITLE:
        match_ratio_title = difflib.SequenceMatcher(None, SCENE_TITLE.lower(), api_title.lower()).ratio()
    else:
        match_ratio_title = 0
    if url_title and api_scene.get("url_title"):
        match_ratio_title_url = difflib.SequenceMatcher(None, url_title.lower(), api_scene["url_title"].lower()).ratio()
    else:
        match_ratio_title_url = 0

    # Rank search result

    debug("[MATCH] Title: {} |-RATIO-| Title: {} / URL: {} |-MATCH-| Duration: {}, Size: {}, Domain: {}".format(api_title, round(match_ratio_title, 5), round(match_ratio_title_url, 5),match_duration, match_size, match_domain))
    match_dict = {}
    match_dict["title"] = match_ratio_title
    match_dict["url"] = match_ratio_title_url
    information_used = ""
    if (single == True and (match_duration == True or (database_dict is None and match_ratio_title_url > 0.5))) or match_ratio_title_url == 1:
        information_used += "A"
    if match_size == True:
        information_used += "S"
    if match_duration == True:
        information_used += "D"
    if match_domain == True:
        information_used += "N"
    if information_used == "":
        information_used = "R"
    match_dict["info"] = information_used
    #debug("[MATCH] {} - {}".format(api_title,match_dict))
    return match_dict


# Final

def scraping_json(api_json, url=None):
    scrape = {}
    # Title
    if api_json.get('title'):
        scrape['title'] = api_json['title'].strip()
    # Date
    scrape['date'] = api_json.get('release_date')
    # Details
    scrape['details'] = re.sub(r'</br>|<br\s/>|<br>|<br/>', '\n', api_json.get('description'))

    # Studio
    scrape['studio'] = {}
    if api_json.get('serie_name'):
        scrape['studio']['name'] = api_json.get('serie_name')
    if api_json.get('network_name'):
        scrape['studio']['name'] = api_json.get('network_name')
    if api_json.get('mainChannelName'):
        scrape['studio']['name'] = api_json.get('mainChannelName')
    if api_json.get('sitename_pretty'):
        scrape['studio']['name'] = api_json.get('sitename_pretty')
    debug("[STUDIO] {} - {} - {} - {}".format(api_json.get('serie_name'),api_json.get('network_name'),api_json.get('mainChannelName'),api_json.get('sitename_pretty')))
    # Performer
    perf = []
    for x in api_json.get('actors'):
        if x.get('gender') == "female":
            perf.append({"name": x.get('name').strip(), "gender":x.get('gender')})
    scrape['performers'] = perf

    # Tags
    list_tag = []
    for x in api_json.get('categories'):
        if x.get('name') is None:
            continue
        tag_name = x.get('name')
        tag_name = " ".join(x.capitalize() for x in tag_name.split(" "))
        if tag_name in IGNORE_TAGS:
            continue
        if tag_name:
            list_tag.append({"name": x.get('name')})
    if FIXED_TAGS:
        list_tag.append({"name": FIXED_TAGS})
    scrape['tags'] = list_tag

    # Image
    try:
        scrape['image'] = 'https://images03-fame.gammacdn.com/movies' + next(iter(api_json['pictures']['nsfw']['top'].values()))
    except:
        try:
            scrape['image'] = 'https://images03-fame.gammacdn.com/movies' + next(iter(api_json['pictures']['sfw']['top'].values()))
        except:
            debug("[ERROR] Can't manage to get the image for some reason.")
    # URL
    if url:
        scrape['url'] = url
    else:
        if api_json.get('member_url') is not None:
            scrape['url'] = api_json.get('member_url')
        else:
            try:
                scrape['url'] = 'https://members.adulttime.com/en/video/{}/{}/{}'.format(api_json['sitename'], api_json['url_title'], api_json['clip_id'])
            except:
                pass
    return scrape


try:
    USERFOLDER_PATH = re.match(r".+\.stash.",__file__).group(0)
    CONFIG_PATH = USERFOLDER_PATH + "config.yml"
    debug("[DEBUG] Config Path: {}".format(CONFIG_PATH))
except:
    USERFOLDER_PATH = None
    CONFIG_PATH = None

SERVER_URL = SERVER_IP + "/graphql"
ADULTIME_HEADERS = {
    "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    "Origin": "https://members.adulttime.com",
    "Referer": "https://members.adulttime.com/"
}

FRAGMENT = json.loads(sys.stdin.read())
SEARCH_TITLE = FRAGMENT.get("name")
SCENE_ID = FRAGMENT.get("id")
SCENE_TITLE = FRAGMENT.get("title")
SCENE_URL = FRAGMENT.get("url")

if "validName" in sys.argv and SCENE_URL is None:
    sys.exit()

if SCENE_URL and SCENE_ID is None:
    debug("[DEBUG] URL Scraping: {}".format(SCENE_URL))
else:
    debug("[DEBUG] Stash ID: {}".format(SCENE_ID))
    debug("[DEBUG] Stash Title: {}".format(SCENE_TITLE))
# Get your sqlite database
DB_PATH = graphql_configdb()
if (CONFIG_PATH and DB_PATH is None):
    if (os.path.isfile(CONFIG_PATH)):
        with open(CONFIG_PATH) as f:
            for line in f:
                if "database: " in line:
                    DB_PATH = line.replace("database: ", "").rstrip('\n')
                    break
debug("[DEBUG] Database Path: {}".format(DB_PATH))
if DB_PATH:
    if SCENE_ID:
        # Get data by GraphQL
        database_dict = graphql_getscene(SCENE_ID)
        if database_dict is None:
            # Get data by SQlite
            debug("[WARN] Fail to use GraphQL, trying to read database directly.")
            database_dict = check_db(DB_PATH, SCENE_ID)
        else:
            database_dict = database_dict["file"]
        debug("[DATABASE] Info: {}".format(database_dict))
    else:
        database_dict = None
        debug("[WARN] Can't connect to the database because URL Scraping.")
else:
    database_dict = None
    debug("[WARN] Can't find the database.")

# Extract things
url_title = None
url_id = None
url_domain = None
if SCENE_URL:
    url_domain = re.sub(r"www\.|\.com","",urlparse(SCENE_URL).netloc)
    debug("[INFO] URL Domain: {}".format(url_domain))
    url_id_check = re.sub('.+/', '', SCENE_URL)
    # Gettings ID
    try:
        if url_id_check.isdigit():
            url_id = url_id_check
        else:
            url_id = re.search(r"/(\d+)/*", SCENE_URL).group(1)
        debug("[INFO] ID: {}".format(url_id))
    except:
        debug("[WARN] Can't get ID from URL")
    # Gettings url_title
    try:
        url_title = re.match(r".+/(.+)/\d+", SCENE_URL).group(1)
        debug("[INFO] URL_TITLE: {}".format(url_title))
    except:
        debug("[WARN] Can't get url_title from URL")
        
# Filter title
if SCENE_TITLE:
    SCENE_TITLE = re.sub(r'[-._\']', ' ', os.path.splitext(SCENE_TITLE)[0])
    # Remove resolution
    SCENE_TITLE = re.sub(r'\sXXX|\s1080p|720p|2160p|KTR|RARBG|\scom\s|\[|]|\sHD|\sSD|', '', SCENE_TITLE)
    # Remove Date
    SCENE_TITLE = re.sub(r'\s\d{2}\s\d{2}\s\d{2}|\s\d{4}\s\d{2}\s\d{2}', '', SCENE_TITLE)
    debug("[INFO] Title: {}".format(SCENE_TITLE))


# ACCESS API
# Check existing API keys
CURRENT_TIME = datetime.datetime.now()
application_id, api_key = apikey_check(CURRENT_TIME)
# Getting new key
if application_id is None:
    application_id, api_key = apikey_get("https://www.girlsway.com/en", CURRENT_TIME)
# Fail getting new key
if application_id is None:
    sys.exit(1)

# Time to search the API
api_url = "https://tsmkfa364q-dsn.algolia.net/1/indexes/*/queries?x-algolia-application-id={}&x-algolia-api-key={}".format(application_id, api_key)
api_search = None
api_json = None


if SEARCH_TITLE:
    SEARCH_TITLE = SEARCH_TITLE.replace("."," ")
    debug("[API] Searching for: {}".format(SEARCH_TITLE))
    api_search = api_search_req("query", SEARCH_TITLE, api_url)
    if api_search:
        result_search = []
        for scene in api_search:
            scraped_json = scraping_json(scene)
            if scraped_json.get("tags"):
                scraped_json.pop("tags")
            result_search.append(scraped_json)
        if not result_search:
            debug("[ERROR] API Search don't give any result")
            scraped_json = {"title":"The search don't give any result."}
            scraped_json = [scraped_json]
        else:
            scraped_json = result_search
        print(json.dumps(scraped_json))
        sys.exit()

if url_id:
    debug("[API] Searching using URL_ID")
    api_search = api_search_req("id", url_id, api_url)
    if api_search:
        debug("[API] Search give {} result(s)".format(len(api_search)))
        api_json = json_parser(api_search, 120, True)
    else:
        debug("[API] No result")
if url_title and api_json is None:
    debug("[API] Searching using URL_TITLE")
    api_search = api_search_req("query", url_title, api_url)
    if api_search:
        debug("[API] Search give {} result(s)".format(len(api_search)))
        api_json = json_parser(api_search)
if SCENE_TITLE and api_json is None:
    debug("[API] Searching using STASH_TITLE")
    api_search = api_search_req("query", SCENE_TITLE, api_url)
    if api_search:
        debug("[API] Search give {} result(s)".format(len(api_search)))
        api_json = json_parser(api_search)

# Scraping the JSON
if api_json:
    debug("[INFO] Scene found: {}".format(api_json["title"]))
    scraped_json = scraping_json(api_json, SCENE_URL)
    print(json.dumps(scraped_json))
else:
    debug("[ERROR] Can't find the scene")
    sys.exit(1)
