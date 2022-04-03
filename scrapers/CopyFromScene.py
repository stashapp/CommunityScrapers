
import json
import sys

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

url="http://localhost:9999/graphql"
headers = {
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Connection": "keep-alive",
    "DNT": "1"
}

def __callGraphQL(query, variables=None):

    json = {}
    json['query'] = query
    if variables != None:
        json['variables'] = variables

    # handle cookies
    response = requests.post(url, json=json, headers=headers)

    if response.status_code == 200:
        result = response.json()
        if result.get("error", None):
            for error in result["error"]["errors"]:
                raise Exception("GraphQL error: {}".format(error))
        if result.get("data", None):
            return result.get("data")
    else:
        raise Exception(
            "GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(response.status_code, response.content, query, variables))

def findGallery(id):
    query = """query findGallery($gallery_id: ID!){
findGallery(id: $gallery_id){
id
path
scenes{
title
url
date
rating
details
organized
studio{
  id
  name
}
performers{
id
  name
}
tags{
id
  name
}
}
}
}"""

    variables = {'gallery_id': id, }
    result = __callGraphQL(query, variables)
    if result is not None:
        return result["findGallery"]
    return None


if sys.argv[1] == "gallery_query":
    fragment = json.loads(sys.stdin.read())
    print("input: " + json.dumps(fragment),file=sys.stderr)
    result = findGallery(fragment['id'])
    if not result:
        print(f"Could not determine details for gallery: `{fragment['id']}`",file=sys.stderr)
        print("{}")
    else:
        if len(result["scenes"])  > 0:
            print (json.dumps(result["scenes"][0]))
        else:
            print ("{}")


