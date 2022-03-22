import json
import io
import sys

from datetime import datetime

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

try:
    from bs4 import BeautifulSoup # requires v4.10.0 and above
except ModuleNotFoundError:
    print("You need to install the BeautifulSoup module (v4.10.0+). (https://pypi.org/project/beautifulsoup4/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install beautifulsoup4", file=sys.stderr)
    sys.exit()
    
    
def check_compat():
    from bs4 import __version__ as ver
    major, minor, _ = ver.split('.')
    if (int(major) == 4 and int(minor) >= 10) or (int(major) > 4):
        return
    print(f'This scraper requires BeautifulSoup 4.10.0 and above. Your version: {ver}', file=sys.stderr)
    sys.exit(1)


def process_name(name):
    name_map = {
        'Ô': 'ou',
        'ô': 'ou',
        'û': 'uu',
        'Û': 'uu',
        'î': 'ii',
        'Î': 'ii'
    }
    for k, v in name_map.items():
        name = name.replace(k, v)
    return name.title()


def get_gender(url):
    if 'female-pornstar' in url:
        return 'female'
    if 'male-pornstar' in url:
        return 'male'


def scrape_performer(url):
    resp = requests.get(url)
    if resp.ok:
        soup = BeautifulSoup(resp.text, 'html.parser')
        if soup.find('div', {'id': 'casting-profil-mini-infos'}):
            return scrape_mini_profile(soup, url)
        else:
            return scrape_full_profile(soup, url)


def scrape_mini_profile(soup, url):
    performer = {}
    birthdate_prefix = 'birthdate: '
    birthplace_prefix = 'birthplace: '
    measurements_prefix = 'measurements: '
    height_prefix = 'height: '

    performer['url'] = url
    if gender := get_gender(url):
        performer['gender'] = gender

    if soup.find(text=lambda t: 'pornstar is not yet in our database' in t):
        print('Performer not in database', file=sys.stderr)
        return

    if profile := soup.find('div', {'id': 'casting-profil-mini-infos'}):
        if alphabet_name := profile.find('meta', {'itemprop': 'name'}):
            name = alphabet_name.attrs['content']
            performer['name'] = process_name(name)
        if additional_name := profile.find('meta', {'itemprop': 'additionalName'}):
            japanese_name = additional_name.attrs['content']
            performer['aliases'] = japanese_name

    if details_node := soup.find('div', {'id': 'casting-profil-mini-infos-details'}):
        if birthdate_node := details_node.find('p', text=lambda t: birthdate_prefix in str(t)):
            birthdate_full = birthdate_node.text.split(birthdate_prefix)[1]
            if birthdate_full != 'unknown':
                performer['birthdate'] = datetime.strptime(birthdate_full, '%B %d, %Y').strftime('%Y-%m-%d')
        if birthplace_node := details_node.find('p', text=lambda t: birthplace_prefix in str(t)):
            birthplace_full = birthplace_node.text.split(birthplace_prefix)[1]
            if ', ' in birthplace_full:
                birthplace = birthplace_full.split(', ')[0]
            else:
                birthplace = birthplace_full
            if birthplace != 'unknown':
                performer['country'] = birthplace
            if birthplace == 'Japan':
                performer['ethnicity'] = 'asian'
        if measurements_node := details_node.find('p', text=lambda t: measurements_prefix in str(t)):
            measurements = measurements_node.text.split(measurements_prefix)[1]
            if measurements != 'unknown':
                performer['measurements'] = measurements
        if height_node := details_node.find('p', text=lambda t: height_prefix in str(t)):
            height = height_node.text.split(height_prefix)[1].split()[0]
            if height != 'unknown':
                performer['height'] = height
    if image_node := soup.find('div', {'id': 'casting-profil-preview'}):
        image_url = image_node.find('img', {'itemprop': 'image'}).attrs['src']
        if '/WAPdB-img/par-defaut/' not in image_url:
            performer['image'] = f'http://warashi-asian-pornstars.fr{image_url}'
    return performer


