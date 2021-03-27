import json
import os
import sys
from pathlib import Path
from urllib.parse import quote, urljoin

'''
This script is here to allow you to search for performer images based on a directory.
The query will be a folder name and the lookup will be the image based on preference.
This is designed to work with the accress pics project on github:
https://github.com/Trizkat/actress-pics

This script needs python3

To support extracting images from the database we need to provide a url where these image are located.
Stash allows you to serve custom files by adding a few lines to the configuration.
This plugin returns the url of that image in the response.

Make the directory and add the following to config.yml configuration:
custom_served_folders:
  /actress-pics: /root/.stash/scrapers/actress-pics

Then clone the actress-pics github project to a folder within stash such as a sub directory in the scrapers folder:
cd /root/.stash/scrapers/
git clone https://github.com/Trizkat/actress-pics.git

update path, url_prefix, and preference as needed
'''

path = Path(r'/root/.stash/scrapers/actress-pics/')
http_prefix = 'http://127.0.0.1:9999/custom/actress-pics/'
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
                # construct a UNIX-style file path relative to the `actress-pics` path
                candidates.append(Path(root, f).relative_to(path).as_posix())

    # Look throuh preferences for an image that matches the preference
    candidates.sort()
    for pattern in preference:
        for f in candidates:
            if pattern in f:
                # return first candiate that matches pattern, replace space with %20 for url encoding
                fragment['image'] = urljoin(http_prefix, quote(f))
                print(json.dumps(fragment))
                exit(0)

    # Just use the first image in the folder as a fall back
    if candidates:
        fragment['image'] = urljoin(http_prefix, quote(candidates[0]))

    print(json.dumps(fragment))


if sys.argv[1] == 'query':
    query()
elif sys.argv[1] == 'fetch':
    fetch()
