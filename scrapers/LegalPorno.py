import json
import sys
import requests
from pathlib import Path

def debug(t):
  sys.stderr.write(t + "\n")

def query_url(query):
  res = requests.get(f"https://www.legalporno.com/api/autocomplete/search?q={query}")
  data = res.json()
  results = data['terms']
  if len(results) > 1:
    debug("Multiple results. Taking first.")
  return results[0]

def detect_delimiter(title):
  delimiters = [" ", "_", "-", "."]
  for d in delimiters:
    if d in title:
      return d

  debug(f"Could not determine delimiter of `{title}`")

def find_scene_id(title):
  # Remove file extension
  title = Path(title).stem
  title = title.replace("'", "")
  delimiter = detect_delimiter(title)
  parts = title.split(delimiter)
  for part in parts:
    if len(part) > 3:
      if part == part.upper():
        if not part[0].isdigit() and part[-1].isdigit():
          return part

if sys.argv[1] == "query":
  fragment = json.loads(sys.stdin.read())
  debug(json.dumps(fragment))

  scene_id = find_scene_id(fragment['title'])
  if not scene_id:
    debug(f"Could not determine scene id in title: `{fragment['title']}`")
  else:
    debug(f"Found scene id: {scene_id}")
    result = query_url(scene_id)
    if result["type"] == "scene":
      debug(f"Found scene {result['name']}")
      fragment["url"] = result["url"]
      fragment["title"] = result["name"]
  print(json.dumps(fragment))
