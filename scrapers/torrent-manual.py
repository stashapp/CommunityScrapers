import torrent_parser as tp
import json
import os

# path='<PATH_TO_TORRENT>'
title='FILE_NAME'

path='./torrents/'

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
                res['details']=data['metadata']['description']
            if 'taglist' in data['metadata']:
                res['tags']=[{"name":x} for x in data['metadata']['taglist']]

        print(json.dumps(res))
        exit(0)
def lookup_torrent(title):
    for root,dirs,files in os.walk(path):
        if title in files:
           query_torrent(title,os.path.join(root,title),found=True)

query(title)
