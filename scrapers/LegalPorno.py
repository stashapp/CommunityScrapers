import json
import sys
import re
from pathlib import Path

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

def debug(t):
  sys.stderr.write(t + "\n")

def query_url(query):
  res = requests.get(f"https://www.analvids.com/api/autocomplete/search?q={query}")
  data = res.json()
  results = data['terms']
  if len(results) > 0:
    if len(results) > 1:
      debug("Multiple results. Taking first.")
    return results[0]
  
def detect_delimiter(title):
  delimiters = [" ", "_", "-", "."]
  for d in delimiters:
    if d in title:
      return d

  debug(f"Could not determine delimiter of `{title}`")


def find_scene_id(title, strict):
  # Remove file extension
  title = Path(title).stem
  title = title.replace("'", "")
  delimiter = detect_delimiter(title)
  parts = title.split(delimiter)
  for part in parts:
    if len(part) > 3:
      if re.match(r'^(\w{2,3}\d{3,4})$', part):
        if not part[0].isdigit() and part[-1].isdigit():
          return part

  # if we're here, the previous method didn't work. Let's try to remove whitespaces and match the most common IDs
  title = title.replace(" ","");
  if (strict):
    id = re.search("(GL|GIO|XF|SZ|GP|AA|RS|OB|BTG|EKS)\d{3}", title)
  else:
    id = re.search("(GL|GIO|XF|SZ|GP|AA|RS|OB|BTG|EKS)\d{3,4}", title)

  if id:
    return id.group()

def search_scene(fragment):
  title = fragment['title']

  scene_id = find_scene_id(title, False)
  if not scene_id:
    debug(f"Could not determine scene id in title: `{title}`")
    return

  strict_scene_id = find_scene_id(title, True)

  debug(f"Found scene id: {scene_id}")

  result = query_url(scene_id)
  if result is None:
    if strict_scene_id is None:
      debug("No scenes found")
      return

    result = query_url(strict_scene_id)
    if result is None:
      debug("No scenes found")
      return

  if result["type"] == "scene":
    debug(f"Found scene {result['name']}")
    fragment["url"] = result["url"]
    fragment["title"] = result["name"]

    


if sys.argv[1] == "query":
  fragment = json.loads(sys.stdin.read())
  debug(json.dumps(fragment))

  search_scene(fragment)

  print(json.dumps(fragment))
