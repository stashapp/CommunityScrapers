import atexit
import datetime
import json
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

"""
Keeps a cache of instance tokens for the Aylo API.

Domains are assumed to omit the TLD, e.g. "brazzers" instead of "brazzers.com"
"""


__TOKENS_FILE = Path(__file__).parent / "aylo_tokens.json"
try:
    __TOKENS = json.load(__TOKENS_FILE.open(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    __TOKENS = {}


@atexit.register
def __save_domains():
    sorted_domains = dict(sorted(__TOKENS.items(), key=lambda x: x[0]))
    json.dump(sorted_domains, __TOKENS_FILE.open("w", encoding="utf-8"), indent=2)


def site_name(url: str) -> str:
    """
    Returns the site name of the given URL, e.g. "brazzers" for "https://www.brazzers.com"
    """
    return urlparse(url).netloc.split(".")[-2]


def get_token_for(domain: str, fallback: Callable[[str], str | None]) -> str | None:
    """
    Returns a token for the given domain. If the stored token is not valid, the provided
    fallback function will be used to generate a new token.

    If the fallback function returns None, it will return None.
    """
    today = datetime.datetime.today().strftime("%Y-%m-%d")

    # If the domain is in the list and if the token is still valid we just return it
    if (entry := __TOKENS.get(domain)) and entry["date"] == today and entry["token"]:
        return entry["token"]

    # Generate the token using the provided fallback function
    url = f"https://www.{domain}.com"
    token = fallback(url)
    if not token:
        return None
    # And persist it
    __TOKENS[domain] = {
        "token": token,
        "date": today,
    }

    return token


def all_domains() -> list[str]:
    """
    Returns a list of all known domains for the Aylo API
    """

    return list(__TOKENS.keys())
