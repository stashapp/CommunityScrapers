import py_common.log as Log
import json
import sys
import re
from pathlib import Path

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

API_URL = "https://www.analvids.com/api/autocomplete/search"


def apiQuery(query):
    res = requests.get(
        f"{API_URL}?q={query}")
    data = res.json()
    results = data['terms']

    return results


def detectDelimiter(title):
    delimiters = [" ", "_", "-", "."]
    for d in delimiters:
        if d in title:
            return d

    Log.debug(f"Could not determine delimiter of `{title}`")


def parseSceneId(title, strict):
    # Remove file extension
    title = Path(title).stem
    title = title.replace("'", "")
    delimiter = detectDelimiter(title)
    parts = title.split(delimiter)
    for part in parts:
        if len(part) > 3:
            if re.match(r'^(\w{2,3}\d{3,4})$', part):
                if not part[0].isdigit() and part[-1].isdigit():
                    return part

    # if we're here, the previous method didn't work. Let's try to remove whitespaces and match the most common IDs
    title = title.replace(" ", "")
    if (strict):
        id = re.search("(GL|GIO|XF|SZ|GP|AA|RS|OB|BTG|EKS)\d{3}", title)
    else:
        id = re.search("(GL|GIO|XF|SZ|GP|AA|RS|OB|BTG|EKS)\d{3,4}", title)

    if id:
        return id.group()

    Log.debug(f"Could not determine scene id in title: `{title}`")


def scrapeScene(title):
    results = apiQuery(title)

    scenes = []

    for result in results:
        if result["type"] == "scene":
            Log.debug(f"Found scene {result['name']}")

            scene = {
                "url": result["url"],
                "title": result["name"]
            }
            scenes.append(scene)

    return scenes


def scrapePerformer(name):
    results = apiQuery(name)

    performers = []

    for result in results:
        if result["type"] != "model":
            continue

        performer = {
            "name": result['name'],
            "url": result['url']
        }
        performers.append(performer)

    return performers


def scrapeSceneByFragment(title):
    sceneId = parseSceneId(title, False)
    if sceneId is None:
        return

    scenes = scrapeScene(sceneId)
    if len(scenes) > 1:
        Log.debug("Found more than one scenes, returning the first")

    if len(scenes) >= 1:
        return scenes[0]

# We couldn't find a scene so let's try again with strict mode
    sceneId = parseSceneId(title, True)
    if sceneId is None:
        return

    scenes = scrapeScene(sceneId)
    if len(scenes) >= 1:
        return scenes[0]


###
### MAIN ###
###


query = sys.stdin.read()
fragment = json.loads(query)

Log.debug(fragment)

argument = sys.argv[1]

if argument == "scene":
    Log.debug("Scraping scene by fragment")

    scene = scrapeSceneByFragment(fragment["title"])

    Log.debug(scene)
    print(json.dumps(scene))

elif argument == "performer":
    Log.debug("Scraping performer")

    performers = scrapePerformer(fragment['name'])

    Log.info(performers)
    print(json.dumps(performers))

elif argument == "sceneName":
    Log.debug("Scraping scene by name")

    scene = scrapeScene(fragment["name"])

    Log.debug(scene)
    print(json.dumps(scene))

else:
    Log.warning(f"Script called with unknown argument {argument}")
