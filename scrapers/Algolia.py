import datetime
import difflib
import json
import os
import re
import sqlite3
import sys
from configparser import ConfigParser, NoSectionError
from urllib.parse import urlparse

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

#
# User variable
#

# Print debug message.
PRINT_DEBUG = True
# Print ratio message. (Show title in search results)
PRINT_MATCH = True
# File to store the Algolia API key.
STOCKAGE_FILE_APIKEY = "Algolia.ini"
# Tag you always want in Scraper window.
FIXED_TAGS = ""
# Include non female performers
NON_FEMALE = True

# Setup


def check_db(DB_PATH, SCENE_ID):
    try:
        sqliteConnection = sqlite3.connect("file:" + DB_PATH + "?mode=ro", uri=True)
        log.debug("Connected to SQLite database")
    except:
        log.warning("Fail to connect to the database")
        return None, None, None
    cursor = sqliteConnection.cursor()
    cursor.execute("SELECT size,duration,height from scenes WHERE id=?;", [SCENE_ID])
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
    log.debug("Request URL: {}".format(url))
    response = requests.post(url, headers=head, json=json, timeout=10)
    #log.debug("Returned URL: {}".format(response.url))
    if response.content and response.status_code == 200:
        return response
    else:
        log.warning("[REQUEST] Error, Status Code: {}".format(response.status_code))
        #print(response.text, file=open("algolia_request.html", "w", encoding='utf-8'))
    return None


# API Authentification
def apikey_get(site_url, time):
    r = sendRequest(site_url, HEADERS)
    if r is None:
        return None, None
    script_html = fetch_page_json(r.text)
    if script_html is not None:
        application_id = script_html['api']['algolia']['applicationID']
        api_key = script_html['api']['algolia']['apiKey']
        # Write key into a file
        write_config(time, application_id, api_key)
        log.info("New API keys: {}".format(api_key))
        return application_id, api_key
    else:
        log.error("Can't retrieve API keys from page ({})".format(site_url))
        return None, None


def fetch_page_json(page_html):
    matches = re.findall(r'window.env\s+=\s(.+);', page_html, re.MULTILINE)
    return None if len(matches) == 0 else json.loads(matches[0])


def check_config(domain, time):
    if os.path.isfile(STOCKAGE_FILE_APIKEY):
        config = ConfigParser()
        config.read(STOCKAGE_FILE_APIKEY)
        try:
            time_past = datetime.datetime.strptime(
                config.get(domain, 'date'), '%Y-%m-%d %H:%M:%S.%f')

            if time_past.hour - 1 < time.hour < time_past.hour + 1 and (time - time_past).days == 0:
                log.debug("Using old key")
                application_id = config.get(domain, 'app_id')
                api_key = config.get(domain, 'api_key')
                return application_id, api_key
            else:
                log.info(
                    "Need new api key: [{}|{}|{}]".format(
                        time.hour, time_past.hour, (time - time_past).days))
        except NoSectionError:
            pass
    return None, None


def write_config(date, app_id, api_key):
    log.debug("Writing config!")
    config = ConfigParser()
    config.read(STOCKAGE_FILE_APIKEY)
    try:
        config.get(SITE, 'date')
    except NoSectionError:
        config.add_section(SITE)
    config.set(SITE, 'date', date.strftime("%Y-%m-%d %H:%M:%S.%f"))
    config.set(SITE, 'app_id', app_id)
    config.set(SITE, 'api_key', api_key)
    with open(STOCKAGE_FILE_APIKEY, 'w') as configfile:
        config.write(configfile)
    return


# API Search Data


def api_search_req(type_search, query, api_url):
    api_request = None
    if type_search == "query":
        api_request = api_search_query(query, api_url)
    if type_search == "id":
        api_request = api_search_id(query, api_url)
    if api_request:
        api_search = api_request.json()["results"][0].get("hits")
        if api_search:
            return api_search
    return None


