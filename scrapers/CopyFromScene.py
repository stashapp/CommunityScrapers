import json
import sys

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! "
        "(CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()


def get_names(data: list):
    return [{"name": i["name"]} for i in data if "name" in i]


def get_name(data: dict):
    if data and (data.get("name")):
        return {"name": data["name"]}
    return None


if sys.argv[1] == "gallery_query":
    fragment = json.loads(sys.stdin.read())
    log.debug("input: " + json.dumps(fragment))
    result = graphql.getGallery(fragment["id"])
    if not result:
        log.info(f"Could not determine details for gallery: `{fragment['id']}`")
        print("{}")
        sys.exit(0)

    if result["scenes"]:
        s = result["scenes"][0]
        log.debug("scene: " + json.dumps(s))
        res = {
            "title": s["title"],
            "details": s["details"],
            "urls": s["urls"],
            "date": s["date"],
            "studio": get_name(s["studio"]),
            "performers": get_names(s["performers"]),
            "tags": get_names(s["tags"]),
        }
        log.debug("output: " + json.dumps(res))
        print(json.dumps(res))
    else:
        print("{}")
