import re, sys, copy, json
import requests

import stashutils.log as log
from traxxx_interface import TraxxxInterface

def main():
  global traxxx

  mode = sys.argv[1]
  traxxx = TraxxxInterface()
  fragment = json.loads(sys.stdin.read())

  data = None

  log.info(mode)

  if mode == 'scene_name':
    data = scene_name(fragment)
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


  if data:
    # log.info(json.dumps(data))
    print(json.dumps(data))
  else:
    print("")

# Return a list of scenes from a search
def scene_name(fragment):
  title = None
  if not title:
    title = fragment.get("title")
  if not title:
    title = fragment.get("name")
  if not title:
    return

  scenes = traxxx.search_scenes(title)
  return scenes

# extract TraxxxID from passed fragment and return new fragment
def scene_query_fragment(fragment):
  scene = traxxx.get_scene(fragment.get("remote_site_id"))
  return scene

# return first result from scene_name
def scene_fragment(fragment):
  return scene_name(fragment)[0]

# Return a list of possible performer matches
def performer_lookup(fragment):
  performers = traxxx.search_performers(fragment["name"])
  return performers

# Return a single best guess for performer based on fragment
def performer_fragment(fragment):
  performer = performer_lookup(fragment)[0]
  return performer

# Get PerformerID from URL and do a lookup on it
def performer_url(fragment):
  m = re.search(r'actor/(\d+)/', fragment['url'])
  if not m:
    return
  performer_id = m.group(1)
  performer = traxxx.get_performer(performer_id)
  return performer


if __name__ == '__main__':
  main()