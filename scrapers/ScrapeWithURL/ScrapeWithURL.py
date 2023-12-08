import json
import os
import sys

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from ther

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()


def scrape_scene(url):
    query = """
query scrapeSceneURL($url: String!) {
    scrapeSceneURL(url: $url) {
        title
        details
        code
        date
        image
        urls
        studio {
            name
            url
            image
            parent {
                name
                url
                image
            }
        }
        tags {
            name
        }
        performers {
            aliases
            birthdate
            career_length
            country
            death_date
            details
            ethnicity
            eye_color
            fake_tits
            gender
            hair_color
            height
            instagram
            images
            measurements
            name
            piercings
            tags {
                name
            }
            tattoos
            twitter
            url
            weight
        }
    }
}"""

    variables = {"url": url}
    result = graphql.callGraphQL(query, variables)
    log.debug(f"result {result}")
    if result:
        return result["scrapeSceneURL"]


FRAGMENT = json.loads(sys.stdin.read())
url = FRAGMENT.get("url")

if url:
    result = scrape_scene(url)
    print(json.dumps(result))
else:
    print("null")
