
import json
import requests
import sys

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

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
            res={"title":s["title"],"details":s["details"],"url":s["url"],"date":s["date"],"rating":s["rating"],"studio":s["studio"],"performers":s["performers"],"tags":s["tags"]}
            print (json.dumps(res))
        else:
            print ("{}")
