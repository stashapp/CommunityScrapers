import re
import json
import requests
import sys
from datetime import datetime
from py_common.cache import cache_to_disk

def fail(message: str):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)

@cache_to_disk(key="iwara_auth_token", ttl=86400)
def login(force=False):
    """Logs in to get an auth token"""
    if force:
        return relogin()

    username = "YOUR_USERNAME"
    password = "YOUR_PASSWORD"
    login_url = 'https://api.iwara.tv/user/login'
    payload = {'email': username, 'password': password}
    response = requests.post(login_url, json=payload)
    if response.status_code != 200:
        print(json.dumps({"error": "Login failed"}), file=sys.stdout)
        sys.exit(1)
    return response.json().get('token')

def relogin():
    """Forces a new login"""
    return login(force=True)

def get_video_details(video_id, token):
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'https://api.iwara.tv/video/{video_id}', headers=headers)
        response.raise_for_status()
        if response.status_code == 401:
            token = relogin()
            return get_video_details(video_id, token)

        video_data = response.json()
    except requests.RequestException as e:
        fail(f"Failed to fetch video data: {e}")
    except json.JSONDecodeError:
        fail("Failed to decode JSON from response")

    return {
        "title": video_data.get('title'),
        "url": f"https://www.iwara.tv/videos/{video_id}",
        "image": f"https://files.iwara.tv/image/thumbnail/{video_data.get('file', {}).get('id')}/thumbnail-00.jpg",
        "date": datetime.strptime(video_data.get('createdAt'), "%Y-%m-%dT%H:%M:%S.%fZ").date().isoformat(),
        "details": video_data.get('body'),
        "studio": {
            "Name": video_data.get('user', {}).get('name'),
            "URL": f"https://www.iwara.tv/profile/{video_data.get('user', {}).get('username')}"
        },
        "tags": [{"name": tag.get('id')} for tag in video_data.get('tags', [])]
    }

def sceneByURL(params):
    token = login()
    video_url = params['url']
    match = re.search(r'/video/([^/]+)/', video_url)
    if not match:
        fail("Invalid video URL")
    video_id = match.group(1)
    return get_video_details(video_id, token)

def sceneByFragment(params):
    token = login()
    video_id = params['video_id']
    return get_video_details(video_id, token)

if __name__ == "__main__":
    calledFunction = sys.argv[1]
    params = json.loads(sys.stdin.read())

    if calledFunction == "sceneByURL":
        print(json.dumps(sceneByURL(params)))
    elif calledFunction == "sceneByFragment":
        print(json.dumps(sceneByFragment(params)))
    else:
        fail("This scrape method has not been implemented!")