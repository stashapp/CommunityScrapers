import sys
import json
from urllib.parse import urlparse

import requests

from py_common.graphql import GRAPHQL_INTROSPECTION

# Static definition, used in the GraphQL request
site_ids = {
    'japanlust.com': 2,
    'honeytrans.com': 3,
    'lesworship.com': 4,
    'joibabes.com': 5,
    'povmasters.com': 8,
    'cuckhunter.com': 10,
    'nudeyogaporn.com': 11,
    'transroommates.com': 12
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

def __prefix(level_char):
    start_level_char = b'\x01'
    end_level_char = b'\x02'

    ret = start_level_char + level_char + end_level_char
    return ret.decode()

def __log(levelChar, s):
    if levelChar == "":
        return

    print(__prefix(levelChar) + s + "\n", file=sys.stderr, flush=True)

def log_trace(s):
    __log(b't', s)

def log_debug(s):
    __log(b'd', s)

def log_info(s):
    __log(b'i', s)

def log_warning(s):
    __log(b'w', s)

def log_error(s):
    __log(b'e', s)


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

        log_debug(json.dumps(result))

        if result.get("errors", None):
            for error in result["errors"]:
                raise Exception("GraphQL error: {}".format(error))
        if result.get("data", None):
            return result.get("data")
    else:
        raise ConnectionError(
            "GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(
                response.status_code, response.content, query, variables)
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
        log_error(f"Could not determine id for site {urlparse(url).netloc}")
        return None

    try:
        scene_id = int(urlparse(url).path.split('/')[2])
    except ValueError:
        log_error(f"No scene id found in url {url}")
        return None

    log_info(f"Scraping scene {scene_id}")

    variables = {
        'id': int(scene_id),
        'siteId': int(site_id)
    }

    try:
        result = call_graphql(query, variables)
    except ConnectionError as e:
        log_error(e)
        return None

    result = result.get('legacyScene')

    ret = {}

    ret['title'] = result.get('title')
    ret['details'] = result.get('summary')
    ret['studio'] = {'name': result.get('sites')[0].get('name')}
    ret['tags'] = [{'name': x.get('name')} for x in result.get('genres')]
    ret['performers'] = [{'name': x.get('stageName')} for x in result.get('actors')]
    ret['image'] = result.get('primaryPhotoUrl')
    ret['date'] = result.get('availableAt') and result.get('availableAt')[:10] \
        or result.get('createdAt') and result.get('createdAt')[:10]
    ret['code'] = str(result.get('id'))

    return ret


if sys.argv[1] == 'scrapeByURL':
    i = read_json_input()
    ret = get_scene(i.get('url'))
    print(json.dumps(ret))
