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

class PythonScraper:
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
            self.__load_arguments()
            self.__load_fragment()
            self.__process()
        except Exception as ex:
            log.debug(ex)
            log.error('Scraper initialisation failed. Exiting.')
            sys.exit(1)

    def __load_arguments(self) -> None:
        '''
        Get the script arguments (specified in the YAML)
        '''
        parser = argparse.ArgumentParser(description='Script argument parser')
        parser.add_argument('action', help='Action for the script to perform')
        self.args = parser.parse_args()

    def __load_fragment(self) -> None:
        '''
        Get the JSON fragment from stdin (this is how stashapp sends it)
        '''
        self.fragment = json.loads(input())
        log.debug(f"fragment: {self.fragment}")

    def __str__(self) -> str:
        '''
        Return the scrape result(s) as JSON
        '''
        return json.dumps(self.result)

    def __get_scene_by_url(self, url: str) -> dict:
        scene = {}
        scene['url'] = url
        return scene

    def __process(self) -> None:
        '''
        Process with the scraper using the initialised arguments and input
        '''
        if self.args.action == 'sceneByURL':
            # TODO: implement properly
            self.result = self.__get_scene_by_url(self.fragment.get('url'))


if __name__ == '__main__':
    # run the scraper
    result = PythonScraper()

    # print scraped result (should be stringified JSON)
    print(result)
