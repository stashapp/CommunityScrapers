import json
import sys
import re
import requests
import time

# initialize the session for making requests
session = requests.session()

try:
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit(1)

try:
    from lxml import html
except ModuleNotFoundError:
    print("You need to install the lxml module. (https://lxml.de/installation.html#installation)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml",
          file=sys.stderr)
    sys.exit()


#  --------------------------------------------
# This is a scraper for: RealityLovers sites
#

def get_scraped(inp):
    if not inp['url']:
        log.error('No URL Entered')
        return None

    # get the url specified in the input and validate the response code
    scraped = session.get(inp['url'])
    if scraped.status_code >= 400:
        log.error('HTTP Error: %s' % scraped.status_code)
        return None
    log.trace('Scraped the url: ' + inp["url"])
    return scraped

def performerByURL():
    # read the input.  A URL must be passed in for the sceneByURL call
    inp = json.loads(sys.stdin.read())
    scraped = get_scraped(inp)
    if not scraped:
        return {}

    # get the data we can scrape directly from the page
    tree = html.fromstring(scraped.content)
    name = "".join(tree.xpath('//div[@class="girlDetails-details"]/h1/text()')).strip()
    main_image_src = re.sub(r'.*1x,(.*) 2x', r'\1', tree.xpath('//img[@class="girlDetails-posterImage"]/@srcset')[0])
    birthdate = time.strptime(
        re.sub(r"(st|nd|rd|th)", r"", tree.xpath('//*[text()="Birthday:"]/../following-sibling::dd/text()')[0].strip()),
        '%b %d %Y')
    country = tree.xpath('//*[text()="Country:"]/../following-sibling::dd/text()')[0].strip()
    measurements = tree.xpath('//*[text()="Cup:"]/../following-sibling::dd/text()')[0].strip()
    height = re.sub(r".*\(([0-9]*) cm\)",
                    r"\1",
                    tree.xpath('//*[text()="Height:"]/../following-sibling::dd/text()')[0].strip())
    weight = re.sub(r".*\(([0-9]*) kg\)",
                    r"\1",
                    tree.xpath('//*[text()="Weight:"]/../following-sibling::dd/text()')[0].strip())
    socials = tree.xpath('//*/a[@class="girlDetails-socialIcon"]/@href')
    tags = tree.xpath('//*/a[@itemprop="keyword"]/text()')
    details = tree.xpath('//*/p[@class="girlDetails-bioText"]/text()')[0].strip()

    return {
        "Name": name,
        # making some assumptions here
        "Gender": "transgender_female" if re.match(r'.*tsvirtuallovers.*', inp['url'], re.IGNORECASE) else "female",
        "URL": inp['url'],
        "Twitter": next((social for social in socials if re.match(r'.*twitter.*', social, re.IGNORECASE)), ""),
        "Instagram": next((social for social in socials if re.match(r'.*instagram.*', social, re.IGNORECASE)), ""),
        "Birthdate": time.strftime("%Y-%m-%d", birthdate),
        "Country": country,
        "Height": height,
        "Weight": weight,
        "Measurements": measurements,
        "Tags": [{
            'name': x
        } for x in tags],
        "Image": main_image_src,
        "Details": details,
    }


def sceneByURL():
    # read the input.  A URL must be passed in for the sceneByURL call
    inp = json.loads(sys.stdin.read())
    scraped = get_scraped(inp)
    if not scraped:
        return {}

    # get the data we can scrape directly from the page
    tree = html.fromstring(scraped.content)
    title = "".join(tree.xpath('//*[@class="video-detail-name"]/text()')).strip()
    details = tree.xpath('//*[@itemprop="description"]/text()[1]')[0].strip()
    details = details + " " + tree.xpath('//*[@itemprop="description"]/span/text()')[0].strip()
    images = tree.xpath('//*[@itemprop="thumbnail"]/@data-big')
    image_url = ""
    if len(images) > 0:
        image_url = re.sub(r' .*', r'', images[0])
    tags = tree.xpath('//a[@itemprop="keyword"]/text()')
    actors = tree.xpath('//a[@itemprop="actor"]/text()')
    studio = tree.xpath('//span[@class="icon header-logo"]/text()')[0]

    # create our output
    return {
        'title': title,
        'tags': [{
            'name': x
        } for x in tags],
        'details': details,
        'image': image_url,
        'studio': {
            'name': studio
        },
        'performers': [{
            'name': x
        } for x in actors]
    }


# Get the scene by the fragment.  The title is used as the search field.  Should return the JSON response.
# This is a script instead of a JSON scraper since the search is a POST
def sceneByName():
    # read the input.  A title or name must be passed in
    inp = json.loads(sys.stdin.read())
    log.trace("Input: " + json.dumps(inp))
    query_value = inp['title'] if 'title' in inp else inp['name']
    if not query_value:
        log.error('No title or name Entered')
        return []
    log.trace("Query Value: " + query_value)

    # call the query url based on the input and validate the response code
    data = {
        "sortBy": "MOST_RELEVANT",
        "searchQuery": query_value,
        "offset": 0,
        "isInitialLoad": True,
        "videoView": "MEDIUM",
        "device": "DESKTOP"
    }
    scraped_scenes = session.post(f"https://realitylovers.com/videos/search?tc={time.time()}",
                                  data=data)
    log.debug("Called: " + scraped_scenes.url + " with body: " + json.dumps(data))
    if scraped_scenes.status_code >= 400:
        log.error('HTTP Error: %s' % scraped_scenes.status_code)
        return []

    # get the data we can scrape directly from the page
    scenes = json.loads(scraped_scenes.content)
    log.debug("Scenes: " + json.dumps(scenes))
    results = []
    for scene in scenes['contents']:
        # Parse the date published.  Get rid of the 'st' (like in 1st) via a regex. ex: "Sep 27th 2018"
        published = time.strptime(re.sub(r"(st|nd|rd|th)", r"", scene['released']), '%b %d %Y')
        main_image_src = re.sub(r'.*1x,(.*) 2x', r'\1', scene['mainImageSrcset'])
        log.debug("Image: " + main_image_src)
        # Add the new scene to the results
        results.append({
            'Title': scene['title'],
            'URL': "https://realitylovers.com/" + scene['videoUri'],
            'Image': main_image_src,
            'Date': time.strftime("%Y-%m-%d", published)
        })

    # create our output
    return results


# Figure out what was invoked by Stash and call the correct thing
if sys.argv[1] == "performerByURL":
    print(json.dumps(performerByURL()))
elif sys.argv[1] == "sceneByURL":
    print(json.dumps(sceneByURL()))
elif sys.argv[1] == "sceneByName":
    scenes = sceneByName()
    print(json.dumps(scenes))
elif sys.argv[1] == "sceneByQueryFragment" or sys.argv[1] == "sceneByFragment":
    scenes = sceneByName()
    if len(scenes) > 0:
        # return the first query result
        print(json.dumps(scenes[0]))
    else:
        # empty array for no results
        log.info("No results")
        print("{}")
else:
    log.error("Unknown argument passed: " + sys.argv[1])
    print(json.dumps({}))
