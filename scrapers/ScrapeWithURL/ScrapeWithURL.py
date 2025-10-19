import json
import sys

import py_common.graphql as graphql
import py_common.log as log


def filter_nones(d):
    if isinstance(d, dict):
        return {k: filter_nones(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [filter_nones(v) for v in d]

    return d


def scrape_scene(url):
    query = """
query scrapeSceneURL($url: String!) {
    scrapeSceneURL(url: $url) {
        title
        details
        code
        date
        director
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
    return (result or {}).get("scrapeSceneURL", None)


FRAGMENT = json.loads(sys.stdin.read())
urls = FRAGMENT.get("urls")

for url in urls:
    if not url.startswith('http'):
      continue # skip urls that don't start with http
    else:
        try:
            result = scrape_scene(url)
            result = filter_nones(result)
            log.debug(f"result {result}")
            print(json.dumps(result))
            if result:
                break
        except Exception:
            continue
else:
    print("null")
