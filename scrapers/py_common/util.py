from argparse import ArgumentParser
from functools import reduce
from typing import Any, Callable, TypeVar
from urllib.error import URLError
from urllib.request import Request, urlopen
import json
import sys


def dig(c: dict | list, *keys: str | int | tuple[str | int, ...], default=None) -> Any:
    """
    Helper function to get a value from a nested dict or list

    If a key is a tuple the items will be tried in order until a value is found

    :param c: dict or list to search
    :param keys: keys to search for
    :param default: default value to return if not found
    :return: value if found, None otherwise

    >>> obj = {"a": {"b": ["c", "d"], "f": {"g": "h"}}}
    >>> dig(obj, "a", "b", 1)
    'd'
    >>> dig(obj, "a", ("e", "f"), "g")
    'h'
    """

    def inner(d: dict | list, key: str | int | tuple):
        if isinstance(d, dict):
            if isinstance(key, tuple):
                for k in key:
                    if k in d:
                        return d[k]
            return d.get(key)
        elif isinstance(d, list) and isinstance(key, int) and key < len(d):
            return d[key]
        else:
            return default

    return reduce(inner, keys, c)  # type: ignore


T = TypeVar("T")


def replace_all(obj: dict, key: str, replacement: Callable[[T], T]) -> dict:
    """
    Helper function to recursively replace values in a nested dict, returning a new dict

    If the key refers to a list the replacement function will be called for each item

    :param obj: dict to search
    :param key: key to search for
    :param replacement: function called on the value to replace it
    :return: new dict

    >>> obj = {"a": {"b": ["c", "d"], "f": {"g": "h"}}}
    >>> replace(obj, "g", lambda x: x.upper()) # Replace a single item
    {'a': {'b': ['c', 'd'], 'f': {'g': 'H'}}}
    >>> replace(obj, "b", lambda x: x.upper()) # Replace all items in a list
    {'a': {'b': ['C', 'D'], 'f': {'g': 'h'}}}
    >>> replace(obj, "z", lambda x: x.upper()) # Do nothing if the key is not found
    {'a': {'b': ['c', 'd'], 'f': {'g': 'h'}}}
    """
    if not isinstance(obj, dict):
        return obj

    new = {}
    for k, v in obj.items():
        if k == key:
            if isinstance(v, list):
                new[k] = [replacement(x) for x in v]
            else:
                new[k] = replacement(v)
        elif isinstance(v, dict):
            new[k] = replace_all(v, key, replacement)
        elif isinstance(v, list):
            new[k] = [replace_all(x, key, replacement) for x in v]
        else:
            new[k] = v
    return new


def replace_at(obj: dict, *path: str, replacement: Callable[[T], T]) -> dict:
    """
    Helper function to replace a value at a given path in a nested dict, returning a new dict

    If the path refers to a list the replacement function will be called for each item

    If the path does not exist, the replacement function will not be called and the dict will be returned as-is

    :param obj: dict to search
    :param path: path to search for
    :param replacement: function called on the value to replace it
    :return: new dict

    >>> obj = {"a": {"b": ["c", "d"], "f": {"g": "h"}}}
    >>> replace_at(obj, "a", "f", "g", replacement=lambda x: x.upper()) # Replace a single item
    {'a': {'b': ['c', 'd'], 'f': {'g': 'H'}}}
    >>> replace_at(obj, "a", "b", replacement=lambda x: x.upper()) # Replace all items in a list
    {'a': {'b': ['C', 'D'], 'f': {'g': 'h'}}}
    >>> replace_at(obj, "a", "z", "g", replacement=lambda x: x.upper()) # Broken path, do nothing
    {'a': {'b': ['c', 'd'], 'f': {'g': 'h'}}}
    """

    def inner(d: dict, *keys: str):
        match keys:
            case [k] if isinstance(d, dict) and k in d:
                if isinstance(d[k], list):
                    return {**d, k: [replacement(x) for x in d[k]]}
                return {**d, k: replacement(d[k])}
            case [k, *ks] if isinstance(d, dict) and k in d:
                return {**d, k: inner(d[k], *ks)}
            case _:
                return d

    return inner(obj, *path)  # type: ignore


def is_valid_url(url):
    """
    Checks if an URL is valid by making a HEAD request and ensuring the response code is 2xx
    """
    try:
        req = Request(url, method="HEAD")
        with urlopen(req) as response:
            return 200 <= response.getcode() < 300
    except URLError:
        return False


