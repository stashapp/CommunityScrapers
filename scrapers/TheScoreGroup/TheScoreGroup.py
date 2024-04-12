import sys
import argparse
import json
import os
import requests
import re

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from ther

try:
    from lxml import html
except ModuleNotFoundError:
    print(
        "You need to install the lxml module. (https://lxml.de/installation.html#installation)",
        file=sys.stderr,
    )
    print(
        "If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml",
        file=sys.stderr,
    )
    sys.exit()

try:
    import py_common.log as log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr,
    )
    sys.exit()

# Shared client because we're making multiple requests
client = requests.Session()


# Example element:
# <div class="li-item model h-100 ">
#   <div class="box pos-rel d-flex flex-column h-100">
#     <div class="item-img pos-rel">
#       <a href="https://www.scoreland.com/big-boob-models/no-model/0/?nats=MTAwNC4yLjIuMi41NDUuMC4wLjAuMA"
#          class="d-block"
#          title=" Scoreland Profile">
#         <img src="https://cdn77.scoreuniverse.com/shared-bits/images/male-model-placeholder-photo.jpg" />
#       </a>
#     </div>
#     <div class="info t-c p-2">
#       <div class="t-trunc t-uc">
#         <a href="https://www.scoreland.com/big-boob-models/no-model/0/?nats=MTAwNC4yLjIuMi41NDUuMC4wLjAuMA"
#            title=""
#            aria-label=" Scoreland Profile"
#            class="i-model accent-text">
#         </a>
#       </div>
#     </div>
#   </div>
# </div>
def map_performer(el):
    url = el.xpath(".//a/@href")[0]
    if "no-model" in url:
        return None
    name = el.xpath(".//a/@title")[1]
    image = el.xpath(".//img/@src")[0]
    fixed_url = re.sub(r".*?([^/]*(?=/2/0))/2/0/([^?]*)", r"https://www.\1.com/\2", url)

    if client.head(fixed_url).status_code != 200:
        log.debug(f"Performer '{name}' has a broken profile link, skipping")
        return None

    return {
        "name": name,
        "url": fixed_url,
        "image": image,
    }


def performer_query(query: str):
    # Form data to be sent as the POST request body
    payload = {
        "ci_csrf_token": "",
        "keywords": query,
        "s_filters[site]": "all",
        "s_filters[type]": "models",
        "m_filters[sort]": "top_rated",
        "m_filters[gender]": "any",
        "m_filters[body_type]": "any",
        "m_filters[race]": "any",
        "m_filters[hair_color]": "any",
    }
    result = client.post("https://www.scoreland.com/search-es/", data=payload)
    tree = html.fromstring(result.content)
    performers = [p for x in tree.find_class("model") if (p := map_performer(x))]

    if not performers:
        log.warning(f"No performers found for '{query}'")
    return performers


def main():
    parser = argparse.ArgumentParser("ScoreGroup Scraper", argument_default="")
    subparsers = parser.add_subparsers(
        dest="operation", help="Operation to perform", required=True
    )
    subparsers.add_parser("search", help="Search for performers").add_argument(
        "name", nargs="?", help="Name to search for"
    )

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    log.debug(f"Arguments from commandline: {args}")
    # Script is being piped into, probably by Stash
    if not sys.stdin.isatty():
        try:
            frag = json.load(sys.stdin)
            args.__dict__.update(frag)
            log.debug(f"With arguments from stdin: {args}")
        except json.decoder.JSONDecodeError:
            log.error("Received invalid JSON from stdin")
            sys.exit(1)

    if args.operation == "search":
        name: str = args.name
        if not name:
            log.error("No query provided")
            sys.exit(1)
        log.debug(f"Searching for '{name}'")
        matches = performer_query(name)
        print(json.dumps(matches))
        sys.exit(0)

    # Just in case the above if statement doesn't trigger somehow
    # Something has gone quite wrong should this ever get hit
    log.error("An error has occured")
    sys.exit(2)


if __name__ == "__main__":
    main()
