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

def get_data_from_gallery(inputurl, galleryid, field):
    # Use a regular expression to extract the model number after '/' and before '#play'
    match = re.search(r'/(\d+)#play', inputurl)
    if match:
        modelid = match.group(1)
    else:
        debugPrint('No model ID found in URL.')
        sys.exit()

    #Build URL to scrape
    scrape_url='https://api.ersties.com/galleries/'+modelid

    #Scrape URL
    scrape = requests.get(scrape_url, headers=scrape_headers)

    #Parse response
    #Check for valid response
    if scrape.status_code ==200:
        gallery_data = scrape.json()
        #Find matching gallery in response
        for i in gallery_data:
            if i['id'] == int(galleryid):
                #Get field data from response
                gallery_field = i[field]
                break            
    else: 
        return
    
    return gallery_field

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

        #Get Gallery ID from response for Gallery Scraping
        gallery_id = str(scrape_data['gallery_id'])

        ret['title'] = scrape_data['title_en']
        ret['code'] = str(scrape_data['id'])
        #Get details from Gallery
        ret['details'] = clean_text(str(get_data_from_gallery(inputurl, gallery_id, 'description_en')))    
        ret['studio'] = {'name':'Ersties'}
        ret['tags'] = [{'name': x['name_en']} for x in scrape_data['tags']]
        ret['performers'] = [{'name': x['name_en']} for x in scrape_data['participated_models']]
        for thumbnail in scrape_data['thumbnails']:
            if thumbnail['is_main']:
                ret['image'] = f'https://thumb.ersties.com/width=900,height=500,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/images_videothumbnails/backup/'+thumbnail['file_name']
                break
        #Get Date
        #Send Gallery ID to fuction for scraping and set the returned date
        epoch_time = get_data_from_gallery(inputurl, gallery_id, 'available_since')
        #Convert date from Epoch Time
        ret['date'] = datetime.fromtimestamp(epoch_time).strftime("%Y-%m-%d")
    else:
        debugPrint('Response: '+str(scrape.status_code)+'. Please check your auth header.')
        sys.exit()    
    return ret

def get_group(inputurl):
    # Check whcih URL is being used, Scene or Profile
    if re.search(r"#play", inputurl):  # Check if URL is a Scene
        urltype = 'scene'
        match = re.search(r'#play-(\d+)-comments', inputurl)
        sceneid = match.group(1)
        match = re.search(r"/profile/(\d+)", inputurl)
        groupid = match.group(1)
    elif re.search(r"/profile/\d+$", inputurl):  # Check if URL is a Profile
        urltype = 'profile'
        match = re.search(r'profile/(\d+)', inputurl)
        groupid = match.group(1)
    else:
        debugPrint('No scene/group ID found in URL. Please make sure you are using the ULR ending with "profile/nnnn".')
        sys.exit()
    
    #Scrape Profile
    if urltype == 'profile':
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

    # Scrape Scene
    if urltype == 'scene':
        ret = {}
        #Get Gallery ID from Scene
        #Build URL to scrape
        scrape_url='https://api.ersties.com/videos/'+sceneid

        #Scrape URL
        scrape = requests.get(scrape_url, headers=scrape_headers)

        #Parse response
        #Check for valid response
        if scrape.status_code ==200:
            scrape_data = scrape.json()

            #Get Gallery ID from response for Gallery Scraping
            gallery_id = str(scrape_data['gallery_id'])

            ret['name'] = get_data_from_gallery(inputurl, gallery_id, 'name_en')
            
            #Get details from Gallery
            details=clean_text(get_data_from_gallery(inputurl, gallery_id, 'description_en'))
            ret['synopsis'] = details

            ret['studio'] = {'name':'Ersties'}

            #Get Date
            #Send Gallery ID to fuction for scraping and set the returned date
            epoch_time = get_data_from_gallery(inputurl, gallery_id, 'available_since')
            ret['date'] = datetime.fromtimestamp(epoch_time).strftime("%Y-%m-%d")

            #Thumbnail Scraper from Profile, Galleries don't provide a source for the thumbnail
            #Build URL to scrape Profile
            scrape_url='https://api.ersties.com/models/'+groupid

            #Scrape URL
            scrape = requests.get(scrape_url, headers=scrape_headers)

            #Parse response
            #Check for valid response
            if scrape.status_code ==200:
                scrape_data = scrape.json()            
                ret['front_image'] = f'https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/Model_Cover_Image/backup/'+scrape_data['thumbnail'] 
            else:
                debugPrint('Response: '+str(scrape.status_code)+'. Please check your auth header.')
                sys.exit() 

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