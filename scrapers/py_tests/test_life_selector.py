'''
Unit tests for life_selector.py scraper

You can run this test with the following command:

python3 -m unittest -v -b scrapers/py_tests/test_life_selector.py
'''
import inspect
import json
import os
import sys
import unittest
from unittest.mock import patch

from . import test_base_python_scraper

# add parent directory (i.e. the scrapers directory) as a Python modules path
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

# now we can import the scraper module from the parent directory
from life_selector import LifeSelectorScraper  # pylint: disable=import-error,wrong-import-order,wrong-import-position

class TestLifeSelectorScraper(test_base_python_scraper.TestBasePythonScraper):
    '''
    Unit tests for LifeSelectorScraper class

    These extend/override the unit tests for the base/parent class
    BasePythonScraper
    '''
    MOVIE_BY_URL = {"url": "https://lifeselector.com/game/DisplayPlayer/gameId/87205"}

    # mock private methods that call external APIs
    @patch.object(
            LifeSelectorScraper,
            '_LifeSelectorScraper__get_movie_from_api_by_id',
            return_value={
                'name': 'The Best Movie',
                'synopsis': 'Brilliant stuff happens'
            }
    )
    @patch.object(
            LifeSelectorScraper,
            '_LifeSelectorScraper__get_movies_from_api_by_name',
            return_value={
                'date': '1999-12-31',
                'rating100': '19.99'
            }
    )
    @patch.object(
            LifeSelectorScraper,
            '_LifeSelectorScraper__get_movie_by_scraping_html',
            return_value={
                'front_image': 'http://domain/front-image.jpg'
            }
    )
    # input/stdin patched in here
    @patch('builtins.input', side_effect=[json.dumps(MOVIE_BY_URL)])
    def test_class_movie_by_url_result(self, _mock1, _mock2, _mock3, _mock4):
        '''
        movieByURL result should contain correct properties
        '''
        # given
        # arguments are here (first one is the script name)
        testargs = ["script_name", "movieByURL"]
        with patch.object(sys, 'argv', testargs):
            # when
            scraper = LifeSelectorScraper()

        # then
        self.assertDictEqual(scraper.result, {
            'back_image': 'https://i.c7cdn.com/generator/games/87205/images/episode-guide-87205.jpg',
            'date': '1999-12-31', 'rating100': '19.99',
            'front_image': 'http://domain/front-image.jpg',
            'name': 'The Best Movie',
            'studio': {
                'name': 'Life Selector',
                'url': 'https://lifeselector.com'
            },
            'synopsis': 'Brilliant stuff happens',
            'url': self.MOVIE_BY_URL['url']
        })

if __name__ == '__main__':
    unittest.main()
