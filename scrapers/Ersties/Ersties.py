import sys
import requests
import re
import json
from py_common.util import guess_nationality

#Authentication tokens and cookies are needed for this scraper. Use the network console in your browsers developer tools to find this information in an api call header.
#Auth Variables For Header
authorization = ''
cookie = ''
x_visit_uid = ''

#Headers for Requests
scrape_headers = {
    'authorization': authorization,
    'cookie': cookie,
    'x-visit-uid': x_visit_uid,
}

#Get JSON from Stash
def readJSONInput():
    input = sys.stdin.read()
    return json.loads(input)

def debugPrint(t):
    sys.stderr.write(t + "\n")

def get_scene(inputurl):

    # Use a regular expression to extract the number after '#play-' and before '-comments'
    match = re.search(r'#play-(\d+)-comments', inputurl)

    # Check if the pattern was found and save it as a variable
    if match:
        sceneid = match.group(1)  
    else:
        debugPrint('No scene ID found in URL. Please make sure you are using the ULR ending with "#play-nnnn-comments".')
        sys.exit()

    #Build URL to scrape
    scrape_url='https://api.ersties.com/videos/'+sceneid

    #Scrape URL
    scrape = requests.get(scrape_url, headers=scrape_headers)

    #Parse response
    #Check for valid response
    if scrape.status_code ==200:
        scrape_data = scrape.json()

        ret = {}

        ret['title'] = scrape_data['title_en']
        ret['code'] = str(scrape_data['id'])
        ret['details'] = scrape_data['model']['description_en']
        ret['studio'] = {'name':'Ersties'}
        ret['tags'] = [{'name': x['name_en']} for x in scrape_data['tags']]
        ret['performers'] = [{'name': x['name_en']} for x in scrape_data['participated_models']]
        for thumbnail in scrape_data['thumbnails']:
            if thumbnail['is_main']:
                ret['image'] = f'https://thumb.ersties.com/width=900,height=500,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/images_videothumbnails/backup/'+thumbnail['file_name']
                break
    else:
        debugPrint('Response: '+str(scrape.status_code)+'. Please check your auth header.')
        sys.exit()    
    return ret

def get_group(inputurl):
    # Use a regular expression to extract the number after 'profile/'
    match = re.search(r'profile/(\d+)', inputurl)

    # Check if the pattern was found and save it as a variable
    if match:
        groupid = match.group(1)  
    else:
        debugPrint('No scene/group ID found in URL. Please make sure you are using the ULR ending with "profile/nnnn".')
        sys.exit()

    #Build URL to scrape group
    scrape_url='https://api.ersties.com/models/'+groupid

    #Scrape URL
    scrape = requests.get(scrape_url, headers=scrape_headers)

    #Parse response
    #Check for valid response
    if scrape.status_code ==200:
        scrape_data = scrape.json()

        ret = {}

        ret['name'] = scrape_data['name_en']
        ret['synopsis'] = scrape_data['description_en']
        ret['studio'] = {'name':'Ersties'}
        ret['front_image'] = f'https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/Model_Cover_Image/backup/'+scrape_data['thumbnail']  
    else:
        debugPrint('Response: '+str(scrape.status_code)+'. Please check your auth header.')
        sys.exit() 
    return ret

def get_performer(inputurl):
    # Use a regular expression to extract the number after '#play-' and before '-comments'
    match = re.search(r'profile/(\d+)', inputurl)

    # Check if the pattern was found and save it as a variable
    if match:
        groupid = match.group(1)  
    else:
        debugPrint('No performer ID found in URL. Please make sure you are using the ULR ending with "profile/nnnn".')
        sys.exit()

    #Build URL to scrape group
    scrape_url='https://api.ersties.com/models/'+groupid

    #Scrape URL
    scrape = requests.get(scrape_url, headers=scrape_headers)

    #Parse response
    #Check for valid response
    if scrape.status_code ==200:
        scrape_data = scrape.json()

        ret = {}

        ret['name'] = scrape_data['name_en']
        if scrape_data['location_en'] is not None:
            ret['country'] = guess_nationality(scrape_data['location_en'])
        ret['details'] = scrape_data['description_en']
        ret['image'] = f'https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,sharpen=1,format=avif/content/images_mysql/Model_Cover_Image/backup/'+scrape_data['thumbnail']  
    else:
        debugPrint('No performer ID found in URL. Please make sure you are using the ULR ending with "profile/nnnn".')
        sys.exit()
    return ret

if sys.argv[1] == 'sceneByURL':
    i = readJSONInput()
    ret = get_scene(i.get('url'))
    print(json.dumps(ret))

if sys.argv[1] == 'groupByURL':
    i = readJSONInput()
    ret = get_group(i.get('url'))
    print(json.dumps(ret))

if sys.argv[1] == 'performerByURL':
    i = readJSONInput()
    ret = get_performer(i.get('url'))
    print(json.dumps(ret))