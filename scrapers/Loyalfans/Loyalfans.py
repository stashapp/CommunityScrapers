import os
import sys
import json

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    # Import Stash logging system from py_common
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo. (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()

try:
    # Import necessary modules.
    import requests
    import re

# If one of these modules is not installed:
except ModuleNotFoundError:
    log.error("You need to install the python modules mentioned in requirements.txt")
    log.error(
        "If you have pip (normally installed with python), run this command in a terminal from the directory the scraper is located: pip install -r requirements.txt"
    )
    sys.exit()

# Lookup table for tag replacements. The tags are in the form of hashtags, and often have multiple words mashed together.
# This is a quick and dirty way of turning these into meaningful data, and can be expanded on to taste.
TAG_REPLACEMENTS = {
    "Fin Dom": "Findom",
    "Fem Dom": "Femdom",
    "bigtits": "Big Tits",
    "titworship": "Tit Worship",
    "financialdomination": "Financial Domination",
    "R I P O F F": "ripoff",
    "pussydenial": "pussy denial",
}


def output_json_url(title, tags, url, image, studio, performers, description, date):
    # Create a tag dictionary from the tag list.
    tag_dicts = [{"name": tag.strip(". ")} for tag in tags if tag.strip() != "N/A"]
    # We're only using the value of 'performers' for our performer list
    performer_dicts = [{"name": performer} for performer in performers]
    # Dump all of this as JSON data.
    return json.dumps(
        {
            "title": title,
            "tags": tag_dicts,
            "url": url,
            "image": image,
            "studio": {"name": studio},
            "performers": performer_dicts,
            "details": description,
            "date": date,
        },
        indent=2,
    )


def get_cookies(scene_url: str):
    # Establish a session.
    session = requests.Session()
    # Set headers required for a successful POST query.
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.loyalfans.com",
        "Referer": scene_url,
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    }
    # URL of the system status API. This is called when a Loyalfans page is first loaded from what I can tell.
    url = "https://www.loyalfans.com/api/v2/system-status"
    # Perform a POST query to capture initial cookies.
    response = session.post(url, headers=headers)
    # Return these cookies.
    return response.cookies


def get_api_url(scene_url: str):
    # Extract the last component of the scene URL.
    end_segment = scene_url.split("/")[-1]
    # Append this to the API link. As far as I can tell, post names in scene URLs are unique. I have yet to encounter any data mismatches.
    return f"https://www.loyalfans.com/api/v1/social/post/{end_segment}"


def get_json(scene_url: str):
    # Set headers required for a successful request.
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.loyalfans.com",
        "Referer": scene_url,
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    }
    # Set cookies using get_cookies function.
    cookie_set = get_cookies(scene_url)
    # Perform request using the API URL of the scene in question, adding headers and cookies.
    response = requests.get(get_api_url(scene_url), headers=headers, cookies=cookie_set)
    # Capture the response as JSON.
    json_data = response.json()
    # Return the JSON data.
    return json_data


def scrape_scene(scene_url: str) -> dict:
    # Capture JSON relating to this scene from the Loyalfans API.
    json = get_json(scene_url)
    # Extract title from the JSON and strip out any whitespace.
    title = json["post"]["title"].strip()
    # Use the video thumbnail/preview poster as the image.
    image = json["post"]["video_object"].get("poster")
    # Extract description, fix apostrophes and remove HTML newline tags.
    description = json["post"]["content"].replace("\u2019", "'").replace("<br />", "")
    # Sometimes hashtags are included at the bottom of the description. This line strips all that junk out, as we're utilising the hashtags for the tags. Also tidies up double-spacing and ellipses.
    description = (
        re.sub(r"#\w+\b", "", description)
        .strip()
        .replace("  ", " ")
        .replace(". . .", "...")
    )
    # Extract studio name.
    studio = json["post"]["owner"]["display_name"]
    # Extract date. The JSON returns the date in the format '2023-06-18 12:00:00', but we only need the date, so the time is stripped out.
    date = json["post"]["created_at"]["date"].split(" ")[0]
    # Extract tags.
    tags_list = json["post"]["hashtags"]
    fixed_tags = []
    # For every tag we find:
    for tag in tags_list:
        # Remove the hash from the start.
        tag = tag[1:]
        modified_tag = tag
        # Split CamelCase tags into separate words.
        modified_tag = re.sub(r"(?<!^)(?=[A-Z])", " ", tag).strip()
        # Perform replacements according to the above lookup table.
        for find, replace in TAG_REPLACEMENTS.items():
            modified_tag = re.sub(
                r"\b" + re.escape(find) + r"\b", replace, modified_tag
            )
        fixed_tags.append(modified_tag)

    # LoyalFans doesn't provide a cast list so we'll just use the studio name as the performer name.
    performers = [studio]

    # Convert into meaningful JSON that Stash can use.
    json_dump = output_json_url(
        title, fixed_tags, scene_url, image, studio, performers, description, date
    )

    print(json_dump)


def main():
    fragment = json.loads(sys.stdin.read())
    url = fragment.get("url")
    # If nothing is passed to the script:
    if url is None:
        log.error("No URL provided")
        sys.exit(1)
    # If we've been given a URL:
    if url is not None:
        scrape_scene(url)


if __name__ == "__main__":
    main()

# Last updated 2023-06-18
