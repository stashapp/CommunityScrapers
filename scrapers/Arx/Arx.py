import json
import sys
from urllib.parse import urlparse

import requests

from py_common import log

# Static definition, used in the GraphQL request
site_ids = {
    'japanlust.com': 2,
    'honeytrans.com': 3,
    'lesworship.com': 4,
    'joibabes.com': 5,
    'povmasters.com': 8,
    'cuckhunter.com': 10,
    'nudeyogaporn.com': 11,
    'transroommates.com': 12,
    'transmidnight.com': 14,
    'transdaylight.com': 15
}

# Timeout (seconds) to prevent indefinite hanging
API_TIMEOUT = 10

# GraphQL API endpoint
ENDPOINT = "https://arwest-api-production.herokuapp.com/graphql"

# Request headers
headers = {
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0",
    "Host": "arwest-api-production.herokuapp.com",
    "Origin": "https://lesworship.com",
    "Referer": "https://lesworship.com"
}


def read_json_input():
    json_input = sys.stdin.read()
    return json.loads(json_input)


def call_graphql(query, variables=None):
    # if the graphQL API changes, uncomment the following to discover available
    # API fields, queries, etc.
    # query = GRAPHQL_INTROSPECTION

    graphql_json = {'query': query}
    if variables is not None:
        graphql_json['variables'] = variables

    response = requests.post(ENDPOINT, json=graphql_json, headers=headers, timeout=API_TIMEOUT)

    if response.status_code == 200:
        result = response.json()

        log.debug(json.dumps(result))

        if result.get("errors", None):
            for error in result["errors"]:
                raise RuntimeError(f"GraphQL error: {error}")
        if result.get("data", None):
            return result.get("data")
    else:
        raise ConnectionError(
            f"GraphQL query failed:{response.status_code} - {response.content}. "
            f"Query: {query}. Variables: {variables}"
        )


def get_scene(url):
    # Sending the full query that gets used in the regular frontend
    query = """
        query 
            Scene($id: Int!, $siteId: Int) {  
                legacyScene(id: $id, siteId: $siteId) 
                {    
                    ...sceneFullFields    
                    __typename  
                }
            }
            fragment sceneFullFields on Scene {
                id  
                title  
                durationText  
                quality  
                thumbnailUrl  
                primaryPhotoUrl  
                url  
                createdAt  
                summary  
                photoCount  
                photoThumbUrlPath  
                photoFullUrlPath  
                isAvailable  
                availableAt  
                metadataTitle  
                metadataDescription  
                downloadPhotosUrl  
                actors {    
                    id    
                    stageName    
                    url    
                    __typename  
                }  
                genres {    
                    id    
                    name    
                    slug    
                    __typename  
                }  
                videoUrls {    
                    trailer    
                    full4k    
                    fullHd    
                    fullLow    
                    __typename  
                }  
                sites {    
                    id    
                    name    
                    __typename  
                }  
                __typename
            }
    """

    site_id = site_ids.get(urlparse(url).netloc)
    if site_id is None:
        log.error(f"Could not determine id for site {urlparse(url).netloc}")
        return None

    try:
        scene_id = int(urlparse(url).path.split('/')[2])
    except ValueError:
        log.error(f"No scene id found in url {url}")
        return None

    log.info(f"Scraping scene {scene_id}")

    variables = {
        'id': int(scene_id),
        'siteId': int(site_id)
    }

    try:
        legacy_scene = call_graphql(query, variables)
    except ConnectionError as e:
        log.error(e)
        return None

    legacy_scene = legacy_scene.get('legacyScene')

    scraped_scene = {}

    scraped_scene['title'] = legacy_scene.get('title')
    scraped_scene['details'] = legacy_scene.get('summary')
    scraped_scene['studio'] = {'name': legacy_scene.get('sites')[0].get('name')}
    scraped_scene['tags'] = [{'name': x.get('name')} for x in legacy_scene.get('genres')]
    scraped_scene['performers'] = [{'name': x.get('stageName')} for x in legacy_scene.get('actors')]
    scraped_scene['image'] = legacy_scene.get('primaryPhotoUrl')
    if (date := legacy_scene.get('availableAt')):
        scraped_scene['date'] = date[:10]
    elif (date := legacy_scene.get('createdAt')):
        scraped_scene['date'] = date[:10]
    scraped_scene['code'] = str(legacy_scene.get('id'))

    return scraped_scene


if sys.argv[1] == 'scrapeByURL':
    i = read_json_input()
    ret = get_scene(i.get('url'))
    print(json.dumps(ret))