def api_search_id(url_id, api_url):
    clip_id = ["clip_id:{}".format(url_id)]
    request_api = {
        "requests":
            [
                {
                    "indexName": "all_scenes",
                    "params": "query=&hitsPerPage=20&page=0",
                    "facetFilters": clip_id
                }
            ]
    }
    r = sendRequest(api_url, HEADERS, request_api)
    return r


def api_search_query(query, api_url):
    request_api = {
        "requests":
            [
                {
                    "indexName": "all_scenes",
                    "params": "query=" + query + "&hitsPerPage=40&page=0"
                }
            ]
    }
    r = sendRequest(api_url, HEADERS, request_api)
    return r


# Searching Result


def json_parser(search_json, range_duration=60, single=False):
    result_dict = {}
    # Just for not printing the full JSON in log...
    debug_dict = {}
    with open("adultime_scene_search.json", 'w', encoding='utf-8') as f:
        json.dump(search_json, f, ensure_ascii=False, indent=4)
    for scene in search_json:
        r_match = match_result(scene, range_duration, single)
        if r_match["info"]:
            if result_dict.get(r_match["info"]):
                # Url should be more accurate than the title
                if r_match["url"] > result_dict[r_match["info"]]["url"]:
                    result_dict[r_match["info"]] = {
                        "title": r_match["title"],
                        "url": r_match["url"],
                        "json": scene
                    }
                    debug_dict[r_match["info"]] = {
                        "title": r_match["title"],
                        "url": r_match["url"],
                        "scene": scene["title"]
                    }
                elif r_match["title"] > result_dict[r_match["info"]]["title"] and r_match[
                        "title"] > result_dict[r_match["info"]]["url"]:
                    result_dict[r_match["info"]] = {
                        "title": r_match["title"],
                        "url": r_match["url"],
                        "json": scene
                    }
                    debug_dict[r_match["info"]] = {
                        "title": r_match["title"],
                        "url": r_match["url"],
                        "scene": scene["title"]
                    }
            else:
                result_dict[r_match["info"]] = {
                    "title": r_match["title"],
                    "url": r_match["url"],
                    "json": scene
                }
                debug_dict[r_match["info"]] = {
                    "title": r_match["title"],
                    "url": r_match["url"],
                    "scene": scene["title"]
                }
    # Engine whoaaaaa
    # A = ByID/Most likely | S = Size | D = Duration | N = Network | R = Only Ratio
    log.info("--- BEST RESULT ---")
    for key, item in debug_dict.items():
        log.info(
            "[{}] Title: {}; Ratio Title: {} - URL: {}".format(
                key, item["scene"], round(item["title"], 3), round(item["url"], 3)))
    log.info("--------------")
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
                api_filesize = api_scene["download_file_sizes"].get(db_height + "p")
            if api_filesize:
                api_filesize = int(api_filesize)
        if api_filesize is None:
            api_filesize = api_scene.get("index_size")
            if api_filesize:
                api_filesize = int(api_filesize)
        if db_duration - range_duration <= api_duration <= db_duration + range_duration:
            match_duration = True
        db_size_max = db_size + (db_size / 100)
        db_size_min = db_size - (db_size / 100)
        if api_filesize:
            if db_size_min <= api_filesize <= db_size_max:
                match_size = True
    # Post process things
    match_domain = False
    if url_domain:
        if api_scene.get("sitename"):
            #log.debug("API Sitename: {}".format(api_scene["sitename"]))
            if api_scene["sitename"] == url_domain:
                match_domain = True
        if api_scene.get("network_name"):
            #log.debug("API Network: {}".format(api_scene["network_name"]))
            if api_scene["network_name"] == url_domain:
                match_domain = True

    # Matching ratio
    if SCENE_TITLE:
        match_ratio_title = difflib.SequenceMatcher(
            None, SCENE_TITLE.lower(), api_title.lower()).ratio()
    else:
        match_ratio_title = 0
    if url_title and api_scene.get("url_title"):
        match_ratio_title_url = difflib.SequenceMatcher(
            None, url_title.lower(), api_scene["url_title"].lower()).ratio()
    else:
        match_ratio_title_url = 0

    # Rank search result

    log.debug(
        "[MATCH] Title: {} |-RATIO-| Title: {} / URL: {} |-MATCH-| Duration: {}, Size: {}, Domain: {}"
        .format(
            api_title, round(match_ratio_title, 5), round(match_ratio_title_url, 5),
            match_duration, match_size, match_domain))
    match_dict = {}
    match_dict["title"] = match_ratio_title
    match_dict["url"] = match_ratio_title_url
    information_used = ""
    if (single and (match_duration or (database_dict is None and match_ratio_title_url > 0.5))) or match_ratio_title_url == 1:
        information_used += "A"
    if match_size:
        information_used += "S"
    if match_duration:
        information_used += "D"
    if match_domain:
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

    log.debug(
        "[STUDIO] {} - {} - {} - {}".format(
            api_json.get('serie_name'), api_json.get('network_name'),
            api_json.get('mainChannelName'), api_json.get('sitename_pretty')))
    # Performer
    perf = []
    for x in api_json.get('actors'):
        if x.get('gender') == "female" or NON_FEMALE:
            perf.append({
                "name": x.get('name').strip(),
                "gender": x.get('gender')
            })
    scrape['performers'] = perf

    # Tags
    list_tag = []
    for x in api_json.get('categories'):
        if x.get('name') is None:
            continue
        tag_name = x.get('name')
        tag_name = " ".join(x.capitalize() for x in tag_name.split(" "))
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
            log.warning("Can't locate image.")
    # URL
    try:
        hostname = api_json['sitename']
        nn = api_json['network_name']
        if nn.lower() == "21 sextury":
            hostname = "21sextury"
        scrape['url'] = f"https://{hostname}.com/en/video/{api_json['sitename']}/{api_json['url_title']}/{api_json['clip_id']}"
    except:
        if url:
            scrape['url'] = url
    #debug("{}".format(scrape))
    return scrape


