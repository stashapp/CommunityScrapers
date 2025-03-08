import sys
import json
import hashlib
import stashapi.log as log
import requests
import re
from bs4 import BeautifulSoup as bs
import io

# TODO: Enable searching from other fields?

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Referer': 'https://coomer.su/search_hash'
}

def extract_mentions_and_tags(text):
    mentions = re.findall(r'@([\w\-._\d]+)', text) if text else []
    hashtags = re.findall(r'#(\w+)\b', text) if text else []
    return mentions, hashtags

def debugPrint(t):
    sys.stderr.write(t + '\n')

# Get JSON from Stash
def readJSONInput():
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    input = sys.stdin.read()
    return json.loads(input)

def custom_title(text):
    def capitalize(match):
        word = match.group()
        if "'" in word:
            parts = word.split("'")
            return parts[0].capitalize() + "'" + parts[1]
        return word.capitalize()
    return re.sub(r"\b\w+('\w+)?", capitalize, text)

def clean_text(details: str) -> (str, str):
    """
    remove escaped backslashes and html parse the details text
    """
    if details:
        details = re.sub(r'\\', '', details)
        details = re.sub(r'<\s*/?br\s*/?\s*>', '\n',
                         details)  # bs.get_text doesnt replace br's with \n
        details = re.sub(r'</?p>', '\n', details)
        details = bs(details, features='html.parser').get_text()
        details = '\n'.join(
            [
                ' '.join([s for s in x.strip(' ').split(' ') if s != ''])
                for x in ''.join(details).split('\n')
            ]
        )
        details = details.strip()
        lines = details.split('\n')
        first_line = lines[0] if lines else ''
        
        if len(first_line) > 100:
            # Consider only the first 100 characters for truncation
            first_100_chars = first_line[:100]
            # Regular expression to match common emoji patterns
            emoji_pattern = re.compile(
                '['
                '\U0001F600-\U0001F64F'  # emoticons
                '\U0001F300-\U0001F5FF'  # symbols & pictographs
                '\U0001F680-\U0001F6FF'  # transport & map symbols
                '\U0001F1E0-\U0001F1FF'  # flags (iOS)
                '\U00002702-\U000027B0'  # Dingbats
                '\U000024C2-\U0001F251' 
                ']+', flags=re.UNICODE
            )
            match = emoji_pattern.search(first_100_chars)
            if match:
                truncated_first_line = first_100_chars[:match.start()]
            else:
                dot_index = first_100_chars.find('.')
                if dot_index != -1:
                    truncated_first_line = first_100_chars[:dot_index + 1]
                else:
                    exclam_index = first_100_chars.find('!')
                    if exclam_index != -1:
                        truncated_first_line = first_100_chars[:exclam_index + 1]
                    else:
                        truncated_first_line = first_100_chars

            rest_of_details = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
            rest_of_details = truncated_first_line + '\n' + rest_of_details
            first_line = truncated_first_line
        else:
            rest_of_details = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''

        first_line = custom_title(first_line)

        return first_line, rest_of_details
    return '', ''

def user_query (service, user):
    if re.match('[0-9]*', user): 
        coomer_getuser_url = f'https://coomer.su/api/v1/{service}/user/{user}/profile'
        log.debug(coomer_getuser_url)
        user_lookup_response = requests.get(coomer_getuser_url, headers=headers)
        if user_lookup_response.status_code == 200:
            data = user_lookup_response.json()
            log.debug(data)
            return data['name']
    return user
       
def post_query(service, user_id, id):
    coomer_getpost_url = f'https://coomer.su/api/v1/{service}/user/{user_id}/post/{id}'
    post_lookup_response = requests.get(coomer_getpost_url, headers=headers)

    if post_lookup_response.status_code == 200:
        data = post_lookup_response.json()
        log.debug(data)
        post = data['post']
        user_name = user_query(service, user_id)
        
        if service == 'onlyfans':
            studio = {'Name': f'{user_name} (OnlyFans)', 'URL': f'https://onlyfans.com/{user_name}'}
        elif service == 'fansly':
            studio = {'Name': f'{user_name} (Fansly)', 'URL': f'https://fansly.com/{user_name}'}
        elif service == 'candfans':
            studio = {'Name': f'{user_name} (CandFans)', 'URL': f'https://candfans.com/{user_name}'}
        else:
            studio = {'Name': f'{user_name}'}
            debugPrint('No service listed')

        mentions, hashtags = extract_mentions_and_tags(post.get('content', ''))

        unique_performers = {user_name}  
        unique_performers.update(mentions)  

        if post['tags'] is not None:
            tags = [{'name': item} for item in post['tags']]
        else:
            tags = [{'name': tag} for tag in hashtags]

        first_line, rest_of_details = clean_text(post['content'])

        out = {
            'Title': first_line,
            'Date': post['published'].split('T')[0],
            'URL': f'https://coomer.su/{post["service"]}/user/{post["user"]}/post/{post["id"]}',
            'Details': rest_of_details,
            'Studio': studio,
            'Performers': [{'Name': name, 'urls': [studio['URL']]} for name in unique_performers],
            'Tags': tags,
        }

        log.debug(out)
        return out
    else:
        debugPrint(f'Response: {str(post_lookup_response.status_code)} \n Text: {str(post_lookup_response.text)}')


def get_scene(inputurl):    
    match = re.search(r'/(\w+?)/user/(.+?)/post/(\d+)', inputurl)
    if match:
        service = match.group(1)
        user = match.group(2)
        id = match.group(3)
    else:
        debugPrint('No post ID found in URL. Please make sure you are using the correct URL.')
        sys.exit()

    return post_query(service, user, id)

def sceneByFragment(fragment):
    file = fragment[0]
    with open(file['path'], 'rb') as f:
        bytes = f.read()
        readable_hash = hashlib.sha256(bytes).hexdigest()
        log.debug(f'sha256 hash: {readable_hash}')

    coomer_searchhash_url = 'https://coomer.su/api/v1/search_hash/'

    hash_lookup_response = requests.get(coomer_searchhash_url + str(readable_hash), headers=headers)


    if hash_lookup_response.status_code == 200:
        data = hash_lookup_response.json()
        post = data['posts'][0]  # Not sure why there would be more than one result, we'll just use the first one
           
        return post_query(post['service'], post['user'], post['id'])

    else:
        debugPrint('The hash of the file was not found. Please make sure you are using an original file.')


if sys.argv[1] == 'sceneByURL':
    i = readJSONInput()
    log.debug(i)
    ret = get_scene(i.get('url'))
    log.debug(f'Returned from search: {json.dumps(ret)}')
    print(json.dumps(ret))

if sys.argv[1] == 'sceneByFragment':
    i = readJSONInput()
    log.debug(f'Existing scene data: {json.dumps(i)}')
    ret = sceneByFragment(i['files'])
    log.debug(f'Returned from search: {json.dumps(ret)}')
    print(json.dumps(ret))
