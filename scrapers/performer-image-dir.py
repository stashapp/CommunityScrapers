import os
import sys
import json

''' This script is here to allow you to search for performer images based on a directory.
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

path='/root/.stash/scrapers/actress-pics/'
http_prefix='http://127.0.0.1:9999/custom/actress-pics/'
preference=['Front_Topless','Front_Nude','Front_NN']
if sys.argv[1] == 'query':
    fragment = json.loads(sys.stdin.read())
    print("input: "+json.dumps(fragment),file=sys.stderr)
    res=[]
    for root,dirs,files in os.walk(path):
        for dir in dirs:
            if fragment['name'].lower() in dir.lower():
                res.append({'name':dir})
    if len(res)==0:
        print("{}")
    else:
        print(json.dumps(res))
elif sys.argv[1]=='fetch':
    fragment = json.loads(sys.stdin.read())
    image=''
    candidates=[]
    print(json.dumps(fragment),file=sys.stderr)
    for root,dirs,files in os.walk(path):
        if fragment['name'] in root:
            for f in files:
                candidates.append(root+'/'+f)
    # Look throuh preferences for an image that matches the preference
    candidates.sort()
    for pattern in preference:
         for f in candidates:
             if pattern in f:
                 # return first candiate that matches pattern, replace space with %20 for url encoding
                 fragment['image']=http_prefix+f[len(path):].replace(' ','%20')
                 print(json.dumps(fragment))
                 exit(0)

    # Just use the first image in the folder as a fall back
    if len(candidates) > 0:
        fragment['image']=http_prefix+f[len(path):].replace(' ','%20')
    print(json.dumps(fragment))
