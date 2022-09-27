import json
import os
import sys
from typing import List, Union
import xml.etree.ElementTree

try:
    import py_common.log as log
    import py_common.graphql as graphql
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo (CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr
    )
    sys.exit()

# Allows us to simply debug the script via CLI args
if len(sys.argv) > 2 and '-d' in sys.argv:
    stdin = sys.argv[sys.argv.index('-d') + 1]
else:
    stdin = sys.stdin.read()

frag: dict = json.loads(stdin)
id = frag.get('id')
scene: dict = None
path_in_frag = frag.get('path', None)
if path_in_frag is None:
    scene: dict = graphql.getScene(id)
else:
    scene = {'path': path_in_frag}
scene_path: str = scene.get('path')
sceneByFragment = 'sceneByFragment' in sys.argv


def CreateNfoPathByScenePath():
    dir: str = os.path.dirname(scene_path)
    nfo_path: str = os.path.join(dir, os.path.splitext(
        os.path.basename(scene_path))[0] + ".nfo")
    if os.path.isfile(nfo_path):
        return nfo_path

    nfo_path: str = os.path.join(
        dir, ".nfo" + os.path.sep, os.path.splitext(os.path.basename(scene_path))[0] + ".nfo")
    log.debug(nfo_path)
    return nfo_path


class Performer:
    def __init__(self, name: str, image: str = ''):
        self.name = name
        self.url: str = ''
        self.image: str = image
        self.gender: str = ''
        self.twitter: str = ''
        self.instagram: str = ''
        self.birthdate: str = ''
        self.deathdate: str = ''
        self.ethnicity: str = ''
        self.country: str = ''
        self.haircolor: str = ''
        self.eyecolor: str = ''
        self.height: str = ''
        self.weight: str = ''
        self.measurements: str = ''
        self.faketits: str = ''
        self.careerlength: str = ''
        self.tattoos: str = ''
        self.piercings: str = ''
        self.aliases: str = ''
        self.tags: List[Tag] = []
        self.details: str = ''

        # Private
        self.singulars = {
            'aliases': 'alias',
            'tags': 'tag',
        }
        self.plurals = {
            'alias': 'aliases',
            'tag': 'tags',
        }

    def ToDict(self):
        return {
            'name': self.name,
            'url': self.url,
            'image': self.image,
            'gender': self.gender,
            'twitter': self.twitter,
            'instagram': self.instagram,
            'birthdate': self.birthdate,
            'deathdate': self.deathdate,
            'ethnicity': self.ethnicity,
            'country': self.country,
            'haircolor': self.haircolor,
            'eyecolor': self.eyecolor,
            'height': self.height,
            'weight': self.weight,
            'measurements': self.measurements,
            'faketits': self.faketits,
            'careerlength': self.careerlength,
            'tattoos': self.tattoos,
            'piercings': self.piercings,
            'aliases': self.aliases,
            'tags': [tag.ToDict() for tag in self.tags],
            'details': self.details,
        }


class Studio:
    def __init__(self, name: str, logo: str = ''):
        self.name = name
        self.details: str = ''
        self.url: str = ''
        self.logo: str = logo
        self.aliases: List[str] = []

        # Private
        self.singulars = {
            'aliases': 'alias',
        }
        self.plurals = {
            'alias': 'aliases',
        }

    def ToDict(self):
        return {
            'name': self.name,
            'details': self.details,
            'url': self.url,
            'logo': self.logo,
            'aliases': self.aliases,
        }


class Tag:
    def __init__(self, name: str):
        self.name = name

    def ToDict(self):
        return {'name': self.name}


class Scene:
    def __init__(self):
        self.id: str = ''
        self.url: str = ''
        self.title: str = ''
        self.performers: List[Performer] = []
        self.details: str = ''
        self.date: str = ''
        self.studio: Studio = None
        self.image: str = ''
        self.rating: int = 0
        self.tags: List[Tag] = []

    def ToDict(self):
        return {
            # 'id': self.id, # We not going to change id and it isn't needed anyway
            'url': self.url,
            'title': self.title,
            'details': self.details,
            'date': self.date,
            'image': self.image,
            # 'rating': self.rating, # Well well, this is a personal thing i guess, so we wont set it because nfo files might be shared
            'studio': None if self.studio is None else self.studio.ToDict(),
            'performers': [performer.ToDict() for performer in self.performers],
            'tags': [tag.ToDict() for tag in self.tags],
        }


def return_result(result: Scene):
    """
    Return the result to stash and exit the script.

    Returns:
        None: Totally exit the scraper via sys.exit(0)
    """
    try:
        if result is None:
            print(json.dumps({}))
        else:
            str_result = json.dumps(result.ToDict())
            log.debug(str_result)
            print(str_result)
        sys.exit(0)
    except Exception as err:
        log.error(f"Exception occurred during returning result: {err}")


