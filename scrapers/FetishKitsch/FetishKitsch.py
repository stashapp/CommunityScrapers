import base64
import os
import json
import sys
from datetime import datetime
from typing import Union, Any, Dict, List
from urllib.parse import urljoin, urlparse


# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    from py_common import log
    from py_common.types import ScrapedPerformer, ScrapedScene, ScrapedTag
except ModuleNotFoundError:
    print(
        'You need to download the folder \'py_common\' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)',
        file=sys.stderr)
    sys.exit()

try:
    import requests
except ModuleNotFoundError:
    print('You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)',
          file=sys.stderr)
    print(
        'If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests',
        file=sys.stderr)
    sys.exit()

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    print(
        'You need to install the Beautiful Soup module. (https://pypi.org/project/beautifulsoup4/)',
        file=sys.stderr,
    )
    print(
        'If you have pip (normally installed with python), run this command in a terminal (cmd): pip install beautifulsoup4',
        file=sys.stderr,
    )
    sys.exit()


USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'


class FetishKitsch:
    """
    Class to scrape FetishKitsch.com.

    Attributes
    ----------
    _base_url : str
        The base URL of the FetishKitsch website.
    """

    _base_url: str = 'https://fetishkitsch.com/'

    @classmethod
    def fetch_post(cls, post_id: str) -> Union[Dict[str, Any], None]:
        """
        Fetches a post from the FetishKitsch website.

        Parameters
        ----------
        post_id : str
            The ID of the post to fetch.

        Returns
        -------
        Union[Dict[str, Any], None]
            The post data if it was found, None otherwise.
        """
        next_build_id: Union[str, None] = cls.scrape_build_id()
        if next_build_id is None:
            return None

        url: str = urljoin(cls._base_url, f'/_next/data/{next_build_id}/post/{post_id}.json?postId={post_id}')
        log.debug(f'Fetching URL {url}')
        try:
            response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=(3, 6))
        except requests.exceptions.RequestException as req_ex:
            log.error(f'Error fetching URL {url}: {req_ex}')
            return None

        if response.status_code >= 400:
            log.info(f'Fetching URL {url} resulted in error status: {response.status_code}')
            return None

        data = response.json()
        log.debug(f'Received data: {data}')
        return data

    @classmethod
    def fetch_thumbnail(cls, thumbnail_url: str) -> Union[str, None]:
        """
        Fetches the thumbnail for a post from the FetishKitsch website.

        Parameters
        ----------
        thumbnail_url : str
            The URL of the thumbnail to fetch.

        Returns
        -------
        Union[str, None]
            The URL of the thumbnail if it was found, None otherwise.
        """
        try:
            response = requests.get(thumbnail_url, headers={'User-Agent': USER_AGENT}, timeout=(3, 6))
            if response and response.status_code < 400:
                content_type = response.headers.get('content-type')
                mime = content_type.split(';')[0] if content_type else 'image/jpeg'
                encoded = base64.b64encode(response.content).decode('utf-8')
                return f'data:{mime};base64,{encoded}'
        except requests.exceptions.RequestException as req_ex:
            log.info(f'Error fetching URL {thumbnail_url}: {req_ex}')
            return None

    @classmethod
    def map_performer(cls, performer: str) -> ScrapedPerformer:
        """
        Maps a raw performer info to a ScrapedPerformer.

        Parameters
        ----------
        performer : str
            The raw performer info to map.

        Returns
        -------
        ScrapedPerformer
            The mapped performer.
        """
        return {
            'name': performer.replace('_', ' '),
        }

    @classmethod
    def map_tag(cls, tag: str) -> ScrapedTag:
        """
        Maps a raw tag to a ScrapedTag.

        Parameters
        ----------
        tag : str
            The raw tag to map.

        Returns
        -------
        ScrapedTag
            The mapped tag.
        """
        return {
            'name': tag.replace('_', ' '),
        }

    @classmethod
    def scrape_build_id(cls) -> Union[str, None]:
        """
        Fetches the buildId from the next.js website.

        Returns
        -------
        Union[str, None]
            The buildId if it was found, None otherwise.
        """
        log.debug(f'Fetching next.js buildId')
        try:
            response = requests.get(cls._base_url, headers={'User-Agent': USER_AGENT}, timeout=(3, 6))
        except requests.exceptions.RequestException as req_ex:
            log.error(f'Error fetching next.js buildId: {req_ex}')
            return None

        if response.status_code >= 400:
            log.info(f'Fetching next.js buildId resulted in error status: {response.status_code}')
            return None

        html_response = BeautifulSoup(response.text, 'html.parser')
        next_meta = json.loads(html_response.find('script', {'id': '__NEXT_DATA__'}).string)
        return next_meta['buildId']

    @classmethod
    def scrape_scene(cls, url: str) -> Union[ScrapedScene, None]:
        """
        Scrapes a scene from FetishKitsch.com.

        Parameters
        ----------
        url : str
            The URL of the scene to scrape.

        Returns
        -------
        Union[ScrapedScene, None]
            The scraped scene if it was found, None otherwise.
        """
        log.info(f'Scraping FetishKitsch.com scene from {url}')
        parsed = urlparse(url)
        path: List[str] = parsed.path.split('/')
        build_id: Union[str, None] = cls.scrape_build_id()

        if build_id is None:
            return None

        post_id: str = path[path.index('post') + 1]
        post: Union[Dict[str, Any], None] = cls.fetch_post(post_id)

        if post is None:
            return None

        post = post['pageProps']['post']
        scene: ScrapedScene = {
            'title': post['title'].replace('_', ' '),
            'url': urljoin(cls._base_url, f'/post/{post_id}'),
            'date': datetime.strptime(post['shootDate'], '%b %d, %Y').strftime('%Y-%m-%d'),
            'tags': list(map(lambda t: cls.map_tag(t), post['tags'])),
            'performers': list(map(lambda p: cls.map_performer(p), post['people'])),
            'studio': {
                'name': 'FetishKitsch',
                'url': 'https://fetishkitsch.com/',
            },
            'code': str(post['shootCode']),
        }

        thumbnail: Union[str, None] = cls.fetch_thumbnail(post['videoThumbnail'])
        if thumbnail is not None:
            scene['image'] = thumbnail

        return scene


scraper_input = sys.stdin.read()
i = json.loads(scraper_input)
log.debug(f'Started with input: {scraper_input}')

ret = {}
scraper = FetishKitsch()
if sys.argv[1] == 'scrape' and sys.argv[2] == 'scene':
    ret = scraper.scrape_scene(i['url'])

output = json.dumps(ret) if ret is not None else '{}'
# log.debug(f'Send output: {output}')
print(output)

# Last Updated May 11, 2024
