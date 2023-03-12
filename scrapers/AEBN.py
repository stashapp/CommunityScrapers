import sys
import random
import json
import base64
import re
import datetime

# Seperators to append scene nr to url
seperators = "+.,"

# Seperator between movie title and Scene Nr string
title_seperator = ": "

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)",
          file=sys.stderr)
    print(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests",
        file=sys.stderr)
    sys.exit()

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    print("You need to install the BeautifulSoup module. (https://pypi.org/project/beautifulsoup4/)", file=sys.stderr)
    print(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install beautifulsoup4",
        file=sys.stderr)
    sys.exit()

try:
    import dateparser
except ModuleNotFoundError:
    print("You need to install the dateparser module. (https://pypi.org/project/dateparser/", file=sys.stderr)
    print(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install dateparser",
        file=sys.stderr)
    sys.exit()

class Scene:
    def __init__(self):
        self.title = ""
        self.performers = []
        self.tags = []
        self.thumbnail = ""
        self.scene_nr = ""
        self.scene_id = ""
        self.movie = None

class Movie(Scene):
    def __init__(self):
        super().__init__()
        self.url = ""
        self.date = ""
        self.director = ""
        self.studio = ""
        self.details = ""
        self.front_cover = ""
        self.back_cover = ""
        self.scenes = []
        self.duration = ""

class Performer():
    def __init__(self):
        self.name = ""
        self.url = ""
        self.aliases = ""
        self.gender = ""
        self.birthdate = ""
        self.ethnicity = ""
        self.hair_color = ""
        self.eye_color = ""
        self.height = ""
        self.weight = ""
        self.tattoos = ""
        self.piercings = ""
        self.url = ""
        self.details = ""
        self.image = ""

def parse_scene(scene):
    scene_parsed = Scene()

    # Get scene id
    scene_parsed.scene_id = scene["id"]

    # Get scene Nr
    scene_parsed.scene_nr = int(scene.h1.span.text.replace("Scene ", ""))

    # Some thumbnails are loaded together with the page, others are loaded when the scrollbar is used
    # Get URLs of visible thumbnails
    thumb_urls = scene.findChildren("img")
    thumb_urls_parsed = []

    for thumb_url in thumb_urls:
        thumb_urls_parsed.append("https:" + thumb_url["src"].split("?")[0])

    # Get URLs of thumbnails, which are loaded when the scrollbar is used
    thumb_urls = scene.findChildren("div", {"class": "dts-collection-item dts-collection-item-scene-thumb"})

    for thumb_url in thumb_urls:
        if thumb_url.div["class"] == ["dts-lazy-loading-placeholder"]:
            thumb_urls_parsed.append("https:" + thumb_url["data-scene-thumb-image-url"].split("?")[0])

    # Choose randomly one of the thumbnails
    scene_parsed.thumbnail = random.choice(thumb_urls_parsed)

    # Get tags for current scene
    tag_groups = [child for child in scene.findChildren("span", {"class": "section-detail-list-item-title"}) if
                  "stars" not in child.text.lower()]

    for tag_group in tag_groups:
        for tag in tag_group.parent.contents:
            if tag.name == "a":
                scene_parsed.tags.append(tag.text)

    # Get performers of current scene
    performers = scene.findChildren("span", {"class": "dts-scene-star-wrapper"})

    for performer in performers:
        scene_parsed.performers.append(performer.a.text.strip())

    return scene_parsed


