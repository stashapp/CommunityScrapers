import json
import sys
import requests
import re
from py_common import log

def strip_html_tags(text):
  return re.sub(r"<[^>]+>", "", text)

def scrape_scene(slug): 
  data = requests.get(f"https://api.faknetworks.com/v1/public/videos/{slug}?lang=en")
  if data.status_code != 200:
    log.error(f"Failed to fetch data for {slug}: {data.status_code}")
    return None
  data = data.json()
  # extract data
  scene = {
    "Studio": { "Name": data["product"] },
    "Title": data["title"],
    "Tags": [{ "Name": category["title"] } for category in data["categories"]],
    "Details": strip_html_tags(data["description"]),
    "Code": data["slug"],
    "Performers": [{ "Name": performer["name"] } for performer in data["performers"]],
    "Date": data["date"],
    "Image": f"https://player.faknetworks.com/almacen/videos/listado_horizontal_{data["horizontalProfile"]}"
  }
  return scene


if __name__ == "__main__":
  FRAGMENT = json.loads(sys.stdin.read())
  URL = FRAGMENT.get('url')
  if sys.argv[1] == "scene-by-url":
    result = scrape_scene(URL.split("/")[-1])
  else:
    sys.exit(1)
  print(json.dumps(result))
