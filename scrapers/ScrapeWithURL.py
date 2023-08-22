import json
import sys

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()


def call_graphql(query, variables=None):
    return graphql.callGraphQL(query, variables)


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
    result = call_graphql(query, variables)
    log.debug(f"result {result}")
    return result["scrapeSceneURL"]


FRAGMENT = json.loads(sys.stdin.read())
url = FRAGMENT.get("url")

if url:
    result = scrape_scene(url)
    print(json.dumps(result))
else:
    print(json.dumps({}))
