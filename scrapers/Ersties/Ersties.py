import sys
import requests
import re
import json
from py_common.util import guess_nationality, scraper_args
from py_common.types import ScrapedScene, ScrapedPerformer, ScrapedGroup
from py_common import log
from py_common.config import get_config
from datetime import datetime
from bs4 import BeautifulSoup as bs

config = get_config(default="""
# Ersties auth configuration
# Use the network console in your browsers developer tools to find this information in an api call header.
AUTHORIZATION = 
COOKIE =
X_VISIT_UID =
""")

#Headers for Requests
scrape_headers = {
    'authorization': config.AUTHORIZATION,
    'cookie': config.COOKIE,
    'x-visit-uid': config.X_VISIT_UID,
}
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

def get_scene(inputurl) -> ScrapedScene:

    # Try to extract the scene ID from URLs like:
    #   ...#play-6138
    #   ...#play-6138-comments
    match = re.search(r'#play-(\d+)(?:-comments)?', inputurl)

    # Check if the pattern was found and save it as a variable
    if match:
        sceneid = match.group(1)  
    else:
        log.error('No scene ID found in URL. Please make sure the URL contains "#play-<id>".')
        sys.exit()

    # Build URL to scrape
    scrape_url = 'https://api.ersties.com/videos/' + sceneid

    #Scrape URL
    scrape = requests.get(scrape_url, headers=scrape_headers)

    #Parse response
    #Check for valid response
    if scrape.status_code ==200:
        scrape_data = scrape.json()

        ret: ScrapedScene = {}
        ret['code'] = str(scrape_data.get('id', ''))
        ret['tags'] = [{'name': x.get('name_en', '')} for x in scrape_data.get('tags', [])]

        gallery = scrape_data.get('gallery') or {}
        gallery_title = gallery.get('title_en') or gallery.get('title')
        scene_title = scrape_data.get('title_en') or scrape_data.get('title')
        if gallery_title and scene_title:
            ret['title'] = f"{gallery_title}: {scene_title}"
        ret['details'] = clean_text(str(gallery.get('description_en', '')))
        ret['studio'] = {'name': 'Ersties'}
        ret['performers'] = [
            {
                'name': model.get('name_en', ''),
                'details': model.get('description_en', ''),
                'urls': [f'https://ersties.com/profile/{model.get("id")}'],
                'images': [
                    f'https://thumb.ersties.com/format=jpeg/content/images_mysql/Model_Cover_Image/backup/{model.get("thumbnail", "")}'
                ],
            }
            for model in scrape_data.get('participated_models', [])
        ]

        # Main image
        for thumbnail in scrape_data.get('thumbnails', []):
            if thumbnail.get('is_main'):
                ret['image'] = f"https://thumb.ersties.com/format=jpeg/content/images_mysql/images_videothumbnails/backup/{thumbnail.get('file_name', '')}"
                break
        # Date (scene + group)
        epoch_time = gallery.get('available_since')
        group_date = None
        if isinstance(epoch_time, int):
            group_date = datetime.fromtimestamp(epoch_time).strftime("%Y-%m-%d")
            ret['date'] = group_date

        ret['groups'] = [{
            'name': gallery.get('title_en', ''),
            'synopsis': clean_text(str(gallery.get('description_en', ''))),
            'studio': {'name': 'Ersties'},
            'urls': [f'https://ersties.com/shoot/{gallery.get("id", "")}'],
            'front_image': f"https://thumb.ersties.com/format=jpeg/content/images_mysql/Shoot_Cover/{gallery.get('image', '')}",
            'date': group_date,
        }]

    else:
        log.error(f"Response:{str(scrape.status_code)}. Please check your auth header.")
        sys.exit()
    return ret

def get_group(inputurl) -> ScrapedGroup:
    # Check if URL is a Shoot
    if re.search(r"/shoot/\d+$", inputurl):
        urltype = 'shoot'
        match = re.search(r'shoot/(\d+)', inputurl)
        if match:
            groupid = match.group(1)
    else:
        log.error('No shoot ID found in URL. Please make sure you are using the correct URL.')
        sys.exit()
    # Scrape Shoot
    if urltype == 'shoot':
        # Build URL to scrape group
        scrape_url = 'https://api.ersties.com/galleries/' + groupid

        # Scrape URL
        scrape = requests.get(scrape_url, headers=scrape_headers)

        # Parse response
        # Check for valid response
        if scrape.status_code == 200:
            scrape_data = scrape.json()

            ret: ScrapedGroup = {}

            ret['name'] = scrape_data.get('title_en', '')
            ret['synopsis'] = clean_text(str(scrape_data.get('description_en', '')))
            ret['studio'] = {'name': 'Ersties'}
            ret['front_image'] = f"https://thumb.ersties.com/format=jpeg/content/images_mysql/Shoot_Cover/{scrape_data.get('image', '')}"
            # Get Date
            epoch_time = scrape_data.get('available_since')
            if isinstance(epoch_time, int):
                ret['date'] = datetime.fromtimestamp(epoch_time).strftime("%Y-%m-%d")
        else:
            log.error(f"Response: {str(scrape.status_code)}. Please check your auth header.")
            sys.exit()
    return ret

def get_performer(inputurl) -> ScrapedPerformer:
    # Use a regular expression to extract the number after '#play-' and before '-comments'
    match = re.search(r'profile/(\d+)', inputurl)

    # Check if the pattern was found and save it as a variable
    if match:
        groupid = match.group(1)  
    else:
        log.error('No performer ID found in URL. Please make sure you are using the ULR ending with "profile/nnnn".')
        sys.exit()

    #Build URL to scrape group
    scrape_url='https://api.ersties.com/models/'+groupid

    #Scrape URL
    scrape = requests.get(scrape_url, headers=scrape_headers)

    #Parse response
    #Check for valid response
    if scrape.status_code ==200:
        scrape_data = scrape.json()

        ret: ScrapedPerformer = {
            "name": scrape_data['name_en'],
            "details": scrape_data['description_en'],
            "image": f'https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/Model_Cover_Image/backup/'+scrape_data['thumbnail']
        }

        if scrape_data['location_en'] is not None:
            ret['country'] = guess_nationality(scrape_data['location_en'])
    else:
        log.error('No performer ID found in URL. Please make sure you are using the ULR ending with "profile/nnnn".')
        sys.exit()
    return ret

if __name__ == '__main__':
    op, args = scraper_args()
    result = None
    match op, args:
        case 'scene-by-url', { "url": url } if url:
            result = get_scene(url)
        case 'group-by-url', { "url": url } if url:
            result = get_group(url)
        case 'performer-by-url', { "url": url } if url:
            result = get_performer(url)
        case _:
            log.debug(f'Unknown operation {op} with arguments {args}')
            sys.exit(1)
    print(json.dumps(result))