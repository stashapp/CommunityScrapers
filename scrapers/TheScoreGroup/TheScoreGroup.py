import sys
import argparse
import json
import requests

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


def performer_query(query: str):
    # Form data to be sent as the POST request body
    payload = {
    "ci_csrf_token": "",
    "keywords": f"{query}",
    "s_filters[site]": "all",
    "s_filters[type]": "models",
    "m_filters[sort]": "top_rated",
    "m_filters[gender]": "any",
    "m_filters[body_type]": "any",
    "m_filters[race]": "any",
    "m_filters[hair_color]": "any"
    }
    result = requests.post("https://www.scoreland.com/search-es/", data=payload)
    tree = html.fromstring(result.content)
    performer_names: list[str] = tree.xpath("//a[contains(concat(' ',normalize-space(@class),' '),' i-model ')]/text()")
    performer_urls: list[str] = tree.xpath("//a[contains(concat(' ',normalize-space(@class),' '),' i-model ')]/@href")
    performers = [
            {
                "Name": name,
                "URL": url,
            }
            for name, url in zip(performer_names, performer_urls)
    ]
    if not performers:
        log.warning(f"No performers found for '{query}'")
    return performers

def main():
    parser = argparse.ArgumentParser("ScoreGroup Scraper",argument_default="")
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
        name: str= args.name
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
