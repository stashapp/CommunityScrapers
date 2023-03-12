'''
lifeselector.com scraper
'''
import re
import sys
from typing import List
import unicodedata
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup as bs
    import requests
except ModuleNotFoundError:
    print(
        "You need to install the following modules 'requests', 'bs4', 'lxml'.",
        file=sys.stderr
    )
    sys.exit(1)


try:
    from py_common import log
except ModuleNotFoundError:
    print(
        "You need to download the folder 'py_common' from the community repo! "
        "(CommunityScrapers/tree/master/scrapers/py_common)",
        file=sys.stderr)
    sys.exit(1)

from py_common import base_python_scraper

class LifeSelectorScraper(base_python_scraper.BasePythonScraper):
    '''
    Implemented script actions and helper functions
    '''
    GENDER_FEMALE = 'female'
    STUDIOS = [
        {
            'name': 'Life Selector',
            'url': 'https://lifeselector.com'
        }
    ]



    def __get_studio_for_domain(self, domain: str) -> dict:
        '''
        Get a studio (from constant list of studios) matching a domain
        '''
        return next(
            (s for s in self.STUDIOS if urlparse(s['url']).netloc == domain),
            None
        )

    def __parse_movie_id_from_url(self, url: str) -> dict:
        '''
        Pick out the movie (game) ID from the movie (game) URL

        example URL: https://lifeselector.com/game/DisplayPlayer/gameId/87050
        example ID: 87050
        '''
        movie_id = re.sub('.*/', '', urlparse(url).path)
        return movie_id

    def __get_movie_url_for_id(self, movie_id: int) -> str:
        return f"https://lifeselector.com/game/DisplayPlayer/gameId/{movie_id}"

    def __api_search(self, search_string: str) -> dict:
        '''
        Search API with a string value

        API result is:

        {
            "games": [ <game objects, up to 3 top matches> ],
            "performers": [ <performer objects, up to top 3 matches> ],
            "gameCount": <int, may be larger than len(games)>,
            "performerCount": <int, may be larger than len(performer)>
        }
        '''
        # call API
        api_result = requests.get(
            f"https://contentworker.ls-tester.com/api/search?q={search_string}"
        ).json()

        return api_result

    def __get_movies_from_api_by_name(self, movie_name: str) -> List[dict]:
        '''
        Get list of movies (games) with properties by searching by name (title)

        List of:
            - date
            - front_image (452x310)
            - id (int)
            - name
            - performers
            - rating (float, scale to 5.0)
            - rating100 (float, rating converted to percentage)
            - synopsis (short/truncated)
            - tags
        '''
        movies = []

        # search API
        api_search_result = self.__api_search(movie_name)

        # parse API search result
        if api_search_result['gameCount'] > 0:
            movies = [
                {
                    'name': game['title'],
                    'id': game['id'],
                    'date': game['releaseDate'],
                    'front_image': game['cover'],
                    'tags': [{ 'name': t['name'] } for t in game['tag'] ],
                    'rating': game['rating'],
                    # convert rating to percentage
                    'rating100': str(100 * game['rating'] / 5),
                    'synopsis': unicodedata.normalize("NFKD", game['smallDescription']),
                    'performers': [{ 'name': p['name'] } for p in game['performer'] ]
                } for game in api_search_result['games']
            ]

        log.debug(f"__get_movies_from_api_by_name, movies: {movies}")
        return movies

    def __get_movie_from_api_by_id(self, movie_id: str) -> dict:
        '''
        Get movie (game) properties by ID

        - name
        - synopsis
        '''
        movie = {}

        # call API
        api_result = requests.get(
            "https://lifeselector.com/game/GetEpisodeDetailsInJson"
            f"/gameId/{movie_id}/choiceId/0"
        ).json()

        movie['name'] = api_result['map']['title']
        movie['synopsis'] = unicodedata.normalize("NFKD", api_result['map']['description'])

        log.debug(f"__get_movie_from_api_by_id, movie: {movie}")
        return movie

    def __get_movie_by_scraping_html(self, url: str) -> dict:
        '''
        Get movie (game) properties by scraping the HTML code of the page

        - name
        - front_image (resolution 2000x1214)
        - scenes (List[{ 'image': '<url>' }], resolution 2000x1214)
        - synopsis
        - url
        '''
        movie = {}

        movie['url'] = url

        # parse web page
        page = bs(requests.get(url).text, 'html.parser')
        movie['name'] = page.title.string.replace(
            ' - Interactive Porn Game',
            ''
        )
        movie['synopsis'] = page.find("div", class_="info").find("p").string
        # image carousel is the movie cover followed by each scene
        carousel_images = page.find("div", class_="player").find_all("img")
        # movie cover is the first image
        movie['front_image'] = carousel_images[0]['src']
        # and scene covers are the 2nd image to last
        movie['scenes'] = [
            { "image": image['src'] } for image in carousel_images[1:]
        ]

        log.debug(f"__get_movie_by_scraping_html, movie: {movie}")
        return movie

    def _get_movie_by_url(self, url: str) -> dict:
        '''
        Get movie (game) properties by using a URL

        - date
        - front_image (resolution 2000x1214)
        - name
        - rating
        - studio
        - synopsis
        - url
        '''
        movie = {}

        # movie data from URL string value
        domain = urlparse(url).netloc
        movie['studio'] = self.__get_studio_for_domain(domain)

        # movie data from API by id
        movie_id = self.__parse_movie_id_from_url(url)
        movie_data_from_id = self.__get_movie_from_api_by_id(movie_id)
        movie['name'] = movie_data_from_id['name']
        movie['synopsis'] = movie_data_from_id['synopsis']
        movie['url'] = self.__get_movie_url_for_id(movie_id)
        movie['back_image'] = f"https://i.c7cdn.com/generator/games/{movie_id}/images/episode-guide-{movie_id}.jpg"

        # movie data from API by name
        movie_data_from_name = self.__get_movies_from_api_by_name(movie['name'])
        if movie_data_from_name:
            movie['date'] = movie_data_from_name['date']
            movie['rating100'] = movie_data_from_name['rating100']

        # movie data from scraping HTML
        movie_data_from_html = self.__get_movie_by_scraping_html(url)
        movie['front_image'] = movie_data_from_html['front_image']

        log.debug(f"_get_movie_by_url, movie: {movie}")
        return movie

    def __get_performers_from_api_by_name(self, performer_name: str) -> List[dict]:
        '''
        Get list of performers properties by searching by name

        List of:
            {
                'aliases': 'Sarah Luvv, Sara Luv, Sarah Love, Sara Love',
                'birthdate': 'May 17, 1986',
                'country': 'Romanian',
                'details': 'Jenna Presley is one of the more recognizable...',
                'ethnicity': 'English, Spanish',
                'eye_color': 'Green',
                'gender': 'female',
                'hair_color': 'Blonde',
                'height': '162 cm',
                'image': 'https://i.c7cdn.com/generator/models/1446/1.jpg',
                'name': 'Shalina Devine',
                'piercings': 'Left nostril; tongue; navel',
                'tattoos': 'Back of neck, left arm, right forearm, lower back, pelvic',
                'url': '',
                'weight': '47 kg'
            }
        '''
        performers = []

        # search API
        api_search_result = self.__api_search(performer_name)

        # parse API search result
        if api_search_result['performerCount'] > 0:
            performers = [
                {
                    'aliases': performer['alias'],
                    'birthdate': self._convert_date(
                        performer['birthday'],
                        '%B %d, %Y',
                        '%Y-%m-%d'
                    ),
                    'country': self._get_country_for_nationality(performer['nationality']),
                    'details': performer['biography'],
                    'ethnicity': performer['language'],
                    'eye_color': performer['eye'],
                    'gender': self.GENDER_FEMALE,
                    'hair_color': performer['hair'],
                    'height': re.sub(r'(\d+)\s*cm.*', r'\1', performer['height']),
                    'image': performer['photos'][0],
                    'name': performer['name'],
                    'piercings': performer['piercing'],
                    'tattoos': performer['tattoos'],
                    'url': performer['website'],
                    'weight': re.sub(r'(\d+)\s*kg.*', r'\1', performer['weight'])
                } for performer in api_search_result['performers']
            ]

        log.debug(f"__get_performers_from_api_by_name, performers: {performers}")
        return performers

    def _get_performer_by_fragment(self, fragment: dict) -> dict:
        '''
        Get performer properties by using fragment object. This method should be
        overriden in a derived class in a scraper file

        This is sent by stashapp when clicking on one of the results in the list
        shown for a Performer > Scrape With... > (name) search, i.e.
        performerByName, and is populated with the values supplied by
        the fragment of the performerByName list item, not what is currently
        in the performer's fields.

        example payload:

        {
            'aliases': None,
            'birthdate': None,
            'career_length': None,
            'country': None,
            'death_date': None,
            'details': None,
            'disambiguation': None,
            'ethnicity': None,
            'eye_color': None,
            'fake_tits': None,
            'gender': None,
            'hair_color': None,
            'height': None,
            'instagram': None,
            'measurements': None,
            'name': 'Dani Blu',
            'piercings': None,
            'remote_site_id': None,
            'stored_id': None,
            'tattoos': None,
            'twitter': None,
            'url': None,
            'weight': None
        }
        '''
        performer = {}

        # add url from id, if url not supplied
        if not fragment.get('url') and fragment.get('remote_site_id'):
            fragment['url'] = f"https://lifeselector.com/model/view/id/{fragment['remote_site_id']}"

        # url should be the performer web page, so try that first
        if fragment.get('url'):
            performer = self._get_performer_by_url(fragment['url'])

        # if no performer name (i.e. no assignment above), search by name if fragment.name
        if not performer.get('name') and fragment.get('name'):
            performers_from_api = self.__get_performers_from_api_by_name(fragment['name'])
            if len(performers_from_api):
                performer = performers_from_api[0]

        return performer

    def _get_performer_by_name(self, name: str) -> List[dict]:
        '''
        Get performer properties by searching a name

        From stashapp's Performer > Scrape With... > (name string)

        Returns: Array of JSON-encoded performer fragments
        '''
        return self.__get_performers_from_api_by_name(name)

    def _get_performer_by_url(self, url: str) -> dict:
        '''
        Get performer properties by using a URL
        '''
        performer = {}

        # parse web page
        page = bs(requests.get(url).text, 'html.parser')

        # just get the name
        performer_name = page.find("div", class_="model-details").find("h1").string
        
        # then search API
        if performer_name:
            performers_from_api = self.__get_performers_from_api_by_name(performer_name)
            if len(performers_from_api):
                performer = performers_from_api[0]

        return performer

    def _get_scene_by_name(self, name: str) -> List[dict]:
        '''
        Get list of scene properties by using a name

        The `name` variable is the string submitted from the Scrape Query
        (Magnifying Glass icon) feature in stashapp web UI

        Returns: Array of JSON-encoded scene fragments

        - title
        - details
        - code ({movie.id}-{scene_number})
            to be used again in sceneByQueryFragment (to pick scene image)
        - url
        - date
        - image
        - studio
            - name
            - url
        - movies: List
            - name
            - date
            - rating
            - rating100
            - studio
                - name
                - url
            - synopsis
            - url
            - front_image
        - tags: List
            - name
        - performers: List
            - name
        - rating100
        '''
        scenes = []
        
        # movie data from name
        movies_data_from_name = self.__get_movies_from_api_by_name(name)
        for movie_data_from_name in movies_data_from_name:
            # movie contains scene info
            movie = {}
            movie['date'] = movie_data_from_name['date']
            movie_id = movie_data_from_name['id']
            movie['rating100'] = movie_data_from_name['rating100']
            movie['performers'] = movie_data_from_name['performers']
            movie['tags'] = movie_data_from_name['tags']
            movie['name'] = movie_data_from_name['name']

            # movie data from id
            movie_data_from_id = self.__get_movie_from_api_by_id(movie_id)
            movie['synopsis'] = movie_data_from_id['synopsis']

            # movie data from URL string value
            movie['url'] = self.__get_movie_url_for_id(movie_id)

            # movie data from url
            domain = urlparse(movie['url']).netloc
            movie['studio'] = self.__get_studio_for_domain(domain)

            # movie data from scraping HTML
            movie_data_from_html = self.__get_movie_by_scraping_html(movie['url'])
            movie['front_image'] = movie_data_from_html['front_image']
            movie['scenes'] = movie_data_from_html['scenes']
        
            # map movie['scenes'] List into List of scene fragments
            scenes.extend(
                [
                    {
                        'title': movie['name'],
                        'details': movie['synopsis'],
                        'code': f"{movie_id}-{scene_number}",
                        'url': movie['url'],
                        'date': movie['date'],
                        'image': scene['image'],
                        'studio': movie['studio'],
                        'movies': [movie],
                        'rating100': movie['rating100'],
                        'tags': movie['tags'],
                        'performers': movie['performers']
                    } for scene_number, scene in enumerate(movie['scenes'], start=1)
                ]
            )

        log.debug(f"_get_scene_by_name, scenes: {scenes}")
        return scenes

    def _get_scene_by_query_fragment(self, fragment: dict) -> dict:
        '''
        Get scene properties by using fragment returned by sceneByName

        This is sent by stashapp when clicking on one of the results in the list
        shown for a Scene > Scrape Query, i.e.
        sceneByName, and is populated with the values supplied by
        the fragment of the sceneByName list item, not what is currently
        in the scene's fields.

        example payload:
        {
            'code': '85900-5',
            'date': '2021-05-24',
            'details': 'You have an extraordinary hobby...',
            'director': None,
            'remote_site_id': None,
            'title': 'The Wedding Crasher',
            'url': 'https://lifeselector.com/game/DisplayPlayer/gameId/85900'
        }
        '''
        scene = {}

        # scene data from fragment
        scene['code'], scene_number = fragment['code'].split('-')
        scene['date'] = fragment['date']
        scene['details'] = fragment.get('details')
        scene['url'] = fragment['url']

        # scene data from fragment.url
        domain = urlparse(scene['url']).netloc
        scene['studio'] = self.__get_studio_for_domain(domain)

        # movie data from scraping HTML
        movie_scenes = []
        movie_data_from_html = self.__get_movie_by_scraping_html(fragment['url'])
        movie_scenes = movie_data_from_html['scenes']

        # scene data from fragment.code
        if len(movie_scenes):
            scene['image'] = movie_scenes[int(scene_number) - 1]['image']

        # movie data from fragment.title
        movies_from_api = self.__get_movies_from_api_by_name(fragment['title'])
        if len(movies_from_api):
            movie = movies_from_api[0]
            scene['title'] = f"{fragment['title']} - {', '.join([ p['name'] for p in movie['performers'] ])} (DELETE AS APPROPRIATE)"
            scene['performers'] = movie['performers']
            scene['tags'] = movie['tags']
            scene['movies'] = [
                { 'name': fragment['title'] }
            ]
        
        log.debug(f"_get_scene_by_query_fragment, scene: {scene}")
        return scene


if __name__ == '__main__':
    result = LifeSelectorScraper()
    print(result)
