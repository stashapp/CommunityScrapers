import json
import sys
from py_common import log
from py_common.util import scraper_args
from py_common.types import PerformerSearchResult
import requests
import re

session = requests.Session()

def get_token() -> str | None:
    result = session.get("https://www.pornhub.com")
    # regex extract
    data_token = re.search(r'data-token="([^"]+)"', result.text)
    return data_token.group(1) if data_token else None


def performer_by_name(name: str) -> list[PerformerSearchResult]:
    token = get_token()
    if not token:
        raise Exception("Failed to retrieve token")

    response = session.get("https://www.pornhub.com/api/v1/video/search_autocomplete", params={
        "q": name,
        "token": token,
        "pornstars": "true",
        "alt": 0 # hardcoded
    })

    data = response.json()
    results: list[PerformerSearchResult] = []
    for model in data.get("models", []):
        results.append({
            "name": model.get("name"),
            "url": f"https://www.pornhub.com/model/{model.get('slug')}"
        })
    for pornstar in data.get("pornstars", []):
        results.append({
            "name": pornstar.get("name"),
            "url": f"https://www.pornhub.com/pornstar/{pornstar.get('slug')}"
        })
    # sort by alphabetical
    results.sort(key=lambda x: x["name"].lower())
    return results

if __name__ == "__main__":
    op, args = scraper_args()
    result = None
    match op, args:
        case "performer-by-name", {"name": name} if name:
            result = performer_by_name(name)
        case _:
          log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
          sys.exit(1)

    print(json.dumps(result))
