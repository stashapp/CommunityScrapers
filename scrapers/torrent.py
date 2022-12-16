import os
import sys
import json
from pathlib import Path
from py_common import log
import difflib
from datetime import datetime
import re

try:
    import torrent_parser as tp
except ModuleNotFoundError:
    print("You need to download the file 'torrent_parser.py' from the community repo! (CommunityScrapers/tree/master/scrapers/torrent_parser.py)", file=sys.stderr)
    sys.exit()

'''  This script parses all torrent files in the specified directory for embedded metadata.
     The title can either be a filename or the filename of the .torrent file
     
     This requires python3.
     This uses the torrent_parser library to parse torrent files from: https://github.com/7sDream/torrent_parser
     This library is under the MIT Licence.

     '''

path='./torrents/'

def readJSONInput():
    input = sys.stdin.read()
    log.debug(input)
    return json.loads(input)

def process_tags_performers(tagList):
    return map(lambda tag: tag.replace('.', ' '), tagList)

def procress_description_bbcode(description):
    res = re.sub('\[.*?\].*?\[\/.*?\]','',description)
    res = re.sub('\[.*?\]','',res)
    return res.rstrip()

def query(title):
#    print(f"Test",file=sys.stderr)
    for root,dirs,files in os.walk(path):
        for name in files:
            if '.torrent' in name:
                query_torrent(title,os.path.join(root,name))

def query_torrent(title,path,found=False):
    data=tp.parse_torrent_file(path)
    # does the torrent contain more than one file and check if the file name we want is in the list
    if not found and 'files' in data['info']:
        for d in data['info']['files']:
            for f in d['path']:
                if title in f:
                    found=True
    elif title in data['info']['name']:
        found=True
    if found:
        res={'title':title}
        if 'metadata' in data:
            if 'title' in data['metadata']:
                res['title']=data['metadata']['title']
            if 'cover url' in data['metadata']:
                res['image']=data['metadata']['cover url']
            if 'description' in data['metadata']:
                res['details']=procress_description_bbcode(data['metadata']['description'])
            if 'taglist' in data['metadata']:
                res['tags']=[{"name":x} for x in data['metadata']['taglist']]
            if 'taglist' in data['metadata']:
                res['performers']=[{"name":x} for x in process_tags_performers(data['metadata']['taglist'])]
            if 'comment' in data:
                res['url'] = data['comment']
            if 'creation date' in data:
                res['date'] = datetime.fromtimestamp(data['creation date']).strftime('%Y-%m-%d')

        print(json.dumps(res))
        exit(0)

def lookup_torrent(title):
    for root,dirs,files in os.walk(path):
        if title in files:
            query_torrent(title,os.path.join(root,title),found=True)

def similarity_file_name(search, fileName):
    result = difflib.SequenceMatcher(a=search.lower(), b=fileName.lower())
    return result.ratio()

def cleanup_name(name):
    ret = str(name)
    ret = ret.removeprefix("torrents\\").removesuffix(".torrent")
    return ret


if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    title=fragment['title']
    log.debug(title)
    if '.torrent' in title:
        lookup_torrent(title)
    else:
        query(title)
    print(json.dumps(fragment))

elif sys.argv[1] == "search":
    search = readJSONInput().get('name')
    torrents = list(Path(path).glob('*.torrent'))
    ratios = {}
    for t in torrents:
        clean_t = cleanup_name(t)
        ratios[round(10000*(1-similarity_file_name(search, clean_t)))] = clean_t

    # Order ratios
    ratios_sorted = dict(sorted(ratios.items()))
    # Only return the top 5 results
    if len(ratios) > 5:
        ratios = ratios_sorted[5:]
    
    res = list(map(lambda i: {'title': ratios_sorted[i] + ".torrent"}, ratios_sorted))
    log.debug(ratios_sorted)
    print(json.dumps(res))

    



# Last Updated December 16, 2022
