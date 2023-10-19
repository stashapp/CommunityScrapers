"""
This script is a companion to the OnlyFans data scrapers by DIGITALCRIMINAL and derivatives.
The above tools download posts from OnlyFans and save metadata to 'user_data.db' SQLite files.

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

try:
    import stashapi.log as log
    from stashapi.tools import file_to_base64
    from stashapi.stashapp import StashInterface
except ModuleNotFoundError:
    print(
        "You need to install the stashapp-tools (stashapi) python module. (cmd): "\
        "pip install stashapp-tools",
        file=sys.stderr
    )
    sys.exit()


###################################  CONFIG ####################################
# Default config
default_config = {
    "stash_connection": {
        "scheme": "http",
        "host": "localhost",
        "port": 9999,
        "apikey": ""
    },
    "max_title_length": 64, # Maximum length for scene/gallery titles.
    "tag_messages": True, # Whether to tag OnlyFans messages.
    "tag_messages_name": "[OF: Messages]", # Name of tag for OnlyFans messages.
    "max_performer_images": 3, # Maximum performer images to generate.
    "cache_time": 300, # Image expiration time (in seconds).
    "cache_dir": "cache", # Directory to store cached base64 encoded images.
    "cache_file": "cache.json" # File to store cache information in.
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

###################################  STASH  ####################################
try:
    stash = StashInterface(STASH_CONNECTION)
except SystemExit:
    log.error("Unable to connect to Stash, please verify your config.")
    # print("{}")
    sys.exit()

###################################  CACHE  ####################################
# Create cache directory
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

def load_cache():
    """
    Load and update cache data, removing expired entries and associated files when necessary.
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
                    log.info(f'[CACHE PURGE] Purging expired image(s) for path: {path}')
                    for image_filename in image_filenames:
                        image_path = Path(CACHE_DIR) / image_filename
                        log.debug(f'[CACHE PURGE] Deleting expired image from disk: {image_path}')
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

