"""
This script is a companion to the OnlyFans/Fansly data scrapers by DIGITALCRIMINAL and derivatives.
Above tools download posts from OnlyFans/Fansly and save metadata to 'user_data.db' SQLite files.

This script requires python3, stashapp-tools, and sqlite3.
"""
import json
import sys
import re
import sqlite3
from pathlib import Path
import time
import random
import uuid
from typing import Dict

try:
    from stashapi import log
    from stashapi.tools import file_to_base64
    from stashapi.stashapp import StashInterface
except ModuleNotFoundError:
    print(
        "You need to install the stashapp-tools (stashapi) python module. (cmd): "
        "pip install stashapp-tools",
        file=sys.stderr
    )
    sys.exit()

# CONFIG ###########################################################################################

# Default config
default_config = {
    "stash_connection": {
        "scheme": "http",
        "host": "localhost",
        "port": 9999,
        "apikey": ""
    },
    "max_title_length": 64,  # Maximum length for scene/gallery titles.
    "tag_messages": True,  # Whether to tag messages.
    "tag_messages_name": "[DC: Messages]",  # Name of tag for messages.
    "max_performer_images": 3,  # Maximum performer images to generate.
    "cache_time": 300,  # Image expiration time (in seconds).
    "cache_dir": "cache",  # Directory to store cached base64 encoded images.
    "cache_file": "cache.json"  # File to store cache information in.
}

# Read config file
try:
    with open('config.json', 'r', encoding="utf-8") as config_file:
        config = json.load(config_file)
except FileNotFoundError:
    # If the file doesn't exist, use the default configuration
    config = default_config

# Update config with missing keys
config.update((k, v) for k, v in default_config.items() if k not in config)

# Write config file
with open('config.json', 'w', encoding="utf-8") as config_file:
    json.dump(config, config_file, indent=2)

STASH_CONNECTION = config['stash_connection']
MAX_TITLE_LENGTH = config['max_title_length']
TAG_MESSAGES = config['tag_messages']
TAG_MESSAGES_NAME = config['tag_messages_name']
MAX_PERFORMER_IMAGES = config['max_performer_images']
CACHE_TIME = config['cache_time']
CACHE_DIR = config['cache_dir']
CACHE_FILE = config['cache_file']

# STASH ############################################################################################
try:
    stash = StashInterface(STASH_CONNECTION)
except SystemExit:
    log.error("Unable to connect to Stash, please verify your config.")
    print('null')
    sys.exit()

# CACHE  ###########################################################################################
# Create cache directory
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)


def load_cache():
    """
    Load and update cache data, removing stale entries and associated files when necessary.
    """
    try:
        with open(CACHE_FILE, 'r', encoding="utf-8") as file:
            cache = json.load(file)
            current_time = time.time()
            updated_cache = {}
            for path, (timestamp, image_filenames) in cache.items():
                if current_time - timestamp <= CACHE_TIME:
                    updated_cache[path] = (timestamp, image_filenames)
                else:
                    log.info(f'[CACHE PURGE] Purging stale image(s) for path: {path}')
                    for image_filename in image_filenames:
                        image_path = Path(CACHE_DIR) / image_filename
                        log.debug(f'[CACHE PURGE] Deleting stale image from disk: {image_path}')
                        if Path(image_path).exists() and Path(image_path).is_file():
                            Path(image_path).unlink()
            return updated_cache
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    """
    Save cache data and log update.
    """
    with open(CACHE_FILE, 'w', encoding="utf-8") as file:
        json.dump(cache, file, indent=2)
        log.info('[CACHE UPDATED]')


