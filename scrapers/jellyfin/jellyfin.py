import os, urllib.parse, datetime
import sys
import json
import base64

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

# Fill in your jellyfin API-Key
api_key = "xxxxxxxxxxxxxxxxxxxxxxxxxx"
# Fill in the jellyfin user-id (extract from Jellyfin->Admin->User from the URL of the User)
userid = "xxxxxxxxxxxxxxxxxxxxxxxx"
# Fill in the Jellyfin Endpoint
host = "http://xxxxxxxxxxx:8096/"
stash_date = '%Y-%m-%d'

def get_image(url):
    dlimage = requests.request("GET", url)
    # Check whether we returned an Errormessage
    if dlimage.headers['Content-Type'].startswith('application/json'):
        return None
    # Encode Image with correct content-type
    b64img = base64.b64encode(dlimage.content)
    encodedImage = ("data:" + dlimage.headers['Content-Type'] + ";" + "base64," + b64img.decode('utf-8'))
    return encodedImage

def performer_query(query):
    log.debug(f"Querying for Performer {query}")
    # Make Actorname URL-Safe
    actor_urlde = urllib.parse.quote(query)
    # Construct URL
    get_url = host + 'emby/Persons/?SearchTerm=' + actor_urlde + '&api_key=' + api_key
    res = requests.get(url=get_url)
    list_actor = json.loads(res.text)
    if list_actor['TotalRecordCount'] > 0:
        performers=[]
        for i in range(len(list_actor["Items"])):
            log.debug(f"Found Performer {list_actor['Items'][i]['Name']}")
            perf = {}
            perf['name']=list_actor['Items'][i]['Name']
            perf['url']=host + 'emby/Persons/' + urllib.parse.quote(list_actor['Items'][i]['Name'])
            performers.append(perf)
    else:
        log.debug(f"Didn't find {query} in Querymode")
        return None

    return performers

def performer_fragment(query):
    log.debug(f"Searching Name Fragment for Performer {query}")
    # Make Actorname URL-Safe
    actor_urlde = urllib.parse.quote(query)
    # Construct URL
    get_url = host + 'emby/Persons/' + actor_urlde + '?api_key=' + api_key
    res = requests.get(url=get_url)
    list_actor = json.loads(res.text)
    if list_actor['MovieCount'] > 0:
        log.debug(f"Found Performer {list_actor['Name']}")
        perf = {}
        perf['name']=list_actor['Name']
        if 'PremiereDate' in list_actor:
            birthdate = datetime.datetime.strptime(list_actor['PremiereDate'][:-2], "%Y-%m-%dT%H:%M:%S.%f" ).strftime(stash_date)
            perf['birthdate']=birthdate
        if 'OriginalTitle' in list_actor:
            perf['aliases']=list_actor['OriginalTitle']
        if 'ProductionLocations' in list_actor:
            country = (list_actor['ProductionLocations'][0].split(',')[-1]).lstrip()
            perf['country']=country
        if list_actor['ExternalUrls']:
            perf['url']=list_actor['ExternalUrls'][0]['Url']
        actorimage=get_image(host + 'Items/' + list_actor['Id'] + '/Images/Primary/0?api_key=' + api_key)
        if actorimage:
            perf["images"]= []
            perf["images"].append(actorimage)
    else:
        log.debug(f"Didn't find {query} in Fragment Mode")
        return None

    return perf


def performer_url(query):
    log.debug(f"Getting Performer through URL: {query}")
    # Construct URL
    get_url = query + '?api_key=' + api_key
    res = requests.get(url=get_url)
    list_actor = json.loads(res.text)
    if list_actor['MovieCount'] > 0:
        log.debug(f"Found Performer {list_actor['Name']}")
        perf = {}
        perf['name']=list_actor['Name']
        if 'PremiereDate' in list_actor:
            birthdate = datetime.datetime.strptime(list_actor['PremiereDate'][:-2], "%Y-%m-%dT%H:%M:%S.%f" ).strftime(stash_date)
            perf['birthdate']=birthdate
        if 'OriginalTitle' in list_actor:
            perf['aliases']=list_actor['OriginalTitle']
        if 'ProductionLocations' in list_actor:
            country = (list_actor['ProductionLocations'][0].split(',')[-1]).lstrip()
            perf['country']=country
        if list_actor['ExternalUrls']:
            perf['url']=list_actor['ExternalUrls'][0]['Url']
        actorimage=host + 'Items/' + list_actor['Id'] + '/Images/Primary/0?api_key=' + api_key
        if actorimage:
            perf["images"]= []
            perf["images"].append(actorimage)
    else:
        log.debug(f"Didn't find URL {query} in Performer URL Mode")
        return None

    return perf