###################################  SCENES ####################################
def lookup_scene(file, db, parent):
    """
    Query database for scene metadata and create a structured scrape result.
    """
    log.debug(f"Using database: {db} for {file}")
    conn = sqlite3.connect(
        db, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    c = conn.cursor()
    # which media type should we look up for our file?
    c.execute(
        "SELECT api_type, post_id FROM medias WHERE medias.filename=?",
        (file.name,))
    match = c.fetchone()
    if not match:
        log.error(f'Could not find metadata for scene: {file}')
        print("{}")
        sys.exit()
    # check for each api_type the right tables
    api_type = str(match[0])
    post_id = str(match[1])
    c.execute("""
        SELECT medias.filename
        FROM medias
        WHERE medias.post_id=?
        AND medias.media_type = 'Videos'
        ORDER BY id ASC
        """, (post_id,))
    post = c.fetchall()

    if api_type in ("Posts", "Stories", "Messages", "Products", "Others"):
        query = f"""
            SELECT posts.post_id, posts.text, posts.created_at
            FROM {api_type.lower()} AS posts, medias
            WHERE posts.post_id = medias.post_id
            AND medias.filename = ?
        """
        c.execute(query, (file.name,))
    else:
        log.error("Unknown api_type {api_type} for post: {post_id}")
        print("{}")
        sys.exit()

    log.info(f'Found {len(post)} video(s) in post {post_id}')
    if len(post) > 1:
        scene_index = [item[0] for item in post].index(file.name) + 1
        log.debug(f'Video is {scene_index} of {len(post)} in post')
    else:
        scene_index = 0

    scene = process_row(c.fetchone(), str(parent.name), scene_index)
    images = find_performer_images(parent)
    performer = find_name_from_alias(str(parent.name))

    scrape = {}
    scrape["title"] = scene["title"]
    scrape["details"] = scene["details"]
    scrape["date"] = scene["date"]
    scrape["code"] = scene["code"]
    scrape["studio"] = {
        "name": f'{parent.name} (OnlyFans)',
        "url": f'https://www.onlyfans.com/{parent.name}',
        "parent": find_parent_studio()
    }
    scrape["urls"] = [f'https://www.onlyfans.com/{scene["code"]}/{parent.name}']
    scrape["performers"] = [performer]
    if images is not None:
        performer["images"] = images
    if api_type == "Messages" and TAG_MESSAGES:
        scrape["tags"] = [{"name": TAG_MESSAGES_NAME}]

    return scrape

##################################  GALLERIES ##################################
def lookup_gallery(file, db, parent):
    """
    Query database for gallery metadata and create a structured scrape result.
    """
    log.debug(f"Using database: {db} for {file}")
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
        print("{}")
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
        log.error("Unknown api_type {api_type} for post: {post_id}")
        print("{}")
        sys.exit()

    post = process_row(c.fetchone(), str(parent.name))
    images = find_performer_images(parent)
    performer = find_name_from_alias(str(parent.name))

    scrape = {}
    scrape["title"] = post["title"]
    scrape["details"] = post["details"]
    scrape["date"] = post["date"]
    scrape["studio"] = {
        "name": f'{parent.name} (OnlyFans)',
        "url": f'https://www.onlyfans.com/{parent.name}',
        "parent": find_parent_studio()
    }
    scrape["urls"] = [f'https://www.onlyfans.com/{post["code"]}/{parent.name}']
    scrape["performers"] = [performer]
    if images is not None:
        performer["images"] = images
    if api_type == "Messages" and TAG_MESSAGES:
        scrape["tags"] = [{"name": TAG_MESSAGES_NAME}]

    return scrape

###################################  LOOKUPS ###################################
def find_scene_path(scene_id):
    """
    Find and return the path for a scene by its ID.
    """
    scene = stash.find_scene(scene_id)
    # log.debug(scene)
    if scene:
        return scene["files"][0]["path"]

    log.error(f'Path for scene {scene_id} could not be found')
    print("{}")
    sys.exit()

def find_gallery_path(gallery_id):
    """
    Find and return the path for a gallery by its ID.
    """
    gallery = stash.find_gallery(gallery_id)
    # log.debug(gallery)
    if gallery:
        return gallery["folder"]["path"]

    log.error(f'Path for gallery {gallery_id} could not be found')
    print("{}")
    sys.exit()

def find_name_from_alias(alias):
    """
    Find and return a performer's name by their alias.
    """
    perfs = stash.find_performers(
        f={"aliases": {"value": alias, "modifier": "EQUALS"}},
        filter={"page": 1, "per_page": 5},
        fragment="name,id",
    )
    log.debug(perfs)
    if len(perfs) > 0:
        perf = {"name": perfs[0]['name'], "stored_id": perfs[0]['id']}
        return perf
    return alias

def find_parent_studio():
    """
    Find and return OnlyFans (network) `stored_id` else return only name
    """
    studios = stash.find_studios(
        f={"name": {"value": "OnlyFans (network)", "modifier": "EQUALS"}},
        filter={"page": 1, "per_page": 5},
        fragment="name,id"
    )
    log.debug(studios)
    if len(studios) > 0:
        studio = {
            "name": studios[0]['name'],
            "url": "https://onlyfans.com/",
            "stored_id": studios[0]['id']
        }
        return studio
    return {"name": "OnlyFans (network)", "url": "https://onlyfans.com/"}

def find_performer_images(path, max_images=MAX_PERFORMER_IMAGES):
    """
    Find and encode performer images to base64.
    """
    log.info(f'Finding image(s) for path: {path}')

    cache = load_cache()

    if str(path) in cache: # check if the images are cached
        log.info(f'[CACHE HIT] Using cached image(s) for path: {path}')
        image_filenames = cache[f'{path}'][1]
        log.debug(image_filenames)
        cached_images = []
        for image_filename in image_filenames:
            with open(Path(CACHE_DIR) / image_filename, 'r', encoding="utf-8") as f:
                base64_data = f.read()
                cached_images.append(base64_data)
        return cached_images

    image_list = list(path.rglob("*.jpg")) # get all jpg files in the provided path

    if len(image_list) == 0: # if no images found
        log.info(f'No image(s) found for path: {path}')
        return None

    # if images found, encode up to `max_images` to base64
    log.info(f'[CACHE MISS] Generating image(s) for path: {path}')
    selected_images = random.choices(image_list, k=min(max_images, len(image_list)))

    encoded_images = []
    cache_filenames = []

    for index, image in enumerate(selected_images):
        log.debug(f"""
            [CACHE MISS] Encoding {index + 1} of {len(selected_images)} image(s) to base64: {image}'
        """)
        base64_data = file_to_base64(image)
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

###################################  UTILS  ####################################
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

def process_row(row, username, scene_index=0):
    """
    Process a database row and format post details.
    """
    date = row[2].strftime("%Y-%m-%d")
    title = format_title(row[1], username, date, scene_index)
    details = row[1]
    code = str(row[0])
    return {"title": title, "details": details, "date": date, "code": code}

def find_metadata_db(start_path, username):
    """
    Recursively search for 'user_data.db' file upwards starting from 'start_path'.
    """
    start_path = Path(start_path).resolve()

    while start_path != start_path.parent:
        # Search for user_data.db in the current directory and its subdirectories
        for db_file in start_path.rglob(username + '/**/user_data.db'):
            if db_file.is_file():
                return db_file

        start_path = start_path.parent

    return None

def username_from_path(path, after='OnlyFans'):
    """
    Extract the username from a given path
    """
    path = path.parts
    try:
        index = path.index(after)
        if index + 1 < len(path):
            return path[index + 1]
        else:
            return None  # Element found but no item follows it
    except ValueError:
        return None  # Element not found in the tuple

####################################  MAIN #####################################
def main():
    """
    Execute scene or gallery lookup and print the result as JSON.
    """
    fragment = json.loads(sys.stdin.read())
    scrape_id = fragment["id"]

    path: Path = None
    if sys.argv[1] == "query":
        lookup = lookup_scene
        path = Path(find_scene_path(scrape_id))
    elif sys.argv[1] == "querygallery":
        lookup = lookup_gallery
        path = Path(find_gallery_path(scrape_id))

    if path:
        username = username_from_path(path)

    if username:
        db = find_metadata_db(path, username)

        username_index = list(path.parts).index(username)
        p = Path(*path.parts[:username_index + 1])

        scene = lookup(path, db, p)
        print(json.dumps(scene))
        sys.exit()

    print("{}") # not found return an empty map

if __name__ == "__main__":
    main()

# Last Updated October 19, 2023
