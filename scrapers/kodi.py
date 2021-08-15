import os
import sys
import json
import sqlite3
import xml.etree.ElementTree as ET
'''  
This script parses kodi nfo files for metadata. The .nfo file must be in the same directory as the video file and must be named exactly alike.
'''

def query_xml(path, title):
    tree=ET.parse(path)
    # print(tree.find('title').text, file=sys.stderr)
    if title == tree.find('title').text:
        debug('Exact match found for ' + title)
    else:
        ebug('No exact match found for ' + title + ". Matching with " + tree.find('title').text + "!")
    
    # Extract matadata from xml
    res={'title':title}
    if tree.find('title') != None:
        res['title'] = tree.find('title').text
    if tree.find('plot') != None:
        res['details'] = tree.find('plot').text
    if tree.find('releasedate') != None:
        res['date'] = tree.find('releasedate').text
    if tree.find('tag') != None:
        res['tags']=[{"name":x.text} for x in tree.findall('tag')]
    if tree.find('genre') != None:
        if res['tags'] is not None:
            res['tags'] += [{"name":x.text} for x in tree.findall('genre')]
        else:
            res['tags'] = [{"name":x.text} for x in tree.findall('genre')]

    print(json.dumps(res))
    exit(0)

def debug(s):
    print(s, file=sys.stderr)

# Would be nicer with Stash API instead of direct SQlite access
def get_file_path(scene_id):
    db_file = "../stash-go.sqlite"

    con = sqlite3.connect(db_file)
    cur = con.cursor()
    for row in cur.execute("SELECT * FROM scenes where id = " + str(scene_id) + ";"):
        #debug_print(row)
        filepath = row[1]
    con.close()
    return filepath

def lookup_xml(path, title):
    # FEATURE: Add more path variantions here to allow for /metadata/ subfolder
    if os.path.isfile(path):
        query_xml(path, title)
    else:
        debug("No file found at" + path)
        
if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    
    # Assume that .nfo is named exactly like the video file and is at the same location
    # WORKAROUND: Read file name from db until filename is given in the fragment
    videoFilePath = get_file_path(fragment['id'])
    
    # Reconstruct file name for .nfo
    temp = videoFilePath.split('.')
    temp[-1] = 'nfo'
    nfoFilePath = '.'.join(temp)
    
    lookup_xml(nfoFilePath, fragment['title'])
    print(json.dumps(fragment))
    
# Last Updated August 15, 2021
