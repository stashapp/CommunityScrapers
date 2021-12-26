import os
import sys
import json
import sqlite3
import mimetypes
import base64
import xml.etree.ElementTree as ET
"""
This script parses xml files for metadata. The .xml file must be in the same directory as the gallery files and named either ComicInfo.xml for loose files (folder full oj jpg/png's) or the same name as the .cbz/.zip file
"""
debug = False

def query_xml(path, title):
    tree=ET.parse(path)
    res={"title":title}
    if tree.find("Title") != None:
        res["title"] = tree.find("Title").text

    if tree.find("Web") != None:
        res["url"] = tree.find("Web").text

    if tree.find("Summary") != None:
        res["details"] = tree.find("Summary").text

    if tree.find("Released") != None:
        res["date"] = tree.find("Released").text
    
    if tree.find("Genre") != None:
        if tree.find("Genre").text:
            new_tags = [t for x in tree.findall("Genre") for t in x.text.split(", ")]
            if "tags" in res:
                res["tags"] += [{"name":x} for x in new_tags]
            else:
                res["tags"] = [{"name":x} for x in new_tags]

    if tree.find("Writer") != None:
        if tree.find("Writer").text:
            res["studio"] = {"name":tree.find("Writer").text}

    return res

def debug(s):
    if debug: print(s, file=sys.stderr)

def get_file_path(gallery_id):
    db_file = "../stash-go.sqlite"

    con = sqlite3.connect(db_file)
    cur = con.cursor()
    for row in cur.execute("SELECT * FROM galleries where id = " + str(gallery_id) + ";"):
        filepath = row[1]
    con.close()
    return filepath

if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    res = {"title": fragment["title"]}
    videoFilePath = get_file_path(fragment["id"])

    # Check for an xml file that exists in the same folder with the same name as the .cbz or .zip
    if "cbz" in videoFilePath:
        temp = videoFilePath.rsplit('/', 1)
        temp[-1] = "ComicInfo.xml"
        xmlFilePath = "/".join(temp)
        debug("CBZ Format, using: " + xmlFilePath)
    elif "zip" in videoFilePath:
        temp = videoFilePath.rsplit('/', 1)
        temp[-1] = "ComicInfo.xml"
        xmlFilePath = "/".join(temp)
        debug("ZIP Format, using: " + xmlFilePath)
    else:
        # Use loose files format
        xmlFilePath = videoFilePath+"/ComicInfo.xml"
        debug("Folder format, using: " + xmlFilePath)

    if os.path.isfile(xmlFilePath):
        res = query_xml(xmlFilePath, fragment["title"])
    else:
        debug("No file found at: " + xmlFilePath)

    print(json.dumps(res))
    exit(0)