import sys
import requests
import re
import json
from py_common.util import guess_nationality
from datetime import datetime
from bs4 import BeautifulSoup as bs

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
        ret['details'] = clean_text(str(scrape_data['gallery']['description_en'])) 
        ret['studio'] = {'name':'Ersties'}
        ret['tags'] = [{'name': x['name_en']} for x in scrape_data['tags']]
        ret['performers'] = [{'name':x['name_en'], 'details':x['description_en'], 'urls':['https://ersties.com/profile/'+str(x['id'])],'images':[f'https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/Model_Cover_Image/backup/'+x['thumbnail']] } for x in scrape_data['participated_models']]
        for thumbnail in scrape_data['thumbnails']:
            if thumbnail['is_main']:
                ret['image'] = f'https://thumb.ersties.com/width=900,height=500,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/images_videothumbnails/backup/'+thumbnail['file_name']
                break
        #Get Date
        epoch_time = scrape_data['gallery']['available_since']
        # Check if the date is returned as an integer.
        if isinstance(epoch_time, int):
            #Convert date from Epoch Time
            ret['date'] = datetime.fromtimestamp(epoch_time).strftime("%Y-%m-%d")
        #Get Group Information
        #Get Group Date
        group_epoch_time = scrape_data['gallery']['available_since']
        # Check if the date is returned as an integer.
        if isinstance(group_epoch_time, int):
            #Convert date from Epoch Time
            group_date = datetime.fromtimestamp(group_epoch_time).strftime("%Y-%m-%d")
        ret['groups'] = [{'name': scrape_data['gallery']['title_en'], 'synopsis': clean_text(str(scrape_data['gallery']['description_en'])), 'studio': {'name':'Ersties'}, 'urls':[f'https://ersties.com/shoot/'+str(scrape_data['gallery']['id'])], 'front_image': f'https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/Shoot_Cover/'+scrape_data['gallery']['image'], 'date': group_date}]
    else:
        debugPrint('Response: '+str(scrape.status_code)+'. Please check your auth header.')
        sys.exit()    
    return ret

def get_group(inputurl):
    # Check if URL is a Shoot
    if re.search(r"/shoot/\d+$", inputurl):
        urltype = 'shoot'
        match = re.search(r'shoot/(\d+)', inputurl)
        groupid = match.group(1)
    else:
        debugPrint('No shoot ID found in URL. Please make sure you are using the correct URL.')
        sys.exit()
    
    #Scrape Shoot
    if urltype == 'shoot':
        #Build URL to scrape group
        scrape_url='https://api.ersties.com/galleries/'+groupid

        #Scrape URL
        scrape = requests.get(scrape_url, headers=scrape_headers)

        #Parse response
        #Check for valid response
        if scrape.status_code ==200:
            scrape_data = scrape.json()

            ret = {}

            ret['name'] = scrape_data['title_en']
            ret['synopsis'] = clean_text(str(scrape_data['description_en']))
            ret['studio'] = {'name':'Ersties'}
            ret['front_image'] = f'https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/Shoot_Cover/'+scrape_data['image']  
            #Get Date
            epoch_time = scrape_data['available_since']
            # Check if the date is returned as an integer.
            if isinstance(epoch_time, int):
                #Convert date from Epoch Time
                ret['date'] = datetime.fromtimestamp(epoch_time).strftime("%Y-%m-%d")
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
        ret['image'] = f'https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/Model_Cover_Image/backup/'+scrape_data['thumbnail']  
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
