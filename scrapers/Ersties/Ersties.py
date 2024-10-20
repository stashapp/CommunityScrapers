import sys
import requests
from random import choice
import re
import json

#Create random UID for site tracking (required for auth)
first=''.join(choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for i in range(14))
second=''.join(choice('0123456789') for i in range(8))

uid=first+'.'+second

#Create Auth Session
url="https://api.ersties.com/auth/login"

auth_headers = {
    'x-visit-uid': uid,
}

auth_json_data = {
    'username': 'your_username',
    'password': 'your_passsword',
}
session = requests.session()
auth = session.post(url, headers=auth_headers, json=auth_json_data)

#Create Bearer Token
bearer_token = "Bearer " + auth.text

bearer_token = bearer_token.replace('"', '')

#Scrape
#example url: https://ersties.com/profile/3265#play-8187-comments

#Get Scene ID from url
inputurl= sys.stdin.read()
# Use a regular expression to extract the number after '#play-' and before '-comments'
match = re.search(r'#play-(\d+)-comments', inputurl)
# Check if the pattern was found and save it as a variable
if match:
    sceneid = match.group(1)  # The captured group (7976)
    print(f'Video ID: {sceneid}')
else:
    print('No match found')

sceneid='8187' #testing scene id
scrape_url='https://api.ersties.com/videos/'+sceneid

scrape_headers = {
    'Authorization': bearer_token,
}

scrape = session.get(scrape_url, headers=scrape_headers)

#Parse response

scrape_data = scrape.json()

ret = {}

ret['title'] = scrape_data['title_en']
ret['code'] = scrape_data['id']
ret['details'] = scrape_data['model']['description_en']
ret['studio'] = "Ersties"
ret['tags'] = [x['name_en'] for x in scrape_data['tags']]
ret['performers'] = [x['name_en'] for x in scrape_data['participated_models']]
for thumbnail in scrape_data['thumbnails']:
    if thumbnail['is_main']:
        ret['image'] = f'https://thumb.ersties.com/width=900,height=500,fit=cover,quality=85,sharpen=1,format=avif/content/images_mysql/images_videothumbnails/backup/'+thumbnail['file_name']
        break

print(json.dumps(ret))

#example poster link: https://thumb.ersties.com/width=900,height=500,fit=cover,quality=85,sharpen=1,format=avif/content/images_mysql/images_videothumbnails/backup/Jin_DaringKiara_Still_1_66dad8920cb13.jpg