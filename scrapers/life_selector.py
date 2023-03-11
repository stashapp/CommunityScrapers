'''
lifeselector.com scraper
'''
import re
import sys
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

from base_python_scraper import BasePythonScraper

class LifeSelectorScraper(BasePythonScraper):
    '''
    Implemented script actions and helper functions
    '''
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

    def __get_clean_url(self, url: str) -> str:
        '''
        Clean the URL, e.g. remove the query params
        '''
        parsed_url = urlparse(url)
        clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        return clean_url

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

    def __get_movie_from_api_by_name(self, movie_name: str) -> dict:
        '''
        Get movie (game) properties by searching by name (title)

        - date
        - front_image (452x310)
        - name
        - performers
        - rating (float, scale to 5.0)
        - synopsis (short/truncated)
        - tags
        '''
        movie = None

        # search API
        api_search_result = self.__api_search(movie_name)

        # parse API search result
        if api_search_result['gameCount'] > 0:
            game = api_search_result['games'][0]
            movie = {}
            movie['name'] = game['title']
            movie['date'] = game['releaseDate']
            movie['front_image'] = game['cover']
            movie['tags'] = [{ 'name': t['name'] for t in game['tag'] }]
            # convert rating to percentage
            movie['rating'] = str(100 * game['rating'] / 5)
            movie['synopsis'] = unicodedata.normalize("NFKD", game['smallDescription'])
            movie['performers'] = [{ 'name': p['name'] for p in game['performer'] }]

        return movie

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
            { "image": tag['src'] } for tag in carousel_images[1:]
        ]

        return movie

    def _get_movie_by_url(self, url: str) -> dict:
        '''
        Get movie (game) properties by using a URL

        - name
        - date
        - front_image (resolution 2000x1214)
        - rating
        - studio
        - synopsis
        - url
        '''
        movie = {}

        # movie data from URL string value
        movie['url'] = self.__get_clean_url(url)
        domain = urlparse(url).netloc
        studio = self.__get_studio_for_domain(domain)
        if studio is not None:
            movie['studio'] = studio

        # movie data from id
        movie_id = self.__parse_movie_id_from_url(url)
        movie_data_from_id = self.__get_movie_from_api_by_id(movie_id)
        movie['name'] = movie_data_from_id['name']
        movie['synopsis'] = movie_data_from_id['synopsis']

        # movie data from name
        movie_data_from_name = self.__get_movie_from_api_by_name(movie['name'])
        if movie_data_from_name is not None:
            movie['date'] = movie_data_from_name['date']
            movie['rating'] = movie_data_from_name['rating']

        # movie data from scraping HTML
        movie_data_from_html = self.__get_movie_by_scraping_html(url)
        movie['front_image'] = movie_data_from_html['front_image']

        log.debug(f"movie: {movie}")
        return movie

    def _get_scene_by_url(self, url: str) -> dict:
        '''
        Get scene properties by using a URL

        Title
        Details
        Code
        Director
        URL
        Date
        Image
        Studio
            Name
            URL
        Movies
            Name
            Aliases
            Duration
            Date
            Rating
            Director
            Studio
            Synopsis
            URL
            FrontImage
            BackImage
        Tags
            Name
        Performers
            Name
            Gender
            URL
            Twitter
            Instagram
            Birthdate
            DeathDate
            Ethnicity
            Country
            HairColor
            EyeColor
            Height
            Weight
            Measurements
            FakeTits
            CareerLength
            Tattoos
            Piercings
            Aliases
            Tags (see Tag fields)
            Image
            Details
        '''
        scene = {}
        scene['url'] = url
        scene['studio'] = {
            'name': 'A Fixed Studio Name'
        }
        return scene

if __name__ == '__main__':
    result = LifeSelectorScraper()
    print(result)
