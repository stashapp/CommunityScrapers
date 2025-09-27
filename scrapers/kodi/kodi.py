import sys
import pathlib

import mimetypes
import base64

import json
import xml.etree.ElementTree as ET

import py_common.graphql as graphql
import py_common.log as log
from py_common.util import scraper_args

"""  
This script parses kodi nfo files for metadata. The .nfo file must be in the same directory as the video file and must be named exactly alike.
"""

# If you want to ingest image files from the .nfo the path to these files may need to be rewritten. Especially when using a docker container.
rewriteBasePath = False
# Example: Z:\Videos\Studio_XXX\example_cover.jpg -> /data/Studio_XXX/example_cover.jpg
basePathBefore = 'Z:\Videos'
basePathAfter = "/data"

def query_xml(path, title):
    res = {"title": title}
    try:
        tree = ET.parse(path)
    except Exception as e:
        log.error(f'xml parsing failed:{e}')
        print(json.dumps(res))
        exit(1)
    
    if title == tree.find("title").text:
        log.info("Exact match found for " + title)
    else:
        log.info("No exact match found for " + title + ". Matching with " + tree.find("title").text + "!")
    
    # Extract matadata from xml
    if tree.find("title") != None:
        res["title"] = tree.find("title").text
    
    if tree.find("plot") != None:
        res["details"] = tree.find("plot").text
    
    if tree.find("releasedate") != None:
        res["date"] = tree.find("releasedate").text
    
    if tree.find("tag") != None:
        res["tags"]=[{"name":x.text} for x in tree.findall("tag")]
    if tree.find("genre") != None:
        if "tags" in res:
            res["tags"] += [{"name":x.text} for x in tree.findall("genre")]
        else:
            res["tags"] = [{"name":x.text} for x in tree.findall("genre")]
    
    if tree.find("actor") != None:
        res["performers"] = []
        for actor in tree.findall("actor"):
            if actor.find("type") != None:
                if actor.find("type").text == "Actor":
                    res["performers"].append({"name": actor.find("name").text})
            elif actor.find("name") != None:
                res["performers"].append({"name": actor.find("name").text})
            else:
                res["performers"].append({"name": actor.text})
    
    if tree.find("studio") != None:
        res["studio"] = {"name":tree.find("studio").text}
    
    if tree.find("art") != None:
        if tree.find("art").find("poster") != None:
            posterElem = tree.find("art").find("poster")
            if posterElem.text != None:
                if not rewriteBasePath and pathlib.Path(posterElem.text).is_file():
                    res["image"] = make_image_data_url(posterElem.text)
                elif rewriteBasePath:
                    rewrittenPath = posterElem.text.replace(basePathBefore, basePathAfter).replace("\\", "/")
                    if pathlib.Path(rewrittenPath).is_file():
                        res["image"] = make_image_data_url(rewrittenPath)
                    else:
                        log.warning("Can't find image: " + posterElem.text.replace(basePathBefore, basePathAfter) + ". Is the base path correct?")
                else:
                    log.warning("Can't find image: " + posterElem.text + ". Are you using a docker container? Maybe you need to change the base path in the script file.")
    return res

def make_image_data_url(image_path):
    # type: (str,) -> str
    mime, _ = mimetypes.guess_type(image_path)
    with open(image_path, 'rb') as img:
        encoded = base64.b64encode(img.read()).decode()
    return 'data:{0};base64,{1}'.format(mime, encoded)

def scene_by_fragment(fragment: dict):
    # Assume that .nfo/.xml is named exactly alike the video file and is at the same location
    # Query graphQL for the file path
    s_id = fragment.get("id")
    if not s_id:
        log.error(f"No ID found")
        sys.exit(1)
    scene = graphql.getScene(s_id)
    if scene:
        scene_path = scene.get("path")
        if scene_path:
            p = pathlib.Path(scene_path)
            
            res = {"title": fragment["title"]}
            
            f = p.with_suffix(".nfo")
            if f.is_file():
                res = query_xml(f, fragment["title"])
            else:
                log.info(f"No nfo/xml files found for the scene: {p}")
            return res

if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "scene-by-fragment", fragment:
            result = scene_by_fragment(fragment)
        case _:
            log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps(result))