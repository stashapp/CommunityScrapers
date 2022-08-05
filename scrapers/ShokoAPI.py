from urllib.request import Request, urlopen
import sys
import json
import re
import urllib.request, urllib.error
from xmlrpc.client import boolean

try:
    import requests
    from requests.utils import requote_uri
    from requests.structures import CaseInsensitiveDict
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()


#user inputs start
Apikey = '' #it gets Shoko apikey with get_apikey
StashAPIKEY = "" #your Stash apikey
Stashurl = "http://localhost:9999/graphql" #your stash playground url
Shokourl = "http://localhost:8111" #your shoko server url
Shoko_user = "" #your shoko server username
Shoko_pass = "" #your shoko server password
#user inputs end




def validate_user_inputs(result):
  result = False
  shoko = bool(re.search(r"^(http|https)://.+:\d+$", Shokourl))
  if shoko == False:
    LogError("Shoko Url needs to be hostname:port and is currently " + Shokourl)
  stash = bool(re.match(r"^(http|https)://.+:\d+/graphql$", Stashurl))
  if stash == False:
    LogError("Stash Url needs to be hostname:port/graphql and is currently " + Stashurl)
  data = [shoko, stash]
  if sum(data) == len(data):
    result = True
  return result


def __prefix(levelChar):
    startLevelChar = b'\x01'
    endLevelChar = b'\x02'

    ret = startLevelChar + levelChar + endLevelChar
    return ret.decode()

def __log(levelChar, s):
    if levelChar == "":
        return

    print(__prefix(levelChar) + s + "\n", file=sys.stderr, flush=True)

def LogTrace(s):
    __log(b't', s)

def LogDebug(s):
    __log(b'd', s)

def LogInfo(s):
    __log(b'i', s)

def LogWarning(s):
    __log(b'w', s)

def LogError(s):
    __log(b'e', s)

def get_filename(scene_id):
  LogDebug("stash sceneid: " + scene_id)
  headers = CaseInsensitiveDict()
  headers["ApiKey"] = StashAPIKEY
  headers["Content-Type"] = "application/json"
  data = data = '{ \"query\": \" query { findScene (id: ' + scene_id + ' ) {path , id} }\" }'
  resp = requests.post(url = Stashurl, headers = headers, data = data)
  if resp.status_code == 200:
    LogDebug("Stash response was stash successful resp_code: " + str(resp.status_code))
  else:
    LogError("response from stash was not successful stash resp_code: " + str(resp.status_code))
    return
  output = resp.json()
  path = output['data']['findScene']['path']
  LogDebug("scene path in stash: " + str(path))
  pattern = "(^.+)([\\\\]|[/])"
  replace = ""
  filename = re.sub(pattern, replace, str(path))
  LogDebug("encoded filename: " + filename)
  return filename

def find_scene_id(scene_id):
  if Apikey == "":
    apikey = get_apikey()
  else:
    apikey = Apikey
  filename = get_filename(scene_id)
  return filename, apikey

def lookup_scene(scene_id, epnumber, apikey, date):
  apikey = apikey
  LogDebug(epnumber)
  title, details, cover, tags = get_series(apikey, scene_id) #, characters
  tags = tags + ["ShokoAPI"] + ["Hentai"]
  #characters_json = json.dumps(characters)
  #JSON_object = json.loads(characters_json)
  #character = JSON_object[0]['character']
  #LogInfo(str(character))
  res={}
  res['title'] = title + " 0" + epnumber
  res['details'] = details
  res['image'] = cover
  res['date'] = date
  res['tags'] = [{"name":i} for i in tags]
  LogDebug("sceneinfo from Shoko: " + str(res))
  return res


def get_apikey():
  headers = CaseInsensitiveDict()
  headers["Content-Type"] = "application/json"

  values = '{"user": "' + Shoko_user + '","pass": "' + Shoko_pass + '","device": "Stash Scan"}'
  
  resp = requests.post(Shokourl + '/api/auth', data=values, headers=headers)
  apikey = str(resp.json()['apikey'])
  if apikey == None:
    LogError("could not get shokos apikey")
  else:
    LogDebug("got apikey")
  return apikey

def find_scene(apikey, filename):
  headers = CaseInsensitiveDict()
  headers["apikey"] = apikey
  url_call = requote_uri(Shokourl + '/api/ep/getbyfilename?filename=' + filename)
  LogDebug("using url: " + url_call)
  request = Request(url_call, headers=headers)

  try:
   response_body = urlopen(request).read()
  except urllib.error.HTTPError as e:
    if e.code == 404:
      LogInfo("the file: " + filename + " is not matched on shoko")
  except urllib.error.URLError as e:
    # Not an HTTP-specific error (e.g. connection refused)
    # ...
    LogError('URLError: {}'.format(e.reason))
  else:
    # 200
    LogInfo("the file: " + filename + " is matched on shoko")
    JSON_object = json.loads(response_body.decode('utf-8'))
    LogDebug("found scene\t" + str(JSON_object))
    scene_id = JSON_object['id']
    epnumber = str(JSON_object['epnumber']) + ' ' + str(JSON_object['name'])
    date = JSON_object['air']
    return scene_id, epnumber, date

def get_series(apikey, scene_id): 
  headers = CaseInsensitiveDict()
  headers["apikey"] = apikey
  request = Request(Shokourl + '/api/serie/fromep?id=' + scene_id, headers=headers)

  
  response_body = urlopen(request).read()
  JSON_object = json.loads(response_body.decode('utf-8'))
  LogDebug("got series:\t" + str(JSON_object))
  title = JSON_object['name']
  details = JSON_object['summary']
  local_sizes = JSON_object['local_sizes']['Episodes']
  LogDebug("number of episodes " + str(local_sizes))
  #characters = JSON_object['roles']
  cover = Shokourl + JSON_object['art']['thumb'][0]['url']
  tags = JSON_object['tags']
  return title, details, cover, tags#, characters

def query(fragment):
    filename, apikey = find_scene_id(fragment['id'])
    try:
      findscene_scene_id, findscene_epnumber, find_date = find_scene(apikey, filename)
    except:
      return
    else:
      scene_id = str(findscene_scene_id)
      epnumber = str(findscene_epnumber)
      date = str(find_date)
      apikey = str(apikey)
      LogDebug("Found scene id: " + scene_id)
      result = lookup_scene(scene_id, epnumber, apikey, date)
      return(result)

def main():
  mode = sys.argv[1]
  fragment = json.loads(sys.stdin.read())
  LogDebug(str(fragment))
  data = None
  result = False
  check_input = validate_user_inputs(result)
  if check_input == True:
    if mode == 'query':
      data = query(fragment)
  print(json.dumps(data))

if __name__ == '__main__':
  main()