def scene_fragment(query):
    log.debug(f"Getting Scene Fragment through Name {query}")
    if '.' in query:
        scenename=query.rsplit('.', 1)[0]
    else:
        scenename=query
    scenename=urllib.parse.quote(scenename)
    log.debug(f"Cleaned up scenename is {scenename}")
    # Construct URL
    get_url = host + 'Items/?SearchTerm=' + scenename + '&Recursive=true&IncludeItemTypes=Movie&fields=Genres,Overview,Studios,People&UserId=' + userid + '&api_key=' + api_key
    res = requests.get(url=get_url)
    list_scenes = json.loads(res.text)
    if list_scenes['TotalRecordCount'] > 0:
        log.debug(f"Found Scene {list_scenes['Items'][0]['Name']}")
        scene = {}
        scene['title']=list_scenes['Items'][0]['Name']
        scene['url']=host + 'Users/' + userid + '/Items/' + list_scenes['Items'][0]['Id']
        movies=[]
        movie=movie_url(host + 'Users/' + userid + '/Items/' + list_scenes['Items'][0]['Id'])
        movies.append(movie)
        scene['movies']=movies
        if 'ProductionYear' in list_scenes['Items'][0]:
            date = datetime.datetime.strptime(str(list_scenes['Items'][0]['ProductionYear']), "%Y" ).strftime(stash_date)
            scene['date']=date
        if 'Overview' in list_scenes['Items'][0]:
            scene['details']=list_scenes['Items'][0]['Overview']
        if 'People' in list_scenes['Items'][0]:
            performers=[]
            for i in range(len(list_scenes['Items'][0]['People'])):
                if list_scenes['Items'][0]['People'][i]['Type']=='Actor':
                    performer = performer_fragment(list_scenes['Items'][0]['People'][i]['Name'])
                    performers.append(performer)
            scene['performers']=performers
        if 'GenreItems' in list_scenes['Items'][0]:
            tags=[]
            for i in range(len(list_scenes['Items'][0]['GenreItems'])):
                tag = {}
                tag['name']=list_scenes['Items'][0]['GenreItems'][i]['Name']
                tags.append(tag)
            scene['tags']=tags
        if 'Studios' in list_scenes['Items'][0]:
            try:
               studio = {}
               studio['name']=list_scenes['Items'][0]['Studios'][0]['Name']
               scene['studio']=studio
            except IndexError:
               scene['studio']= None
#Uncomment if you want to set the Cover Image from Jellyfin for the Scene
        #sceneimage=get_image(host + 'Items/' + list_scenes['Items'][0]['Id'] + '/Images/Primary/0?api_key=' + api_key)
        #if sceneimage:
        #     scene["image"]= sceneimage
    else:
        log.debug(f"Didn't find {query} in Fragment mode")
        return None

    return scene

def scene_url(query):
    log.debug(f"Getting Scene through URL {query}")
    # Construct URL
    get_url = query + '?api_key=' + api_key
    res = requests.get(url=get_url)
    list_scenes = json.loads(res.text)
    if list_scenes['Name']:
        log.debug(f"Found Scene {list_scenes['Name']}")
        scene = {}
        scene['title']=list_scenes['Name']
        scene['url']=host + 'Users/' + userid + '/Items/' + list_scenes['Id']
        movies=[]
        movie=movie_url(host + 'Users/' + userid + '/Items/' + list_scenes['Id'])
        movies.append(movie)
        scene['movies']=movies
        if 'ProductionYear' in list_scenes:
            date = datetime.datetime.strptime(str(list_scenes['ProductionYear']), "%Y" ).strftime(stash_date)
            scene['date']=date
        if 'Overview' in list_scenes:
            scene['details']=list_scenes['Overview']
        if 'People' in list_scenes:
            performers=[]
            for i in range(len(list_scenes['People'])):
                if list_scenes['People'][i]['Type']=='Actor':
                    performer = performer_fragment(list_scenes['People'][i]['Name'])
                    performers.append(performer)
            scene['performers']=performers
        if 'GenreItems' in list_scenes:
            tags=[]
            for i in range(len(list_scenes['GenreItems'])):
                tag = {}
                tag['name']=list_scenes['GenreItems'][i]['Name']
                tags.append(tag)
            scene['tags']=tags
        if 'Studios' in list_scenes:
            try:
               studio = {}
               studio['name']=list_scenes['Studios'][0]['Name']
               scene['studio']=studio
            except IndexError:
               scene['studio']= None
        #sceneimage=get_image(host + 'Items/' + list_scenes['Items'][0]['Id'] + '/Images/Primary/0?api_key=' + api_key)
        #if sceneimage:
        #     scene["image"]= sceneimage
    else:
        log.debug(f"Didn't find {query} in URL mode")
        return None

    return scene

