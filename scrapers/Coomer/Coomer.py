import sys
import json
import hashlib
import stashapi.log as log
import requests

# TODO: Enable searching from other fields?

def debugPrint(t):
    sys.stderr.write(t + "\n")

# Get JSON from Stash
def readJSONInput():
    input = sys.stdin.read()
    return json.loads(input)

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

        coomer_getpost_url = f"https://coomer.su/api/v1/{post['service']}/user/{post['user']}/post/{post['id']}"

        post_lookup_response = requests.get(coomer_getpost_url)

        if post_lookup_response.status_code == 200:
            data = post_lookup_response.json()
            post = data['post']

            out = {"Title": post['title'],
                   "Date": post['published'][:10],
                   "URL": f"https://coomer.su/{post['service']}/user/{post['user']}/post/{post['id']}",
                   "Details": post['content']
                   }

            log.debug(out)
            return out
        else:
            debugPrint("The hash of the file was found, but there was no post.")
    else:
        debugPrint("The hash of the file was not found. Please make sure you are using an original file.")





if sys.argv[1] == 'sceneByFragment':
    i = readJSONInput()
    log.debug(f"Existing scene data: {json.dumps(i)}")
    ret = sceneByFragment(i["files"])
    log.debug(f"Returned from search: {json.dumps(ret)}")
    print(json.dumps(ret))
else:
    print("Unknown command")
    exit(1)