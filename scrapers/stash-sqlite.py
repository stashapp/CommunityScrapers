import json
import sys
import sqlite3
from os import path 

''' This script uses the sqlite database from another stash database and allows you to parse performers
    Copy stash-go.sqlite to the scrapers directory
    This script needs python3 and sqlite3
    
    To support extracting images from the database we need to provide a url where these image are located.
    Stash allows you to serve custom files by adding a few lines to the configuration.
    This plugin will then export the performer images to that folder and add the url of that image in the response.
    
    Make the directory and add the following to config.yml configuration:
    custom_served_folders:
      /stash_sqlite: /root/.stash/stash_sqlite
   
    Make the directory /root/.stash/stash_sqlite or update the configuration with the path
    To enable this feature change enable_images to: True
   '''

http_prefix='http://127.0.0.1:9999/custom/stash_sqlite/'
image_output_dir='/root/.stash/stash_sqlite/'
enable_images=False

def query_performers(name):
    c = conn.cursor()
    c.execute('SELECT name FROM performers WHERE lower(name) like lower(?)',('%' + name + '%',))
    rec=[]
    for row in c.fetchall():
        res={}
        res['name']= row[0]
        rec.append(res)
    return rec

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
    if enable_images:
        performer_id=row[16]
        c.execute('select image from performers_image where performer_id=?',(performer_id,))
        row=c.fetchone()
        if row == None:
            return res
        with open("%s%d.jpg" % (image_output_dir,performer_id), 'wb') as file:
            file.write(row[0])
        res['image']="%s%d.jpg" % (http_prefix,performer_id)
    return res


if not path.exists("stash-go.sqlite"):
    print("Error, the sqlite database stash-go.sqlite does not exist in the scrapers directory.",file=sys.stderr)
    print("Copy this database from another stash instance and place this in the scrapers directory",file=sys.stderr)
    exit(1)


conn = sqlite3.connect('stash-go.sqlite',detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    print(json.dumps(fragment),file=sys.stderr)
    result = query_performers(fragment['name'])
    if not result:
        print(f"Could not determine details for performer: `{fragment['name']}`",file=sys.stderr)
        print("{}")
    else:
        print (json.dumps(result))
    conn.close()

if sys.argv[1] == "fetch":
    fragment = json.loads(sys.stdin.read())
    print(json.dumps(fragment),file=sys.stderr)
    result = fetch_performer_name(fragment['name'])
    if not result:
        print(f"Could not determine details for performer: `{fragment['name']}`",file=sys.stderr)
        print("{}")
    else:
        print (json.dumps(result))
    conn.close()
