import requests
import sys
import json
from urllib.parse import urlparse

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

# GraphQL API endpoint
endpoint = "https://arwest-api-production.herokuapp.com/graphql"

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

def __prefix(levelChar):
    startLevelChar = b'\x01'
    endLevelChar = b'\x02'

    ret = startLevelChar + levelChar + endLevelChar
    return ret.decode()

def __log(levelChar, s):
    if levelChar == "":
        return

    print(__prefix(levelChar) + s + "\n", file=sys.stderr, flush=True)

def LogTrace(s):
    __log(b't', s)

def LogDebug(s):
    __log(b'd', s)

def LogInfo(s):
    __log(b'i', s)

def LogWarning(s):
    __log(b'w', s)

def LogError(s):
    __log(b'e', s)


def readJSONInput():
    input = sys.stdin.read()
    return json.loads(input)


def callGraphQL(query, variables=None):
    json = {'query': query}
    if variables is not None:
        json['variables'] = variables

    response = requests.post(endpoint, json=json, headers=headers)

    if response.status_code == 200:
        result = response.json()
        if result.get("errors", None):
            for error in result["errors"]["errors"]:
                raise Exception("GraphQL error: {}".format(error))
        if result.get("data", None):
            return result.get("data")
    else:
        raise ConnectionError(
            "GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(
                response.status_code, response.content, query, variables)
        )


def getScene(url):
    # Sending the full query that gets used in the regular frontend
    query = """
        query 
            Scene($id: Int!, $siteId: Int) {  
                scene(id: $id, siteId: $siteId) 
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
        LogError(f"Could not determine id for site {urlparse(url).netloc}")
        return None

    scene_id = int(urlparse(url).path.split('/')[2])
    LogInfo(f"Scraping scene {scene_id}")

    variables = {
        'id': int(scene_id),
        'siteId': int(site_id)
    }

    try:
        result = callGraphQL(query, variables)
    except ConnectionError as e:
        LogError(e)
        return None

    result = result.get('scene')

    ret = {}

    ret['title'] = result.get('title')
    ret['details'] = result.get('summary')
    ret['studio'] = {'name': result.get('sites')[0].get('name')}
    ret['tags'] = [{'name': x.get('name')} for x in result.get('genres')]
    ret['performers'] = [{'name': x.get('stageName')} for x in result.get('actors')]
    ret['image'] = result.get('primaryPhotoUrl')
    ret['date'] = result.get('createdAt')[:10]

    return ret


if sys.argv[1] == 'scrapeByURL':
    i = readJSONInput()
    ret = getScene(i.get('url'))
    print(json.dumps(ret))
