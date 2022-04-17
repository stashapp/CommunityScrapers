import json
import sys

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

def call_graphql(query, variables=None):
    return graphql.callGraphQL(query, variables)

def scrape_scene(url):
    query = """query scrapeSceneURL($url: String!) {
                  scrapeSceneURL(url: $url) {
                        title
                        details
                        date
                        image
                        studio {
                            name
                        }
                        tags {
                            name
                        }
                        performers {
                            name
                        }
                        url
                    }
                }"""

    variables = {'url': url}
    result = call_graphql(query, variables)
    log.debug(f"result {result}")
    return result["scrapeSceneURL"]


FRAGMENT = json.loads(sys.stdin.read())
SCENE_ID = FRAGMENT.get("id")

scene = graphql.getScene(SCENE_ID)
if scene:
    scene_url = scene['url']

    if scene_url:
        result = scrape_scene(scene_url)
        print(json.dumps(result))
    else:
        print(json.dumps({}))
