from datetime import date, datetime
import json
import os
import sys
import typing
import zipfile

try:
    from py_common import graphql, log
    from py_common.util import dig, scraper_args
except:
    # can be ignored if running in test
    if 'unittest' in sys.modules:
        pass
    else:
        raise


def get_gallery_metadatas(path:str) -> typing.Iterable[dict[str, str | list | dict]] | None:
    # is directory of files
    if os.path.isdir(path):
        return get_gallery_metadatas_in_directory(path)
    # is file (archive)
    elif os.path.isfile(path):
        return get_gallery_metadatas_in_archive(path)
    # something else???
    else:
        return []


def get_gallery_metadatas_in_directory(path:str) -> typing.Iterable[dict[str, str | list | dict]] | None:
    for root, dirs, files in os.walk(path):
        for file in files:
            if file == 'info.json':
                with open(os.path.join(root, file)) as info_file:
                    yield json.loads(info_file.read())


def get_gallery_metadatas_in_archive(path:str) -> typing.Iterable[dict[str, str | list | dict]] | None:
    with zipfile.ZipFile(path) as zip:
        for filepath in zip.namelist():
            if os.path.basename(filepath) == 'info.json':
                with zip.open(filepath) as info_file:
                    yield json.loads(info_file.read())


def get_file_metadatas(path:str) -> typing.Iterable[dict[str, str | list | dict]] | None:
    # detect if file is within zip or cbz file
    archive_path = None
    file_path_in_archive = None
    current_path, current_file_path = os.path.split(path)
    while current_path is not None and len(current_path) > 0 and current_path != '/':
        if current_path.endswith('.zip') or current_path.endswith('.cbz'):
            archive_path = current_path
            file_path_in_archive = current_file_path
            break

        current_path, current_file_name = os.path.split(current_path)
        current_file_path = os.path.join(current_file_name, current_file_path)

    if archive_path is not None:
        return get_file_metadatas_in_archive(archive_path, file_path_in_archive)
    else:
        return get_file_metadatas_in_directory(path)

