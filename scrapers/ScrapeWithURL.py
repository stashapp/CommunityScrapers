import json
import sys

import py_common.graphql as graphql
import py_common.log as log

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
                    }
                }"""

    variables = {'url': url}
    result = call_graphql(query, variables)
    log.info("result %s" % str(result))
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
