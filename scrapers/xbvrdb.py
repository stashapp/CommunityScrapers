import json
import sys
import sqlite3
import os
import requests

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

# Set XBVR_HOST to your xbvr instance, if set to None it will use xbvr.db and query that instead
XBVR_HOST='http://192.168.0.35:9999'
#XBVR_HOST=None


''' This script uses the sqlite database from xbvr (3d porn manager) 
    Copy main.db from yout xbvr configuration and rename this to xbvr.db
    docker cp xbvr:/root/.config/xbvr/main.db xbvr.db
    This script needs python3 and sqlite3 
   '''
def lookup_scene(id):
    c=conn.cursor()
    c.execute('SELECT title,synopsis,site,cover_url,scene_url,date(release_date, "localtime") FROM scenes WHERE id=?',(id,))
    row=c.fetchone()
    res={}
    res['title']=row[0]
    res['details']=row[1]
    res['studio']={"name":row[2]}
    res['image']=row[3]
    res['url']=row[4]
    res['date']=row[5]
    c.execute("SELECT tags.name FROM scene_tags,tags WHERE scene_tags.tag_id=tags.id AND scene_tags.scene_id=? ;",(id,))
    row = c.fetchall()
    res['tags']=[{"name":x[0]} for x in row]
    c.execute("SELECT actors.name FROM scene_cast,actors WHERE actors.id=scene_cast.actor_id AND scene_cast.scene_id=? ;",(id,))
    row = c.fetchall()
    res['performers']=[{"name":x[0]} for x in row]
    return res

def find_scene_id(title):
    c = conn.cursor()
    c.execute('SELECT scene_id FROM files WHERE filename LIKE ?', (title,))
    id=c.fetchone()
    if id == None:
        c.execute('SELECT scene_id FROM files WHERE filename LIKE ?', (title+'____',))
        id=c.fetchone()
        if id is not None:
            return id[0]
        c.execute('SELECT id FROM scenes WHERE scene_id LIKE ?', (title,))
        id = c.fetchone()
        if id is not None:
            return id[0]
        if title.endswith(".zip"):
            title=title[:-4]
        if title.startswith("wankzvr-") or title.startswith("milfvr-") or title.startswith("povr-originals-"):
            # file names are in the format wankzvr-choosy-dads-choose-chu-46-hr-2400.zip  split on - and discard the first token and last 3
            t=title.split('-')[1:-3]
            if 's' in t:
                t.remove('s')
            if 't' in t:
                t.remove('t')
            if 'originals' in t:
                t.remove('originals')
            title='%'.join(t)+'%'
        c.execute('SELECT id FROM scenes WHERE title LIKE ?',(title+'%',))
        id=c.fetchone()
        if id is not None:
            return id[0]
    else:
        return id[0]
    return None

def query_api(filename):
    request_config={"dlState":"available","cardSize":"1","lists":[],"isAvailable":True,"isAccessible":True,"isHidden":False,"isWatched":None,"releaseMonth":"","cast":[],"sites":[],"tags":[],"cuepoint":[],"attributes":[],"volume":0,"sort":"release_desc","offset":0,"limit":1}
    response = requests.post(XBVR_HOST+'/api/scene/list', json=request_config)
    if response.status_code == 200:
        total_scenes = response.json()['results']
        log.debug('total scenes %s' % (total_scenes))
        request_config['limit'] = 500
        request_config['offset'] = 0
        while request_config['offset'] < total_scenes:
            response = requests.post(XBVR_HOST+'/api/scene/list', json=request_config)
            for s in response.json()['scenes']:
                for f in s['file']:
                    if f['filename'] == filename:

                       result={
                               'title':s['title'],
                               'details':s['synopsis'],
                               'studio':{'name':s['site']},
                               'image':s['cover_url'],
                               'url':s['scene_url'],
                               'date':s['release_date_text'],
                               'tags':[{"name":x['name']} for x in s['tags']],
                               'performers':[{"name":x['name']} for x in s['cast']]
                               }
                       log.debug(result)
                       print(json.dumps(result))
                       exit(0)
            request_config['offset'] = request_config['offset'] + request_config['limit']





if XBVR_HOST is not None:
    if sys.argv[1] == "query":
        fragment = json.loads(sys.stdin.read())
        response=graphql.getScene(fragment['id'])
        filename = os.path.basename(response['path'])
        query_api(filename)

    exit(0)

if not os.path.exists("xbvr.db"):
    print("Error, the sqlite database xbvr.db does not exist in the scrapers directory.",file=sys.stderr)
    print("Copy this database from the docker container and give it the name xbvr.db",file=sys.stderr)
    print("docker cp xbvr:/root/.config/xbvr/main.db xbvr.db",file=sys.stderr)
    exit(1)

conn = sqlite3.connect('xbvr.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    print(json.dumps(fragment),file=sys.stderr)
    response=graphql.getScene(fragment['id'])
    filename = os.path.basename(response['path'])
    scene_id=find_scene_id(filename)
    if scene_id:
        result=lookup_scene(scene_id)
        print(json.dumps(result))

        conn.close()
        exit(0)
    scene_id = find_scene_id(fragment['title'])
    if not scene_id:
        print(f"Could not determine scene id in title: `{fragment['title']}`",file=sys.stderr)
        print("{}")
    else:
        print(f"Found scene id: {scene_id}",file=sys.stderr)
        result=lookup_scene(scene_id)
        print(json.dumps(result))
    conn.close()
elif sys.argv[1] == "gallery_query":
    fragment= json.loads(sys.stdin.read())
    print(json.dumps(fragment),file=sys.stderr)
    scene_id = find_scene_id(fragment['title'])
    if not scene_id:
        print(f"Could not determine scene id in title: `{fragment['title']}`",file=sys.stderr)
        print("{}")
    else:
        print(f"Found scene id: {scene_id}",file=sys.stderr)
        result=lookup_scene(scene_id)
        result.pop("image",None)
        print(json.dumps(result))
    conn.close()
    
