import sys
import json
import hashlib
import stashapi.log as log
import requests
import re
from bs4 import BeautifulSoup as bs

# TODO: Enable searching from other fields?

def debugPrint(t):
    sys.stderr.write(t + "\n")

# Get JSON from Stash
def readJSONInput():
    input = sys.stdin.read()
    return json.loads(input)

def clean_text(details: str) -> str:
    """
    remove escaped backslashes and html parse the details text
    """
    if details:
        details = re.sub(r"\\", "", details)
        details = re.sub(r"<\s*/?br\s*/?\s*>", "\n",
                         details)  # bs.get_text doesnt replace br's with \n
        details = re.sub(r'</?p>', '\n', details)
        details = bs(details, features='html.parser').get_text()
        # Remove leading/trailing/double whitespaces
        details = '\n'.join(
            [
                ' '.join([s for s in x.strip(' ').split(' ') if s != ''])
                for x in ''.join(details).split('\n')
            ]
        )
        details = details.strip()
    return details

def post_query(service, user, id):
    coomer_getpost_url = f"https://coomer.su/api/v1/{service}/user/{user}/post/{id}"
    post_lookup_response = requests.get(coomer_getpost_url)

    if post_lookup_response.status_code == 200:
        data = post_lookup_response.json()
        log.debug(data)
        post = data['post']
        studio = {"Name": user}
        if service == "onlyfans":
            studio["URL"] = f"https://onlyfans.com/{user}"
        elif service == "fansly":
            studio["URL"] = f"https://fansly.com/{user}"
        elif service == "candfans":
            studio["URL"] = f"https://candfans.com/{user}"
        else:
            debugPrint("No service listed")

        out = {"Title": post['title'],
               "Date": post['published'][:10],
               "URL": f"https://coomer.su/{post['service']}/user/{post['user']}/post/{post['id']}",
               "Details": clean_text(post['content']),
               "Studio": studio
        }


        log.debug(out)
        return out
    else:
        debugPrint(f'Response: {str(post_lookup_response.status_code)} \n Text: {str(post_lookup_response.text)}')

def get_scene(inputurl):
    debugPrint(inputurl)
    match = re.search(r'/(\w+?)/user/(.+?)/post/(\d+)', inputurl)
    if match:
        service = match.group(1)
        user = match.group(2)
        id = match.group(3)
    else:
        debugPrint('No post ID found in URL. Please make sure you are using the correct URL.')
        sys.exit()

    return post_query(service, user, id)

def sceneByFragment(fragment):
    file = fragment[0]
    with open(file["path"], "rb") as f:
        bytes = f.read()
        readable_hash = hashlib.sha256(bytes).hexdigest()
        log.debug(f"sha256 hash: {readable_hash}")

    coomer_searchhash_url = "https://coomer.su/api/v1/search_hash/"

    hash_lookup_response = requests.get(coomer_searchhash_url + str(readable_hash))

    if hash_lookup_response.status_code == 200:
        data = hash_lookup_response.json()
        post = data['posts'][0]  # Not sure why there would be more than one result, we'll just use the first one

        return post_query(post['service'], post['user'], post['id'])

    else:
        debugPrint("The hash of the file was not found. Please make sure you are using an original file.")



if sys.argv[1] == 'sceneByURL':
    i = readJSONInput()
    log.debug(i)
    ret = get_scene(i.get('url'))
    log.debug(f"Returned from search: {json.dumps(ret)}")
    print(json.dumps(ret))

if sys.argv[1] == 'sceneByFragment':
    i = readJSONInput()
    log.debug(f"Existing scene data: {json.dumps(i)}")
    ret = sceneByFragment(i["files"])
    log.debug(f"Returned from search: {json.dumps(ret)}")
    print(json.dumps(ret))
