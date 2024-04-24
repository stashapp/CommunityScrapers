import json
import os
import sys
import datetime

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from ther

## This scraper will assume that the JSON files are stored in the same directory as the video files,
## with the same name, but with a .json extension.  You can add a second directory to check
## for JSON files here.  JSON file names here must match the original media file name, but with a 
## .json extension.  JSON files will first be taken from the media's folder first, and if not 
## present there a suitably named JSON file in the below directory will be used.
alternateJsonDir = ''

try:
    from py_common import graphql
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()

def scene_from_json(js):
    scene_id = js["id"]
    scene_title = js["title"]
    response = graphql.callGraphQL(
        """
    query FilenameBySceneId($id: ID){
      findScene(id: $id){
        files {
          path
        }
      }
    }""",
        {"id": scene_id},
    )
    assert response is not None
    path = response["findScene"]["files"][0]["path"]
    mediaFile = os.path.basename(path)
    mediaDir  = os.path.dirname(path)
    jsonInfoFile = os.path.splitext(mediaFile)[0] + '.json'
    log.debug("[YT-dlp] JSon Info File Name " + jsonInfoFile)
    
    scene = {}

    if os.path.isfile(os.path.join(mediaDir,jsonInfoFile)):
        jsonInfoFile = os.path.join(mediaDir,jsonInfoFile)
    elif alternateJsonDir != '' and os.path.isfile(os.path.join(alternateJsonDir,jsonInfoFile)):
        jsonInfoFile = os.path.join(alternateJsonDir,jsonInfoFile)
    else:
        log.debug(f"[YT-dlp] No JSON file for {mediaFile} found")
        return(scene)
    log.debug(f"[YT-dlp] JSON file: {jsonInfoFile}")
    with open(jsonInfoFile,"r") as read_content:
        ytJson = json.load(read_content)

    scene['performers'] = []
    scene['tags'] = []
    if 'title' in ytJson:
        scene['title'] = ytJson['title']
    if 'thumbnail' in ytJson:
        scene['image'] = ytJson['thumbnail']
    if 'webpage_url' in ytJson:
        scene['url'] = ytJson['webpage_url']
    if 'cast' in ytJson:
        for actor in ytJson['cast']:
            scene['performers'].append({"name": actor})
    if 'tags' in ytJson:    
        for tag in ytJson['tags']:
            scene['tags'].append({"name": tag})
    if 'categories' in ytJson:
        for tag in ytJson['categories']:
            scene['tags'].append({"name": tag})
  
    tubesite = ytJson['extractor']   if 'extractor'   in ytJson  else "UNKNOWN"
    uploadOn = ytJson['upload_date'] if 'upload_date' in ytJson  else "UNKNOWN"
    uploadBy = ytJson['uploader']    if 'uploader'    in ytJson  else "UNKNOWN"
    
    if uploadOn != 'UNKNOWN':
       s = datetime.datetime.strptime(uploadOn,"%Y%m%d")
       uploadOn = s.strftime("%B %d, %Y") 

    scene['details'] = f"Uploaded to {tubesite} on {uploadOn} by {uploadBy}"

    return scene

input = sys.stdin.read()
js = json.loads(input)

if sys.argv[1] == "scene_from_json":
    log.debug("[YT-dlp] scene from JSON")
    ret = scene_from_json(js)
    log.debug(json.dumps(ret))
    print(json.dumps(ret))
