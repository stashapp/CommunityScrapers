from urllib.request import Request, urlopen
import sys
import json
import re
import urllib.request, urllib.error

try:
    import requests
    from requests.structures import CaseInsensitiveDict
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()


Apikey = '' #it gets Shoko apikey with get_apikey
StashAPIKEY = "" #your Stash apikey
Stashurl = "http://localhost:9999/graphql" #your stash playground url
Shokourl = "http://localhost:8111" #your shoko server url
Shoko_user = "" #your shoko server username
Shoko_pass = "" #your shoko server password

def debug(q):
    print(q, file=sys.stderr)

def get_filename(scene_id):
  debug(scene_id)
  headers = CaseInsensitiveDict()
  headers["ApiKey"] = StashAPIKEY
  headers["Content-Type"] = "application/json"
  #'{"query":"query{findScene(id: 4071){path , id}}"}' --compressed
  data = data = '{ \"query\": \" query { findScene (id: ' + scene_id + ' ) {path , id} }\" }'
  resp = requests.post(url = Stashurl, headers = headers, data = data)
  debug(resp.status_code)
  output = resp.json()
  path = output['data']['findScene']['path']
  debug(str(path))
  pattern = "(^.+)([\\\\]|[/])"
  replace = ""
  filename = re.sub(pattern, replace, str(path))
  filename = requests.utils.quote(filename)
  return filename

def find_scene_id(scene_id):
  if Apikey == "":
    apikey = get_apikey()
  else:
    apikey = Apikey
  filename = get_filename(scene_id)
  debug(filename)
  findscene_scene_id, findscene_epnumber, find_date = find_scene(apikey, filename)
  scene_id = str(findscene_scene_id)
  epnumber = str(findscene_epnumber)
  date = str(find_date)
  return scene_id, epnumber, apikey, date

def lookup_scene(scene_id, epnumber, apikey, date):
  apikey = apikey
  debug(epnumber)
  title, details, cover, tags = get_series(apikey, scene_id) #, staff, staff_image, character
  tags = tags + ["ShokoAPI"] + ["Hentai"]
  #staff = staff
  #staff_image = staff_image
  res={}
  res['title'] = title + " 0" + epnumber
  res['details'] = details
  res['image'] = cover
  res['date'] = date
  res['tags'] = [{"name":i} for i in tags]
  #perf  = {}
  #perf['name'] = staff
  #perf['image'] = staff_image
  #res['performers'] = perf
  debug(tags)
  debug(res)
  return res


def get_apikey():
  headers = CaseInsensitiveDict()
  headers["Content-Type"] = "application/json"

  values = '{"user": "' + Shoko_user + '","pass": "' + Shoko_pass + '","device": "Stash Scan"}'
  
  resp = requests.post(Shokourl + '/api/auth', data=values, headers=headers)
  apikey = str(resp.json()['apikey'])
  return apikey

def find_scene(apikey, filename):
  headers = CaseInsensitiveDict()
  headers["apikey"] = apikey

  request = Request(Shokourl + '/api/ep/getbyfilename?filename=' + filename, headers=headers)

  try:
   response_body = urlopen(request).read()
  except urllib.error.HTTPError as e:
    if e.code == 404:
      debug("the file: " + filename + " is not matched on shoko")
      error = ["Shoko_not_found"]
      not_found(error)
    debug('HTTPError: {}'.format(e.code))
  except urllib.error.URLError as e:
    # Not an HTTP-specific error (e.g. connection refused)
    # ...
    debug('URLError: {}'.format(e.reason))
  else:
    # 200
    # ...
    debug('good')
    JSON_object = json.loads(response_body.decode('utf-8'))
    debug("found scene\t" + str(JSON_object))
    scene_id = JSON_object['id']
    epnumber = str(JSON_object['epnumber']) + ' ' + str(JSON_object['name'])
    date = JSON_object['air']
    return scene_id, epnumber, date

def not_found(error):
  tags = error + ["Shoko_error"]
  res={}
  res['tags'] = [{"name":i} for i in tags]
  print(json.dumps(res))
  error_exit()

def error_exit():
  sys.exit()

def get_series(apikey, scene_id): 
  headers = CaseInsensitiveDict()
  headers["apikey"] = apikey
  request = Request(Shokourl + '/api/serie/fromep?id=' + scene_id, headers=headers)

  
  response_body = urlopen(request).read()
  JSON_object = json.loads(response_body.decode('utf-8'))
  debug("got series:\t" + str(JSON_object))
  title = JSON_object['name']
  details = JSON_object['summary']
  local_sizes = JSON_object['local_sizes']['Episodes']
  debug("number of episodes " + str(local_sizes))
  #staff = JSON_object['roles'][0]['staff']
  #staff_image = Shokourl + JSON_object['roles'][0]['staff_image']
  #character = JSON_object['roles'][0]['character']
  cover = Shokourl + JSON_object['art']['thumb'][0]['url']
  tags = JSON_object['tags']
  #debug("staff: " + staff + "\tImage: " + staff_image)
  return title, details, cover, tags, #staff, staff_image, character

if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    print(json.dumps(fragment),file=sys.stderr)
    fscene_id, fepnumber, fapikey, fdate = find_scene_id(fragment['id'])
    scene_id = str(fscene_id)
    epnumber = str(fepnumber)
    apikey = str(fapikey)
    date = str(fdate)
    if not scene_id:
      print(f"Could not determine scene id in filename: `{fragment['id']}`",file=sys.stderr)
    else:
      print(f"Found scene id: {scene_id}",file=sys.stderr)
      result = lookup_scene(scene_id, epnumber, apikey, date)
      print(json.dumps(result))