SITE = sys.argv[1]

try:
    USERFOLDER_PATH = re.match(r".+\.stash.", __file__).group(0)
    CONFIG_PATH = USERFOLDER_PATH + "config.yml"
    log.debug("Config Path: {}".format(CONFIG_PATH))
except:
    USERFOLDER_PATH = None
    CONFIG_PATH = None

HEADERS = {
    "User-Agent":
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    "Origin":
        "https://www.{}.com".format(SITE),
    "Referer":
        "https://www.{}.com".format(SITE)
}

FRAGMENT = json.loads(sys.stdin.read())
SEARCH_TITLE = FRAGMENT.get("name")
SCENE_ID = FRAGMENT.get("id")
SCENE_TITLE = FRAGMENT.get("title")
SCENE_URL = FRAGMENT.get("url")

#log.debug(HEADERS)
#log.debug('{}'.format(FRAGMENT))

if "validName" in sys.argv and SCENE_URL is None:
    sys.exit(1)

if SCENE_URL and SCENE_ID is None:
    log.debug("URL Scraping: {}".format(SCENE_URL))
else:
    log.debug("Stash ID: {}".format(SCENE_ID))
    log.debug("Stash Title: {}".format(SCENE_TITLE))

# Get your sqlite database
stash_config = graphql.configuration()
DB_PATH = None
if stash_config:
    DB_PATH = stash_config["general"]["databasePath"]
if (CONFIG_PATH and DB_PATH is None):
    # getting your database from the config.yml
    if (os.path.isfile(CONFIG_PATH)):
        with open(CONFIG_PATH) as f:
            for line in f:
                if "database: " in line:
                    DB_PATH = line.replace("database: ", "").rstrip('\n')
                    break
log.debug("Database Path: {}".format(DB_PATH))
if DB_PATH:
    if SCENE_ID:
        # Get data by GraphQL
        database_dict = graphql.getScene(SCENE_ID)
        if database_dict is None:
            # Get data by SQlite
            log.warning("GraphQL request failed, accessing database directly...")
            database_dict = check_db(DB_PATH, SCENE_ID)
        else:
            database_dict = database_dict["file"]
        log.debug("[DATABASE] Info: {}".format(database_dict))
    else:
        database_dict = None
        log.debug("URL scraping... Ignoring database...")
