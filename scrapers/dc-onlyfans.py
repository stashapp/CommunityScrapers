import json
import sys
import sqlite3
from pathlib import Path
import base64
import mimetypes

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

def lookup_scene(file,db,parent):
    log.info(f"using database: {db.name}  {file.name}")
    conn = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    c=conn.cursor()
    # which media type should we look up for our file?
    c.execute('select api_type from medias where medias.filename=?',(file.name,))
    row=c.fetchone()
    #check for each api_type the right tables
    api_type = str(row[0])
    if api_type == 'Posts':
        c.execute('select posts.post_id,posts.text,medias.link,posts.created_at from posts,medias where posts.post_id=medias.post_id and medias.filename=?',(file.name,))
    elif api_type == "Stories":
        c.execute('select posts.post_id,posts.text,medias.link,posts.created_at from stories as posts,medias where posts.post_id=medias.post_id and medias.filename=?',(file.name,))
    elif api_type == "Messages":
        c.execute('select posts.post_id,posts.text,medias.link,posts.created_at from messages as posts,medias where posts.post_id=medias.post_id and medias.filename=?',(file.name,))
    elif api_type == "Products":
        c.execute('select posts.post_id,posts.text,medias.link,posts.created_at from products as posts,medias where posts.post_id=medias.post_id and medias.filename=?',(file.name,))
    else: # api_type == "Others"
        c.execute('select posts.post_id,posts.text,medias.link,posts.created_at from others as posts,medias where posts.post_id=medias.post_id and medias.filename=?',(file.name,))
    row=c.fetchone()
    res={}
    res['title']=str(parent.name)+ ' - '+row[3].strftime('%Y-%m-%d')
    res['details']=row[1]
    res['studio']={'name':'OnlyFans','url':'https://www.onlyfans.com/'}
    res['url']='https://www.onlyfans.com/'+str(row[0])+'/'+parent.name
    res['date']=row[3].strftime('%Y-%m-%d')
    performer={"name":parent.name}
    image=findPerformerImage(parent)
    if image is not None:
        performer['image']=make_image_data_url(image)
    res['performers']=[performer]


    return res

def lookup_gallery(file,db,parent):
    log.info(f"using database: {db.name}  {file.name}")
    conn = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    c=conn.cursor()
    # which media type should we look up for our file?
    c.execute('select distinct api_type, post_id from medias where medias.directory = ?',(file.as_posix(),))
    row=c.fetchone()
    #check for each api_type the right tables
    api_type = str(row[0])
    post_id = str(row[1])
    if api_type == 'Posts':
        c.execute('select posts.post_id,posts.text,posts.created_at from posts where posts.post_id=?',(post_id,))
    elif api_type == "Stories":
        c.execute('select posts.post_id,posts.text,posts.created_at from stories as posts where posts.post_id=?',(post_id,))
    elif api_type == "Messages":
        c.execute('select posts.post_id,posts.text,posts.created_at from messages as posts where posts.post_id=?',(post_id,))
    elif api_type == "Products":
        c.execute('select posts.post_id,posts.text,posts.created_at from products as posts where posts.post_id=?',(post_id,))
    else: # api_type == "Others"
        c.execute('select posts.post_id,posts.text,posts.created_at from others as posts where posts.post_id=?',(post_id,))
    row=c.fetchone()
    res={}
    res['title']=str(parent.name)+ ' - '+row[2].strftime('%Y-%m-%d')
    res['details']=row[1]
    res['studio']={'name':'OnlyFans','url':'https://www.onlyfans.com/'}
    res['url']='https://www.onlyfans.com/'+str(row[0])+'/'+parent.name
    res['date']=row[2].strftime('%Y-%m-%d')
    performer={"name":parent.name}
    image=findPerformerImage(parent)
    if image is not None:
        performer['image']=make_image_data_url(image)
    res['performers']=[performer]


    return res

def findFilePath(id):
    scene=graphql.getScene(id)
    if scene:
        return scene["path"]
    log.error(f"Error connecting to api")
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
        gallery = graphql.getGalleryPath(id)
        if gallery:
            gallery_path = gallery.get("path")
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