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
    from bs4 import BeautifulSoup as bs
    from lxml import html
except ModuleNotFoundError:
    print("You need to install the following modules 'requests', 'bs4', 'lxml'.")
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


def clean_text(details: str) -> dict:
    """
    remove escaped backslashes and html parse the details text
    """
    if details:
        details = re.sub(r"\\", "", details)
        details = bs(details, features='lxml').get_text()
    return details


def check_db(DB_PATH:str , SCENE_ID:str) -> dict:
    """
    get scene data (size, duration, height) directly from the database file
    """
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



def sendRequest(url: str, head:str, json="") -> requests.Response:
    """
    get post response from url
    """
    log.debug(f"Request URL: {url}")
    try:
        response = requests.post(url, headers=head, json=json, timeout=10)
    except requests.RequestException as req_error:
        log.warning(f"Requests failed: {req_error}")
        return None
    #log.debug(f"Returned URL: {response.url}")
    if response.content and response.status_code == 200:
        return response
    else:
        log.warning(f"[REQUEST] Error, Status Code: {response.status_code}")
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


def api_search_id(scene_id, api_url):
    clip_id = [f"clip_id:{scene_id}"]
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

def api_search_movie_id(m_id, api_url):
    movie_id = [f"movie_id:{m_id}"]
    request_api = {
        "requests":
            [
                {
                    "indexName": "all_movies",
                    "params": "query=&hitsPerPage=20&page=0",
                    "facetFilters": movie_id
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
            f'[{key}] Title: {item["scene"]}; Ratio Title: {round(item["title"], 3)} - URL: {round(item["url"], 3)}'
            )
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
    if URL_DOMAIN:
        if api_scene.get("sitename"):
            #log.debug("API Sitename: {}".format(api_scene["sitename"]))
            if api_scene["sitename"].lower() == URL_DOMAIN:
                match_domain = True
        if api_scene.get("network_name"):
            #log.debug("API Network: {}".format(api_scene["network_name"]))
            if api_scene["network_name"].lower() == URL_DOMAIN:
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
        f"[MATCH] Title: {api_title} |-RATIO-| Ratio: {round(match_ratio_title, 5)} / URL: {round(match_ratio_title_url, 5)} |-MATCH-| Duration: {match_duration}, Size: {match_size}, Domain: {match_domain}"
        )
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

def get_id_from_url(url: str) -> str:
    '''
    gets  the id from a valid url
    expects urls of the form www.example.com/.../title/id
    '''
    if url is None or url == "":
        return None

    id_check = re.sub('.+/', '', url)
    id_from_url = None
    try:
        if id_check.isdigit():
            id_from_url = id_check
        else:
            id_from_url = re.search(r"/(\d+)/*", url).group(1)
            log.info(f"ID: {id_from_url}")
    except:
        log.warning("Can't get ID from URL")
    return id_from_url

def parse_movie_json(movie_json: dict) -> dict:
    """
    process an api movie dictionary and return a scraped one
    """
    scrape = {}
    scrape["synopsis"] = clean_text(movie[0].get("description"))
    scrape["name"] = movie[0].get("title")
    scrape["studio"] = {"name": movie[0].get("sitename_pretty")}
    scrape["duration"] = movie[0].get("total_length")

    scrape["date"] = movie[0].get("date_created") # available options are "date_created", "upcoming", "last_modified"
                                                  # dates don't seem to be accurate (modifed by studio) at least for evilangel

    scrape["front_image"] = f"https://transform.gammacdn.com/movies{movie[0].get('cover_path')}_front_400x625.jpg"
    scrape["back_image"] = f"https://transform.gammacdn.com/movies{movie[0].get('cover_path')}_back_400x625.jpg"

    directors = []
    for x in movie[0].get('directors'):
        directors.append(x.get('name').strip())
    scrape["director"] = ", ".join(directors)
    return scrape

def parse_scene_json(scene_json, url=None):
    """
    process an api scene dictionary and return a scraped one
    """
    scrape = {}
    # Title
    if scene_json.get('title'):
        scrape['title'] = scene_json['title'].strip()
    # Date
    scrape['date'] = scene_json.get('release_date')
    # Details
    #scrape['details'] = re.sub(r'</br>|<br\s/>|<br>|<br/>', '\n', scene_json.get('description'))
    scrape['details'] = clean_text(scene_json.get('description'))

    # Studio
    scrape['studio'] = {}
    if scene_json.get('serie_name'):
        scrape['studio']['name'] = scene_json.get('serie_name')

    log.debug(
        f"[STUDIO] {scene_json.get('serie_name')} - {scene_json.get('network_name')} - {scene_json.get('mainChannelName')} - {scene_json.get('sitename_pretty')}"
        )
    # Performer
    perf = []
    for x in scene_json.get('actors'):
        if x.get('gender') == "female" or NON_FEMALE:
            perf.append({
                "name": x.get('name').strip(),
                "gender": x.get('gender')
            })
    scrape['performers'] = perf

    # Tags
    list_tag = []
    for x in scene_json.get('categories'):
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
        scrape['image'] = 'https://images03-fame.gammacdn.com/movies' + next(iter(scene_json['pictures']['nsfw']['top'].values()))
    except:
        try:
            scrape['image'] = 'https://images03-fame.gammacdn.com/movies' + next(iter(scene_json['pictures']['sfw']['top'].values()))
        except:
            log.warning("Can't locate image.")
    # URL
    try:
        hostname = scene_json['sitename']
        net_name = scene_json['network_name']
        if net_name.lower() == "21 sextury":
            hostname = "21sextury"
        elif net_name.lower() == "21 naturals":
            hostname = "21naturals"
        scrape['url'] = f"https://{hostname}.com/en/video/{scene_json['sitename']}/{scene_json['url_title']}/{scene_json['clip_id']}"
    except:
        if url:
            scrape['url'] = url
    #debug(f"{scrape}")
    return scrape



#
# Start processing
#

try:
    USERFOLDER_PATH = re.match(r".+\.stash.", __file__).group(0)
    CONFIG_PATH = USERFOLDER_PATH + "config.yml"
    log.debug(f"Config Path: {CONFIG_PATH}")
except:
    USERFOLDER_PATH = None
    CONFIG_PATH = None

SITE = sys.argv[1]
HEADERS = {
    "User-Agent":
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
    "Origin":
        f"https://www.{SITE}.com",
    "Referer":
        f"https://www.{SITE}.com"
}

FRAGMENT = json.loads(sys.stdin.read())
SEARCH_TITLE = FRAGMENT.get("name")
SCENE_ID = FRAGMENT.get("id")
SCENE_TITLE = FRAGMENT.get("title")
SCENE_URL = FRAGMENT.get("url")

# ACCESS API
# Check existing API keys
CURRENT_TIME = datetime.datetime.now()
application_id, api_key = check_config(SITE, CURRENT_TIME)
# Getting new key
if application_id is None:
    application_id, api_key = apikey_get(f"https://www.{SITE}.com/en", CURRENT_TIME)
# Failed to get new key
if application_id is None:
        sys.exit(1)
api_url = f"https://tsmkfa364q-dsn.algolia.net/1/indexes/*/queries?x-algolia-application-id={application_id}&x-algolia-api-key={api_key}"

#log.debug(HEADERS)
#log.debug(FRAGMENT)
URL_DOMAIN = None
if SCENE_URL:
    URL_DOMAIN = re.sub(r"www\.|\.com", "", urlparse(SCENE_URL).netloc).lower()
    log.info(f"URL Domain: {URL_DOMAIN}")

if "validName" in sys.argv and SCENE_URL is None:
    sys.exit(1)

if SCENE_URL and SCENE_ID is None:
    log.debug(f"URL Scraping: {SCENE_URL}")
else:
    log.debug(f"Stash ID: {SCENE_ID}")
    log.debug(f"Stash Title: {SCENE_TITLE}")

if "movie" not in sys.argv:
    # Get your sqlite database
    stash_config = graphql.configuration()
    DB_PATH = None
    if stash_config:
        DB_PATH = stash_config["general"]["databasePath"]
           
    if (CONFIG_PATH and DB_PATH is None):
        # getting your database from the config.yml
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                for line in f:
                    if "database: " in line:
                        DB_PATH = line.replace("database: ", "").rstrip('\n')
                        break
    log.debug(f"Database Path: {DB_PATH}")
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
            log.debug(f"[DATABASE] Info: {database_dict}")
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
        url_id = get_id_from_url(SCENE_URL)
        try:
            url_title = re.match(r".+/(.+)/\d+", SCENE_URL).group(1)
            log.info(f"URL_TITLE: {url_title}")
        except:
            log.warning("Can't get url_title from URL")

    # Filter title
    if SCENE_TITLE:
        SCENE_TITLE = re.sub(r'[-._\']', ' ', os.path.splitext(SCENE_TITLE)[0])
        # Remove resolution
        SCENE_TITLE = re.sub(r'\sXXX|\s1080p|720p|2160p|KTR|RARBG|\scom\s|\[|]|\sHD|\sSD|', '', SCENE_TITLE)
        # Remove Date
        SCENE_TITLE = re.sub(r'\s\d{2}\s\d{2}\s\d{2}|\s\d{4}\s\d{2}\s\d{2}', '', SCENE_TITLE)
        log.debug(f"Title: {SCENE_TITLE}")

    # Time to search the API
    api_search = None
    api_json = None

    # sceneByName
    if SEARCH_TITLE:
        SEARCH_TITLE = SEARCH_TITLE.replace(".", " ")
        log.debug(f"[API] Searching for: {SEARCH_TITLE}")
        api_search = api_search_req("query", SEARCH_TITLE, api_url)
        final_json = None
        if api_search:
            result_search = []
            for scene in api_search:
                scraped_json = parse_scene_json(scene)
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
        log.debug(f"[API] Searching using URL_ID {url_id}")
        api_search = api_search_req("id", url_id, api_url)
        if api_search:
            log.info(f"[API] Search gives {len(api_search)} result(s)")
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
        log.info(f"Scene found: {api_json['title']}")
        scraped_json = parse_scene_json(api_json, SCENE_URL)
        print(json.dumps(scraped_json))
    else:
        log.error("Can't find the scene")
        print(json.dumps({}))
        sys.exit()
else:
    log.debug("Scraping movie")
    movie_id = get_id_from_url(SCENE_URL)
    if movie_id:
        movie_results = api_search_movie_id(movie_id, api_url)
        movie = movie_results.json()["results"][0].get("hits")
        scraped_movie = parse_movie_json(movie)
        log.debug(scraped_movie)
        print(json.dumps(scraped_movie))