def __default_parser(**kwargs):
    parser = ArgumentParser(**kwargs)
    # Some scrapers can take extra arguments so we can
    # do rudimentary configuration in the YAML file
    parser.add_argument("extra", nargs="*")
    subparsers = parser.add_subparsers(dest="operation", required=True)

    # "Scrape with..." and the subsequent search box
    subparsers.add_parser(
        "performer-by-name", help="Search for performers"
    ).add_argument("--name", help="Performer name to search for")

    # The results of performer-by-name will be passed to this
    pbf = subparsers.add_parser("performer-by-fragment", help="Scrape a performer")
    # Technically there's more information in this fragment,
    # but in 99.9% of cases we only need the URL or the name
    pbf.add_argument("--url", help="Scene URL")
    pbf.add_argument("--name", help="Performer name to search for")

    # Filling in an URL and hitting the "Scrape" icon
    subparsers.add_parser(
        "performer-by-url", help="Scrape a performer by their URL"
    ).add_argument("--url")

    # Filling in an URL and hitting the "Scrape" icon
    subparsers.add_parser(
        "movie-by-url", help="Scrape a movie by its URL"
    ).add_argument("--url")

    # The looking glass search icon
    # name field is guaranteed to be filled by Stash
    subparsers.add_parser("scene-by-name", help="Scrape a scene by name").add_argument(
        "--name", help="Name to search for"
    )

    # Filling in an URL and hitting the "Scrape" icon
    subparsers.add_parser(
        "scene-by-url", help="Scrape a scene by its URL"
    ).add_argument("--url")

    # "Scrape with..."
    sbf = subparsers.add_parser("scene-by-fragment", help="Scrape a scene")
    sbf.add_argument("-u", "--url")
    sbf.add_argument("--id")
    sbf.add_argument("--title")  # Title will be filename if not set in Stash
    sbf.add_argument("--date")
    sbf.add_argument("--details")
    sbf.add_argument("--urls", nargs="+")

    # Tagger view or search box
    sbqf = subparsers.add_parser("scene-by-query-fragment", help="Scrape a scene")
    sbqf.add_argument("-u", "--url")
    sbqf.add_argument("--id")
    sbqf.add_argument("--title")  # Title will be filename if not set in Stash
    sbqf.add_argument("--code")
    sbqf.add_argument("--details")
    sbqf.add_argument("--director")
    sbqf.add_argument("--date")
    sbqf.add_argument("--urls", nargs="+")

    # Filling in an URL and hitting the "Scrape" icon
    subparsers.add_parser(
        "gallery-by-url", help="Scrape a gallery by its URL"
    ).add_argument("--url", help="Gallery URL")

    # "Scrape with..."
    gbf = subparsers.add_parser("gallery-by-fragment", help="Scrape a gallery")
    gbf.add_argument("-u", "--url")
    gbf.add_argument("--id")
    gbf.add_argument("--title")
    gbf.add_argument("--date")
    gbf.add_argument("--details")
    gbf.add_argument("--urls", nargs="+")

    return parser


def scraper_args(**kwargs):
    """
    Helper function to parse arguments for a scraper

    This allows scrapers to be called from the command line without
    piping JSON to stdin but also from Stash

    Returns a tuple of the operation and the parsed arguments: operation is one of
    - performer-by-name
    - performer-by-fragment
    - performer-by-url
    - movie-by-url
    - scene-by-name
    - scene-by-url
    - scene-by-fragment
    - scene-by-query-fragment
    - gallery-by-url
    - gallery-by-fragment

    A scraper can be configured to take extra arguments by adding them to the YAML file:
    ```yaml
    sceneByName:
      action: script
      script:
        - python
        - my-scraper.py
        - extra
        - args
        - scene-by-name
    ```

    When called from Stash through the above configuration this function would return:
    ```python
    ("scene-by-name", {"extra": ["extra", "args"], "name": "scene name"})
    ```
    """

    parser = __default_parser(**kwargs)
    args = vars(parser.parse_args())

    # If stdin is not connected to a TTY the script is being executed by Stash
    if not sys.stdin.isatty():
        try:
            stash_fragment = json.load(sys.stdin)
            args.update(stash_fragment)
        except json.decoder.JSONDecodeError:
            # This would only happen if Stash passed invalid JSON
            sys.exit(69)

    return args.pop("operation"), args
