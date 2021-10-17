import base64
import json
import mimetypes
import os
import sys
from pathlib import Path

'''
This script is here to allow you to search for performer images based on a directory.
The query will be a folder name and the lookup will be the image based on preference.
This is designed to work with the accress pics project on github:
https://github.com/Trizkat/actress-pics

This script needs python3

Clone the actress-pics github project to a folder within stash such as a sub directory in the scrapers folder:
cd /root/.stash/scrapers/
git clone https://github.com/Trizkat/actress-pics.git

update path and preference below as needed
'''

path = r'/root/.stash/scrapers/actress-pics/'
preference = ['Front_Topless', 'Front_Nude', 'Front_NN']

debug = True

# ======================

def query():
    fragment = json.loads(sys.stdin.read())
    if debug:
        print("input: " + json.dumps(fragment), file=sys.stderr)

    res = []
    for root, dirs, files in os.walk(path):
        for dir in dirs:
            if fragment['name'].lower() in dir.lower():
                res.append({'name': dir})

    print(json.dumps(res))

def fetch():
    fragment = json.loads(sys.stdin.read())
    if debug:
        print("input: " + json.dumps(fragment), file=sys.stderr)

    candidates = []
    for root, dirs, files in os.walk(path):
        if fragment['name'] in root:
            for f in files:
                candidates.append(str(Path(root, f)))

    # Look throuh preferences for an image that matches the preference
    candidates.sort()
    for pattern in preference:
        for f in candidates:
            if pattern in f:
                # return first candiate that matches pattern, replace space with %20 for url encoding
                fragment['images'] = [make_image_data_url(f)]
                print(json.dumps(fragment))
                exit(0)

    # Just use the first image in the folder as a fall back
    if candidates:
        fragment['images'] = [make_image_data_url(candidates[0])]

    print(json.dumps(fragment))

def make_image_data_url(image_path):
    # type: (str,) -> str
    mime, _ = mimetypes.guess_type(image_path)
    with open(image_path, 'rb') as img:
        encoded = base64.b64encode(img.read()).decode()
    return 'data:{0};base64,{1}'.format(mime, encoded)


if sys.argv[1] == 'query':
    query()
elif sys.argv[1] == 'fetch':
    fetch()

# Last Updated March 28, 2021