def parse_movie(url):

    movie = Movie()

    # Get domain name and movie path (necessary for scraping of performer names)
    match = re.search(".*[.]com", url)
    domain_name = match.group()
    movie_path = url.replace(domain_name, "")

    request = requests.get(url)
    soup = BeautifulSoup(request.text, 'html.parser')

    # Title
    movie.title = soup.h1.text

    # URL
    movie.url = url

    # Date
    date = soup.find_all("li", "section-detail-list-item-release-date")
    if len(date) > 0:
        date_str = date[0].text.replace("Released: ", "")
        movie.date = dateparser.parse(date_str)

    # Director
    director_soup = soup.find_all("li", "section-detail-list-item-director")
    if len(director_soup) > 0:
        directors = director_soup[0].find_all("a")

        for director in directors:
            movie.director = movie.director + director.text.strip() + ", "

        if movie.director[-2:] == ", ":
            movie.director = movie.director[:-2]

    # Studio
    studio = soup.find_all("div", "dts-studio-name-wrapper")

    if len(studio) > 0:
        movie.studio = studio[0].a.text

    # Performers
    performers = soup.find_all("div", "dts-collection-item dts-collection-item-star")

    for i in range(len(performers)):
        if "data-loc" in performers[i].attrs:
            # Performer is loaded on demand, if the scrollbar is used. Data is retrieved via POST request
            payload = {
                "f": movie_path,
                "fbase": movie_path,
                "starIdRoot": performers[i]["data-star-id-root"],
                "imgHeight": performers[i]["data-img-height"],
                "useHeadshot": performers[i]["data-use-headshot"],
                "useSilhouette": performers[i]["data-use-silhouette"],
                "showFavoriteLink": performers[i]["data-show-favorite-link"]
            }

            performer_request = requests.post(domain_name + performers[i]["data-loc"], params=payload)
            performer_soup = BeautifulSoup(performer_request.text, 'html.parser')
            movie.performers.append(performer_soup.a.text.strip())
        else:
            movie.performers.append(performers[i]["title"])

    # Tags
    tags = soup.find_all("div", "dts-collection-item dts-collection-item-category")

    for tag in tags:
        movie.tags.append(tag.text.strip())

    # Description
    movie.details = soup.find_all("div", "dts-section-page-detail-description-body")[0].text.strip()

    # Cover Images
    movie.front_cover = "https:" + soup.find_all("img", "dts-modal-boxcover-front")[0]["src"]
    movie.back_cover = "https:" + soup.find_all("img", "dts-modal-boxcover-back")[0]["src"]

    # Scenes
    scenes = soup.find_all("section", id=lambda x: x and x.startswith("scene"))

    for scene in scenes:
        parsed_scene = parse_scene(scene)

        # Title, URL, date, director and studio are inherited from movie
        parsed_scene.title = movie.title + title_seperator +  "Scene " + str(parsed_scene.scene_nr).zfill(2)
        parsed_scene.movie = movie

        movie.scenes.append(parsed_scene)

        # Add performers and tags from scenes to movie performers and tags
        movie.performers = movie.performers + parsed_scene.performers
        movie.tags = movie.tags + parsed_scene.tags

    # Remove duplicated performers and tags
    movie.performers = list(dict.fromkeys(movie.performers))
    movie.tags = list(dict.fromkeys(movie.tags))

    # Get movie duration
    # For some reason movie quality shares the same class as movie duration
    entries = soup.find_all("li", "section-detail-list-item-duration")

    for entry in entries:
        if "Running Time: " in entry.text:
            movie.duration = entry.text.replace("Running Time: ", "")

    return movie

