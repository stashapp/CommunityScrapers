import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timedelta
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
    print("You need to take the folder 'py_common' in the community repo (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()


def check_datelist(file: str, days=7):
    days_ago = datetime.now() - timedelta(days)
    filetime = datetime.fromtimestamp(os.path.getctime(file))
    if filetime < days_ago:
        # file older than
        return True
    return False


def reading_md(file: str):
    scrapers = {}
    with open(file, "r") as md:
        Lines = md.readlines()
    for line in Lines:
        if "Non url scrapers" in line:
            break
        if ".yml" not in line:
            continue
        splt = line.split("|")
        # not a scene scraper
        if splt[2] != ":heavy_check_mark:":
            continue
        scrapers[splt[0]] = {"url": splt[0], "name": splt[1], "needs": splt[6]}
    return scrapers


def get_domain(url: str):
    domain = urlparse(url).netloc
    if domain:
        domain = domain.replace("www.", "")
    return domain


def zip_extract(filename):
    dir = os.path.dirname(PATH_ZIP)
    new_file = os.path.join(dir, os.path.basename(filename))
    with zipfile.ZipFile(PATH_ZIP) as z:
        with z.open('CommunityScrapers-master/scrapers/' + filename) as zf, open(new_file, 'wb') as f:
            shutil.copyfileobj(zf, f)
    return


def github_dwl():
    list_md = "https://raw.githubusercontent.com/stashapp/CommunityScrapers/master/SCRAPERS-LIST.md"
    zip_master = "https://github.com/stashapp/CommunityScrapers/archive/refs/heads/master.zip"
    try:
        r = requests.get(zip_master, timeout=10)
        with open(PATH_ZIP, "wb") as zip_file:
            zip_file.write(r.content)
    except Exception as err:
        sys.exit(f"Error downloading the zip file. ({err})")
    try:
        r = requests.get(list_md, timeout=10)
        with open(PATH_MDLIST, "wb") as file:
            file.write(r.content)
    except Exception as err:
        sys.exit(f"Error downloading to download the scraper list. ({err})")


def find_scraper(scene_url, scrapers):
    for scraper in scrapers.values():
        if scene_url == scraper["url"]:
            return scraper
    return None


def main():
    # create tmp folder
    if not os.path.exists(PATH_TMP):
        log.info("Creating tmp folder")
        os.makedirs(PATH_TMP)
    # checking if list exist or too old
    getting_newlist = True
    if os.path.exists(PATH_MDLIST):
        getting_newlist = check_datelist(PATH_MDLIST)
        if getting_newlist:
            os.remove(PATH_MDLIST)
            if os.path.exists(PATH_ZIP):
                os.remove(PATH_ZIP)
    # download file from github (zip & list)
    if getting_newlist:
        log.info("Downloading file from github...")
        github_dwl()
    # reading the md
    scrapers = reading_md(PATH_MDLIST)
    # url domain eg: google.com
    scene_domain = get_domain(SCENE_URL)
    # find scraper in the list with this domain
    scraper_file = find_scraper(scene_domain, scrapers)
    if not scraper_file:
        log.error(f"Didn't find a scene scraper with this url ({scene_domain})")
        return None
    if scraper_file["needs"] == "Python":
        log.error(f"A scraper exist ({scraper_file['name']}) but it's a python scraper.")
        return None
    log.debug(f"Scraper: {scraper_file['name']}")
    # path of the tmp scraper
    scraper_path = os.path.join(PATH_TMP, scraper_file['name'])
    try:
        zip_extract(scraper_file['name'])
    except Exception as err:
        log.error(f"Error extraction the scraper ({err})")
        return None
    if not os.path.exists(scraper_path):
        log.error(f"The scraper ({scraper_file['name']}) didn't move.")
        return None

    graphql.reloadScrapers()
    try:
        scraped_data = graphql.scrape_SceneURL(SCENE_URL)
    except Exception as err:
        os.remove(scraper_path)
        log.error(f"Error with the scraper ({err})")
        return None

    os.remove(scraper_path)
    if scraped_data:
        scraped_data["url"] = SCENE_URL
        return scraped_data


FRAGMENT = json.loads(sys.stdin.read())
SEARCH_TITLE = FRAGMENT.get("name")
SCENE_ID = FRAGMENT.get("id")
SCENE_TITLE = FRAGMENT.get("title")
SCENE_URL = FRAGMENT.get("url")

if SCENE_URL and SCENE_ID is None:
    log.debug("URL Scraping: {}".format(SCENE_URL))
else:
    log.debug("Stash ID: {}".format(SCENE_ID))
    log.debug("Stash Title: {}".format(SCENE_TITLE))

STASH_CONFIG = graphql.configuration()

PATH_TMP = os.path.join(STASH_CONFIG["general"]["scrapersPath"], "tmp")
PATH_MDLIST = os.path.join(PATH_TMP, "scraper_list.md")
PATH_ZIP = os.path.join(PATH_TMP, "scraper_master.zip")
PATH_MYSELF = os.path.realpath(__file__).replace(".py", ".yml")

# trick to don't call himself  (for some reason, the request (scrape_SceneURL) can use this script)
os.rename(PATH_MYSELF, PATH_MYSELF + '.tmp')
result = main()
#log.debug(result)
if result is None:
    result = {}
# Stash error when result is None ? runtime error: invalid memory address or nil pointer dereference
os.rename(PATH_MYSELF + '.tmp', PATH_MYSELF)
graphql.reloadScrapers()
print(json.dumps(result))
