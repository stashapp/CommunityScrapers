import sys
import pathlib

import mimetypes
import base64

import json
import xml.etree.ElementTree as ET

import py_common.graphql as graphql
import py_common.log as log

"""  
This script parses WDTV xml metadata files. 
The .xml file must be in the same directory as the video file and must be named exactly alike.

Code borrowed from the kodi nfo scraper (in https://github.com/stashapp/CommunityScrapers/pull/689)
It was found the .nfo files exported from Whisparr, did not contain all details required.
Using the WDTV format instead had all information. 

The intention is not to be a generic WDTV metadata parser, but one that specifically parses WDTV metadata from Whisparr. Based on version v2.0.0.168. This simplifies the integration of Whisparr and Stash.
"""
def query_xml(path, title):
    res = {"title": title}
    try:        
        tree = ET.parse(path)
    except Exception as e:
        log.error(f'xml parsing failed:{e}')
        print(json.dumps(res))
        exit(1)
    
    if title == tree.find("episode_name").text:
        log.info("Exact match found for " + title)
    else:
        log.info("No exact match found for " + title + ". Matching with " + tree.find("title").text + "!")
    
    # Extract matadata from xml
    if tree.find("episode_name") != None:
        res["title"] = tree.find("episode_name").text
    
    if tree.find("overview") != None:
        res["details"] = tree.find("overview").text
    
    if tree.find("firstaired") != None:
        res["date"] = tree.find("firstaired").text

    # This is based on how my version of Whisparr (v2.0.0.168) output the WDTV .xml
    # It seperated actors by " / " 
    # then for some reason had duplicated the name seperated by " - "
    if tree.find("actor") != None and tree.find("actor").text:
        res["performers"] = []
        for actor in tree.find("actor").text.split(" / "):
            res["performers"].append({"name": actor.split(" - ")[0]})
    
    if tree.find("series_name") != None:
        res["studio"] = {"name":tree.find("series_name").text}
    
    return res

if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    s_id = fragment.get("id")
    if not s_id:
        log.error(f"No ID found")
        sys.exit(1)
    
    # Assume that .xml is named exactly alike the video file and is at the same location
    # Query graphQL for the file path
    scene = graphql.getScene(s_id)
    if scene:
        scene_path = scene.get("path")
        if scene_path:
            p = pathlib.Path(scene_path)
            
            res = {"title": fragment["title"]}
            
            f = p.with_suffix(".xml")
            if f.is_file():
                res = query_xml(f, fragment["title"])
            else:
                log.info(f"No xml files found for the scene: {p}")
            
            print(json.dumps(res))
            exit(0)