def parse_performer(url):

    performer = Performer()

    request = requests.get(url)
    soup = BeautifulSoup(request.text, 'html.parser')

    # Title
    performer.name = soup.h1.text

    attributes = soup.find_all("span", "section-detail-list-item-title")

    for attribute in attributes:
        # Gender
        if "Gender" in attribute.text:
            performer.gender = attribute.parent.text.replace("Gender: ", "")

        # Birthdate
        if "Birth Date" in attribute.text:
            birthdate_str = attribute.parent.text.replace("Birth Date: ", "")

            # Datetime expects "Sep" instead of "Sept"
            birthdate_str = birthdate_str.replace("Sept", "Sep")

            birthdate = datetime.datetime.strptime(birthdate_str, "%b %d, %Y")
            performer.birthdate = birthdate.strftime("%Y-%m-%d")

        # Ethnicity
        if "Ethnicity" in attribute.text:
            performer.ethnicity = attribute.parent.text.replace("Ethnicity: ", "")

        # Hair Color
        if "Hair Color" in attribute.text:
            performer.hair_color = attribute.parent.text.replace("Hair Color: ", "")

        # Eye Color
        if "Eye Color" in attribute.text:
            performer.eye_color = attribute.parent.text.replace("Eye Color: ", "")

        # Height
        if "Height" in attribute.text:
            height_str = attribute.parent.text
            match_height = re.search("(\d*) cm", height_str)
            if match_height:
                performer.height = match_height.group(1)

        # Weight
        if "Weight" in attribute.text:
            weight_str = attribute.parent.text
            match_weight = re.search("(\d*)kg", weight_str)
            if match_weight:
                performer.weight = match_weight.group(1)

    # Details
    details = soup.find_all("div", "dts-star-bio")

    if len(details) > 0:
        performer.details = details[0].text

    # Tattoos are given in the details section
    if "Tattoos: " in performer.details:
        match_tattoos = re.search("Tattoos: (.*)", performer.details)
        if match_tattoos:
            performer.tattoos = match_tattoos.group(1)
            performer.details = performer.details.replace("Tattoos: " + performer.tattoos, "")

    if "Tattoo: " in performer.details:
        match_tattoos = re.search("Tattoo: (.*)", performer.details)
        if match_tattoos:
            performer.tattoos = match_tattoos.group(1)
            performer.details = performer.details.replace("Tattoo: " + performer.tattoos, "")

    # Piercings are given in the details section
    if "Piercings:" in performer.details:
        match_piercings = re.search("Piercings: (.*)", performer.details)
        if match_piercings:
            performer.piercings = match_piercings.group(1)
            performer.details = performer.details.replace("Piercings: " + performer.piercings, "")

    if "Non-ear piercings:" in performer.details:
        match_piercings = re.search("Non-ear piercings: (.*)", performer.details)
        if match_piercings:
            performer.piercings = match_piercings.group(1)
            performer.details = performer.details.replace("Non-ear piercings: " + performer.piercings, "")

    # Aliases are given in the details section
    if "AKA" in performer.details:
        match_aliases = re.search("AKA (.*)", performer.details)
        if match_aliases:
            performer.aliases = match_aliases.group(1)
            performer.details = performer.details.replace("AKA " + performer.aliases, "")

    if "A.K.A:" in performer.details:
        match_aliases = re.search("A.K.A: (.*)", performer.details)
        if match_aliases:
            performer.aliases = match_aliases.group(1)
            performer.details = performer.details.replace("A.K.A: " + performer.aliases, "")

    # Remove leading/trailing spaces from performer bio
    performer.details = performer.details.strip()

    # Image
    image = soup.find_all("div", "dts-section-page-detail-main-image-wrapper")

    if len(image) > 0:
        image_url_small = image[0].img.attrs["src"]

        match_image_url = re.search("(.*\.jpg)", image_url_small)
        if match_image_url:
            performer.image = "https:" + match_image_url.group(1)

    # URL
    performer.url = url

    return performer

def build_stash_scene_json(title, date, director, studio, performers, movie, tags, thumbnail, details = ""):

    # Decode image
    img = requests.get(thumbnail).content
    b64img = base64.b64encode(img)
    utf8img = b64img.decode('utf-8')

    # Build JSON for Stash API
    json = {}
    json["title"] = title
    json["url"] = url
    if date != "":
        json["date"] = date.strftime("%Y-%m-%d")
    json["director"] = director
    json["studio"] = {"name": studio}
    json["performers"] = [{"name": performer} for performer in performers]
    json["movies"] = [build_stash_movie_json(movie, decode_cover=False)]
    json["tags"] = [{"name": tag} for tag in tags]
    json["details"] = details
    json["image"] = "data:image/jpeg;base64," + utf8img

    return json

