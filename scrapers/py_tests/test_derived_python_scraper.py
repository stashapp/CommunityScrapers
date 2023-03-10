'''
Unit tests for derived_python_scraper.py

You can run this test with the following command:

python3 -m unittest -v -b scrapers/py_tests/derived_python_scraper.py
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
from derived_python_scraper import DerivedPythonScraper  # pylint: disable=import-error,wrong-import-order,wrong-import-position

class TestDerivedPythonScraper(test_base_python_scraper.TestBasePythonScraper):
    '''
    Unit tests for DerivedPythonScraper class

    These extend/override the unit tests for the base/parent class
    BasePythonScraper
    '''
    SCENE_BY_URL = {"url": "http://domain/scene-by-url"}

    # input/stdin patched in here
    @patch('builtins.input', side_effect=[json.dumps(SCENE_BY_URL)])
    def test_class_scene_by_url_result(self, _):
        '''
        sceneByURL result should contain correct properties
        '''
        # given
        # arguments are here (first one is the script name)
        testargs = ["script_name", "sceneByURL"]
        with patch.object(sys, 'argv', testargs):
            # when
            scraper = DerivedPythonScraper()

        # then
        self.assertDictEqual(scraper.result, {
            'studio': {
                'name': 'A Fixed Studio Name'
            },
            'url': self.SCENE_BY_URL['url']
        })

if __name__ == '__main__':
    unittest.main()
