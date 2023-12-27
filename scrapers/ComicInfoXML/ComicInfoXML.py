import json
import os
import pathlib
import sys
import xml.etree.ElementTree as ET

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()

"""
This script parses xml files for metadata. 
The .xml file must be in the same directory as the gallery files and named either ComicInfo.xml for loose files (folder full of jpg/png's) 
or the same name as the .cbz/.zip file
"""


def query_xml(gallery_path, title):
    res = {"title": title}
    try:
        tree = ET.parse(gallery_path)
    except Exception as e:
        log.error(f"xml parsing failed:{e}")
        print("null")
        exit(1)

    if (node := tree.find("Title")) is not None and (title := node.text):
        res["title"] = title

    if (node := tree.find("Web")) is not None and (url := node.text):
        res["url"] = url

    if (node := tree.find("Summary")) is not None and (details := node.text):
        res["details"] = details

    if (node := tree.find("Released")) is not None and (date := node.text):
        res["date"] = date

    year = month = day = None
    if (node := tree.find("Year")) is not None:
        year = node.text
    if (node := tree.find("Month")) is not None:
        month = node.text
    if (node := tree.find("Day")) is not None:
        day = node.text

    if year and month and day:
        res["date"] = f"{year}-{month:>02}-{day:>02}"

    if (node := tree.find("Genre")) is not None and (tags := node.text):
        res["tags"] = [{"name": x} for x in tags.split(", ")]

    if (node := tree.find("Series")) is not None and (series := node.text):
        res["tags"] = res.get("tags", []) + [{"name": f"Series/Parody: {series}"}]

    if (node := tree.find("Characters")) is not None and (characters := node.text):
        res["performers"] = [{"name": x} for x in characters.split(", ")]

    if (node := tree.find("Writer")) is not None and (studio := node.text):
        res["studio"] = {"name": studio}

    return res


if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    if not (gallery_path := graphql.getGalleryPath(fragment["id"])):
        log.error(f"No gallery path found for gallery with ID {fragment['id']}")
        print("null")
        sys.exit(1)

    p = pathlib.Path(gallery_path)
    # Determine if loose file format or archive such as .cbz or .zip
    if "cbz" in gallery_path or "zip" in gallery_path:
        # Look for filename.xml where filename.(cbz|zip) is the gallery
        f = p.with_suffix(".xml")
        log.debug(f"Single File Format: trying '{f}'")
    else:
        # Use loose files format
        # Look for ComicInfo.xml in the gallery's folder
        f = p.resolve() / "ComicInfo.xml"
        log.debug(f"Folder format: trying '{f}'")

    if not f.is_file():
        log.warning(f"No xml files found for the gallery: {p}")
        print("null")
        sys.exit(1)

    res = query_xml(f, fragment["title"])
    print(json.dumps(res))
