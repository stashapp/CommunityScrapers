import json
import os
import re
import requests
import sys

import py_common.log as log

try:
    from lxml import html
except ModuleNotFoundError:
    log.error("You need to install the lxml module. (https://lxml.de/installation.html#installation)")
    log.error("If you have pip (normally installed with python), run this command in a terminal (cmd): python -m pip install lxml")
    sys.exit()

kgs_per_lb = 0.45359237
cms_per_in = 2.54
filename_pattern = re.compile(r"(?P<model_id>[a-z]{3}\d{3})ATK_(?P<movie_id>\d{6})(?P<scene>\d{3})_(?P<resolution>\w+)(?:\.(?P<extension>\w+))?", re.IGNORECASE)

def getSceneByFilename(filename):
    # Parse filename
    filename_match = filename_pattern.match(filename)
    (model_id, movie_id, _, _, _) = filename_match.groups()

    # Fetch model page
    model_url = f"https://www.atkgirlfriends.com/tour/model/{model_id}"
    log.debug(f"Fetching {model_url} ({movie_id})")
    response = requests.get(model_url, cookies=dict(start_session_galleria = 'stash'))
    if (response.url.startswith("https://www.atkgirlfriends.com?nats")):
        # Refetch page on cookie failure
        response = requests.get(model_url, cookies=dict(start_session_galleria = 'stash'))

    # Build performer
    tree = html.fromstring(response.text)
    performer = dict(Gender = "female")
    model_profile_wrap_xpath = '//div[contains(@class, "model-profile-wrap")]'
    performer["name"] = tree.xpath('//h1[contains(@class, "page-title")]')[0].text
    performer["url"] = f"{model_url}/1/atk-girlfriends-{performer['name'].replace(' ', '-')}"
    performer["ethnicity"] = tree.xpath(f'{model_profile_wrap_xpath}/b[contains(text(), "Ethnicity")]/following-sibling::text()')[0].strip().capitalize()
    performer["hair_color"] = tree.xpath(f'{model_profile_wrap_xpath}/b[contains(text(), "Hair Color")]/following-sibling::text()')[0].strip().capitalize()
    height_ft_ins_str = tree.xpath(f'{model_profile_wrap_xpath}/b[contains(text(), "Height")]/following-sibling::text()')[0].strip()
    (height_ft_str, height_ins_str) = re.compile(r"(\d+)[\"'](\d+)").findall(height_ft_ins_str)[0]
    height_ins = float(height_ft_str) * 12 + float(height_ins_str)
    performer["height"] = str(int(height_ins * cms_per_in))
    weight_lbs_str = tree.xpath(f'{model_profile_wrap_xpath}/b[contains(text(), "Weight")]/following-sibling::text()')[0].strip()
    weight_lbs = float(re.compile(r"\d+").findall(weight_lbs_str)[0])
    performer["weight"] = str(int(weight_lbs * kgs_per_lb))
    performer["measurements"] = tree.xpath(f'{model_profile_wrap_xpath}/b[contains(text(), "Bust Size")]/following-sibling::text()')[0].strip()
    performer["image"] = tree.xpath(f'{model_profile_wrap_xpath}/img/@src')[0]

    # Build scene
    scene = dict(studio = dict(name = "ATK Girlfriends"), performers = [performer])
    movie_wrap_xpath = f'//img[contains(@src, "/{model_id}/{movie_id}")]/../../../..'
    scene["title"] = tree.xpath(f'{movie_wrap_xpath}//h1')[0].text.strip()
    scene["details"] = tree.xpath(f'{movie_wrap_xpath}//b[contains(text(), "Description")]/following-sibling::text()')[0].strip()
    movie_url_relative = tree.xpath(f'{movie_wrap_xpath}//a/@href')[0]
    scene["url"] = f'https://www.atkgirlfriends.com{movie_url_relative}'
    scene["image"] = tree.xpath(f'{movie_wrap_xpath}//img/@src')[0]

    return scene

input = sys.stdin.read()
match = filename_pattern.search(input)
if (match):
    scene = getSceneByFilename(match.group())
    output = json.dumps(scene)
    print(output)
else:
    log.debug("Filename does not match ATKGirlfriends pattern")
    print(r"{}")
