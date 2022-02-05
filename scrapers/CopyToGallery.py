import json
import sys
import os
import requests

import py_common.graphql as graphql
import py_common.log as log

SERVER_IP = "http://localhost:9999"
# API key (Settings > Configuration > Authentication)
STASH_API = ""
SERVER_URL = SERVER_IP + "/graphql"

find_gallery = False

def call_graphql(query, variables=None):
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "DNT": "1",
        "ApiKey": STASH_API
    }
    json = {'query': query}
    if variables is not None:
        json['variables'] = variables
    try:
        response = requests.post(SERVER_URL, json=json, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result.get("error"):
                for error in result["error"]["errors"]:
                    raise Exception("GraphQL error: {}".format(error))
            if result.get("data"):
                return result.get("data")
        elif response.status_code == 401:
            log.debug("401 returned from callGraphQL")
            # debug("[ERROR][GraphQL] HTTP Error 401, Unauthorised.")
            return None
        else:
            raise ConnectionError("GraphQL query failed:{} - {}".format(response.status_code, response.content))
    except Exception as err:
        log.error(err)
        # debug(err)
        return None

def get_gallery_id_by_path(gallery_path):
    log.debug("get_gallery_by_path gallery_path " + str(gallery_path))
    query = """
            query FindGalleries($galleries_filter: GalleryFilterType) {
              findGalleries(gallery_filter: $galleries_filter filter: {per_page: -1}) {
                count
                    galleries {
                        id
                    }
              }
            }
            """
    variables = {"galleries_filter": {"path": {'value': gallery_path, "modifier": "INCLUDES_ALL"}}}
    result = call_graphql(query, variables)
    log.debug("get_gallery_by_path callGraphQL result " + str(result))
    return result['findGalleries']['galleries'][0]['id']

def update_gallery(input):
    log.debug("gallery input " + str(input))
    query = """
                mutation GalleryUpdate($input : GalleryUpdateInput!) {
                  galleryUpdate(input: $input) {
                    id
                    title
                  }
                }
                """
    variables = {
        "input": input
    }
    result = call_graphql(query, variables)
    log.debug("updateGallery callGraphQL result " + str(result))
    return result

def get_id(obj):
    ids = []
    for item in obj:
        ids.append(item['id'])
    return ids

def find_galleries(scene_id, scene_path):
    ids = []
    directory_path = os.path.dirname(scene_path)
    for (cur, dirs, files) in os.walk(directory_path):

        for file in files:
            if file.endswith('.zip'):
                gallery_path = os.path.join(cur, file)
                id = get_gallery_id_by_path(gallery_path)
                updateScene_with_gallery(scene_id, id)
                ids.append(id)
        break
    log.debug("find_galleries ids' found " + str(ids))
    return ids

def updateScene_with_gallery(scene_id, gallery_id):
    data = {'id': scene_id, 'gallery_ids': [gallery_id]}
    log.debug("data " + str(data))
    query = """
                mutation SceneUpdate($input : SceneUpdateInput!) {
                  sceneUpdate(input: $input) {
                    id
                    title
                  }
                }
                """
    variables = {
        "input": data
    }
    result = call_graphql(query, variables)
    log.debug("graphql_updateGallery callGraphQL result " + str(result))

FRAGMENT = json.loads(sys.stdin.read())
SCENE_ID = FRAGMENT.get("id")

scene = graphql.getScene(SCENE_ID)
if scene:
    scene_galleries = scene['galleries']
    log.debug("scene_galleries " + str(scene_galleries))
    gallery_ids = []
    if len(scene_galleries) > 0:
        for gallery_obj in scene_galleries:
            gallery_ids.append(gallery_obj['id'])
    elif find_gallery:
        # if no galleries are associated see if any gallery zips exist in directory
        gallery_ids = find_galleries(SCENE_ID, scene["path"])
    log.debug("gallery_ids " + str(gallery_ids))

    for gallery_id in gallery_ids:
        studio = None
        if scene['studio']:
            studio = scene['studio']['id']
        gallery_input = {'id': gallery_id,
                         'url': scene['url'],
                         'title': scene['title'],
                         'date': scene["date"],
                         'details': scene['details'],
                         'studio_id': studio,
                         'tag_ids': get_id(scene['tags']),
                         'performer_ids': get_id(scene['performers'])}
        update_gallery(gallery_input)

    print(json.dumps({}))