def _build_possible_metadata_file_paths(path: str) -> list[str]:
    ret = [path + '.json']

    # try looking for other variants (for stuff like when pngs got optimized to jpg)
    path_without_extension = path[:path.rfind('.')]
    for extension in ('jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'jxl', 'avif', 'mp4', 'mkv'):
        ret.append(path_without_extension + '.' + extension + '.json')

    return ret

def get_file_metadatas_in_directory(path:str) -> typing.Iterable[dict[str, str | list | dict]] | None:
    metadata_file_paths = _build_possible_metadata_file_paths(path)

    for metadata_file_path in metadata_file_paths:
        if os.path.exists(metadata_file_path):
            with open(metadata_file_path) as info_file:
                yield json.loads(info_file.read())


def get_file_metadatas_in_archive(archive_path:str, file_path_in_archive:str) -> typing.Iterable[dict[str, str | list | dict]] | None:
    metadata_file_paths = {filepath for filepath in _build_possible_metadata_file_paths(file_path_in_archive)}
    with zipfile.ZipFile(archive_path) as zip:
        for filepath in zip.namelist():
            if filepath in metadata_file_paths:
                with zip.open(filepath) as info_file:
                    yield json.loads(info_file.read())


def process_metadata(metadata: dict[str, int | str | list[str]], context: str) -> dict[str, str | list[str] | dict[str, str]]:
    ret = {
        'Performers': [],
        'Tags': []
    } #  type: dict[str, str|list[str]|dict[str, str]]

    has_artist = False
    title_suffixed = False

    for key, value in metadata.items():
        if key.lower() == 'title':
            ret['Title'] = value
        # fields like 'title_en' - first come first serve, 'title has priority over it'
        elif key.lower().startswith('title'):
            # title field names with suffixes  have lower priority than those that
            if 'Title' not in ret:
                ret['Details'] = value
        elif key.lower() == 'description':
            ret['Details'] = value
        elif context == 'gallery' and (key.lower() == 'gallery_id' or key.lower() == 'gid' or key.lower() == 'id') and 'Code' not in ret:
            ret['Code'] = str(value)
        elif key.lower() == 'date':
            value_as_date = None
            # is probably a timestamp
            if isinstance(value, int):
                # > 10 x MAX_INT -> probably millisecondy
                if value > 2147483647 * 10:
                    timestamp = value / 1000
                else:
                    timestamp = value
                value_as_date = date.fromtimestamp(timestamp)
            # probably ISO date
            elif isinstance(value, str):
                # ISO datetime
                if len(value) > 12:
                    try:
                        value_as_date = datetime.fromisoformat(value).date()
                    except:
                        # guessed wrong
                        pass
                # ISO date
                else:
                    try:
                        value_as_date = date.fromisoformat(value)
                    except:
                        # guessed wrong
                        pass
            
            if value_as_date is not None:
                ret['Date'] = value_as_date.isoformat()
        elif key.lower() == 'artist' or key.lower() == 'artists':
            for value_entry in _value_to_list(value):
                # artist has priority over group for studio
                if 'Studio' not in ret or not has_artist:
                    ret['Studio'] = {
                        'Name': value_entry
                    }
                    has_artist = True
        elif key.lower() == 'group' or key.lower() == 'studio' or key.lower() == 'studios':
            for value_entry in _value_to_list(value):
                if 'Studio' not in ret:
                    ret['Studio'] = {
                        'Name': value_entry
                    }
                if 'Photographer' not in ret:
                    ret['Photographer'] = value_entry
        # tags
        elif key.lower() == 'tags' or key.lower() == 'categories' or key.lower() == 'parody':
            for value_entry in _value_to_list(value, key.lower()):
                # prefixed tag
                if ':' in value_entry:
                    value_entry_prefix, value_entry_value = value_entry.split(':', 1)
                    # map group prefix to studio and photographer
                    if value_entry_prefix == 'group' :
                        ret['Studio'] = {
                            'Name': value_entry_value
                        }
                        if 'Photographer' not in ret:
                            ret['Photographer'] = value_entry_value
                    # map artists prefix to studio
                    elif value_entry_prefix == 'artist':
                        # artist has priority over group for studio
                        if 'Studio' not in ret or not has_artist:
                            ret['Studio'] = {
                                'Name': value_entry_value
                            }
                            has_artist = True
                    # performer tags
                    elif value_entry_prefix == 'character' or key.lower() == 'models' or value_entry_prefix == 'cosplayer':
                        ret['Performers'].append({
                            'Name': value_entry_value
                        })
                    # wan't to keep the prefix for some
                    elif value_entry_prefix == 'male' or value_entry_prefix == 'language':
                        ret['Tags'].append({
                            'Name': value_entry
                        })
                    # emit tag without prefix
                    else:
                        ret['Tags'].append({
                            'Name': value_entry_value
                        })
                # unprefixed tag
                else:
                    ret['Tags'].append({
                        'Name': value_entry
                    })
        # performers
        elif key.lower() == 'characters' or key.lower() == 'models' or key.lower() == 'performers':
            for value_entry in _value_to_list(value):
                ret['Performers'].append({
                    'Name': value_entry
                })

    if len(ret['Performers']) == 0:
        del ret['Performers']
    if len(ret['Tags']) == 0:
        del ret['Tags']

    return ret


def process_gallery_path(path) -> dict[str, str|list[str]|dict[str, str]]:
    ret = {}

    for metadata in get_gallery_metadatas(path):
        data = process_metadata(metadata, context="gallery")
        ret.update(data)

    return ret


def process_image_path(path) -> dict[str, str|list[str]|dict[str, str]]:
    ret = {}

    for metadata in get_file_metadatas(path):
        data = process_metadata(metadata, context="image")
        ret.update(data)

    return ret


def process_scene_path(path) -> dict[str, str|list[str]|dict[str, str]]:
    ret = {}

    for metadata in get_file_metadatas(path):
        data = process_metadata(metadata, context="scene")
        ret.update(data)

    return ret


def _value_to_list(value:str|list, field_name=None) -> list:
    if isinstance(value, list):
        return value
    # special logic for tags field value that is a single string
    elif value and isinstance(value, str) and field_name == 'tags':
        # is comma-separated string
        if ',' in value:
            return [value_part.strip() for value_part in value.split(',')]
        # is space-separated string
        elif ' ' in value:
            return [value_part.strip().replace('_', ' ') for value_part in value.split(' ')]
    elif value:
        return [value]
    else:
        return []


def get_imape_paths(image_id):
    query = """
	query FindImage($id: ID!) {
	  findImage(id: $id) {
	    id
	    visual_files {
	    	__typename
	    	... on BaseFile {
	      	path
	    	}
	  	}
	  }
	}
	"""
    result = graphql.callGraphQL(query, {"id": image_id})
    data = dig(result, "findImage")

    log.trace(f"image paths data: {data}")

    return data['visual_files']


def get_scene_paths(scene_id):
    query = """
	query FindScene($id: ID!) {
	  findScene(id: $id) {
	    id
	    files {
	    	__typename
	    	... on BaseFile {
	      	path
	    	}
	  	}
	  }
	}
	"""
    result = graphql.callGraphQL(query, {"id": scene_id})
    data = dig(result, "findScene")

    log.trace(f"scene paths data: {data}")

    return data['files']

#
# Start processing
#

if __name__ == "__main__":
    op, args = scraper_args()
    log.trace(f"invoked {op} with {args}")
    result = None
    match op, args:
        case "gallery-by-fragment", {"files": files} if files:
            ret = {}

            for file in files:
                data = process_gallery_path(file['path'])
                ret.update(data)
            
            print(json.dumps(ret))
            sys.exit(0)
        case "image-by-fragment", {"id": image_id} if image_id:
            ret = {}

            files = get_imape_paths(image_id)
            for file in files:
                data = process_image_path(file['path'])
                ret.update(data)

            print(json.dumps(ret))
            sys.exit(0)
        case "scene-by-fragment", {"id": scene_id} if scene_id:
            ret = {}

            files = get_scene_paths(scene_id)
            for file in files:
                data = process_scene_path(file['path'])
                ret.update(data)

            print(json.dumps(ret))
            sys.exit(0)
        case _:
            log.error(f"Not Implemented: Operation: {op}, arguments: {json.dumps(args)}")
            sys.exit(1)

    print(json.dumps({}))
    sys.exit(1)