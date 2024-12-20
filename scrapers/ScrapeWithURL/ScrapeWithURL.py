import json
import sys

import py_common.graphql as graphql
import py_common.log as log


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
    return (result or {}).get("scrapeSceneURL", None)


FRAGMENT = json.loads(sys.stdin.read())
url = FRAGMENT.get("url")

if url:
    result = scrape_scene(url)
    print(json.dumps(result))
else:
    print("null")
