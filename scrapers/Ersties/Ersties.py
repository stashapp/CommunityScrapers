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

#Read the input
i = readJSONInput()
sys.stderr.write(json.dumps(i))

#Scrape Scene URL

#Get Scene ID from url
inputurl= i['url']
# Use a regular expression to extract the number after '#play-' and before '-comments'
match = re.search(r'#play-(\d+)-comments', inputurl)
# Check if the pattern was found and save it as a variable
if match:
    sceneid = match.group(1)  # The captured group (7976)
else:
    print('No match found')

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
ret['studio'] = "Ersties"
ret['tags'] = [x['name_en'] for x in scrape_data['tags']]
ret['performers'] = [x['name_en'] for x in scrape_data['participated_models']]
for thumbnail in scrape_data['thumbnails']:
    if thumbnail['is_main']:
        ret['image'] = f'https://thumb.ersties.com/width=900,height=500,fit=cover,quality=85,sharpen=1,format=avif/content/images_mysql/images_videothumbnails/backup/'+thumbnail['file_name']
        break

print(json.dumps(ret))