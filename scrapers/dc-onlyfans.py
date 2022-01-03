import json
import sys
import sqlite3
import requests
from os import path
from pathlib import Path


''' This script is a companion to the onlyfans data scraper by DIGITALCRIMINAL
    https://github.com/DIGITALCRIMINAL/OnlyFans
    This tool allows you to download data from onlyfans and saves some metadata on what it downloads.
    
    This script needs python3 and requests and sqlite3 
    If you have a password on your instance you need to specify the api key below by removing the # and adding the key.
   '''


headers = {
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Connection": "keep-alive",
#   "ApiKey":"xxxxxxxxxx",
    "DNT": "1"
}
graphql_api='http://localhost:9999/graphql'



def lookup_scene(file,db,parent):
    print(f"using database: {db.name}  {file.name}", file=sys.stderr)
    conn = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    c=conn.cursor()
    c.execute('select posts.post_id,posts.text,medias.link,posts.created_at from posts,medias where posts.post_id=medias.post_id and medias.filename=?',(file.name,))
    row=c.fetchone()
    res={}
    res['title']=str(parent.name)+ ' - '+row[3].strftime('%Y-%m-%d')
    res['details']=row[1]
    res['url']=row[2]
    res['date']=row[3].strftime('%Y-%m-%d')
    res['performers']=[{"name":parent.name}]
    return res

def findFilePath(id):
    json = {}
    json['query'] = """query FindScene($id: ID!, $checksum: String) {
  findScene(id: $id, checksum: $checksum) {
      id
      path
  }
}"""
    json['variables'] = {"id":id}

    # handle cookies
    response = requests.post(graphql_api, json=json, headers=headers)

    if response.status_code == 200:
        result = response.json()
        if result.get("error", None):
            for error in result["error"]["errors"]:
                print("GraphQL error: {}".format(error),file=sys.stderr)
                print("{}")
                sys.exit()
        if result.get("data", None):
            data=result.get("data")
            if "findScene" in data:
                return data["findScene"]["path"]
    print(f"Error connecting to api",file=sys.stderr)
    print("{}")
    sys.exit()

if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    print(json.dumps(fragment),file=sys.stderr)
    id=fragment['id']
    file=Path(findFilePath(id))

    p=file.parent
    while not (Path(p.root)==p):
        p=p.parent
        for child in p.iterdir():
            if child.is_dir():
                for c in child.iterdir():
                    if c.name== "user_data.db":
                        scene=lookup_scene(file,c,p)
                        print(json.dumps(scene))
                        sys.exit()
            if child.name=="user_data.db":
                scene = lookup_scene(file, child, p)
                print(json.dumps(scene))
                sys.exit()
    # not found return an empty map
    print("{}")