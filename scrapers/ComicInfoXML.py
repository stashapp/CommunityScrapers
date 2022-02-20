import sys
import json
import xml.etree.ElementTree as ET
import pathlib

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

"""
This script parses xml files for metadata. 
The .xml file must be in the same directory as the gallery files and named either ComicInfo.xml for loose files (folder full of jpg/png's) 
or the same name as the .cbz/.zip file
"""

def query_xml(gallery_path, title):
    res={"title":title}
    try:        
        tree=ET.parse(gallery_path)
    except Exception as e:
        log.error(f'xml parsing failed:{e}')
        print(json.dumps(res))
        exit(1)
    
    if tree.find("Title") != None:
        res["title"] = (tree.find("Title").text).title()

    if tree.find("Web") != None:
        res["url"] = tree.find("Web").text

    # if tree.find("Series") != None:
    #     Collection = tree.find("Series").text

    if tree.find("Summary") != None:
        res["details"] = tree.find("Summary").text

    if tree.find("Released") != None:
        res["date"] = tree.find("Released").text
  
    if tree.find("Genre") != None:
        if tree.find("Genre").text:

            # Need a more suitable spot for this but one doesn't really exist yet
            if tree.find("Series").text:
                split_tags = [t for x in tree.findall("Genre") for t in x.text.split(", ")]+[str("Series/Parody: " + tree.find("Series").text)]
            else:
                split_tags = [t for x in tree.findall("Genre") for t in x.text.split(", ")]

            if "tags" in res:
                res["tags"] += [{"name":x.title()} for x in split_tags]
            else:
                res["tags"] = [{"name":x.title()} for x in split_tags]
    
    if tree.find("Characters") != None:
        if tree.find("Characters").text:
            split_performers = [t for x in tree.findall("Characters") for t in x.text.split(", ")]
            if "performers" in res:
                res["performers"] += [{"name":x.title()} for x in split_performers]
            else:
                res["performers"] = [{"name":x.title()} for x in split_performers]

    if tree.find("Writer") != None:
        if tree.find("Writer").text:
            res["studio"] = {"name":tree.find("Writer").text}

    return res

if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    g_id = fragment.get("id")
    if not g_id:
        log.error(f"No ID found")
        sys.exit(1)

    gallery = graphql.getGalleryPath(g_id)
    if gallery:
        gallery_path = gallery.get("path")
        if gallery_path:
            p = pathlib.Path(gallery_path)
            
            res = {"title": fragment["title"]}
            # Determine if loose file format or archive such as .cbz or .zip
            if "cbz" in gallery_path or "zip" in gallery_path:
                 # Look for filename.xml where filename.(cbz|zip) is the gallery
                 f = p.with_suffix('.xml')
                 log.debug(f"Single File Format, using: {f}")
            else:
                # Use loose files format
                # Look for ComicInfo.xml in the gallery's folder
                f = pathlib.Path(p.resolve(),"ComicInfo.xml")
                log.debug(f"Folder format, using:{f}")

            if f.is_file():
                res = query_xml(f, fragment["title"])
            else:
                log.warning(f'No xml files found for the gallery: {p}')

            print(json.dumps(res))
            exit(0)
