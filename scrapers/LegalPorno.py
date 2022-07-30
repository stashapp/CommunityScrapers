

import datetime
import difflib
import json
import sys
import re
from pathlib import Path

try:
    import py_common.log as Log
    import py_common.graphql as Stash
    import py_common.config as Config
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

# TODO: Don't kick people out if they don't have the thing
try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    print("You need to install the BS4 module", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install bs4", file=sys.stderr)
    sys.exit()

API_URL = "https://www.analvids.com/api/autocomplete/search"
SCENE_NAME_MATCH_THRESHOLD = 90

SCENE_ID_TAGS = "(GL|GIO|XF|SZ|GP|AA|RS|OB|BTG|EKS|VG)"
DATE_FORMAT = "%Y-%m-%d"


def getStashScenePerformers(sceneId):
    scene = Stash.getScene(sceneId)
    if scene is None:
        return

    performers = []

    for performer in scene["performers"]:
        performers.append(performer["name"])

    # filter duplicate names (sometimes Stash adds a performer twice on a scene)
    return list(dict.fromkeys(performers))


def apiQuery(query):
    response = requests.get(f"{API_URL}?q={query}")
    if response is None:
        return

    data = response.json()
    results = data['terms']

    return results


def getScenesFromPerformerPage(url):
    page = requests.get(url)
    if page is None:
        return

    soup = BeautifulSoup(page.text, "html.parser")
    scenesHTML = soup.find_all("div", {"class": "thumbnail-title gradient"})

    scenes = []

    for html in scenesHTML:
        scene = {
            "title": html.a.text,
            "url": html.a['href']
        }
        scenes.append(scene)

    return scenes


def getSceneFromURL(url):
    page = requests.get(url)
    if page is None:
        return

    soup = BeautifulSoup(page.text, "html.parser")

    descriptionHTML = soup.find(
        "dl", {"class": "dl-horizontal scene-description__column"}).find_all("div")

    performers = []
    for performerHTML in descriptionHTML[0].find_all("a"):
        text = performerHTML.text.strip()

        if "(" not in text:
            performer = {
                "name": performerHTML.text
            }
            performers.append(performer)

    tags = []
    for tag in descriptionHTML[1].find_all("a"):
        tags.append({"name": tag.text.strip()})

    details = descriptionHTML[2].find("dd")
    if details is not None:
        details = details.text.strip()

    title = soup.find("h1", {"class": 'watchpage-title'}).text.strip()

    studio = {
        "name": soup.find("a", {"class": "watchpage-studioname"}).text.strip()
    }

    image = soup.find("div", {"id": "player"})["style"]
    image = re.search('.+(https[^"]+).+', image)
    if image is not None:
        image = image.group(1)

    rawDate = soup.find("span", {"title": "Release date"}).text.strip()
    date = datetime.datetime.strptime(
        rawDate, "%Y-%m-%d").strftime(DATE_FORMAT)

    scene = {
        "url": url,
        "title": title,
        "date": date,
        "performers": performers,
        "details": details,
        "studio": studio,
        "image": image,
        "tags": tags
    }

    return scene


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
        id = re.search(SCENE_ID_TAGS + "\d{3}", title, re.IGNORECASE)
    else:
        id = re.search(SCENE_ID_TAGS + "\d{3,4}", title, re.IGNORECASE)

    if id:
        return id.group()

    Log.debug(f"Could not determine scene id in title: `{title}`")


def scrapeScene(title):
    results = apiQuery(title)

    scenes = []

    for result in results:
        if result["type"] == "scene":
            Log.debug(f"Found scene {result['name']}")

            scene = getSceneFromURL(result['url'])
            if scene is None:
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


def scrapeSceneById(title):
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
    if len(scenes) > 1:
        Log.debug("Found more than one scenes, returning the first")

    if len(scenes) >= 1:
        return scenes[0]


def parseDateFromTitle(title):
    date = re.search(
        "((19\d|20\d\d)|([0-3]\d))( |-|\.)(([0-3]\d)|[1-9])( |-|\.)(((19|20)\d\d)|([0-3]\d))", title)

    if date is not None:
        date = date.group()

    date = re.split("( |-|\.)", date)
    date = list(filter(lambda d: d.isdigit(), date))
    date = list(map(int, date))

    dates = []

    try:
        dates.append(datetime.datetime(date[0], date[1], date[2]))
    except:
        None

    try:
        dates.append(datetime.datetime(date[0], date[2], date[1]))
    except:
        None

    try:
        dates.append(datetime.datetime(date[2], date[1], date[0]))
    except:
        None

    try:
        dates.append(datetime.datetime(date[2], date[0], date[1]))
    except:
        None

    dates = list(map(lambda d: d.strftime(DATE_FORMAT), dates))

    return dates


def doScrapeSceneFragment(fragment):
    title = re.sub("((480|720|1080)p)|4K", "",
                   fragment["title"], flags=re.IGNORECASE)

# try scraping by ID; most accurate
    performerScene = scrapeSceneById(title)
    if performerScene is not None:
        return performerScene

# if ID failed, we get the performer name; sometimes Stash has it in metadata
    performers = getStashScenePerformers(fragment["id"])
    if len(performers) == 0:
        return

# Let's get the performer URL
    lpPerformer = scrapePerformer(performers[0])
    if len(lpPerformer) == 0:
        return

    performerUrl = lpPerformer[0]['url']
# And use it to get all the scenes this performer is in
    performerScenes = getScenesFromPerformerPage(performerUrl)

# Calculate how similar they are to the original title
    for performerScene in performerScenes:
        performerScene['match'] = difflib.SequenceMatcher(
            None, performerScene['title'].lower(), title.lower()).ratio()*100

    performerScenes.sort(key=lambda x: x["match"], reverse=True)

# If the match exceeds the threshold, we have our scene!
    if performerScenes[0]['match'] >= SCENE_NAME_MATCH_THRESHOLD:
        return getSceneFromURL(performerScenes[0]['url'])

    Log.debug(
        f"No scene meets diff threshold, closest is {performerScenes[0]['match']}% - {performerScenes[0]['title']}")

# Let's try to parse the scene date if it's on the title
    dates = parseDateFromTitle(title)
    if len(dates) == 0:
        return

    Log.debug(f"Got dates: {dates}")

# Now let's get the date for each performer scene, hopefully that will match the date we have
    for performerScene in performerScenes:
        sceneData = getSceneFromURL(performerScene['url'])
        Log.debug(f"Got scene data: {sceneData}")

        if any(sceneData['date'] in d for d in dates):
            return sceneData


#----------------------------------#
#               MAIN               #
#----------------------------------#
query = sys.stdin.read()
fragment = json.loads(query)

Log.debug(f"Fragment: {fragment}")

argument = sys.argv[1]

if argument == "scene":
    Log.debug("Scraping scene by fragment")

    performerScene = doScrapeSceneFragment(fragment)

    Log.debug(performerScene)
    print(json.dumps(performerScene))

elif argument == "performer":
    Log.debug("Scraping performer")

    performers = scrapePerformer(fragment['name'])

    Log.info(performers)
    print(json.dumps(performers))

elif argument == "sceneName":
    Log.debug("Scraping scene by name")

    performerScene = scrapeScene(fragment["name"])

    Log.debug(performerScene)
    print(json.dumps(performerScene))

else:
    Log.warning(f"Script called with unknown argument {argument}")
