import re, sys, copy, json

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()
    
try:
    from traxxx_interface import TraxxxInterface
except ModuleNotFoundError:
    print("You need to download the file 'traxxx_interface.py' from the community repo! (CommunityScrapers/tree/master/scrapers/traxxx_interface.py)", file=sys.stderr)
    sys.exit()

def main():
  global traxxx

  mode = sys.argv[1]
  traxxx = TraxxxInterface()
  fragment = json.loads(sys.stdin.read())

  data = None

  log.info(mode)

  if mode == 'scene_name':
    data = scene_by_name(fragment)
  if mode == 'scene_url':
    data = scene_query_fragment(fragment)
  if mode == 'scene_query_fragment':
    data = scene_query_fragment(fragment)
  if mode == 'scene_fragment':
    data = scene_fragment(fragment)

  if mode == 'performer_lookup':
    data = performer_lookup(fragment)
  if mode == 'performer_fragment':
    data = performer_fragment(fragment)
  if mode == 'performer_url':
    data = performer_url(fragment)

  # log.info(json.dumps(data))
  print(json.dumps(data))

def search_traxxx_for_scene(fragment):
  title = fragment.get("title")
  if not title:
    title = fragment.get("name")
  if not title:
    return
  return traxxx.search_scenes(title)

# Return a list of scenes from a search
def scene_by_name(fragment):
  scenes = search_traxxx_for_scene(fragment)
  if scenes:
    return [traxxx.parse_to_stash_scene_search(s) for s in scenes]
  else:
    log.warning("No scene results from Traxxx")
    return []

# extract TraxxxID from passed fragment and return new fragment
def scene_query_fragment(fragment):
  traxxx_url = fragment.get("url", "")
  m = re.search(r'traxxx.me/scene/(\d+)/', traxxx_url)
  if not m:
    log.warning(f'could not parse scene ID from URL: {traxxx_url}')
    return
  scene_id = m.group(1)
  scene = traxxx.get_scene(scene_id)
  return traxxx.parse_to_stash_scene(scene)

# return first result from scene_name
def scene_fragment(fragment):
  scenes = search_traxxx_for_scene(fragment)
  if scenes:
    return traxxx.parse_to_stash_scene(scenes[0])

# Return a list of possible performer matches
def performer_lookup(fragment):
  performers = traxxx.search_performers(fragment["name"])
  if performers:
    return [traxxx.parse_to_stash_performer_search(p) for p in performers]
  else:
    log.warning("No performer results from Traxxx")
    return []

# Return a single best guess for performer based on fragment
def performer_fragment(fragment):
  # check if fragment has Traxxx URL
  performer = performer_url(fragment)
  if performer:
    return performer

  # search and take first result from lookup
  performer = performer_lookup(fragment)[0]
  return performer

# Get PerformerID from URL and do a lookup on it
def performer_url(fragment):
  m = re.search(r'traxxx.me/actor/(\d+)/', fragment['url'])
  if not m:
    return
  performer_id = m.group(1)
  performer = traxxx.get_performer(performer_id)
  return traxxx.parse_to_stash_performer(performer)


if __name__ == '__main__':
  main()
