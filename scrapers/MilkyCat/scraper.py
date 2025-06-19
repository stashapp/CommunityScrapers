import json
import sys
import re
import bs4
import requests  
from os import path
import datetime
import urllib.parse
from py_common.cache import cache_to_disk

@cache_to_disk(ttl=24 * 60 * 60)
def fetchNews():
  news_url = "https://www.milky-cat.com/movie/news.html"
  content = requests.get(news_url).text
  soup = bs4.BeautifulSoup(content, 'html.parser')
  lines = [[l.strip() for l in s.split("\n")] for s in soup.select_one("td").text.split("\n\n")]
  # Look for the first news item that looks like:
  # 2013/7/12 add movie.
  # 2007/9/10 add 2 movies.
  news = []
  for line in lines:
    e = re.match(r"^([0-9]{4}\/[0-9]{1,2}\/[0-9]{1,2}) add (?:\d+ movies|movie).$", line[0])
    if not e:
      continue
    date = e.group(1)
    year, month, day = map(int, date.split("/"))
    news_date = datetime.date(year, month, day)
    if news_date > datetime.date.today():
      continue
    for line in line[1:]:
      # if we can match the regex for "<long title> (<studio_code>)", then we have a match
      e = re.match(r"^- ([^(]+)\(([a-zA-Z0-9]{2,4}\s?-\s?[a-zA-Z0-9]{2,4})\)$", line)
      if e:
        news.append({
          "Title": e.group(1),
          "Code": e.group(2),
          "Date": news_date.strftime("%Y-%m-%d"),
        })
  return news

def readJSONInput(): 
	input = sys.stdin.read()
	return json.loads(input)

def debugPrint(t):
    sys.stderr.write(t + "\n")

def prettyCodeFromURL(url):
  query = urllib.parse.urlparse(url).query
  # we get something like 'blt04'
  m = re.match(r"^([a-z]{2,4})(\d{1,4})$", query)
  if m:
    return f"{m.group(1)}-{m.group(2)}".upper()
  return None

def sceneByURL(url):
  # debugPrint(f"sceneByURL({url})")
  content = requests.get(url).text
  soup = bs4.BeautifulSoup(content, 'html.parser')
  title = soup.select_one(".title_p").text
  desc = "\n".join([e.text for e in soup.select(".main_p")])
  table = [[str(e2.text).strip("：") for e2 in e.select("td")] for e in soup.select_one("div.product_2").select("tr")]
  category = next(filter(lambda x: x[0] == "category", table), [None, None])[1]
  jackett = soup.select_one(".jacket")
  image_url = jackett["href"] if jackett else None
  image = image_url if requests.head(image_url).status_code == 200 else None
  pretty_code = prettyCodeFromURL(url)
  # debugPrint(f"pretty_code: {pretty_code}")
  news = fetchNews()
  # debugPrint(f"news: {news}")
  matching_news = next(filter(lambda x: x["Code"] == pretty_code, news), None)
  out = {
    "Title": title,
    "Details": desc,
    "Image": image,
    "Url": url,
    # "category": category,
    # "tags": [e[0] for e in table if e[0] != "category"],
  }
  if matching_news:
    # format in Go format: 2006-01-02
    out["Date"] = matching_news["Date"]
  else:
    # debugPrint(f"No matching news for {pretty_code}")
    pass

  return [out]
def sceneByName(name):
  # debugPrint(f"sceneByName({name})")
  # remove all spaces and anyting not in [a-zA-Z0-9] after the regex /[a-zA-Z]{2,4}\s?-\s?[0-9]{1,4}/
  clean = re.sub(r"[^a-zA-Z0-9]", "", name)
  url = f"https://www.milky-cat.com/movie/indexe.php?{clean}"
  return sceneByURL(url)

def sceneByNameSmart(name):
  # debugPrint(f"sceneByNameSmart({name})")
  # remove all spaces and anyting after the regex /[a-zA-Z]{2,4}\s?-\s?[0-9]{1,4}/
  e = re.match(r"^([a-zA-Z0-9]{2,4})\s?-\s?([0-9]{1,4})", name)
  if e:
    studio = e.group(1).lower()
    scene = e.group(2).lower()
  else:
    # debugPrint(f"sceneByNameSmart: No match for {name}")
    return []
  new_name = f"{studio}{scene}"
  return sceneByName(new_name)

def sceneByQueryFragment(fragment):
  # debugPrint(f"sceneByQueryFragment({fragment})")
  if "filename" in fragment:
    return sceneByNameSmart(fragment["filename"])
  elif "url" in fragment:
    return sceneByURL(fragment["url"])
  elif "title" in fragment:
    return sceneByNameSmart(fragment["title"])
  else:
    # debugPrint(f"sceneByQueryFragment: No match for {fragment}")
    return []

def sceneByFragment(fragment):
  # debugPrint(f"sceneByFragment({fragment})")
  if fragment["url"]:
    return sceneByURL(fragment["url"])
  elif fragment["files"]:
    files = fragment["files"]
    if len(files) == 0:
      return []
    elif len(files) == 1:
      return sceneByNameSmart(path.basename(files[0]["path"]))
  else:
    # debugPrint(f"sceneByFragment: No match for {fragment}")
    return []

def getFirstOrNone(l):
  # # debugPrint(f"getFirstOrNone({l})")
  # if it is a list of length 1, return the first element
  try:
    return l[0]
  except IndexError:
    return None



# read the input 
i = readJSONInput()

if sys.argv[1] == "sceneByURL":
    ret = sceneByURL(i['url'])
    print(json.dumps(getFirstOrNone(ret)))
elif sys.argv[1] == "sceneByName":
    ret = sceneByNameSmart(i['name'])
    print(json.dumps(ret))
elif sys.argv[1] == "sceneByQueryFragment":
    ret = sceneByQueryFragment(i)
    print(json.dumps(getFirstOrNone(ret)))
elif sys.argv[1] == "sceneByFragment":
    ret = sceneByFragment(i)
    print(json.dumps(getFirstOrNone(ret)))
else:
    print("Unknown command")
    exit(1)