def scrape_full_profile(soup, url):
    performer = {}
    measurements_prefix = 'measurements: '
    activity_prefix = 'porn/AV activity: '

    if alphabet_name := soup.find('span', {'itemprop': 'name'}):
        alphabet_name = alphabet_name.text

    japanese_name = None
    if additional_name := soup.find('span', {'itemprop': 'additionalName'}):
        japanese_name = additional_name.text
    performer['name'] = process_name(alphabet_name)
    performer['url'] = url
    if gender := get_gender(url):
        performer['gender'] = gender
    if gender_node := soup.find('meta', {'property': 'og:gender'}):
        performer['gender'] = gender_node.attrs['content']
    if twitter_node := soup.find(text='official Twitter'):
        performer['twitter'] = twitter_node.parent.attrs['href']
    if birthday_node := soup.find('time', {'itemprop': 'birthDate'}):
        performer['birthdate'] = birthday_node.attrs['content']
    if height_node := soup.find('p', {'itemprop': 'height'}):
        if height_value_node := height_node.find('span', {'itemprop': 'value'}):
            performer['height'] = height_value_node.text
    if weight_node := soup.find('p', {'itemprop': 'weight'}):
        if weight_value_node := weight_node.find('span', {'itemprop': 'value'}):
            performer['Weight'] = weight_value_node.text
    if measurements_node := soup.find(text=lambda t: measurements_prefix in str(t)):
        measurements = measurements_node.text.split(measurements_prefix)[1]
        if measurements != 'unknown':
            performer['measurements'] = measurements_node.text.split(measurements_prefix)[1]
    if activity_node := soup.find(text=lambda t: activity_prefix in str(t)):
        performer['career_length'] = activity_node.text.split(activity_prefix)[1].strip()

    if image_container_node := soup.find('div', {'id': 'pornostar-profil-photos-0'}):
        if image_node := image_container_node.find('img', {'itemprop': 'image'}):
            image_url = image_node.attrs['src']
            if '/WAPdB-img/par-defaut/' not in image_url:
                performer['image'] = f'http://warashi-asian-pornstars.fr{image_url}'

    if len(country_nodes := soup.find_all('span', {'itemprop': 'addressCountry'})) > 1:
        country = country_nodes[1].text
        performer['country'] = country
        if country == 'Japan':
            performer['ethnicity'] = 'asian'

    aliases = []
    if japanese_name:
        aliases.append(japanese_name)
    if alias_node := soup.find('div', {'id': 'pornostar-profil-noms-alternatifs'}):
        for couple in alias_node.find_all('li'):
            alias = process_name(couple.text)
            if alias == alphabet_name or alias == str(japanese_name):
                continue
            if alias not in aliases:
                aliases.append(alias)
    performer['aliases'] = ', '.join(set(aliases))

    if tags_node := soup.find('p', {'class': 'implode-tags'}):
        for tag in tags_node.find_all('a'):
            if tag.text == 'breast augmentation':
                performer['fake_tits'] = 'Y'
            if tag.text == 'tatoos':
                performer['tattoos'] = 'Y'
            if tag.text == 'piercings':
                performer['piercings'] = 'Y'

    if physical_characteristics := soup.find('p', text=lambda t: 'distinctive physical characteristics' in str(t)):
        dpc = physical_characteristics.text
        if 'breast augmentation' in dpc:
            performer['fake_tits'] = 'Y'
        if 'tattoo(s)' in dpc:
            performer['tattoos'] = 'Y'
        if 'piercing(s)' in dpc:
            performer['piercings'] = 'Y'

    return performer


def search_performer(frag):
    data = {
        'recherche_critere': 'f',
        'recherche_valeur': frag['name'],
        'x': '20',
        'y': '17'
    }
    base_site = 'http://warashi-asian-pornstars.fr'
    performers = []
    resp = requests.post(f'{base_site}/en/s-12/search', data=data)
    if resp.ok:
        soup = BeautifulSoup(resp.text, 'html.parser')
        entries = []
        already_seen = []
        if exact_match := soup.find('div', {'class': 'correspondance_exacte'}):  # process exact matches first
            entries.append(exact_match)
        for e in soup.find_all('div', {'class': 'resultat-pornostar'}):
            entries.append(e)
        for entry in entries:
            p = {}
            if n := entry.find('span', {'class': 'correspondance-lien'}):
                name = n.parent.text.strip()
                p['name'] = process_name(name)
                p['url'] = f'{base_site}{n.parent.attrs["href"]}'
            elif len(n := entry.find_all('a')) > 1:
                p['name'] = process_name(n[1].text.strip())
                p['url'] = f'{base_site}{n[1].attrs["href"]}'
            if p:
                if p['url'] not in already_seen:
                    performers.append(p)
                    already_seen.append(p['url'])
        return performers


def main():
    check_compat()
    # workaround for cp1252
    sys.stdin = io.TextIOWrapper(sys.stdin.detach(), encoding='utf-8')
    frag = json.loads(sys.stdin.read())
    arg = sys.argv[-1]
    if arg == 'performerByName':
        performers = search_performer(frag)
        result = json.dumps(performers)
        print(result)
    if arg in ['performerByFragment', 'performerByURL']:
        performer = scrape_performer(frag['url'])
        result = json.dumps(performer)
        print(result)


if __name__ == '__main__':
    main()
