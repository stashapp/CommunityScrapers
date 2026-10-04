r"""
Parser for the React Server Components (RSC) "flight" payload that Next.js App Router pages embed as `self.__next_f.push([1, "..."])` script chunks

The joined chunks are a stream of rows:
- `<id>:<json>\n` for ordinary rows (non-JSON rows like `I[...]` imports and `:HL[...]` hints are skipped)
- `<id>:T<hex byte length>,<text>` for long strings, with no terminator

JSON rows point at other rows with `"$<id>"` or `"$<id>:<key>:<key>"`, which is how long descriptions end up as a bare `"$4a"`,
and `Flight` resolves every reference up front, so `rows` and `find` only ever see the real values

This is an example of what such a payload looks like when embedded in a HTML page along with how it can be parsed into a Flight object

>>> html = r'''
... <script>(self.__next_f=self.__next_f||[]).push([0])</script>
... <script>self.__next_f.push([1,"1:I[8063,[],\"LoadingBoundaryProvider\"]\n:HL[\"https://d1mr1qahd2jlw8.cloudfront.net/_next/static/css/5bef1d47e6740614.css\",\"style\"]\n0:[\"$\",\"main\",null,{\"pageType\":\"video\",\"data\":\"$2\"}]\n3:{\"peo"])</script>
... <script>self.__next_f.push([1,"ple\":[{\"screen_name\":\"Zoë\"}]}\n5:T25,<p>$$$ Big Spender’s café date</p>2:{\"title\":\"Café Date\",\"description\":\"$5\",\"price\":\"$$20\",\"publish_date\":\"$D2024-01-02T00:00:00.000Z\",\"trailer\":\"$undefined\",\"casts\":\"$3:people\"}\n"])</script>
... '''
>>> flight = Flight.from_html(html)
>>> data = flight.first(lambda d: d.get("pageType") == "video")["data"]
>>> data
{'title': 'Café Date', 'description': '<p>$$$ Big Spender’s café date</p>', 'price': '$20', 'publish_date': '2024-01-02T00:00:00.000Z', 'trailer': None, 'casts': [{'screen_name': 'Zoë'}]}

>>> from py_common.types import ScrapedPerformer, ScrapedScene
>>> ScrapedScene(
...     title=data["title"],
...     date=data["publish_date"].split("T")[0],
...     performers=[ScrapedPerformer(name=p["screen_name"]) for p in data["casts"]],
... )
{'title': 'Café Date', 'date': '2024-01-02', 'performers': [{'name': 'Zoë'}]}

If your scraper fetches a raw stream of RSC it can use `from_stream` instead of `from_html` to achieve the same effect
"""

import json
import re
from collections.abc import Callable, Iterator
from typing import Any

_CHUNK = re.compile(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', re.DOTALL)
_ROW = re.compile(rb"([0-9a-f]*):(?:T([0-9a-f]+),)?")
_REF = re.compile(r"\$([0-9a-f]+)((?::[^:]+)*)")


class _Text(str):
    """
    A T row's text: raw, unlike JSON strings, so a leading `$` is literal
    """


class Flight:
    """
    Every row of a flight payload, with references resolved

    Each row is resolved once and every reference to it shares that object;
    other `$`-prefixed values (lazy components, promises, server actions) are
    left as they are, and so is a reference that would loop

    >>> Flight({"0": {"next": "$1"}, "1": {"back": "$0"}}).rows
    {'0': {'next': {'back': '$0'}}, '1': {'back': '$0'}}
    """

    def __init__(self, raw_rows: dict[str, Any]):
        self.rows = _resolve_rows(raw_rows)

    @classmethod
    def from_html(cls, html: str) -> "Flight":
        """
        Parses every flight chunk in a server-rendered page
        """
        stream = "".join(json.loads(f'"{chunk}"') for chunk in _CHUNK.findall(html))
        return cls.from_stream(stream)

    @classmethod
    def from_stream(cls, stream: str) -> "Flight":
        r"""
        Parses a bare flight stream

        >>> Flight.from_stream('0:{"cover":"$1"}\n1:"https://example.com/cover.jpg"\n').rows
        {'0': {'cover': 'https://example.com/cover.jpg'}, '1': 'https://example.com/cover.jpg'}
        """
        # T row lengths count UTF-8 bytes, not characters
        data = stream.encode()
        rows: dict[str, Any] = {}
        pos = 0
        while row := _ROW.match(data, pos):
            row_id, text_length = row[1].decode(), row[2]
            if text_length:
                pos = row.end() + int(text_length, 16)
                rows[row_id] = _Text(data[row.end() : pos].decode())
                continue
            if (pos := data.find(b"\n", row.end())) == -1:
                pos = len(data)
            try:
                rows[row_id] = json.loads(data[row.end() : pos])
            except ValueError:
                pass
            pos += 1
        return cls(rows)

    def find(
        self, predicate: Callable[[dict[str, Any]], bool]
    ) -> Iterator[dict[str, Any]]:
        """
        Yields every dict in the payload that satisfies the predicate, once
        """
        return _walk(list(self.rows.values()), predicate, set())

    def first(
        self, predicate: Callable[[dict[str, Any]], bool]
    ) -> dict[str, Any] | None:
        return next(self.find(predicate), None)


def _resolve_rows(raw: dict[str, Any]) -> dict[str, Any]:
    done: dict[str, Any] = {}
    active: set[str] = set()

    def row(row_id: str) -> Any:
        if row_id not in done:
            active.add(row_id)
            done[row_id] = value(raw[row_id])
            active.discard(row_id)
        return done[row_id]

    def value(v: Any) -> Any:
        match v:
            case dict():
                return {k: value(x) for k, x in v.items()}
            case list():
                return [value(x) for x in v]
            case _Text():
                return str(v)
            case str() if v.startswith("$"):
                return reference(v)
        return v

    def reference(v: str) -> Any:
        match v:
            case "$undefined":
                return None
            case _ if v.startswith("$$"):
                return v[1:]
            case _ if v.startswith("$D"):
                return v[2:]
        if not (ref := _REF.fullmatch(v)) or ref[1] not in raw or ref[1] in active:
            return v
        target = row(ref[1])
        for key in ref[2].split(":")[1:]:
            match target:
                case list() if key.isdigit() and int(key) < len(target):
                    target = target[int(key)]
                case dict() if key in target:
                    target = target[key]
                case _:
                    return v
        return target

    return {row_id: row(row_id) for row_id in raw}


def _walk(
    node: Any, predicate: Callable[[dict[str, Any]], bool], seen: set[int]
) -> Iterator[dict[str, Any]]:
    if id(node) in seen:
        return
    match node:
        case dict():
            seen.add(id(node))
            if predicate(node):
                yield node
            for value in node.values():
                yield from _walk(value, predicate, seen)
        case list():
            seen.add(id(node))
            for value in node:
                yield from _walk(value, predicate, seen)
