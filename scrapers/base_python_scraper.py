'''
Generic scraper to investigate interaction with stashapp
'''
import argparse
import json
import sys

try:
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! "
        "(CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit(1)

class BasePythonScraper:
    '''
    Class to encapsulate data and functions
    '''
    args: argparse.Namespace = None
    fragment: dict = {}

    def __init__(self):
        '''
        Constructor
        '''
        try:
            self._load_arguments()
            self.__load_fragment()
            self.__process()
        except Exception as ex:
            log.debug(ex)
            log.error('Scraper failed. Exiting.')
            sys.exit(1)

    def _load_arguments(self) -> None:
        '''
        Get the script arguments (specified in the YAML)
        '''
        parser = argparse.ArgumentParser(description='Script argument parser')
        parser.add_argument('action', help='Action for the script to perform')
        self.args = parser.parse_args()
        log.debug(f"args: {self.args}")

    def __load_fragment(self) -> None:
        '''
        Get the JSON fragment from stdin (this is how stashapp sends it)
        '''
        self.fragment = json.loads(input())
        log.debug(f"fragment: {self.fragment}")

    def __str__(self) -> str:
        '''
        Return the string value of the class. In this case, we can use it to
        output the scrape result(s) as JSON
        '''
        return json.dumps(self.result)

    def _get_gallery_by_fragment(self, fragment: dict) -> dict:
        '''
        Get gallery properties by using fragment object. This method should be
        overriden in a derived class in a scraper file

        See derived_python_scraper.py for an example
        '''
        gallery = {}
        gallery['url'] = fragment.get('url')
        return gallery

    def _get_gallery_by_url(self, url: str) -> dict:
        '''
        Get gallery properties by using a URL. This method should be overriden
        in a derived class in a scraper file

        See derived_python_scraper.py for an example
        '''
        gallery = {}
        gallery['url'] = url
        return gallery

    def _get_movie_by_url(self, url: str) -> dict:
        '''
        Get movie properties by using a URL. This method should be overriden in
        a derived class in a scraper file

        See derived_python_scraper.py for an example
        '''
        movie = {}
        movie['url'] = url
        return movie

    def _get_performer_by_fragment(self, fragment: dict) -> dict:
        '''
        Get performer properties by using fragment object. This method should be
        overriden in a derived class in a scraper file

        See derived_python_scraper.py for an example
        '''
        performer = {}
        performer['url'] = fragment.get('url')
        return performer

    def _get_performer_by_name(self, name: str) -> dict:
        '''
        Get performer properties by using a name. This method should be
        overriden in a derived class in a scraper file

        See derived_python_scraper.py for an example
        '''
        performer = {}
        performer['name'] = name
        return performer

    def _get_performer_by_url(self, url: str) -> dict:
        '''
        Get performer properties by using a URL. This method should be overriden
        in a derived class in a scraper file

        See derived_python_scraper.py for an example
        '''
        performer = {}
        performer['url'] = url
        return performer

    def _get_scene_by_fragment(self, fragment: dict) -> dict:
        '''
        Get scene properties by using fragment object. This method should be
        overriden in a derived class in a scraper file

        See derived_python_scraper.py for an example
        '''
        scene = {}
        scene['url'] = fragment.get('url')
        return scene

    def _get_scene_by_name(self, name: str) -> dict:
        '''
        Get scene properties by using a name. This method should be overriden in
        a derived class in a scraper file

        See derived_python_scraper.py for an example
        '''
        scene = {}
        scene['title'] = name
        return scene

    def _get_scene_by_query_fragment(self, fragment: dict) -> dict:
        '''
        Get scene properties by using fragment object. This method should be
        overriden in a derived class in a scraper file

        See derived_python_scraper.py for an example
        '''
        scene = {}
        scene['url'] = fragment.get('url')
        return scene

    def _get_scene_by_url(self, url: str) -> dict:
        '''
        Get scene properties by using a URL. This method should be overriden in
        a derived class in a scraper file

        See derived_python_scraper.py for an example
        '''
        scene = {}
        scene['url'] = url
        return scene

    def __process(self) -> None:
        '''
        Process with the scraper using the initialised arguments and input
        '''
        if self.args.action == 'galleryByFragment':
            self.result = self._get_gallery_by_fragment(self.fragment)
        elif self.args.action == 'galleryByURL':
            self.result = self._get_gallery_by_url(self.fragment.get('url'))
        elif self.args.action == 'movieByURL':
            self.result = self._get_movie_by_url(self.fragment.get('url'))
        elif self.args.action == 'performerByFragment':
            self.result = self._get_performer_by_fragment(self.fragment)
        elif self.args.action == 'performerByName':
            self.result = self._get_performer_by_name(self.fragment.get('name'))
        elif self.args.action == 'performerByURL':
            self.result = self._get_performer_by_url(self.fragment.get('url'))
        elif self.args.action == 'sceneByFragment':
            self.result = self._get_scene_by_fragment(self.fragment)
        elif self.args.action == 'sceneByName':
            self.result = self._get_scene_by_name(self.fragment.get('name'))
        elif self.args.action == 'sceneByQueryFragment':
            self.result = self._get_scene_by_query_fragment(self.fragment)
        elif self.args.action == 'sceneByURL':
            self.result = self._get_scene_by_url(self.fragment.get('url'))
        else:
            raise NotImplementedError(f"'{self.args.action}' is not implemented")


if __name__ == '__main__':
    # run the scraper
    result = BasePythonScraper()

    # print scraped result (should be stringified JSON)
    print(result)