def scene_query(query):
    if '.' in query:
        scenename=query.rsplit('.', 1)[0]
    else:
        scenename=query
    scenename=urllib.parse.quote(scenename)
    log.debug(f"Searching for Scene {scenename} in Query Mode")
    get_url = host + 'Items/?SearchTerm=' + scenename + '&Recursive=true&IncludeItemTypes=Movie&UserId=' + userid + '&api_key=' + api_key
    res = requests.get(url=get_url)
    list_scenes = json.loads(res.text)
    if list_scenes['TotalRecordCount'] > 0:
        scenes=[]
        for i in range(len(list_scenes['Items'])):
            log.debug(f"Found Scene {list_scenes['Items'][i]['Name']}")
            scene = {}
            scene['title']=list_scenes['Items'][i]['Name']
            scene['url']=host + 'Users/' + userid + '/Items/' + list_scenes['Items'][i]['Id']
            scenes.append(scene)
    else:
        log.debug(f"Didn't find Scene {query} in Query Mode")
        return None

    return scenes

def movie_url(query):
    # Construct URL
    get_url = query + '?api_key=' + api_key
    log.debug(f"Try to scrape Movie via URL {get_url}")
    res = requests.get(url=get_url)
    list_movie = json.loads(res.text)
    if list_movie['Name']:
        log.debug(f"Found movie {list_movie['Name']}")
        movie = {}
        movie['name']=list_movie['Name']
        movie['url']=host + 'Users/' + userid + '/Items/' + list_movie['Id']
        if 'RunTimeTicks' in list_movie:
            runtime= datetime.timedelta(seconds=(int(list_movie["RunTimeTicks"] / 10000000)))
            movie['duration']=str(runtime)
        if 'ProductionYear' in list_movie:
            date = datetime.datetime.strptime(str(list_movie['ProductionYear']), "%Y" ).strftime(stash_date)
            movie['date']=date
        if 'Overview' in list_movie:
            movie['synopsis']=list_movie['Overview']
        if 'People' in list_movie:
            for i in range(len(list_movie['People'])):
                if list_movie['People'][i]['Type']=='Director':
                    if not 'director' in movie:
                        movie['director']=director=list_movie['People'][i]['Name']
        if 'Studios' in list_movie:
            try:
               studio = {}
               studio['name']=list_movie['Studios'][0]['Name']
               movie['studio']=studio
            except IndexError:
               movie['studio']= None
        frontimage=get_image(host + 'Items/' + list_movie['Id'] + '/Images/Primary/0?api_key=' + api_key)
        if frontimage:
             movie["front_image"]= frontimage
    else:
        log.debug(f"Didn't Scrape Movie via URL {query}")
        return None

    return movie




# ===================================
if not len(sys.argv) > 1:
    print("Need an argument")
    sys.exit(0)

if sys.argv[1] == "queryperformer":
    fragment = json.loads(sys.stdin.read())
    ret=performer_query(fragment['name'])

if sys.argv[1] == "fragmentperformer":
    fragment = json.loads(sys.stdin.read())
    ret=performer_fragment(fragment['name'])

if sys.argv[1] == "urlperformer":
    fragment = json.loads(sys.stdin.read())
    ret=performer_url(fragment['url'])

if sys.argv[1] == "queryscene":
    fragment = json.loads(sys.stdin.read())
    ret=scene_query(fragment['name'])

if sys.argv[1] == "fragmentscene":
    fragment = json.loads(sys.stdin.read())
    ret=scene_fragment(fragment['title'])

if sys.argv[1] == "urlscene":
    fragment = json.loads(sys.stdin.read())
    ret=scene_url(fragment['url'])

if sys.argv[1] == "urlmovie":
    fragment = json.loads(sys.stdin.read())
    ret=movie_url(fragment['url'])

if sys.argv[1] == "validSearch":
    fragment = json.loads(sys.stdin.read())
    ret=scene_url(fragment['url'])

print(json.dumps(ret))

sys.exit(0)
