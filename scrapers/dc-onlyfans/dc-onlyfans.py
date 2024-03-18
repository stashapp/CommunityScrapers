import json
import sys
import sqlite3
from pathlib import Path
import base64
import mimetypes
import datetime

try:
    import py_common.graphql as graphql
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()


''' This script is a companion to the onlyfans data scraper by DIGITALCRIMINAL
    https://github.com/DIGITALCRIMINAL/OnlyFans
    This tool allows you to download data from onlyfans and saves some metadata on what it downloads.

    This script needs python3 and requests and sqlite3
    If you have a password on your instance you need to specify the api key by adding it to py_common/config.py
   '''
def format_date_from_string(date_str):
    """Convert a date string from the database to the format '%Y-%m-%d'."""
    # Attempt to parse the date_str assuming it's in a recognizable datetime format
    try:
        # If the string includes time information, it's parsed and ignored
        return datetime.strptime(date_str.split(' ')[0], "%Y-%m-%d").strftime('%Y-%m-%d')
    except ValueError:
        # Log the error or handle unexpected formats as needed
        log.error("Unrecognized date format: " + date_str)
def lookup_scene(file, db, parent):
    log.info(f"using database: {db.name}  {file.name}")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    # Which media type should we look up for our file?
    c.execute('SELECT api_type FROM medias WHERE medias.filename=?', (file.name,))
    row = c.fetchone()
    # Check for each api_type the right tables
    api_type = str(row[0])
    if api_type == 'Posts':
        c.execute('SELECT posts.post_id, posts.text, medias.link, posts.created_at FROM posts, medias WHERE posts.post_id = medias.post_id AND medias.filename = ?', (file.name,))
    elif api_type == "Stories":
        c.execute('SELECT posts.post_id, posts.text, medias.link, posts.created_at FROM stories AS posts, medias WHERE posts.post_id = medias.post_id AND medias.filename = ?', (file.name,))
    elif api_type == "Messages":
        c.execute('SELECT posts.post_id, posts.text, medias.link, posts.created_at FROM messages AS posts, medias WHERE posts.post_id = medias.post_id AND medias.filename = ?', (file.name,))
    elif api_type == "Products":
        c.execute('SELECT posts.post_id, posts.text, medias.link, posts.created_at FROM products AS posts, medias WHERE posts.post_id = medias.post_id AND medias.filename = ?', (file.name,))
    else:  # api_type == "Others"
        c.execute('SELECT posts.post_id, posts.text, medias.link, posts.created_at FROM others AS posts, medias WHERE posts.post_id = medias.post_id AND medias.filename = ?', (file.name,))
    row = c.fetchone()

    # Manually format the date from the fetched row
    formatted_date = row[3][:10]  # Assuming the date is in 'YYYY-MM-DD' format in the string

    res = {
        'title': f"{str(parent.name)} - {formatted_date}",
        'details': row[1],
        'studio': {'name': 'OnlyFans', 'url': 'https://www.onlyfans.com/'},
        'url': f"https://www.onlyfans.com/{row[0]}/{parent.name}",
        'date': formatted_date,
        'performers': [{'name': parent.name, 'images': []}]
    }

    image = findPerformerImage(parent)
    if image is not None:
        res['performers'][0]['images'].append(make_image_data_url(image))

    return res
def lookup_gallery(file, db, parent):
    log.info(f"using database: {db.name}  {file.name}")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    # Determine which media type we're looking up for our file
    c.execute('SELECT DISTINCT api_type, post_id FROM medias WHERE medias.directory = ?', (file.as_posix(),))
    row = c.fetchone()

    if row:
        api_type, post_id = row
        # Check for each api_type the right tables
        if api_type == 'Posts':
            c.execute('SELECT post_id, text, created_at FROM posts WHERE post_id = ?', (post_id,))
        elif api_type == "Stories":
            c.execute('SELECT post_id, text, created_at FROM stories WHERE post_id = ?', (post_id,))
        elif api_type == "Messages":
            c.execute('SELECT post_id, text, created_at FROM messages WHERE post_id = ?', (post_id,))
        elif api_type == "Products":
            c.execute('SELECT post_id, text, created_at FROM products WHERE post_id = ?', (post_id,))
        else:  # api_type == "Others"
            c.execute('SELECT post_id, text, created_at FROM others WHERE post_id = ?', (post_id,))

        row = c.fetchone()
        if row:
            # Manually format the date from the fetched row
            formatted_date = row[2][:10]  # Assuming the date is in 'YYYY-MM-DD' format in the string

            res = {
                'title': f"{parent.name} - {formatted_date}",
                'details': row[1],
                'studio': {'name': 'OnlyFans', 'url': 'https://www.onlyfans.com/'},
                'url': f"https://www.onlyfans.com/{row[0]}/{parent.name}",
                'date': formatted_date,
                'performers': [{'name': parent.name, 'images': []}]
            }

            image = findPerformerImage(parent)
            if image is not None:
                res['performers'][0]['images'].append(make_image_data_url(image))

            return res
    return {}


def findFilePath(id):
    scene=graphql.getScene(id)
    if scene and "files" in scene:
        return scene["files"][0].get("path")
    log.error("Error connecting to api")
    print("{}")
    sys.exit()

def findPerformerImage(path):
    for c in path.iterdir():
        if c.is_file() and c.name.endswith('.jpg'):
            return c
        elif c.is_dir():
            r=findPerformerImage(c)
            if r is not None:
                return r
    return None

def make_image_data_url(image_path):
    # type: (str,) -> str
    mime, _ = mimetypes.guess_type(image_path)
    with open(image_path, 'rb') as img:
        encoded = base64.b64encode(img.read()).decode()
    return 'data:{0};base64,{1}'.format(mime, encoded)

if __name__ == '__main__':
    fragment = json.loads(sys.stdin.read())
    log.debug(json.dumps(fragment))
    id=fragment['id']

    file: Path = None
    if sys.argv[1] == "query":
        lookup = lookup_scene
        file=Path(findFilePath(id))
    elif sys.argv[1] == "querygallery":
        lookup = lookup_gallery
        gallery_path = graphql.getGalleryPath(id)
        if gallery_path:
            file = Path(gallery_path)

    if file:
        p=file.parent
        while not (Path(p.root)==p):
            p=p.parent
            for child in p.iterdir():
                if child.is_dir():
                    for c in child.iterdir():
                        if c.name== "user_data.db":
                            scene=lookup(file,c,p)
                            print(json.dumps(scene))
                            sys.exit()
                if child.name=="user_data.db":
                    scene = lookup(file, child, p)
                    print(json.dumps(scene))
                    sys.exit()
        # not found return an empty map
        print("{}")
