'''
Unit tests for base_python_scraper.py

You can run this test with the following command:

python3 -m unittest -v -b scrapers/py_tests/base_python_scraper.py
'''
import inspect
import json
import os
import sys
import unittest
from unittest.mock import patch

from . import base_test_case

# add parent directory (i.e. the scrapers directory) as a Python modules path
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

# now we can import the scraper module from the parent directory
from base_python_scraper import BasePythonScraper  # pylint: disable=import-error,wrong-import-order,wrong-import-position

FRAGMENT_URL = {"url": "http://domain"}

class TestBasePythonScraper(base_test_case.BaseTestCase):
    '''
    Unit tests for BasePythonScraper class
    '''

    def test_base_class_init_with_no_args(self):
        '''
        no script arguments, no fragment input
        '''
        # given
        testargs = ["script_name"]
        scraper = None
        with patch.object(sys, 'argv', testargs):
            # then
            with self.assertRaises(SystemExit):
                # when
                scraper = BasePythonScraper()

        # then
        self.assertIsNone(scraper)

    # input/stdin patched in here
    @patch('builtins.input', side_effect=[json.dumps(FRAGMENT_URL)])
    def test_class_init_with_valid_args_and_valid_stdin(self, _):
        '''
        the positional first argument 'action', and fragment with just url
        '''
        # given
        # arguments are here (first one is the script name)
        testargs = ["script_name", "sceneByURL"]
        with patch.object(sys, 'argv', testargs):
            # when
            scraper = BasePythonScraper()

        # then
        self.assertIsInstance(scraper, BasePythonScraper)
        self.assertHasAttr(scraper, '__init__')
        self.assertHasAttr(scraper, '__str__')
        self.assertHasAttr(scraper, '_get_scene_by_url')
        self.assertHasAttr(scraper, '_load_arguments')
        self.assertHasAttr(scraper, 'args')
        self.assertHasAttr(scraper, 'fragment')
        self.assertIsNotNone(scraper.args)
        self.assertEqual(scraper.args.action, 'sceneByURL')
        self.assertDictEqual(scraper.fragment, FRAGMENT_URL)

    # input/stdin patched in here
    @patch('builtins.input', side_effect=[json.dumps(FRAGMENT_URL)])
    def test_class_scene_by_url_result(self, _):
        '''
        sceneByURL result should contain correct properties
        '''
        # given
        # arguments are here (first one is the script name)
        testargs = ["script_name", "sceneByURL"]
        with patch.object(sys, 'argv', testargs):
            # when
            scraper = BasePythonScraper()

        # then
        self.assertDictEqual(scraper.result, {
            'url': FRAGMENT_URL['url']
        })

if __name__ == '__main__':
    unittest.main()
