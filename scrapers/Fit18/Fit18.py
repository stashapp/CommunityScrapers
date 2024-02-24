import json
import os
import re
import sys
import urllib.parse
from urllib.parse import urlparse

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",file=sys.stderr)
    sys.exit()


class Site:

    def __init__(self, name: str):
        self.name = name
        self.homepage = "https://" + self.name.lower() + ".com"
        self.api = "https://" + self.name.lower() + ".team18.app/graphql"
        if name == "Fit18":
            self.api_key = "77cd9282-9d81-4ba8-8868-ca9125c76991"
        elif name == "Thicc18":
            self.api_key = "0e36c7e9-8cb7-4fa1-9454-adbc2bad15f0"

    def isValidURL(self, url: str):
        u = url.lower().rstrip("/")
        up = urlparse(u)
        if up.hostname is None:
            return False
        if up.hostname.lstrip("www.").rstrip(".com") == self.name.lower():
            splits = u.split("/")
            if len(splits) < 4:
                return False
            if splits[-2] == "videos":
                self.id = urllib.parse.unquote(url).split("/")[-1]
                ns = self.id.split(":")
                if len(ns) < 2:
                    return False
                self.number = ns[-1]
                return True
        return False

    def getScene(self, url: str):
        log.debug(f"Scraping using {self.name} graphql API")
        q = {"variables": {"videoId": self.id}, "query": self.getVideoQuery}
        r = self.callGraphQL(q)
        return self.parse_scene(r)

    def getImage(self, talentId: str):
        q = {
            "variables": {
                "paths": [
                    f"/members/models/{talentId}/scenes/{self.number}/videothumb.jpg"
                ]
            },
            "query": self.getAssetQuery
        }
        r = self.callGraphQL(q)
        if r:
            if r["asset"]["batch"].get("result"):
                if r["asset"]["batch"]["result"][0].get("serve"):
                    return r["asset"]["batch"]["result"][0]["serve"].get("uri")
        return None

    def callGraphQL(self, query: dict):
        headers = {
            "Content-type": "application/json",
            "argonath-api-key": self.api_key,
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
            "Origin": self.homepage,
            "Referer": self.homepage
        }

        try:
            response = requests.post(self.api,
                                     json=query,
                                     headers=headers,
                                     timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("error"):
                    for error in result["error"]["errors"]:
                        raise Exception(f"GraphQL error: {error}")
                if result.get("data"):
                    return result.get("data")
            elif response.status_code >= 400:
                sys.exit(f"HTTP Error {response.status_code}, {response.text}")
            else:
                raise ConnectionError(
                    f"GraphQL query failed:{response.status_code} - {response.text}"
                )
        except Exception as err:
            log.error(f"GraphqQL query failed {err}")
            return None

    def parse_scene(self, response):
        scene = {}
        if response is None or response.get('video') is None:
            return scene

        data = response["video"]["find"]["result"]
        if data:
            scene['title'] = data.get("title")
            if data.get("description"):
                d = None
                if data["description"].get("short"):
                    d = data["description"]["short"]
                if data["description"].get("long"):
                    d = data["description"]["long"]
                # Remove double space
                if d:
                    d = re.sub(r" +", " ", d).strip()
                    d = re.sub(r"^In 60FPS.\s*", "", d)
                scene['details'] = d

            perf_id = None
            if data.get("talent"):
                perf = None

                # There are no 2 performers in a scene so useless to deal with lists
                # performers = [x["talent"].get("name") for x in scene_info["talent"]]
                perf = data["talent"][0]["talent"].get("name")
                # Performer ID for getting the image
                perf_id = data["talent"][0]["talent"].get("talentId")
                if perf:
                    scene['performers'] = [{"name": perf}]

            scene['studio'] = {'name': self.name}
            if perf_id:
                scene['image'] = self.getImage(perf_id)

            return scene
        return None

    getVideoQuery = """
    query FindVideo($videoId: ID!) {
        video {
            find(input: { videoId: $videoId }) {
                result {
                    videoId
                    title
                    duration
                    description {
                        short
                        long
                    }
                    talent {
                        type
                        talent {
                            talentId
                            name
                        }
                    }
                }
            }
        }
    }
    """
    getAssetQuery = """
    query BatchFindAssetQuery($paths: [String!]!) {
        asset {
            batch(input: { paths: $paths }) {
                result {
                    path
                    mime
                    size
                    serve {
                        type
                        uri
                    }
                }
            }
        }
    }
    """


studios = {Site('Fit18'), Site('Thicc18')}
fragment = json.loads(sys.stdin.read())
url = fragment.get("url")

if url:
    for x in studios:
        if x.isValidURL(url):
            s = x.getScene(url)
            #log.debug(f"{json.dumps(s)}")
            print(json.dumps(s))
            sys.exit(0)

log.error(f"URL: {url} is not supported")
print("{}")
sys.exit(1)
