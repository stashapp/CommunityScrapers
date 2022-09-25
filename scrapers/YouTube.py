reformat_url = True  # if true scraper will reformat all passed URLs to "https://www.youtube.com/?v={video_id}"
channels_are_studios = False  # if true scraper will return channel name as the Studio name instead of the hardcoded one
HARDCODED_STUDIO_NAME = 'YouTube'  # change to suite your needs

# To get an API key:
# 1. Go to https://console.cloud.google.com/home/dashboard and create a new project
# 2. Add 'YouTube Data API v3' to your project's 'Enabled APIs & Services'
# 3. Navigate to the 'Credentials' page and create a new API key to paste in here
API_KEY = ''
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
# The YouTube API assigns a cost to every query. You get 10,000 "tokens" to spend per day.
# Costs can be found here: https://developers.google.com/youtube/v3/determine_quota_cost
# As of right now (2022-09-25) the costs of running this scraper are as follows:
#   SceneByURL: 1 token (10,000 uses/day)

import os
import re
import json
import sys
from datetime import datetime

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ModuleNotFoundError:
    print("You need to install Google's API client.", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install google-api-python-client",
        file=sys.stderr)
    sys.exit(1)

try:
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit(1)


# Exacts the video ID from the URL by matching all patterns I could find that come immediately prior
def regex_id_from_url(url):
    regex = r'(v=|\.be\/|v\/|\?vi=|embed\/)([A-Za-z0-9_-]{11})'
    id = re.search(regex, url).group(2)
    log.debug("Extracted videoID [" + str(id) + "] from URL.")
    return id


# Calls this endpoint: https://developers.google.com/youtube/v3/docs/videos/list
def scrape_video_metadata(videoID):
    request = youtube.videos().list(part='snippet', id=videoID)
    response = request.execute()
    details = response['items'][0]['snippet']
    scene_dict = {
        "title": details['title'],
        "url": "https://www.youtube.com/watch?v=" + videoID,
        "date": datetime.strptime(details['publishedAt'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d'),
        'details': details['description'],
        'image' : "https://img.youtube.com/vi/" + videoID + "/maxresdefault.jpg",
        'studio': {'name': HARDCODED_STUDIO_NAME}
    }
    if "tags" in details:  # Some videos have no tags
        scene_dict['tags'] = [{'name': t} for t in details['tags']]
    if channels_are_studios:
        scene_dict['studio']['name'] = details['channelTitle']
    return scene_dict


if __name__ == '__main__':
    try:
        youtube = build(API_SERVICE_NAME, API_VERSION, developerKey=API_KEY)
    except Error as e:
        log.error("Unable to initialize YouTube API!")
        log.error(e)

    if sys.argv[1] == "video_url_lookup":
        log.debug("Script running sceneByURL path.")
        input_json = json.loads(sys.stdin.read())
        url = input_json['url']
        try:
            video_id = regex_id_from_url(url)
            scene_data = scrape_video_metadata(video_id)
            if not reformat_url:
                scene_data['url'] = url  # keep input url
            log.trace("Returning scene JSON: " + str(json.dumps(scene_data)))
            print(json.dumps(scene_data))
        except HttpError as e:
            log.error('An HTTP error %d occurred:\n%s' % (e.resp.status, e.content))