class NFO:
    def __init__(self, nfo_path: str) -> None:
        self.nfo_path = nfo_path
        self.nfo = None
        self.scene: Scene = Scene()
        self.nfo_path = self.nfo_path if self.__fix_file() else None

    def __fix_file(self) -> bool:
        """By now, this function eliminates empty line breaks at the start of a file
        until it reaches the <?xml

        Python's xml parser throws exception in such cases, and `kodi-helper` creates such files.

        """
        if self.nfo_path is None or os.path.isfile(self.nfo_path) == False:
            return False

        with open(self.nfo_path, 'r+') as f:
            counter: int = 0
            line = ''
            # First of all, before eliminating the lines, check if it's really xml/nfo file.
            data = f.read()
            if '<?xml' not in data or '?>' not in data or '<movie>' not in data:
                return False
            f.seek(0)
            data = ''

            while True:
                line = f.readline()
                if len(line.strip()) > 0 and line.lower().startswith('<?xml'):
                    break
                else:
                    counter += 1
            if counter > 0:
                # File has to be fixed/modified
                data = line + f.read()
                f.seek(0)
                f.write(data)
                f.truncate()
        return True

    def __parse_actors(self, actors: List[xml.etree.ElementTree.Element]):
        for actor in actors:
            performer = Performer(actor.findtext(
                'name'), actor.findtext('thumb'))
            performer_dict = performer.ToDict()
            for key in performer_dict:
                value: Union[str, list] = performer_dict[key]
                if isinstance(value, str):
                    # Trim the value if is string
                    value = value.strip()
                if value is None or len(value) == 0:
                    # Value is empty, let's try to set it by it's actor's equivalent element
                    # We check for both singular and plural keys,
                    # example: including several <aliases> with a single alias is not correct in grammar
                    # so we check for <alias> too.
                    keys_to_check: List[str] = []
                    keys_to_check.append(key)
                    if key in performer.singulars:
                        keys_to_check.append(performer.singulars.get(key))
                    if key in performer.plurals:
                        keys_to_check.append(performer.plurals.get(key))
                    result_list: List[str] = []
                    for key_to_check in keys_to_check:
                        results = actor.findall(key_to_check)
                        if len(results) > 0:
                            result_list.extend(
                                [result.text for result in results])
                    # Set the Performer's attribute value.
                    setattr(performer, key, " / ".join(result_list)
                            if isinstance(value, list) == False else result_list)

            self.scene.performers.append(performer)

    def __parse_studio(self, studio: xml.etree.ElementTree.Element):
        if studio is None:
            return
        studio_has_child: bool = studio.__len__() > 0
        if studio_has_child == False:
            return
        if self.scene.studio is None:
            self.scene.studio = Studio('')
        studio_dict = self.scene.studio.ToDict()
        for key in studio_dict:
            value: Union[str, list] = studio_dict[key]
            if isinstance(value, str):
                # Trim the value if is string
                value = value.strip()
            if value is None or len(value) == 0:
                # Value is empty, let's try to set it by it's actor's equivalent element
                # Value is empty, let's try to set it by it's actor's equivalent element
                # We check for both singular and plural keys,
                # example: including several <aliases> with a single alias is not correct in grammar
                # so we check for <alias> too.
                keys_to_check: List[str] = []
                keys_to_check.append(key)
                if key in self.scene.singulars:
                    keys_to_check.append(self.scene.studio.singulars.get(key))
                if key in self.scene.studio.plurals:
                    keys_to_check.append(self.scene.studio.plurals.get(key))
                result_list: List[str] = []
                for key_to_check in keys_to_check:
                    results = studio.findall(key_to_check)
                    if len(results) > 0:
                        result_list.extend(
                            [result.text for result in results])
                # Set the Performer's attribute value.
                setattr(self.scene.studio, key, " / ".join(result_list)
                        if isinstance(value, list) == False else result_list)

    def parse(self) -> bool:
        if self.nfo_path is None or os.path.isfile(self.nfo_path) == False:
            return False

        # create element tree object
        tree = xml.etree.ElementTree.parse(self.nfo_path)

        # get root element
        movie = tree.getroot()

        unique_ids = movie.findall('uniqueid')
        for unique_id in unique_ids:
            type: str = unique_id.get('type').lower()
            if type == 'stash':
                self.scene.id = unique_id.text

        self.scene.url = movie.findtext('url')

        self.scene.title = movie.findtext('title')

        self.__parse_actors(movie.findall('actor'))

        self.scene.details = movie.findtext('plot')

        self.scene.date = movie.findtext('premiered')

        # Kodi backward compatibility
        self.scene.studio = Studio(movie.findtext('studio'))

        # A full Studio model which can have name, url, and logo child elements
        studio_with_childs = movie.find('studiomodel')
        self.__parse_studio(studio_with_childs)

        thumbs = movie.findall('thumb')
        for thumb in thumbs:
            aspect: str = thumb.get('aspect').lower()
            if aspect == 'poster':
                self.scene.image = thumb.text
            elif aspect == 'clearlogo':
                self.scene.studio.logo = thumb.text

        self.scene.rating = movie.findtext('userrating')

        tags = movie.findall('tag')
        self.scene.tags = [Tag(tag.text) for tag in tags]

        return True


nfo: NFO = NFO(CreateNfoPathByScenePath())
parse_result = nfo.parse()
if parse_result == False:
    nfo.scene = None

return_result(nfo.scene)

# Last Updated September 26, 2022
