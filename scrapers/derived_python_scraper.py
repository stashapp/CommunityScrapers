'''
This is an example of how to use the BasePythonScraper to create your
own scraper with a lot of the code already set up.
'''

from base_python_scraper import BasePythonScraper

class DerivedPythonScraper(BasePythonScraper):
    '''
    Example class to show overrides
    '''

    def _get_scene_by_url(self, url: str) -> dict:
        '''
        Get scene properties by using a URL
        '''
        scene = {}
        scene['url'] = url
        scene['studio'] = {
            'name': 'A Fixed Studio Name'
        }
        return scene

if __name__ == '__main__':
    result = DerivedPythonScraper()
    print(result)
