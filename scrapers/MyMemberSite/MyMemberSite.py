import base64
import os
import json
import sys
import re
from urllib.parse import urlparse

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  # parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    from py_common import log
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


class MyMemberSite:
    """
    MyMemberSite scraper class.
    """

    _studios = {
        'aeriefans.com': {
            'api': 'aerie-saunders.mymember.site',
            'name': 'Aerie Saunders',
        },
        'alterpic.com': {
            'api': 'alterpic.mymember.site',
            'name': 'Alterpic',
        },
        'amieesfetishhouse.com': {
            'api': 'amiees-fetish-house.mymember.site',
            'name': 'Amiees Fetish House',
        },
        'asianmassagemaster.com': {
            'api': 'asianmassagemaster.mymember.site',
            'name': 'Asian Massage Master',
        },
        'bbwxxxadventures.com': {
            'api': 'bbwxxxadventures.mymember.site',
            'name': 'BBW XXX Adventures',
        },
        'bdsmkinkyplay.com': {
            'api': 'bdsmkinkyplay.mymember.site',
            'name': 'BDSM Kinky Play',
        },
        'beverlybluexxx.com': {
            'api': 'beverlybluexxx.mymember.site',
            'name': 'BeverlyBlueXxX',
        },
        'bindastimesuk.com': {
            'api': 'bindastimesuk.mymember.site',
            'name': 'Bindastimesuk',
        },
        'bondageliberation.com': {
            'api': 'bondageliberation.mymember.site',
            'name': 'Bondage Liberation',
        },
        'brookesballoons.com': {
            'api': 'brookesballoons.mymember.site',
            'name': 'BrookesBalloons',
        },
        'castersworldwide.com': {
            'api': 'castersworldwide.mymember.site',
            'name': 'Casters Worldwide',
        },
        'chloestoybox.com': {
            'api': 'chloestoybox.mymember.site',
            'name': 'Chloe Toy',
        },
        'clubsteffi.fun': {
            'api': 'clubsteffi.mymember.site',
            'name': 'ClubSteffi',
        },
        'cristalkinky.com': {
            'api': 'cristalkinky.mymember.site',
            'name': 'Cristal Kinky',
        },
        'curvymary.com': {
            'api': 'curvy-mary.mymember.site',
            'name': 'Curvy Mary',
        },
        'deemariexxx.com': {
            'api': 'deemariexxx.mymember.site',
            'name': 'Dee Marie',
        },
        'europornvids.com': {
            'api': 'europornvids.mymember.site',
            'name': 'Euro Porn Vids',
        },
        'faexcheta.com': {
            'api': 'faexcheta.mymember.site',
            'name': 'Fae and Cheta',
        },
        'fetiliciousfans.com': {
            'api': 'fetilicousfans.mymember.site',
            'name': 'Miss Fetilicious',
        },
        'fetishchimera.com': {
            'api': 'fetishchimera.mymember.site',
            'name': 'Fetish Chimera',
        },
        'friskyfairyk.com': {
            'api': 'friskyfairyk.mymember.site',
            'name': 'xoXokmarie',
        },
        'girlsofhel.com': {
            'api': 'girls-of-hel.mymember.site',
            'name': 'Girls of HEL',
        },
        'glass-dp.com': {
            'api': 'glassdp.mymember.site',
            'name': 'Glassdp',
        },
        'glassdeskproductions.com': {
            'api': 'glassdeskproductions.mymember.site',
            'name': 'GlassDeskProductions',
        },
        'goddesslesley.com': {
            'api': 'goddesslesley.mymember.site',
            'name': 'Goddess Lesley',
        },
        'goddessrobin.com': {
            'api': 'goddessrobin.mymember.site',
            'name': 'Goddess Robin',
        },
        'greatbritishfeet.com': {
            'api': 'greatbritishfeet.mymember.site',
            'name': 'Great British Feet',
        },
        'greendoorlive.tv': {
            'api': 'greendoorlivetv.mymember.site',
            'name': 'The World Famous Green Door',
        },
        'heavybondage4life.com': {
            'api': 'heavybondage4life.mymember.site',
            'name': 'Heavybondage4Life',
        },
        'hornysilver.com': {
            'api': 'hornysilver.mymember.site',
            'name': 'Hornysilver',
        },
        'josyblack.tv': {
            'api': 'josyblack.mymember.site',
            'name': 'Josy Black',
        },
        'kingnoirexxx.com': {
            'api': 'kingnoirexxx.mymember.site',
            'name': 'King Noire',
        },
        'kinkography.com': {
            'api': 'kinkography.mymember.site',
            'name': 'Kinkography',
        },
        'kinkyponygirl.com': {
            'api': 'kinkyponygirl.mymember.site',
            'name': 'KinkyPonygirl',
        },
        'kitehkawasaki.com': {
            'api': 'kitehkawasaki.mymember.site',
            'name': 'Kiteh Kawasaki',
        },
        'lady-asmondena.com': {
            'api': 'ladyasmondena.mymember.site',
            'name': 'Lady Asmondena',
        },
        'latexlolanoir.com': {
            'api': 'latexlolanoir.mymember.site',
            'name': 'Lola Noir',
        },
        'latexrapturefans.com': {
            'api': 'latexrapturefans.mymember.site',
            'name': 'LatexRapture',
        },
        'letseatcakexx.com': {
            'api': 'letseatcakexx.mymember.site',
            'name': 'LetsEatCakeXx',
        },
        'loonerlanding.com': {
            'api': 'loonerlanding.mymember.site',
            'name': 'Looner Landing',
        },
        'lukespov.vip': {
            'api': 'lukespov.mymember.site',
            'name': 'Luke\'s POV'},
        'marvalstudio.com': {
            'api': 'marvalstudio.mymember.site',
            'name': 'MarValStudio',
        },
        'michaelfittnation.com': {
            'api': 'michaelfittnation.mymember.site',
            'name': 'Michael Fitt',
        },
        'milenaangel.club': {
            'api': 'milenaangel.mymember.site',
            'name': 'MilenaAngel',
        },
        'mondofetiche.com': {
            'api': 'mondofetiche.mymember.site',
            'name': 'Mondo Fetiche',
        },
        'mrhappyendings.com': {
            'api': 'mrhappyendings.mymember.site',
            'name': 'Mr Happy Endings',
        },
        'nikitzo.com': {
            'api': 'nikitzo.mymember.site',
            'name': 'NIKITZO',
        },
        'nikkidavisxo.com': {
            'api': 'nikkidavisxo.mymember.site',
            'name': 'NikkiDavisXO',
        },
        'peacockcouple.com': {
            'api': 'peacockcouple.mymember.site',
            'name': 'PeacockCouple',
        },
        'pedal-passion.com': {
            'api': 'pedal-passion.mymember.site',
            'name': 'Pedal Passion',
        },
        'pervfect.net': {
            'api': 'pervfect.mymember.site',
            'name': 'Pervfect',
        },
        'riggsfilms.vip': {
            'api': 'riggsfilms.mymember.site',
            'name': 'Riggs Films',
        },
        'royalfetishxxx.com': {
            'api': 'royalfetishxxx.mymember.site',
            'name': 'RoyalFetishXXX',
        },
        'rubber-pervs.com': {
            'api': 'rubberpervs.mymember.site',
            'name': 'Rubber-Pervs',
        },
        'rubberdollemmalee.com': {
            'api': 'rubberdollemmalee.mymember.site',
            'name': 'Rubberdoll Emma Lee',
        },
        'sexyhippies.com': {
            'api': 'sexyhippies.mymember.site',
            'name': 'Sexy Hippies',
        },
        'shemalevalentina.com': {
            'api': 'shemalevalentina.mymember.site',
            'name': 'Shemale Valentina',
        },
        'strong-men.com': {
            'api': 'strong-men.mymember.site',
            'name': 'Strong-Men',
        },
        'tabooseduction.com': {
            'api': 'tabooseduction.mymember.site',
            'name': 'TabooSeduction',
        },
        'taboosexstories4k.com': {
            'api': 'taboosexstories4k.mymember.site',
            'name': 'Taboo Sex Stories',
        },
        'the-strapon-site.com': {
            'api': 'thestraponsite.mymember.site',
            'name': 'The Strapon Site',
        },
        'thegoonhole.com': {
            'api': 'thegoonhole.mymember.site',
            'name': 'The Goonhole',
        },
        'thekandikjewel.com': {
            'api': 'thekandikjewel.mymember.site',
            'name': 'The Kandi K Jewel',
        },
        'yourfitcrush.com': {
            'api': 'yourfitcrush.mymember.site',
            'name': 'Your Fit Crush',
        },
    }

    @classmethod
    def fetch_cover_image(cls, response):
        """
        Fetch cover image.

        Parameters
        ----------
        response: dict
            JSON response
        """
        for image_type in ['poster_src', 'cover_photo']:
            if image_type not in response:
                continue
            try:
                response = requests.get(response[image_type], headers={'User-Agent': USER_AGENT}, timeout=(3, 6))
                if response and response.status_code < 400:
                    content_type = response.headers.get('content-type')
                    mime = content_type.split(';')[0] if content_type else 'image/jpeg'
                    encoded = base64.b64encode(response.content).decode('utf-8')
                    return f'data:{mime};base64,{encoded}'
            except requests.exceptions.RequestException as req_ex:
                log.info(f'Error fetching URL {response["Image"]}: {req_ex}')
        return None

    @classmethod
    def fetch_resource(cls, base_url, resource_type, resource_id):
        """
        Fetch resource information.

        Parameters
        ----------
        base_url: str
            Base URL.
        resource_type: str
            Resource type.
        resource_id: str
            Resource ID.

        Returns
        -------
        Union[dict[str,str],None]
            Resource information or None on error.
        """
        url = f'{base_url}/api/{resource_type}/{resource_id}'
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
    def parse_url(cls, url, resource_type):
        """
        Parse resource URL.

        Parameters
        ----------
        url: str
            URL to scrape.
        resource_type: str
            Resource type to scrape - gallery or scene

        Returns
        -------
        Union[dict[str,str],None]
            Parsed URL information or None on error.
        """
        parsed = urlparse(url)

        domain = re.sub(r'^www\.', '', parsed.netloc)
        if domain not in cls._studios:
            log.error(f'Domain {domain} not supported, URL: {url}')
            return None
        path = parsed.path.split('/')
        path_types = {
            'gallery': 'photosets',
            'scene': 'videos',
        }
        if resource_type not in path_types:
            log.error(f'Resource type {resource_type} not supported, URL: {url}')
            return None
        pattern = re.compile(r'^(?P<id>\d+)(-(?P<name>.+))?$')
        match = pattern.match(path[path.index(path_types[resource_type]) + 1])
        return {
            'api': f'https://{cls._studios[domain]["api"]}',
            'domain': domain,
            'id': match.group('id'),
        }

    @classmethod
    def parse_resource(cls, response, resource_type, domain):
        """
        Parse resource information.

        Parameters
        ----------
        response: dict
            JSON response.
        resource_type: str
            Resource type.
        domain: str
            Domain name.

        Returns
        -------
        dict
            Resource information.
        """
        if response['description'] is not None:
            response['description'] = BeautifulSoup(response['description'], 'html.parser').get_text()
        info = {
            'Title': response['title'],
            'Details': response['description'] if response['description'] is not None else '',
            'URLs': [f'https://{domain}/{resource_type}/{response["id"]}'],
            'Date': response['publish_date'][0:response['publish_date'].find('T')],
            'Tags': list(map(lambda t: {'Name': t['name']}, response['tags'])),
            'Performers': list(map(lambda m: {'Name': m['screen_name']}, response['casts'])),
            'Studio': {
                'Name': cls._studios[domain]['name'] if domain in cls._studios else '',
                'URL': f'https://{domain}',
            },
            'Code': str(response['id']),
        }
        if resource_type == 'videos':
            info['Image'] = cls.fetch_cover_image(response)
        return info

    @classmethod
    def scrape_url(cls, url, resource_type):
        """
        Scrape gallery or scene from URL.

        Parameters
        ----------
        url: str
            Resource URL.
        resource_type: str
            Resource type (gallery, scene)

        Returns
        -------
        Union[dict[str,str],None]
            Scraped information or None on error.
        """
        parsed_url = cls.parse_url(url, resource_type)
        if parsed_url is None:
            return None

        if resource_type == 'scene':
            scraped = cls.scrape_scene(parsed_url)
        elif resource_type == 'gallery':
            scraped = cls.scrape_gallery(parsed_url)
        else:
            scraped = None

        return scraped

    @classmethod
    def scrape_gallery(cls, parsed_url):
        """
        Scrape gallery.

        Parameters
        ----------
        parsed_url: dict
            Parsed URL information.

        Returns
        -------
        dict
            Gallery information.
        """
        log.info(f'Scraping gallery ID {parsed_url["id"]}')
        data = cls.fetch_resource(parsed_url['api'], 'photo-collections', parsed_url["id"])
        return cls.parse_resource(data, 'photosets', parsed_url['domain']) if data is not None else None

    @classmethod
    def scrape_scene(cls, parsed_url):
        """
        Scrape scene.

        Parameters
        ----------
        parsed_url: dict
            Parsed URL information.

        Returns
        -------
        dict
            Scene information.
        """
        log.info(f'Scraping scene ID {parsed_url["id"]}')
        data = cls.fetch_resource(parsed_url['api'], 'videos', parsed_url['id'])
        return cls.parse_resource(data, 'videos', parsed_url['domain']) if data is not None else None


scraper_input = sys.stdin.read()
i = json.loads(scraper_input)
log.debug(f'Started with input: {scraper_input}')

scraper = MyMemberSite()
ret = {}
if sys.argv[1] == 'scrape':
    ret = scraper.scrape_url(i['url'], sys.argv[2])

output = json.dumps(ret) if ret is not None else '{}'
# log.debug(f'Send output: {output}')
print(output)

# Last Updated May 08, 2024