def build_stash_movie_json(movie, decode_cover=True):

    json = {}

    if decode_cover:
        # Decode front cover image
        front_img = requests.get(movie.front_cover).content
        front_b64img = base64.b64encode(front_img)
        front_utf8img = front_b64img.decode('utf-8')
        json["front_image"] = "data:image/jpeg;base64," + front_utf8img

        # Decode back cover image
        back_img = requests.get(movie.back_cover).content
        back_b64img = base64.b64encode(back_img)
        back_utf8img = back_b64img.decode('utf-8')
        json["back_image"] = "data:image/jpeg;base64," + back_utf8img

    # Build JSON for Stash API
    json["name"] = movie.title
    json["duration"] = movie.duration
    if movie.date != "":
        json["date"] = movie.date.strftime("%Y-%m-%d")
    json["studio"] = {"name": movie.studio}
    json["director"] = movie.director
    json["url"] = movie.url
    json["synopsis"] = movie.details

    return json

def build_stash_performer_json(performer):

    # Build JSON for Stash API
    json = {}
    json["name"] = performer.name
    json["aliases"] = performer.aliases
    json["gender"] = performer.gender
    json["birthdate"] = performer.birthdate
    json["ethnicity"] = performer.ethnicity
    json["hair_color"] = performer.hair_color
    json["eye_color"] = performer.eye_color
    json["height"] = performer.height
    json["weight"] = performer.weight
    json["tattoos"] = performer.tattoos
    json["piercings"] = performer.piercings
    json["url"] = performer.url
    json["details"] = performer.details

    # Decode image
    if performer.image != "":
        img = requests.get(performer.image).content
        b64img = base64.b64encode(img)
        utf8img = b64img.decode('utf-8')
        json["images"] = ["data:image/jpeg;base64," + utf8img]

    return json

#Debug
# url = "https://straight.aebn.com/straight/stars/3090/erik-everhard?fmc=1"
# sys.argv.append("performer")
#End Debug

frag = json.loads(sys.stdin.read())
url = frag["url"]

if not frag['url']:
    log.error("No URL entered")
    sys.exit(1)

if len(sys.argv) > 1:
    if sys.argv[1] == "movie" or sys.argv[1] == "scene":
        movie = parse_movie(url)
        if sys.argv[1] == "scene":
            # Check if complete movie shall be returned or only one of the movie scenes
            match_scene_url = re.search(".*#(scene-\d*)$", url)
            if match_scene_url:
                scene_id = match_scene_url.group(1)
                scene_found = False
                for scene in movie.scenes:
                    if scene.scene_id == scene_id:
                        ret = build_stash_scene_json(scene.title, movie.date, movie.director, movie.studio,
                                                     scene.performers, scene.movie, scene.tags, scene.thumbnail)
                        scene_found = True
                if not scene_found:
                    log.error("Scene not found")
                    sys.exit()

            match_scene_nr = re.search(".*[" + seperators + "](\d*)$", url)
            if match_scene_nr:
                try:
                    scene_nr = int(match_scene_nr.group(1))
                except ValueError:
                    log.error("Scene Nr must be Integer")
                scene_found = False
                for scene in movie.scenes:
                    if scene.scene_nr == scene_nr:
                        ret = build_stash_scene_json(scene.title, movie.date, movie.director, movie.studio,
                                                     scene.performers, scene.movie, scene.tags, scene.thumbnail)
                        scene_found = True
                if not scene_found:
                    log.error("Scene not found")
                    sys.exit()

            if not match_scene_url and not match_scene_nr:
                ret = build_stash_scene_json(movie.title, movie.date, movie.director, movie.studio, movie.performers,
                                             movie, movie.tags, movie.front_cover, movie.details)
        else:
            ret = build_stash_movie_json(movie)
    else:
        mode = "performer"
        performer = parse_performer(url)
        ret = build_stash_performer_json(performer)

print(json.dumps(ret))
