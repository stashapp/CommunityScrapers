import os
import sys
import json
import sqlite3
import mimetypes
import base64
import re
"""  
This script looks for image files in the directory of the scene's video file that have "cover" or "fanart" in the name and suggests these as scene cover.
"""

# Do the image files contain the video file name or are they named sparsely?
containVideoName = False

# Pattern to look for in order of priority
pattern = ["fanart", "cover", "poster", "landscape"]

# Delimiter before the pattern
delimiter = [""," ", "-", ".", "_"]

# Specify the file type of the image files
fileType = "jpg"

debug = False

def debug(s):
    if debug: print(s, file=sys.stderr)

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
    
def make_image_data_url(image_path):
    # type: (str,) -> str
    mime, _ = mimetypes.guess_type(image_path)
    with open(image_path, 'rb') as img:
        encoded = base64.b64encode(img.read()).decode()
    return 'data:{0};base64,{1}'.format(mime, encoded)
        
if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    res = {"title": fragment["title"]}
    
    # WORKAROUND: Read file name from db until filename is given in the fragment
    videoFilePath = get_file_path(fragment["id"])
    
    # Reconstruct possible file names based on provided pattern
    for p in pattern:
        # /data/Studio/Scene_cover.jpg
        if containVideoName:
            for d in delimiter:
                # Split and join file path so that file extention is gone. Then add delimiter, pattern and new file extention
                imageFilePath = ".".join(videoFilePath.split(".")[:-1]) + d + p + "." + fileType
                
                if os.path.isfile(imageFilePath):
                    debug("File " + imageFilePath + " exists!")
                    res["image"] = make_image_data_url(imageFilePath)
                    break
                debug("File " + imageFilePath + " doesn't exist!")
        else:
            imageFilePath = os.path.join(os.path.dirname(videoFilePath), p + "." + fileType)
            if os.path.isfile(imageFilePath):
                debug("File " + imageFilePath + " exists!")
                res["image"] = make_image_data_url(imageFilePath)
                break
            debug("File " + imageFilePath + " doesn't exist!")
    
    print(json.dumps(res))
    exit(0)
