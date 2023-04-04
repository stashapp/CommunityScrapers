'''
VirtualRealPorn Network scraper
'''
import json
import re
import sys
from typing import List
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
    COMMON_TAGS = ['Virtual Reality']
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
        log.trace(f"domain (parameter): {domain}")
        domains_to_search = []
        if domain:
            domains_to_search.append(domain)
        else:
            domains_to_search.extend([ urlparse(s['url']).netloc for s in self.STUDIOS ])
        log.trace(f"domains_to_search: {domains_to_search}")

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

    def __cm_to_inches(self, cm: int) -> int:
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

    def __get_scenes_from_api_by_name(self, scene_name: str) -> List[dict]:
        '''
        Get scenes from api via search string

        List of:
        - id
        - image
        - title
        - url
        '''
        scenes = []

        api_search_result = self.__api_search(scene_name)

        if api_search_result and len(api_search_result['data']['results']['videos']) > 1:
            scenes = [
                {
                    'id': video['id'],
                    'title': video['name'],
                    'url': video['url'],
                    'image': video['image']['src']
                } for video in api_search_result['data']['results']['videos']
            ]

        return scenes

    def _get_scene_by_fragment(self, fragment: dict) -> dict:
        scene = {}

        if fragment.get('url'):
            scene_by_url = self._get_scene_by_url(fragment['url'])

            if scene_by_url.get('title'):
                scene.update(scene_by_url)
            elif fragment.get('title'):
                scene_by_name = self._get_scene_by_name(fragment['title'])
                if scene.get('title'):
                    scene.update(scene_by_name)

        return scene


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

        # scene data from name
        scenes_from_api = self.__get_scenes_from_api_by_name(name)
        if scenes_from_api and len(scenes_from_api) > 0:
            for scene_from_api in scenes_from_api:
                scene = {
                    'code': str(scene_from_api['id']),
                    'image': scene_from_api['image'],
                    'title': scene_from_api['title'],
                    'url': scene_from_api['url']
                }

                # scrape HTML page for the rest of the scene properties
                scene_by_scraping_html = self.__get_scene_by_scraping_html(scene['url'])
                if scene_by_scraping_html.get('title'):
                    scene.update(scene_by_scraping_html)

                scenes.append(scene)

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
            'title': 'Brazilian paradise I',
            'code': None,
            'details': None,
            'director': None,
            'url': 'https://virtualrealtrans.com/vr-trans-porn-video/brazilian-paradise-i/',
            'date': None,
            'remote_site_id': None
        }
        '''
        scene = {}

        # scene data from fragment
        scene['title'] = fragment['title']
        scene['details'] = fragment.get('details')
        scene['url'] = fragment['url']

        # scene data from fragment.url
        scene['studio'] = self.__get_studio_for_url(scene['url'])

        # scrape HTML page for the rest of the scene properties
        scene_by_scraping_html = self.__get_scene_by_scraping_html(scene['url'])
        if scene_by_scraping_html.get('title'):
            scene.update(scene_by_scraping_html)

        log.debug(f"_get_scene_by_query_fragment, scene: {scene}")
        return scene

    def __get_tag_names(self, page: bs, tag_group_label: str):
        '''
        Parse tag names from HTML, given the label name of the group
        '''
        tag_names = []
        tag_group_label_tag = page.find('label', string=tag_group_label)
        if tag_group_label_tag:
            links = tag_group_label_tag \
                    .find_parent('div') \
                    .find_next_sibling('div', class_='metaSingleData') \
                    .find_all('a')
            tag_names = [ link.find('span').string for link in links ]

        log.trace(f"__get_tag_names: for tag_group_label {tag_group_label} returns {tag_names}")
        return tag_names

    def __get_scene_by_scraping_html(self, url: str) -> dict:
        '''
        Scrape HTML page for scene properties

        - code
        - date
        - details
        - image
        - performers
        - studio
        - tags
        - title
        - url
        '''
        scene = {}

        # parse web page
        headers = self.__generate_post_headers_for_domain(urlparse(url).netloc)
        html = requests.get(url, headers=headers, timeout=self.PAGE_TIMEOUT).text
        page = bs(html, 'html.parser')

        if page:
            # page parsed, so the url is valid
            scene['url'] = url
            scene['studio'] = self.__get_studio_for_url(url)

            scene['title'] = re.sub(r'\ +\|.*', '', page.title.string).strip()

            categories = self.__get_tag_names(page, 'Categories')
            tags = self.__get_tag_names(page, 'Tags')
            tags.extend(categories)
            tags.extend(self.COMMON_TAGS)
            scene['tags'] = [ { 'name': tag } for tag in tags ]

            # scene['details'] = page.find('div', class_="g-cols onlydesktop").string
            # details
            inline_json_scripts = page.find_all('script', type='application/ld+json')
            log.trace(f"inline_json_scripts: {len(inline_json_scripts)}")
            log.trace(f"inline_json_scripts: {inline_json_scripts}")
            for script_string in [ s.string for s in inline_json_scripts ]:
                if scene.get('details') is None:
                    try:
                        info = json.loads(script_string)
                        if 'description' in info:
                            scene['details'] = info['description']
                    except Exception as ex:
                        log.debug(ex)

            scene_date = page.find('div', class_='video-date').span.string
            scene['date'] = self._convert_date(scene_date, '%b %d, %Y', '%Y-%m-%d')

            video = page.find('dl8-video') or page.find('video')
            if video:
                scene['image'] = video.get('poster')
            else:
                attachment_gallery_full = page.find('img', class_='attachment-gallery-full')
                if attachment_gallery_full:
                    scene['image'] = attachment_gallery_full.get('data-lazy-src')
            if scene.get('image') and scene['image'].startswith('/'):
                scene['image'] = f"{scene['studio']['url']}{scene['image']}"


            script = page.find('script', id='virtualreal_video-streaming-js-extra')
            if script:
                log.trace(f"script.string: {script.string}")
                json_text = re.sub(r'[^\{]*(\{.*\})[^\{]*', r'\1', script.string)
                log.trace(f"json_text: {json_text}")
                try:
                    streaming_obj = json.loads(json_text)
                    log.trace(f"streaming_obj: {streaming_obj}")
                    scene['code'] = streaming_obj.get('vid')
                except Exception as ex:
                    log.warning("Could not parse JSON from script text")
                    log.debug(ex)

            performer_items = page.find_all('div', class_='performerItem')
            if len(performer_items) > 0:
                scene['performers'] = [ { 'name': performer.img.get('alt') } for performer in performer_items ]

        return scene

    def _get_scene_by_url(self, url: str) -> dict:
        '''
        Scrape HTML page and search API for scene properties

        - code
        - date
        - details
        - image
        - performers
        - studio
        - tags
        - title
        - url
        '''
        scene = {}

        # parse web page
        scene_by_scraping_html = self.__get_scene_by_scraping_html(url)

        if scene_by_scraping_html.get('title'):
            scene = scene_by_scraping_html

        return scene


if __name__ == '__main__':
    result = VirtualRealPornScraper()
    print(result)
