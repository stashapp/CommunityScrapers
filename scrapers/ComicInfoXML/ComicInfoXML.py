import json
import pathlib
import sys
import xml.etree.ElementTree as ET
import zipfile

import py_common.graphql as graphql
import py_common.log as log

"""
This script parses xml files for metadata

If your gallery is in a .cbz/.zip file, the .xml file must either be:
- the first .xml file inside of the .cbz/.zip
- be in the same directory as the .cbz/.zip and have the same name

If your gallery is a folder of loose files, the .xml file must be named ComicInfo.xml and be in the same directory as the gallery
"""


def query_xml(xml_file):
    try:
        tree = ET.parse(xml_file)
    except Exception as e:
        log.error(f"Failed to parse XML file: {e}")
        print("null")
        exit(1)

    scraped = {}

    if (node := tree.find("Title")) is not None and (title := node.text):
        scraped["title"] = title

    if (node := tree.find("Web")) is not None and (url := node.text):
        scraped["url"] = url

    if (node := tree.find("Summary")) is not None and (details := node.text):
        scraped["details"] = details.strip()

    if (node := tree.find("Released")) is not None and (date := node.text):
        scraped["date"] = date

    year = month = day = None
    if (node := tree.find("Year")) is not None:
        year = node.text
    if (node := tree.find("Month")) is not None:
        month = node.text
    if (node := tree.find("Day")) is not None:
        day = node.text

    if year and month and day:
        scraped["date"] = f"{year}-{month:>02}-{day:>02}"

    if (node := tree.find("Genre")) is not None and (tags := node.text):
        scraped["tags"] = [{"name": x} for x in tags.split(", ")]

    # Stash has no concept of Series so we include it as a custom tag
    if (node := tree.find("Series")) is not None and (series := node.text):
        scraped["tags"] = scraped.get("tags", []) + [
            {"name": f"Series/Parody: {series}"}
        ]

    if (node := tree.find("Characters")) is not None and (characters := node.text):
        scraped["performers"] = [{"name": x} for x in characters.split(", ")]

    if (node := tree.find("Writer")) is not None and (studio := node.text):
        scraped["studio"] = {"name": studio}

    return scraped


if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    if not (gallery_path := graphql.getGalleryPath(fragment["id"])):
        log.error(f"No gallery path found for gallery with ID {fragment['id']}")
        print("null")
        sys.exit(1)

    p = pathlib.Path(gallery_path)
    f = None

    log.debug(f"Searching for ComicInfo.xml based on gallery path: {p}")
    if p.suffix in (".cbz", ".zip"):
        log.debug("Gallery is an archive file")
        # Look inside the archive for the xml file
        archive = zipfile.ZipFile(p)
        if xmlfile := next((x for x in archive.namelist() if x.endswith(".xml")), None):
            log.debug(f"Found '{xmlfile}' inside '{archive.filename}'")
            f = archive.open(xmlfile)
    elif p.is_dir() and (xmlfile := p.resolve() / "ComicInfo.xml") and xmlfile.exists():
        log.debug(f"Found '{xmlfile}' in '{p}'")
        f = xmlfile.open()
    elif (xmlfile := p.with_suffix(".xml")) and xmlfile.exists():
        log.debug(f"Found '{xmlfile}' in the same directory as '{p}'")
        f = xmlfile.open()

    if not f:
        log.warning(f"No XML files found for the gallery: {p}")
        print("null")
        sys.exit()

    res = query_xml(f)
    print(json.dumps(res))
