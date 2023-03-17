'''
VirtualRealPorn Network scraper
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

class VirtualRealPornScraper(base_python_scraper.BasePythonScraper):
    '''
    Implemented script actions and helper functions
    '''
    # tuple for API timeout: (connection_timeout, response_read_timeout)
    API_TIMEOUT = (5, 5)
    PAGE_TIMEOUT = (5, 10)
    STUDIOS = [
        {
            'name': 'VirtualRealAmateur',
            'url': 'https://virtualrealamateurporn.com'
        },
        {
            'name': 'VirtualRealGay',
            'url': 'https://virtualrealgay.com'
        },
        {
            'name': 'VirtualRealJapan',
            'url': 'https://virtualrealjapan.com'
        },
        {
            'name': 'VirtualRealPassion',
            'url': 'https://virtualrealpassion.com'
        },
        {
            'name': 'VirtualRealPorn',
            'url': 'https://virtualrealporn.com'
        },
        {
            'name': 'VirtualRealTrans',
            'url': 'https://virtualrealtrans.com'
        },
    ]

    def __generate_post_headers_for_domain(self, domain: str) -> dict:
        return {
            'authority': domain,
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'en-GB,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'cookie': 'wp-wpml_current_language=en; cookielawinfo-checkbox-necessary=yes; vr_nut=typein; vr_nc=none; vr_npid=0; av-accepted=1',
            'origin': f"https://{domain}",
            'referer': f"https://{domain}",
            'sec-ch-ua': '"Brave";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': 'Windows',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }

    def __get_studio_for_url(self, url: str) -> dict | None:
        '''
        Get a studio (from constant list of studios) matching a url
        '''
        domain = urlparse(url).netloc
        return next(
            (s for s in self.STUDIOS if urlparse(s['url']).netloc == domain),
            None
        )

    def __api_search(self, search_string: str, domain: str = None) -> dict:
        '''
        Search API with a string value. Interesting data in:

        - data.results.videos
        - data.results.models

        API result is:

        {
            "success": boolean,
            "data": {
                "results": {
                    "videos": [
                        {
                            "id": "67873",
                            "name": "My Personal Consultant",
                            "slug": "my-personal-consultant",
                            "url": "https://virtualrealtrans.com/vr-trans-porn-video/my-personal-consultant/",
                            "image": {
                                "src": "https://virtualrealtrans.com/wp-content/uploads/sites/3/2023/02/001_Portada_video_A-5-265x150.jpg",
                                "alt": "Bikini Hottie Wants Sex in VR Trans"
                            },
                            "resolution": "8K",
                            "feelconnect": false
                        }
                    ],
                    "models": [
                        {
                            "id": 54923,
                            "siteid": 3,
                            "name": "Mirella Ferraz",
                            "url": "https://virtualrealtrans.com/vr-models/mirella-ferraz/",
                            "image": {
                                "src": "https://virtualrealtrans.com/wp-content/uploads/sites/3/2022/07/8vxk030863c958d844625993d60b301baf644.jpg",
                                "alt": null
                            },
                            "logo": null,
                            "videos": "2"
                        }
                    ],
                    "categories": [],
                    "tags": []
                },
                "counts": {
                    "videos": 3,
                    "models": 2,
                    "categories": 0,
                    "tags": 0
                }
            }
        }
        '''
        # if the optional parameter `domain` is supplied, only search that domain
        # otherwise search them all
        log.debug(f"domain (parameter): {domain}")
        domains_to_search = []
        if domain:
            domains_to_search.append(domain)
        else:
            domains_to_search.extend([ urlparse(s['url']).netloc for s in self.STUDIOS ])
        log.debug(f"domains_to_search: {domains_to_search}")

        # this will be merge-updated to populate it
        search_result = {}

        for search_domain in domains_to_search:
            # call API
            post_headers = self.__generate_post_headers_for_domain(search_domain)
            form_data = {
                'action': 'virtualreal_search',
                'query': search_string
            }
            search_url = f"https://{search_domain}/wp-admin/admin-ajax.php"
            try:
                api_result = requests.post(
                    search_url,
                    data=form_data,
                    headers=post_headers,
                    timeout=self.API_TIMEOUT
                ).json()
                # merge-update (combine, deduplicate, and don't overwrite/replace)
                search_result = {**search_result, **api_result}
            except Exception as ex:
                log.warning('API error')
                log.debug(ex)

        return search_result

    def __get_performers_from_api_by_name(self, performer_name: str) -> List[dict]:
        '''
        Get list of performers properties by searching by name

        List of:
            {
                "name": "Jessica Bell",
                "url": "https://virtualrealporn.com/vr-pornstars/jessica-bell/",
                "image": "https://virtualrealtrans.com/wp-content/uploads/.../Jessica-Bell.jpg"
            }
        '''
        performers = []

        # search API
        api_search_result = self.__api_search(performer_name)

        # parse API search result
        if api_search_result \
                and len(api_search_result['data']['results']['models']) > 0:
            performers = [
                {
                    'image': model['image']['src'],
                    'name': model['name'],
                    'url': model['url']
                } for model in api_search_result['data']['results']['models']
            ]

        log.debug(f"__get_performers_from_api_by_name, performers (count): {len(performers)}")
        log.trace(f"__get_performers_from_api_by_name, performers: {performers}")
        return performers

    def _get_performer_by_fragment(self, fragment: dict) -> dict:
        '''
        Get performer properties by using fragment object

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

        # url should be the performer web page, so try that first
        if fragment.get('url'):
            performer = self._get_performer_by_url(fragment['url'])

        # if no performer name (i.e. no assignment above), search by name if fragment.name
        if not performer.get('name') and fragment.get('name'):
            performers_from_api = self.__get_performers_from_api_by_name(fragment['name'])
            if len(performers_from_api) > 0:
                performer = performers_from_api[0]

        log.debug(f"_get_performer_by_fragment, performer: {performer}")
        return performer

    def _get_performer_by_name(self, name: str) -> List[dict]:
        '''
        Get performer properties by searching a name

        From stashapp's Performer > Scrape With... > (name string)

        Returns: Array of JSON-encoded performer fragments
        '''
        performers = self.__get_performers_from_api_by_name(name)

        log.debug(f"_get_performer_by_name, performers: {performers}")
        return performers

    def __get_table_cell_value_for_header(self, page: bs, header: str) -> str:
        '''
        Gets the corresponding value from a table, given the table header value
        '''
        return page.find("th", string=header).findNextSibling('td').string

    def __get_social_media_links(self, page: bs) -> dict:
        '''
        Get the social media usernames, by searching for a page link
        '''
        usernames = {}

        social_links = page.find('div', id='social').find_all('a')

        if social_links:
            for link in social_links:
                uri_path = urlparse(link.get('href')).path
                username = uri_path.replace('/', '')
                # get the social network name from the class with a find first
                social_network = next(
                    (
                        class_name for class_name in link.get('class') \
                                if class_name != 'socialItem'
                    ),
                    None
                )
                if social_network:
                    usernames[social_network] = username

        return usernames

    def __cm_to_inches(self, cm: int) -> str:
        '''
        Convert cm to inch (integer)
        '''
        return int(float(cm) / 2.54)

    def _get_performer_by_url(self, url: str) -> dict:
        '''
        Get performer properties by using a URL

        - birthdate
        - country
        - eye_color
        - gender
        - hair_color
        - image
        - instagram
        - measurements
        - name
        - twitter
        '''
        performer = {}

        # parse web page
        headers = self.__generate_post_headers_for_domain(urlparse(url).netloc)
        page = bs(requests.get(url, headers=headers, timeout=self.PAGE_TIMEOUT).text, 'html.parser')

        if page:
            performer_image = page.find("div", class_="feature_img_model").find('img')
            performer['name'] = performer_image.get('alt')
            performer['image'] = performer_image.get('data-lazy-src')

            # if there is a name, then the url is valid
            if performer.get('name'):
                performer['url'] = url

            gender = self.__get_table_cell_value_for_header(page, 'Gender')
            if gender == 'Female Trans':
                gender = 'Transfemale'
            performer['gender'] = gender

            date_of_birth = self.__get_table_cell_value_for_header(page, 'Date of birth')
            performer['birthdate'] = self._convert_date(date_of_birth, '%d/%m/%Y', '%Y-%m-%d')

            performer['country'] = self.__get_table_cell_value_for_header(page, 'Country')

            performer['eye_color'] = self.__get_table_cell_value_for_header(page, 'Eyes color')

            performer['hair_color'] = self.__get_table_cell_value_for_header(page, 'Hair color')

            # there is a 'Blog / Web' table row, not sure if this would go somewhere, as probably
            # want to keep performer['url'] as the VRP site URL for the performer

            if performer['gender'] in ('Female', 'Transfemale'):
                bust = self.__cm_to_inches(
                    int(self.__get_table_cell_value_for_header(page, 'Bust'))
                )
                # round up if odd
                bust += bust % 2
                waist = self.__cm_to_inches(
                    int(self.__get_table_cell_value_for_header(page, 'Waist'))
                )
                hips = self.__cm_to_inches(
                    int(self.__get_table_cell_value_for_header(page, 'Hips'))
                )
                performer['measurements'] = \
                    f"{bust}-{waist}-{hips}"

            # the 'Piercing' and 'Tattoo' sections only seem to be 'Yes' or blank
            # so not really a useful scrape value

            social_media_links = self.__get_social_media_links(page)
            performer['twitter'] = social_media_links.get('twitter')
            performer['instagram'] = social_media_links.get('instagram')

        log.debug(f"_get_performer_by_url, performer: {performer}")
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
            movie['studio'] = self.__get_studio_for_url(movie['url'])

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
        scene['studio'] = self.__get_studio_for_url(scene['url'])

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
    result = VirtualRealPornScraper()
    print(result)
