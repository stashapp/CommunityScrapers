import atexit
import base64
import datetime
import json
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

"""
Keeps a cache of API tokens for the Algolia API.

Domains are assumed to omit the TLD, e.g. "evilangel" instead of "evilangel.com"
"""


__TOKENS_FILE = Path(__file__).parent / "algolia_tokens.json"
try:
    __TOKENS = json.load(__TOKENS_FILE.open(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    __TOKENS = {}


@atexit.register
def __save_domains():
    sorted_domains = dict(sorted(__TOKENS.items(), key=lambda x: x[0]))
    json.dump(sorted_domains, __TOKENS_FILE.open("w", encoding="utf-8"), indent=2)


__OWN_SITE_FILE = Path(__file__).parent / "own_site_cache.json"
try:
    __OWN_SITE_CACHE = json.load(__OWN_SITE_FILE.open(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    __OWN_SITE_CACHE = {}


@atexit.register
def __save_own_site_cache():
    sorted_cache = dict(sorted(__OWN_SITE_CACHE.items(), key=lambda x: x[0]))
    json.dump(sorted_cache, __OWN_SITE_FILE.open("w", encoding="utf-8"), indent=2)


def site_name(url: str) -> str:
    """
    Returns the site name of the given URL, e.g. "evilangel" for "https://www.evilangel.com"
    """
    return urlparse(url).netloc.split(".")[-2]


def base_url(url: str) -> str:
    """
    Returns the base for a given URL, eg. "https://www.evilangel.com" for "https://www.evilangel.com/scene/1234"
    """
    return urlparse(url)._replace(path="").geturl()


def token_expiration(key: str) -> datetime.datetime | None:
    try:
        params = parse_qs(base64.b64decode(key).decode()[64:])
    except (ValueError, UnicodeDecodeError):
        return None
    if not (valid_until := params.get("validUntil")):
        return None
    return datetime.datetime.fromtimestamp(int(valid_until[0]))


def get_auth_for(
    domain: str, fallback: Callable[[str], tuple[str, str] | None]
) -> tuple[str, str] | None:
    """
    Returns the (app_id, key) for the given domain. If the stored key is not valid, the provided
    fallback function will be used to generate a new one

    If the fallback function returns None, it will return None
    """
    # A short buffer avoids reusing a key that expires mid-request
    now = datetime.datetime.now() + datetime.timedelta(minutes=5)

    if (
        (entry := __TOKENS.get(domain))
        and (pair := entry.get("pair"))
        and (expires := token_expiration(pair[1]))
        and expires > now
    ):
        return pair

    # Generate the app_id and key using the provided fallback function
    url = f"https://www.{domain}.com"
    pair = fallback(url)
    if not pair:
        return None
    # And persist it
    __TOKENS[domain] = {"pair": pair}

    return pair


def has_own_site(site: str) -> bool:
    """
    Some sites in `availableOnSite` no longer have a live site of their own:
    even their own homepage 301s straight to a *different* site (usually the network's main site)

    Cached for two weeks because honestly how often do they retire domains?
    """
    cutoff = (datetime.datetime.today() - datetime.timedelta(days=14)).strftime(
        "%Y-%m-%d"
    )
    if (entry := __OWN_SITE_CACHE.get(site)) and entry["checked"] >= cutoff:
        return entry["resolves"]

    import requests

    home = f"https://www.{site}.com"
    try:
        resp = requests.head(
            home,
            timeout=10,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resolves = (urlparse(resp.url).hostname or "").removeprefix("www.") == (
            urlparse(home).hostname or ""
        ).removeprefix("www.")
    except requests.RequestException:
        resolves = False

    __OWN_SITE_CACHE[site] = {
        "resolves": resolves,
        "checked": datetime.datetime.today().strftime("%Y-%m-%d"),
    }
    return resolves


def all_domains() -> list[str]:
    """
    Returns a list of all known domains for the Algolia API
    """

    return list(__TOKENS.keys())
