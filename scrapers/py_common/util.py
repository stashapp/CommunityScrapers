from functools import reduce
from typing import Any


def dig(c: dict | list, *keys: str | int | tuple, default=None) -> Any:
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