# SCENES ###########################################################################################
def lookup_scene(file, db, media_dir, username, network):
    """
    Query database for scene metadata and create a structured scrape result.
    """
    log.info(f"Using database: {db} for {file}")
    conn = sqlite3.connect(
        db, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    c = conn.cursor()

    c.execute("""
        SELECT medias.filename, medias.post_id, match.api_type
        FROM medias
        JOIN (
            SELECT api_type, post_id
            FROM medias
            WHERE medias.filename = ?
        ) AS match
        ON medias.post_id = match.post_id
        WHERE medias.media_type = 'Videos'
        ORDER BY medias.id ASC
    """, (file.name,))

    result = c.fetchall()

    if not result:
        log.error(f'Could not find metadata for scene: {file}')
        print('null')
        sys.exit()

    api_type = result[0][2]
    post_id = result[0][1]

    if api_type in ("Posts", "Stories", "Messages", "Products", "Others"):
        query = f"""
            SELECT posts.post_id, posts.text, posts.created_at
            FROM {api_type.lower()} AS posts, medias
            WHERE posts.post_id = medias.post_id
            AND medias.filename = ?
        """
        c.execute(query, (file.name,))
    else:
        log.error(f"Unknown api_type {api_type} for post: {post_id}")
        print('null')
        sys.exit()

    log.debug(f'Found {len(result)} video(s) in post {post_id}')
    if len(result) > 1:
        scene_index = [item[0] for item in result].index(file.name) + 1
        log.debug(f'Video is {scene_index} of {len(result)} in post')
    else:
        scene_index = 0

    scene = process_row(c.fetchone(), username, network, scene_index)

    scrape = {
        "title": scene["title"], "details": scene["details"], "date": scene["date"],
        "code": scene["code"], "urls": scene["urls"],
        "studio": get_studio_info(username, network),
        "performers": get_performer_info(username, media_dir)
    }
    if api_type == "Messages" and TAG_MESSAGES:
        scrape["tags"] = [{"name": TAG_MESSAGES_NAME}]

    return scrape


# GALLERIES ########################################################################################
def lookup_gallery(file, db, media_dir, username, network):
    """
    Query database for gallery metadata and create a structured scrape result.
    """
    log.info(f"Using database: {db} for {file}")
    conn = sqlite3.connect(
        db, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    c = conn.cursor()
    # which media type should we look up for our file?
    c.execute("""
        SELECT DISTINCT api_type, post_id
        FROM medias
        WHERE medias.directory = ?
    """, (file.as_posix(),))
    row = c.fetchone()
    if not row:
        log.error(f'Could not find metadata for gallery: {file}')
        print('null')
        sys.exit()
    # check for each api_type the right tables
    api_type = str(row[0])
    post_id = str(row[1])
    if api_type in ("Posts", "Stories", "Messages", "Products", "Others"):
        query = f"""
            SELECT posts.post_id, posts.text, posts.created_at
            FROM {api_type.lower()} AS posts
            WHERE posts.post_id = ?
        """
        c.execute(query, (post_id,))
    else:
        log.error(f"Unknown api_type {api_type} for post: {post_id}")
        print('null')
        sys.exit()

    gallery = process_row(c.fetchone(), username, network)

    scrape = {
        "title": gallery["title"], "details": gallery["details"], "date": gallery["date"],
        "urls": gallery["urls"],
        "studio": get_studio_info(username, network),
        "performers": get_performer_info(username, media_dir)
    }
    if api_type == "Messages" and TAG_MESSAGES:
        scrape["tags"] = [{"name": TAG_MESSAGES_NAME}]

    return scrape


# UTILS ############################################################################################
def get_scene_path(scene_id):
    """
    Find and return the path for a scene by its ID.
    """
    scene = stash.find_scene(scene_id)
    # log.debug(scene)
    if scene:
        return scene["files"][0]["path"]

    log.error(f'Path for scene {scene_id} could not be found')
    print('null')
    sys.exit()


def get_gallery_path(gallery_id):
    """
    Find and return the path for a gallery by its ID.
    """
    gallery = stash.find_gallery(gallery_id)
    # log.debug(gallery)
    if gallery:
        return gallery["folder"]["path"]

    log.error(f'Path for gallery {gallery_id} could not be found')
    print('null')
    sys.exit()


def get_performer_info(username, media_dir):
    """
    Resolve performer based on username
    """
    req = stash.find_performers(
        f={
            "name": {"value": username, "modifier": "EQUALS"},
            "OR":{
                "aliases": {"value": username, "modifier": "EQUALS"}
            }
        },
        filter={"page": 1, "per_page": 5},
        fragment="id, name, aliases",  # type: ignore
    )
    log.debug(f'found performer(s): {req}')
    res: Dict = {}
    if len(req) == 1:
        log.debug(f"Found performer id: {req[0]['id']}")
        res['stored_id'] = req[0]['id']
    res['name'] = username

    images = get_performer_images(media_dir)
    if images is not None:
        res["images"] = images

    return [res]


def get_studio_info(studio_name, studio_network):
    """
    Resolve studio based on name and network
    """
    req = stash.find_studios(
        f={
            "name": {"value": f"{studio_name} ({studio_network})", "modifier": "EQUALS"},
            "OR":{
                "aliases": {"value": f"{studio_name} ({studio_network})", "modifier": "EQUALS"}
            }
        },
        filter={"page": 1, "per_page": 5},
        fragment="id, name, aliases"
    )
    log.debug(f'found studio(s): {req}')
    res: Dict = {'parent': {}}
    if len(req) == 1:
        log.debug(f"Found studio id: {req[0]['id']}")
        res['stored_id'] = req[0]['id']
    res['name'] = f'{studio_name} ({studio_network})'
    res['parent']['name'] = f'{studio_network} (network)'
    if studio_network == 'OnlyFans':
        res['url'] = f'https://onlyfans.com/{studio_name}'
        res['parent']['url'] = 'https://onlyfans.com/'
    elif studio_network == 'Fansly':
        res['url'] = f'https://fansly.com/{studio_name}'
        res['parent']['url'] = 'https://fansly.com/'
    return res


def get_performer_images(path):
    """
    Find and encode performer images to base64.
    """
    log.debug(f'Finding image(s) for path: {path}')

    cache = load_cache()

    if str(path) in cache:  # check if the images are cached
        log.debug(f'[CACHE HIT] Using cached image(s) for path: {path}')
        image_filenames = cache[f'{path}'][1]
        log.debug(image_filenames)
        cached_images = []
        for image_filename in image_filenames:
            with open(Path(CACHE_DIR) / image_filename, 'r', encoding="utf-8") as f:
                base64_data = f.read()
                cached_images.append(base64_data)
        return cached_images

    image_types = ["*.jpg", "*.png"]
    image_list = []
    for image_type in image_types:  # get jpg and png files in provided path
        type_result = list(path.rglob(image_type))
        image_list += type_result

    if len(image_list) == 0:  # if no images found
        log.warning(f'No image(s) found for path: {path}')
        return None

    # if images found, encode up to `max_images` to base64
    log.debug(f'[CACHE MISS] Generating image(s) for path: {path}')
    selected_images = random.choices(image_list, k=min(MAX_PERFORMER_IMAGES, len(image_list)))

    encoded_images = []
    cache_filenames = []

    for index, image in enumerate(selected_images):
        log.debug(f"""
            [CACHE MISS] Encoding {index + 1} of {len(selected_images)} image(s) to base64: {image}'
        """)
        base64_data = file_to_base64(image)
        if base64_data is None:
            log.error(f"Error converting image to base64: {image}")
            print('null')
            sys.exit()

        encoded_images.append(base64_data)

        # Store the base64 image data on disk
        image_filename = f'{uuid.uuid4().hex}.b64'
        with open(Path(CACHE_DIR) / image_filename, 'w', encoding="utf-8") as f:
            f.write(base64_data)

        cache_filenames.append(image_filename)

    # Store the file name and timestamp in the cache
    cache[f'{path}'] = (time.time(), cache_filenames)
    save_cache(cache)

    return encoded_images


def truncate_title(title, max_length):
    """
    Truncate title to provided maximum length while preserving word boundaries.
    """
    # Check if the title is already within the desired length
    if len(title) <= max_length:
        return title

    # Find the last space character before the max length
    last_space_index = title.rfind(" ", 0, max_length)
    # If there's no space before the max length, simply truncate the string
    if last_space_index == -1:
        return title[:max_length]
    # Otherwise, truncate at the last space character
    return title[:last_space_index]


def format_title(title, username, date, scene_index):
    """
    Format a post title based on various conditions.
    """
    if len(title) == 0:
        scene_info = f' ({scene_index})' if scene_index > 0 else ''
        return f'{username} - {date}{scene_info}'

    f_title = truncate_title(title.split("\n")[0].strip().replace("<br />", ""), MAX_TITLE_LENGTH)
    scene_info = f' ({scene_index})' if scene_index > 0 else ''

    if len(f_title) <= 5:
        return f'{f_title} - {date}{scene_info}'

    if not bool(re.search("[A-Za-z0-9]", f_title)):
        if scene_index == 0:
            title_max_len = MAX_TITLE_LENGTH - 13
        else:
            title_max_len = MAX_TITLE_LENGTH - 16 - len(str(scene_index))
        t_title = truncate_title(f_title, title_max_len)
        scene_info = f' ({scene_index})' if scene_index > 0 else ''
        return f'{t_title} - {date}{scene_info}'

    scene_info = f' ({scene_index})' if scene_index > 0 else ''
    return f'{f_title}{scene_info}'


def process_row(row, username, network, scene_index=0):
    """
    Process a database row and format post details.
    """
    res = {}
    res['date'] = row[2].strftime("%Y-%m-%d")
    res['title'] = format_title(row[1], username, res['date'], scene_index)
    res['details'] = row[1]
    res['code'] = str(row[0])
    if network == 'OnlyFans':
        res['urls'] = [f"https://onlyfans.com/{res['code']}/{username}"]
    elif network == 'Fansly':
        res['urls'] = [f"https://fansly.com/post/{res['code']}"]
    return res


def get_metadata_db(search_path, username, network):
    """
    Recursively search for 'user_data.db' file starting from 'search_path'
    """
    search_path = Path(search_path).resolve()

    while search_path != search_path.parent:
        db_files = list(search_path.rglob(f"{network}/**/{username}/**/user_data.db"))
        db_files = [db for db in db_files if db.is_file()]
        if db_files:
            return db_files[0]

        search_path = search_path.parent

    return None


def get_path_info(path):
    """
    Extract the username and network from a given path
    """
    network = 'Fansly' if 'Fansly' in str(path) else 'OnlyFans'
    try:
        index = path.parts.index(network)
        if index + 1 < len(path.parts):
            return path.parts[index + 1], network, Path(*path.parts[:index + 2])
        raise ValueError
    except ValueError:
        log.error(f'Could not find username or network in path: {path}')
        print('null')
        sys.exit(1)


# MAIN #############################################################################################
def main():
    """
    Execute scene or gallery lookup and print the result as JSON to stdout
    """
    fragment = json.loads(sys.stdin.read())
    scrape_id = fragment["id"]

    if sys.argv[1] == "queryScene":
        lookup = lookup_scene
        path = Path(get_scene_path(scrape_id))
    elif sys.argv[1] == "queryGallery":
        lookup = lookup_gallery
        path = Path(get_gallery_path(scrape_id))
    else:
        log.error('Invalid argument(s) provided: ' + str(sys.argv))
        print('null')
        sys.exit()

    username, network, media_dir = get_path_info(path)
    db = get_metadata_db(path, username, network)

    media = lookup(path, db, media_dir, username, network)
    print(json.dumps(media))
    sys.exit()


if __name__ == "__main__":
    main()
