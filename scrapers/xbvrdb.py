import json
import sys
import sqlite3
from os import path

''' This script uses the sqlite database from xbvr (3d porn manager) 
    Copy main.db from yout xbvr configuration and rename this to xbvr.db
    docker cp xbvr:/root/.config/xbvr/main.db xbvr.db
    This script needs python3 and sqlite3 
   '''
def lookup_scene(id):
    c=conn.cursor()
    c.execute('select title,synopsis,site,cover_url,scene_url,date(release_date) from scenes where id=?',(id,))
    row=c.fetchone()
    res={}
    res['title']=row[0]
    res['details']=row[1]
    res['studio']={"name":row[2]}
    res['image']=row[3]
    res['url']=row[4]
    res['date']=row[5]
    c.execute("select tags.name from scene_tags,tags where scene_tags.tag_id=tags.id and scene_tags.scene_id=? ;",(id,))
    row = c.fetchall()
    res['tags']=[{"name":x[0]} for x in row]
    c.execute("select actors.name from scene_cast,actors where actors.id=scene_cast.actor_id and scene_cast.scene_id=? ;",(id,))
    row = c.fetchall()
    res['performers']=[{"name":x[0]} for x in row]
    return res

def find_scene_id(title):
    c = conn.cursor()
    c.execute('SELECT scene_id FROM files WHERE filename=?', (title,))
    id=c.fetchone()
    if id == None:
        c.execute('select id from scenes where title=?',(title,))
        id=c.fetchone()
        return id[0]
    return id[0]

if not path.exists("xbvr.db"):
    print("Error, the sqlite database xbvr.db does not exist in the scrapers directory.",file=sys.stderr)
    print("Copy this database from the docker container and give it the name xbvr.db",file=sys.stderr)
    print("docker cp xbvr:/root/.config/xbvr/main.db xbvr.db",file=sys.stderr)
    exit(1)


conn = sqlite3.connect('xbvr.db',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    print(json.dumps(fragment),file=sys.stderr)
    scene_id = find_scene_id(fragment['title'])
    if not scene_id:
        print(f"Could not determine scene id in title: `{fragment['title']}`",file=sys.stderr)
    else:
        print(f"Found scene id: {scene_id}",file=sys.stderr)
        result=lookup_scene(scene_id)
        print(json.dumps(result))
    conn.close()
