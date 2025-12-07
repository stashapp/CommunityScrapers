import sys
import requests
import re
import json
# Try to import guess_nationality from py_common if available,
# otherwise define a simple stub so the script still works.
try:
    from py_common.util import guess_nationality
except ModuleNotFoundError:
    def guess_nationality(location: str):
        # You can improve this later if you want,
        # for now just return None so it doesn't break.
        return None

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

    # Try to extract the scene ID from URLs like:
    #   ...#play-6138
    #   ...#play-6138-comments
    match = re.search(r'#play-(\d+)(?:-comments)?', inputurl)

    if match:
        sceneid = match.group(1)
    else:
        debugPrint('No scene ID found in URL. Please make sure the URL contains "#play-<id>".')
        sys.exit()

    # Build URL to scrape
    scrape_url = 'https://api.ersties.com/videos/' + sceneid

    # Scrape URL
    scrape = requests.get(scrape_url, headers=scrape_headers)

    # Parse response
    # Check for valid response
    if scrape.status_code == 200:
        scrape_data = scrape.json()

        # Debug info so we can see what the API returns
        debugPrint(f"Scene API URL: {scrape_url}")
        debugPrint(f"Scene API status: {scrape.status_code}")
        debugPrint(f"title_en from API: {repr(scrape_data.get('title_en'))}")
        debugPrint(f"gallery.title_en from API: {repr(scrape_data.get('gallery', {}).get('title_en'))}")

        ret = {}

        # --- Title handling with multiple fallbacks ---
        gallery = scrape_data.get('gallery') or {}

        gallery_title = (
            gallery.get('title_en')
            or gallery.get('title')
            or ''
        )

        scene_title = (
            scrape_data.get('title_en')
            or scrape_data.get('title')
            or ''
        )

        if gallery_title and scene_title:
            # e.g. "Ana B’s fantasy - Intro"
            title = f"{gallery_title}: {scene_title}"
        elif gallery_title or scene_title:
            # whichever exists
            title = gallery_title or scene_title
        else:
            # fallback
            title = f"Ersties {scrape_data.get('id', '')}"

        ret['title'] = title

        # Details / description
        ret['details'] = clean_text(str(gallery.get('description_en', '')))
        ret['studio'] = {'name': 'Ersties'}

        # Code / ID
        ret['code'] = str(scrape_data.get('id', ''))

        # Tags
        ret['tags'] = [{'name': x.get('name_en', '')} for x in scrape_data.get('tags', [])]

        # Performers
        ret['performers'] = [
            {
                'name': x.get('name_en', ''),
                'details': x.get('description_en', ''),
                'urls': [f'https://ersties.com/profile/{x.get("id")}'],
                'images': [
                    f'https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,sharpen=1,format=jpeg/content/images_mysql/Model_Cover_Image/backup/{x.get("thumbnail", "")}'
                ],
            }
            for x in scrape_data.get('participated_models', [])
        ]

        # Main image
        for thumbnail in scrape_data.get('thumbnails', []):
            if thumbnail.get('is_main'):
                ret['image'] = (
                    'https://thumb.ersties.com/width=900,height=500,fit=cover,quality=85,'
                    'sharpen=1,format=jpeg/content/images_mysql/images_videothumbnails/backup/'
                    + thumbnail.get('file_name', '')
                )
                break

        # Date (scene + group)
        epoch_time = gallery.get('available_since')
        if isinstance(epoch_time, int):
            ret['date'] = datetime.fromtimestamp(epoch_time).strftime("%Y-%m-%d")
            group_date = datetime.fromtimestamp(epoch_time).strftime("%Y-%m-%d")
        else:
            group_date = None

        # Group info
        ret['groups'] = [{
            'name': gallery.get('title_en', ''),
            'synopsis': clean_text(str(gallery.get('description_en', ''))),
            'studio': {'name': 'Ersties'},
            'urls': [f'https://ersties.com/shoot/{gallery.get("id", "")}'],
            'front_image': (
                'https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,'
                'sharpen=1,format=jpeg/content/images_mysql/Shoot_Cover/'
                + gallery.get('image', '')
            ),
            'date': group_date,
        }]

    else:
        debugPrint('Response: ' + str(scrape.status_code) + '. Please check your auth header.')
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

            # Optional debug
            debugPrint(f"Group API URL: {scrape_url}")
            debugPrint(f"Group API status: {scrape.status_code}")
            debugPrint(f"group.title_en from API: {repr(scrape_data.get('title_en'))}")

            ret = {}

            ret['name'] = scrape_data.get('title_en', '')
            ret['synopsis'] = clean_text(str(scrape_data.get('description_en', '')))
            ret['studio'] = {'name': 'Ersties'}
            ret['front_image'] = (
                'https://thumb.ersties.com/width=510,height=660,fit=cover,quality=85,'
                'sharpen=1,format=jpeg/content/images_mysql/Shoot_Cover/'
                + scrape_data.get('image', '')
            )

            # Get Date
            epoch_time = scrape_data.get('available_since')
            if isinstance(epoch_time, int):
                ret['date'] = datetime.fromtimestamp(epoch_time).strftime("%Y-%m-%d")
        else:
            debugPrint('Response: ' + str(scrape.status_code) + '. Please check your auth header.')
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
