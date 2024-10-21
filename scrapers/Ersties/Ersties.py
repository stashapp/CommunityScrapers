import sys
import requests
import re
import json

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
        debugPrint('No match found')

    #Build URL to scrape
    scrape_url='https://api.ersties.com/videos/'+sceneid

    #Scrape URL
    scrape = requests.get(scrape_url, headers=scrape_headers)

    #Parse response

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

    return ret

if sys.argv[1] == 'scrapeByURL':
    i = readJSONInput()
    ret = get_scene(i.get('url'))
    print(json.dumps(ret))