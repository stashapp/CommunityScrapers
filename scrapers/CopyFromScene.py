import json
import requests
import sys

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

def get_names(data: list):
    kn = []
    if data:
        for i in data:
            if (i.get('name')):
                kn.append({"name": i['name']})
    return kn

def get_name(data: dict):
    if data and (data.get("name")):
        return { "name": data["name"] }
    return None

if sys.argv[1] == "gallery_query":
    fragment = json.loads(sys.stdin.read())
    log.debug("input: " + json.dumps(fragment))
    result=graphql.getGallery(fragment['id'])
    if not result:
        log.info(f"Could not determine details for gallery: `{fragment['id']}`")
        print("{}")
    else:
        if len(result["scenes"])  > 0:
            s=result["scenes"][0]
            log.debug("data: " + json.dumps(s))
            res={"title":s["title"],"details":s["details"],"url":s["url"],"date":s["date"],"studio":get_name(s["studio"]),"performers":get_names(s["performers"]),"tags":get_names(s["tags"])}
            print (json.dumps(res))
        else:
            print ("{}")
