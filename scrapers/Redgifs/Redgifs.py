import base64
import json
import os
import re
import sys
from datetime import datetime

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
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()
try:
    import requests
except ModuleNotFoundError:
    log.error(
        "You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)"
    )
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests"
    )
    sys.exit()

PROXIES = {}
TIMEOUT = 10


class Redgifs:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"content-type": "application/json; charset=UTF-8"}
        )

        self.session.proxies.update(PROXIES)

        self.getTemporaryToken()

    def log_session_headers(self):
        log.debug(self.session.headers)

    def GET_req(self, url):
        scraped = None
        try:
            scraped = self.session.get(url, timeout=TIMEOUT)
        except:
            log.error("scrape error")
            return None
        if scraped.status_code >= 400:
            log.error(f"HTTP Error: {scraped.status_code}")
            return None
        return scraped.content

    def GET_req_json(self, url):
        scraped = None
        try:
            scraped = self.session.get(url, timeout=TIMEOUT)
        except:
            log.error("scrape error")
            return None
        if scraped.status_code >= 400:
            log.error(f"HTTP Error: {scraped.status_code}")
            return None
        return scraped.json()

    def output_json(self, title, tags, url, b64img, performers, date):
        return {
            "title": title,
            "tags": [{"name": x} for x in tags],
            "url": url,
            "image": "data:image/jpeg;base64," + b64img.decode("utf-8"),
            "performers": [{"name": x.strip()} for x in performers],
            "date": date
        }

    def getTemporaryToken(self):
        req = self.GET_req_json("https://api.redgifs.com/v2/auth/temporary")

        authToken = req.get("token")

        self.session.headers.update(
            {"Authorization": 'Bearer ' + authToken,}
        )

        log.debug(req)

    def getIdFromUrl(self, url):
        id = url.split("/")
        id = id[-1]
        id = id.split("?")[0]

        return id;

    def getApiUrlFromId(self, id):
        return f"https://api.redgifs.com/v2/gifs/{id}?views=yes&users=yes"


    def getParseUrl(self, url):
        id = self.getIdFromUrl(url)
        return self.getParseId(id)

    def getParseId(self, id):
        id_lowercase = id.lower()

        log.debug(str(id))

        apiurl = self.getApiUrlFromId(id_lowercase)

        req = self.GET_req_json(apiurl)

        log.debug(req)

        gif = req.get("gif")
        user = req.get("user")

        tags = gif.get("tags")

        date = gif.get("createDate")
        date = datetime.fromtimestamp(date)
        date = str(date.date())

        imgurl = gif.get("urls").get("poster")
        img = self.GET_req(imgurl)
        b64img = base64.b64encode(img)

        studio_name = user.get("name")

        performers = []

        if user.get("name"):
            performers = [user.get("name")]
        elif user.get("username"):
            performers = [user.get("username")]


        return self.output_json(
            id, tags, f"https://www.redgifs.com/watch/{id}", b64img, performers, date
        )

def parseFilename(filename):
    id = filename.replace("redgifs_", "") #remove possible filename prefix
    id = id.split(".")[0] #remove file extension
    
    return id


FRAGMENT = json.loads(sys.stdin.read())

log.debug(FRAGMENT)

scraper = Redgifs()

result = ""

if sys.argv[1] == "url":
    url = FRAGMENT.get("url")

    log.debug(url)

    result = json.dumps(scraper.getParseUrl(url))
elif sys.argv[1] == "queryFragment" or sys.argv[1] == "fragment":
    id = parseFilename(FRAGMENT.get("title"))

    log.debug(id)

    result = json.dumps(scraper.getParseId(id))
elif sys.argv[1] == "name":
    id = parseFilename(FRAGMENT.get("name"))

    log.debug(id)

    result = json.dumps([scraper.getParseId(id)])

print(result)
