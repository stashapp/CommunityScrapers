import base64
import imghdr
import json
import mimetypes
import sys
import sqlite3
from os import path

'''
This script uses the sqlite database from another stash database and allows you to parse performers
Copy stash-go.sqlite to the scrapers directory

This script needs python3
'''

def query_performers(name):
    c = conn.cursor()
    c.execute('SELECT name FROM performers WHERE lower(name) like lower(?)',('%' + name + '%',))
    rec=[]
    for row in c.fetchall():
        res={}
        res['name']= row[0]
        rec.append(res)
    return rec

def make_image_data_url(image_data):
    # type: (bytes,) -> str
    img_type = imghdr.what(None, h=image_data) or 'jpeg'
    mime = mimetypes.types_map.get('.' + img_type, 'image/jpeg')
    encoded = base64.b64encode(image_data).decode()
    return 'data:{0};base64,{1}'.format(mime, encoded)

def fetch_performer_name(name):
    c = conn.cursor()
    c.execute('SELECT name,gender,url,twitter,instagram,date(birthdate),ethnicity,country,eye_color,height,measurements,fake_tits,career_length,tattoos,piercings,aliases,id FROM performers WHERE lower(name) = lower(?)', (name,))

    row =c.fetchone()
    res={}
    if row == None:
       return res
    res['name']= row[0]
    res['gender']=row[1]
    res['url']=row[2]
    res['twitter']=row[3]
    res['instagram']=row[4]
    res['birthdate']=row[5]
    res['ethnicity']=row[6]
    res['country']=row[7]
    res['eye_color']=row[8]
    res['height']=row[9]
    res['measurements']=row[10]
    res['fake_tits']=row[11]
    res['career_length']=row[12]
    res['tattoos']=row[13]
    res['piercings']=row[14]
    res['aliases']=row[15]

    performer_id=row[16]
    c.execute('select image from performers_image where performer_id=?',(performer_id,))
    row=c.fetchone()
    if row == None:
        return res

    image = make_image_data_url(row[0])
    res['images']=[image]

    return res


if not path.exists("stash-go.sqlite"):
    print("Error, the sqlite database stash-go.sqlite does not exist in the scrapers directory.",file=sys.stderr)
    print("Copy this database from another stash instance and place this in the scrapers directory",file=sys.stderr)
    exit(1)


conn = sqlite3.connect('stash-go.sqlite',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    print("input: " + json.dumps(fragment),file=sys.stderr)
    result = query_performers(fragment['name'])
    if not result:
        print(f"Could not determine details for performer: `{fragment['name']}`",file=sys.stderr)
        print("{}")
    else:
        print (json.dumps(result))
    conn.close()

if sys.argv[1] == "fetch":
    fragment = json.loads(sys.stdin.read())
    print("input: " + json.dumps(fragment),file=sys.stderr)
    result = fetch_performer_name(fragment['name'])
    if not result:
        print(f"Could not determine details for performer: `{fragment['name']}`",file=sys.stderr)
        print("{}")
    else:
        print (json.dumps(result))
    conn.close()

# Last Updated March 31, 2021