else:
    database_dict = None
    log.warning("Database path missing.")

# Extract things
url_title = None
url_id = None
url_domain = None
if SCENE_URL:
    url_domain = re.sub(r"www\.|\.com", "", urlparse(SCENE_URL).netloc)
    log.info("URL Domain: {}".format(url_domain))
    url_id_check = re.sub('.+/', '', SCENE_URL)
    # Gettings ID
    try:
        if url_id_check.isdigit():
            url_id = url_id_check
        else:
            url_id = re.search(r"/(\d+)/*", SCENE_URL).group(1)
        log.info("ID: {}".format(url_id))
    except:
        log.warning("Can't get ID from URL")
    # Gettings url_title
    try:
        url_title = re.match(r".+/(.+)/\d+", SCENE_URL).group(1)
        log.info("URL_TITLE: {}".format(url_title))
    except:
        log.warning("Can't get url_title from URL")

# Filter title
if SCENE_TITLE:
    SCENE_TITLE = re.sub(r'[-._\']', ' ', os.path.splitext(SCENE_TITLE)[0])
    # Remove resolution
    SCENE_TITLE = re.sub(r'\sXXX|\s1080p|720p|2160p|KTR|RARBG|\scom\s|\[|]|\sHD|\sSD|', '', SCENE_TITLE)
    # Remove Date
    SCENE_TITLE = re.sub(r'\s\d{2}\s\d{2}\s\d{2}|\s\d{4}\s\d{2}\s\d{2}', '', SCENE_TITLE)
    log.debug("Title: {}".format(SCENE_TITLE))

# ACCESS API
# Check existing API keys
CURRENT_TIME = datetime.datetime.now()
application_id, api_key = check_config(SITE, CURRENT_TIME)

# Getting new key
if application_id is None:
    application_id, api_key = apikey_get("https://www.{}.com/en".format(SITE), CURRENT_TIME)
# Fail getting new key
if application_id is None:
    sys.exit(1)

# Time to search the API
api_url = "https://tsmkfa364q-dsn.algolia.net/1/indexes/*/queries?x-algolia-application-id={}&x-algolia-api-key={}".format(
    application_id, api_key)
api_search = None
api_json = None

# sceneByName
if SEARCH_TITLE:
    SEARCH_TITLE = SEARCH_TITLE.replace(".", " ")
    log.debug("[API] Searching for: {}".format(SEARCH_TITLE))
    api_search = api_search_req("query", SEARCH_TITLE, api_url)
    final_json = None
    if api_search:
        result_search = []
        for scene in api_search:
            scraped_json = scraping_json(scene)
            if scraped_json.get("tags"):
                scraped_json.pop("tags")
            result_search.append(scraped_json)
        if result_search:
            final_json = result_search
    if final_json is None:
        log.error("API Search finished. No results!")
    print(json.dumps(final_json))
    sys.exit()

if url_id:
    log.debug("[API] Searching using URL_ID")
    api_search = api_search_req("id", url_id, api_url)
    if api_search:
        log.info("[API] Search give {} result(s)".format(len(api_search)))
        api_json = json_parser(api_search, 120, True)
    else:
        log.warning("[API] No result")
if url_title and api_json is None:
    log.debug("[API] Searching using URL_TITLE")
    api_search = api_search_req("query", url_title, api_url)
    if api_search:
        log.info("[API] Search give {} result(s)".format(len(api_search)))
        api_json = json_parser(api_search)
if SCENE_TITLE and api_json is None:
    log.debug("[API] Searching using STASH_TITLE")
    api_search = api_search_req("query", SCENE_TITLE, api_url)
    if api_search:
        log.info("[API] Search give {} result(s)".format(len(api_search)))
        api_json = json_parser(api_search)

# Scraping the JSON
if api_json:
    log.info("Scene found: {}".format(api_json["title"]))
    scraped_json = scraping_json(api_json, SCENE_URL)
    print(json.dumps(scraped_json))
else:
    log.error("Can't find the scene")
    print(json.dumps(None))
    sys.exit()
