import base64
import requests
import json
import sys
import re

from py_common import graphql
from py_common import log
from py_common.util import scraper_args, dig

stash_url = graphql.config["url"].rstrip("/")
stash_api_key = graphql.config["api_key"]


def get_image_from_stash(image_url: str) -> bytes:
    return requests.get(image_url, headers={"ApiKey": stash_api_key}).content


def copy_scene(url: str):
    if not (match := re.match(rf"(?:{stash_url}/scenes/)?(\d+)", url)):
        log.error(f"Unable to extract scene ID from url: {url}")
        return None
    source_id = int(match.group(1))

    if not (
        response := graphql.callGraphQL(
            "query FindScene($id: ID!){findScene(id: $id) { title code date details director urls groups { group { name id } } performers { name } tags { name } studio { name } paths { screenshot } }}",
            variables={"id": source_id},
        )
    ) or not (source := response["findScene"]):
        log.error(f"Could not find scene with ID {source_id}")
        return None

    copy = {
        "title": dig(source, "title"),
        "code": dig(source, "code"),
        "date": dig(source, "date"),
        "details": dig(source, "details"),
        "director": dig(source, "director"),
        "urls": dig(source, "urls"),
        "studio": dig(source, "studio"),
        "performers": dig(source, "performers"),
        "tags": dig(source, "tags"),
    }

    if groups := dig(source, "groups"):
        copy["movies"] = [{"name": g["group"]["name"]} for g in groups]

    if image := dig(source, "paths", "screenshot"):
        image_bytes = get_image_from_stash(image)
        uri_encoded = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode()
        copy["image"] = uri_encoded

    return {k: v for k, v in copy.items() if v}


def copy_gallery(url: str):
    if not (match := re.match(rf"(?:{stash_url}/galleries/)?(\d+)", url)):
        log.error(f"Unable to extract gallery ID from url: {url}")
        return None
    source_id = int(match.group(1))

    if not (
        response := graphql.callGraphQL(
            "query FindGallery($id: ID!){findGallery(id: $id) { title code date details photographer urls scenes { title id } performers { name } tags { name } studio { name } }}",
            variables={"id": source_id},
        )
    ) or not (source := response["findGallery"]):
        log.error(f"Could not find gallery with ID {source_id}")
        return None

    return {k: v for k, v in source.items() if v}


if __name__ == "__main__":
    op, args = scraper_args()

    # urls can be None but we need an iterable
    urls = args["urls"] or []

    local_url = next(
        (url for url in urls if url.startswith(stash_url) or url.isnumeric()), None
    )
    if not local_url:
        log.error("No suitable URLs to copy: please add a local URL before scraping")
        sys.exit(1)

    if op == "gallery-by-fragment":
        result = copy_gallery(local_url)
    elif op == "scene-by-fragment":
        result = copy_scene(local_url)
    else:
        log.error(f"Operation: {op}, arguments: {json.dumps(args)}")
        sys.exit(1)

    print(json.dumps(result))
