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
        except Exception as ex:
            log.debug(ex)
            log.error('Scraper initialisation failed. Exiting.')
            sys.exit(1)

    def __load_arguments(self):
        '''
        Get the script arguments (specified in the YAML)
        '''
        parser = argparse.ArgumentParser(description='Script argument parser')
        parser.add_argument('action', help='Action for the script to perform')
        self.args = parser.parse_args()

    def __load_fragment(self):
        '''
        Get the JSON scene fragment from stdin (this is how stashapp sends it)
        '''
        self.fragment = json.loads(input())
        log.debug(f"fragment: {self.fragment}")

    def start_processing(self):
        '''
        Start processing the scraper with the supplied arguments and input
        '''
        pass


if __name__ == '__main__':
    # instantiate class
    scraper = PythonScraper()

    # start processing
    scraper.start_processing()
