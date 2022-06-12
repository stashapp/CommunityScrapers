import base64
import datetime
import json
import string
import sys
import time
import re
import random
import requests
from urllib.parse import urlparse
# extra modules below need to be installed
try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

try:
    import cloudscraper
except ModuleNotFoundError:
    print("You need to install the cloudscraper module. (https://pypi.org/project/cloudscraper/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install cloudscraper", file=sys.stderr)
    sys.exit()
    
try:
    from lxml import html
except ModuleNotFoundError:
    print("You need to install the lxml module. (https://lxml.de/installation.html#installation)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml", file=sys.stderr)
    sys.exit()

class Scraper:
    def set_value(self,value):
        if value:
            if not re.match(r'(?i)no data', value[0]):
                    return value[0]
        return None

    def set_stripped_value(self,value):
        if value:
            return value[0].strip("\n ")
        return None

    def set_concat_value(self,sep,values):
        if values:
            return sep.join(values)
        return None

    def set_named_value(self, name, value):
        if value:
            attr = { name: value[0] }
            return attr
        return None

    def set_named_values(self, name, values):
        res = []
        for v in values:
            r = { name: v }
            res.append(r)
        return res

    def print(self):
        for a in dir(self):
            if not a.startswith('__') and not callable(getattr(self, a)) :
                if vars(self)[a]:
                    print("%s: %s" % (a , vars(self)[a] ) )

    def to_json(self):
        for a in dir(self):
            if not a.startswith('__') and not callable(getattr(self, a)) :
                if not vars(self)[a]:
                    del vars(self)[a]
        return json.dumps(self.__dict__)

    def map_ethnicity(self, value):
        ethnicity = {
             'Asian': 'asian',
             'Caucasian': 'white',
             'Black': 'black',
             'Latin': 'hispanic',
        }
        return ethnicity.get(value, value)

    def map_gender(self, value):
        gender = {
             'f': 'Female',
             'm': 'Male',
        }
        return gender.get(value, value)

    def map_country(self, value):
        country = {
              # https://en.wikipedia.org/wiki/List_of_adjectival_and_demonymic_forms_for_countries_and_nations
              "Abkhaz": "Abkhazia",
              "Abkhazian": "Abkhazia",
              "Afghan": "Afghanistan",
              "Albanian": "Albania",
              "Algerian": "Algeria",
              "American Samoan": "American Samoa",
              "American": "United States of America",
              "Andorran": "Andorra",
              "Angolan": "Angola",
              "Anguillan": "Anguilla",
              "Antarctic": "Antarctica",
              "Antiguan": "Antigua and Barbuda",
              "Argentine": "Argentina",
              "Argentinian": "Argentina",
              "Armenian": "Armenia",
              "Aruban": "Aruba",
              "Australian": "Australia",
              "Austrian": "Austria",
              "Azerbaijani": "Azerbaijan",
              "Azeri": "Azerbaijan",
              "Bahamian": "Bahamas",
              "Bahraini": "Bahrain",
              "Bangladeshi": "Bangladesh",
              "Barbadian": "Barbados",
              "Barbudan": "Antigua and Barbuda",
              "Basotho": "Lesotho",
              "Belarusian": "Belarus",
              "Belgian": "Belgium",
              "Belizean": "Belize",
              "Beninese": "Benin",
              "Beninois": "Benin",
              "Bermudan": "Bermuda",
              "Bermudian": "Bermuda",
              "Bhutanese": "Bhutan",
              "BIOT": "British Indian Ocean Territory",
              "Bissau-Guinean": "Guinea-Bissau",
              "Bolivian": "Bolivia",
              "Bonaire": "Bonaire",
              "Bonairean": "Bonaire",
              "Bosnian": "Bosnia and Herzegovina",
              "Botswanan": "Botswana",
              "Bouvet Island": "Bouvet Island",
              "Brazilian": "Brazil",
              "British Virgin Island": "Virgin Islands, British",
              "British": "United Kingdom",
              "Bruneian": "Brunei",
              "Bulgarian": "Bulgaria",
              "Burkinabé": "Burkina Faso",
              "Burmese": "Burma",
              "Burundian": "Burundi",
              "Cabo Verdean": "Cabo Verde",
              "Cambodian": "Cambodia",
              "Cameroonian": "Cameroon",
              "Canadian": "Canada",
              "Cantonese": "Hong Kong",
              "Caymanian": "Cayman Islands",
              "Central African": "Central African Republic",
              "Chadian": "Chad",
              "Channel Island": "Guernsey",
              #Channel Island: "Jersey"
              "Chilean": "Chile",
              "Chinese": "China",
              "Christmas Island": "Christmas Island",
              "Cocos Island": "Cocos (Keeling) Islands",
              "Colombian": "Colombia",
              "Comoran": "Comoros",
              "Comorian": "Comoros",
              "Congolese": "Congo",
              "Cook Island": "Cook Islands",
              "Costa Rican": "Costa Rica",
              "Croatian": "Croatia",
              "Cuban": "Cuba",
              "Curaçaoan": "Curaçao",
              "Cypriot": "Cyprus",
              "Czech": "Czech Republic",
              "Danish": "Denmark",
              "Djiboutian": "Djibouti",
              "Dominican": "Dominica",
              "Dutch": "Netherlands",
              "Ecuadorian": "Ecuador",
              "Egyptian": "Egypt",
              "Emirati": "United Arab Emirates",
              "Emiri": "United Arab Emirates",
              "Emirian": "United Arab Emirates",
              "English people": "England",
              "English": "England",
              "Equatoguinean": "Equatorial Guinea",
              "Equatorial Guinean": "Equatorial Guinea",
              "Eritrean": "Eritrea",
              "Estonian": "Estonia",
              "Ethiopian": "Ethiopia",
              "European": "European Union",
              "Falkland Island": "Falkland Islands",
              "Faroese": "Faroe Islands",
              "Fijian": "Fiji",
              "Filipino": "Philippines",
              "Finnish": "Finland",
              "Formosan": "Taiwan",
              "French Guianese": "French Guiana",
              "French Polynesian": "French Polynesia",
              "French Southern Territories": "French Southern Territories",
              "French": "France",
              "Futunan": "Wallis and Futuna",
              "Gabonese": "Gabon",
              "Gambian": "Gambia",
              "Georgian": "Georgia",
              "German": "Germany",
              "Ghanaian": "Ghana",
              "Gibraltar": "Gibraltar",
              "Greek": "Greece",
              "Greenlandic": "Greenland",
              "Grenadian": "Grenada",
              "Guadeloupe": "Guadeloupe",
              "Guamanian": "Guam",
              "Guatemalan": "Guatemala",
              "Guinean": "Guinea",
              "Guyanese": "Guyana",
              "Haitian": "Haiti",
              "Heard Island": "Heard Island and McDonald Islands",
              "Hellenic": "Greece",
              "Herzegovinian": "Bosnia and Herzegovina",
              "Honduran": "Honduras",
              "Hong Kong": "Hong Kong",
              "Hong Konger": "Hong Kong",
              "Hungarian": "Hungary",
              "Icelandic": "Iceland",
              "Indian": "India",
              "Indonesian": "Indonesia",
              "Iranian": "Iran",
              "Iraqi": "Iraq",
              "Irish": "Ireland",
              "Israeli": "Israel",
              "Israelite": "Israel",
              "Italian": "Italy",
              "Ivorian": "Ivory Coast",
              "Jamaican": "Jamaica",
              "Jan Mayen": "Jan Mayen",
              "Japanese": "Japan",
              "Jordanian": "Jordan",
              "Kazakh": "Kazakhstan",
              "Kazakhstani": "Kazakhstan",
              "Kenyan": "Kenya",
              "Kirghiz": "Kyrgyzstan",
              "Kirgiz": "Kyrgyzstan",
              "Kiribati": "Kiribati",
              "Korean": "South Korea",
              "Kosovan": "Kosovo",
              "Kosovar": "Kosovo",
              "Kuwaiti": "Kuwait",
              "Kyrgyz": "Kyrgyzstan",
              "Kyrgyzstani": "Kyrgyzstan",
              "Lao": "Lao People's Democratic Republic",
              "Laotian": "Lao People's Democratic Republic",
              "Latvian": "Latvia",
              "Lebanese": "Lebanon",
              "Lettish": "Latvia",
              "Liberian": "Liberia",
              "Libyan": "Libya",
              "Liechtensteiner": "Liechtenstein",
              "Lithuanian": "Lithuania",
              "Luxembourg": "Luxembourg",
              "Luxembourgish": "Luxembourg",
              "Macanese": "Macau",
              "Macedonian": "North Macedonia",
              "Magyar": "Hungary",
              "Mahoran": "Mayotte",
              "Malagasy": "Madagascar",
              "Malawian": "Malawi",
              "Malaysian": "Malaysia",
              "Maldivian": "Maldives",
              "Malian": "Mali",
              "Malinese": "Mali",
              "Maltese": "Malta",
              "Manx": "Isle of Man",
              "Marshallese": "Marshall Islands",
              "Martinican": "Martinique",
              "Martiniquais": "Martinique",
              "Mauritanian": "Mauritania",
              "Mauritian": "Mauritius",
              "McDonald Islands": "Heard Island and McDonald Islands",
              "Mexican": "Mexico",
              "Moldovan": "Moldova",
              "Monacan": "Monaco",
              "Mongolian": "Mongolia",
              "Montenegrin": "Montenegro",
              "Montserratian": "Montserrat",
              "Monégasque": "Monaco",
              "Moroccan": "Morocco",
              "Motswana": "Botswana",
              "Mozambican": "Mozambique",
              "Myanma": "Myanmar",
              "Namibian": "Namibia",
              "Nauruan": "Nauru",
              "Nepalese": "Nepal",
              "Nepali": "Nepal",
              "Netherlandic": "Netherlands",
              "New Caledonian": "New Caledonia",
              "New Zealand": "New Zealand",
              "Ni-Vanuatu": "Vanuatu",
              "Nicaraguan": "Nicaragua",
              "Nigerian": "Nigeria",
              "Nigerien": "Niger",
              "Niuean": "Niue",
              "Norfolk Island": "Norfolk Island",
              "Northern Irish": "Northern Ireland",
              "Northern Marianan": "Northern Mariana Islands",
              "Norwegian": "Norway",
              "Omani": "Oman",
              "Pakistani": "Pakistan",
              "Palauan": "Palau",
              "Palestinian": "Palestine",
              "Panamanian": "Panama",
              "Papua New Guinean": "Papua New Guinea",
              "Papuan": "Papua New Guinea",
              "Paraguayan": "Paraguay",
              "Persian": "Iran",
              "Peruvian": "Peru",
              "Philippine": "Philippines",
              "Pitcairn Island": "Pitcairn Islands",
              "Polish": "Poland",
              "Portuguese": "Portugal",
              "Puerto Rican": "Puerto Rico",
              "Qatari": "Qatar",
              "Romanian": "Romania",
              "Russian": "Russia",
              "Rwandan": "Rwanda",
              "Saba": "Saba",
              "Saban": "Saba",
              "Sahraouian": "Western Sahara",
              "Sahrawi": "Western Sahara",
              "Sahrawian": "Western Sahara",
              "Salvadoran": "El Salvador",
              "Sammarinese": "San Marino",
              "Samoan": "Samoa",
              "Saudi Arabian": "Saudi Arabia",
              "Saudi": "Saudi Arabia",
              "Scottish": "Scotland",
              "Senegalese": "Senegal",
              "Serbian": "Serbia",
              "Seychellois": "Seychelles",
              "Sierra Leonean": "Sierra Leone",
              "Singapore": "Singapore",
              "Singaporean": "Singapore",
              "Slovak": "Slovakia",
              "Slovene": "Slovenia",
              "Slovenian": "Slovenia",
              "Solomon Island": "Solomon Islands",
              "Somali": "Somalia",
              "Somalilander": "Somaliland",
              "South African": "South Africa",
              "South Georgia Island": "South Georgia and the South Sandwich Islands",
              "South Ossetian": "South Ossetia",
              "South Sandwich Island": "South Georgia and the South Sandwich Islands",
              "South Sudanese": "South Sudan",
              "Spanish": "Spain",
              "Sri Lankan": "Sri Lanka",
              "Sudanese": "Sudan",
              "Surinamese": "Suriname",
              "Svalbard resident": "Svalbard",
              "Swati": "Eswatini",
              "Swazi": "Eswatini",
              "Swedish": "Sweden",
              "Swiss": "Switzerland",
              "Syrian": "Syrian Arab Republic",
              "Taiwanese": "Taiwan",
              "Tajikistani": "Tajikistan",
              "Tanzanian": "Tanzania",
              "Thai": "Thailand",
              "Timorese": "Timor-Leste",
              "Tobagonian": "Trinidad and Tobago",
              "Togolese": "Togo",
              "Tokelauan": "Tokelau",
              "Tongan": "Tonga",
              "Trinidadian": "Trinidad and Tobago",
              "Tunisian": "Tunisia",
              "Turkish": "Turkey",
              "Turkmen": "Turkmenistan",
              "Turks and Caicos Island": "Turks and Caicos Islands",
              "Tuvaluan": "Tuvalu",
              "Ugandan": "Uganda",
              "Ukrainian": "Ukraine",
              "Uruguayan": "Uruguay",
              "Uzbek": "Uzbekistan",
              "Uzbekistani": "Uzbekistan",
              "Vanuatuan": "Vanuatu",
              "Vatican": "Vatican City State",
              "Venezuelan": "Venezuela",
              "Vietnamese": "Vietnam",
              "Wallis and Futuna": "Wallis and Futuna",
              "Wallisian": "Wallis and Futuna",
              "Welsh": "Wales",
              "Yemeni": "Yemen",
              "Zambian": "Zambia",
              "Zimbabwean": "Zimbabwe",
              "Åland Island": "Åland Islands",
        }
        return country.get(value,value)

stash_date = '%Y-%m-%d'
iafd_date = '%B %d, %Y'
iafd_date_scene = '%b %d, %Y'


def strip_end(text, suffix):
    if suffix and text.endswith(suffix):
        return text[:-len(suffix)]
    return text

def performer_query(query):
    tree = scrape(f"https://www.iafd.com/results.asp?searchtype=comprehensive&searchstring={query}")
    performer_names = tree.xpath('//table[@id="tblFem" or @id="tblMal"]//td[a[img]]/following-sibling::td[1]/a/text()')
    performer_urls = tree.xpath('//table[@id="tblFem" or @id="tblMal"]//td[a[img]]/following-sibling::td[1]/a/@href')
    performers = []
    for i, name in enumerate(performer_names):
        p = {
            'Name': name,
            'URL': "https://www.iafd.com/" + performer_urls[i],
        }
        performers.append(p)
    print(json.dumps(performers))
    if not performers:
        log.warning("<no performers> found")
    sys.exit(0)
 

def scrape(url, retries=0):
    scraper = cloudscraper.create_scraper()
    try:
        scraped = scraper.get(url, timeout=(3,7))
    except requests.exceptions.Timeout as exc_time:
        log.debug(f"Timeout: {exc_time}")
        return scrape(url, retries+1)
    except Exception as e:
        log.error(f"scrape error {e}")
        sys.exit(1)
    if scraped.status_code >= 400:
        if retries < 10:
            log.debug(f'HTTP Error: {scraped.status_code}')
            time.sleep(random.randint(1, 4))
            return scrape(url, retries+1)
        else:
            log.error(f'HTTP Error: {scraped.status_code}')
            sys.exit(1)
    return html.fromstring(scraped.content)

def scrape_image(url, retries=0):
    scraper = cloudscraper.create_scraper()
    try:
        scraped = scraper.get(url, timeout=(3,5))
    except requests.exceptions.Timeout as exc_time:
        log.debug(f"Timeout: {exc_time}")
        return scrape_image(url, retries+1)
    except Exception as e:
        log.debug(f"scrape error {e}")
        return None
    if scraped.status_code >= 400:
        log.debug(f'HTTP Error: {scraped.status_code}')
        if retries < 10:
            time.sleep(random.randint(1, 4))
            return scrape_image(url, retries+1)
        return None
    b64img = base64.b64encode(scraped.content)
    return "data:image/jpeg;base64," + b64img.decode('utf-8')

def performer_from_tree(tree):
    p = Scraper()

    performer_name = tree.xpath("//h1/text()")
    p.name = p.set_stripped_value(performer_name)

    performer_gender = tree.xpath('//form[@id="correct"]/input[@name="Gender"]/@value')
    p.gender = p.set_value(performer_gender)
    p.gender = p.map_gender(p.gender)

    performer_url = tree.xpath('//div[@id="perfwith"]//*[contains(@href,"person.rme")]/@href')
    if performer_url:
        p.url = "https://www.iafd.com" + performer_url[0]
    performer_twitter = tree.xpath('//p[@class="biodata"]/a[contains(text(),"http://twitter.com/")]/@href')
    p.twitter = p.set_value(performer_twitter)

    performer_instagram = tree.xpath('//p[@class="biodata"]/a[contains(text(),"http://instagram.com/")]/@href')
    p.instagram = p.set_value(performer_instagram)

    performer_birthdate = tree.xpath('(//p[@class="bioheading"][text()="Birthday"]/following-sibling::p)[1]//text()')
    p.birthdate = p.set_value(performer_birthdate)
    if p.birthdate:
        p.birthdate = re.sub(r'(\S+\s+\d+,\s+\d+).*', r'\1', p.birthdate)
        try:
            p.birthdate = datetime.datetime.strptime(p.birthdate, iafd_date).strftime(stash_date)
        except:
            p.birthdate = None
            if performer_birthdate[0].lower() != "no data":
                dob =  f'D.O.B. : {performer_birthdate[0]}\n'
                try:
                    p.details = p.details + dob
                except:
                    p.details = dob
            pass

    performer_deathdate = tree.xpath('(//p[@class="bioheading"][text()="Date of Death"]/following-sibling::p)[1]//text()')
    p.death_date = p.set_value(performer_deathdate)
    if p.death_date:
        p.death_date = re.sub(r'(\S+\s+\d+,\s+\d+).*', r'\1', p.death_date)
        try:
            p.death_date = datetime.datetime.strptime(p.death_date, iafd_date).strftime(stash_date)
        except:
            p.death_date = None
            if performer_deathdate[0].lower() != "no data":
                dod = f'D.O.D. : {performer_deathdate[0]}\n'
                try:
                    p.details = p.details + dod
                except:
                    p.details = dod
            pass

    performer_ethnicity = tree.xpath('//div[p[text()="Ethnicity"]]/p[@class="biodata"][1]//text()')
    p.ethnicity = p.set_value(performer_ethnicity)
    p.ethnicity = p.map_ethnicity(p.ethnicity)

    performer_country = tree.xpath('//div/p[text()="Nationality"]/following-sibling::p[1]//text()')
    p.country = p.set_value(performer_country)
    if p.country:
        p.country = re.sub(r'^American,.+','American',p.country)
        p.country = p.map_country(p.country)

    performer_height = tree.xpath('//div/p[text()="Height"]/following-sibling::p[1]//text()')
    p.height = p.set_value(performer_height)
    if p.height:
        p.height = re.sub(r'.*\((\d+)\s+cm.*', r'\1', p.height)

    performer_weight = tree.xpath('//div/p[text()="Weight"]/following-sibling::p[1]//text()')
    p.weight = p.set_value(performer_weight)
    if p.weight:
        p.weight = re.sub(r'.*\((\d+)\s+kg.*', r'\1', p.weight)

    performer_haircolor = tree.xpath('//div/p[starts-with(.,"Hair Color")]/following-sibling::p[1]//text()')
    p.hair_color = p.set_value(performer_haircolor)

    performer_measurements = tree.xpath('//div/p[text()="Measurements"]/following-sibling::p[1]//text()')
    p.measurements = p.set_value(performer_measurements)

    performer_careerlength = tree.xpath('//div/p[@class="biodata"][contains(text(),"Started around")]/text()')
    p.career_length = p.set_value(performer_careerlength)
    if p.career_length:
        p.career_length = re.sub(r'(\D+\d\d\D+)$', "", p.career_length)

    performer_aliases = tree.xpath('//div[p[@class="bioheading" and contains(normalize-space(text()),"Performer AKA")]]//div[@class="biodata" and not(text()="No known aliases")]/text()')
    p.aliases = p.set_value(performer_aliases)

    performer_tattoos = tree.xpath('//div/p[text()="Tattoos"]/following-sibling::p[1]//text()')
    p.tattoos = p.set_value(performer_tattoos)

    performer_piercings = tree.xpath('//div/p[text()="Piercings"]/following-sibling::p[1]//text()')
    p.piercings = p.set_value(performer_piercings)

    performer_image_url = tree.xpath('//div[@id="headshot"]//img/@src')
    if performer_image_url:
        try:
            log.debug(f"downloading image from {performer_image_url[0]}")
            p.images = [scrape_image(performer_image_url[0])]
        except Exception as e:
            log.debug(f"error downloading image {e}")

    res = p.to_json()
    #log.debug(res)
    print(res)
    sys.exit(0)

def scene_from_tree(tree):
    s = Scraper()

    scene_title = tree.xpath('//h1/text()')
    s.title = s.set_stripped_value(scene_title)

    scene_date =  tree.xpath('//div[@class="col-xs-12 col-sm-3"]//p[text() = "Release Date"]/following-sibling::p[1]//text()')
    s.date = s.set_stripped_value(scene_date)
    if s.date:
        try:
            s.date = datetime.datetime.strptime(s.date, iafd_date_scene).strftime(stash_date)
        except:
            pass

    scene_details = tree.xpath('//div[@id="synopsis"]/div[@class="padded-panel"]//text()')
    s.details = s.set_value(scene_details)

    scene_studio = tree.xpath('//div[@class="col-xs-12 col-sm-3"]//p[text() = "Studio"]/following-sibling::p[1]//text()')
    s.studio = s.set_named_value("name",scene_studio)

    scene_performers = tree.xpath('//div[@class="castbox"]/p/a/text()')
    s.performers = s.set_named_values("name", scene_performers)

    res = s.to_json()
    print(res)
    sys.exit(0)

def movie_from_tree(tree):
    m = Scraper()
    movie_name = tree.xpath("//h1/text()")
    m.name = m.set_stripped_value(movie_name)
    if m.name:
        m.name = re.sub(r'\s*\([0-9]+\)$', "", m.name)

    movie_directors = tree.xpath('//p[@class="bioheading"][contains(text(), "Directors")]/following-sibling::p[@class="biodata"][1]/a/text()')
    m.direcors = m.set_stripped_value(movie_directors)

    movie_synopsis = tree.xpath('//div[@id="synopsis"]/div[@class="padded-panel"]//text()')
    m.synopsis = m.set_value(movie_synopsis)

    movie_duration = tree.xpath('//p[@class="bioheading"][contains(text(), "Minutes")]/following-sibling::p[@class="biodata"][1]/text()')
    m.duration = m.set_stripped_value(movie_duration)

    movie_date = tree.xpath('//p[@class="bioheading"][contains(text(), "Release Date")]/following-sibling::p[@class="biodata"][1]/text()') 
    m.date = m.set_stripped_value(movie_date)
    if m.date:
        try:
            m.date = datetime.datetime.strptime(m.date, iafd_date_scene).strftime(stash_date)
        except:
            pass

    movie_aliases = tree.xpath('//div[@class="col-sm-12"]/dl/dd//text()')
    m.aliases = m.set_concat_value(", ", movie_aliases)

    movie_studio = tree.xpath('//p[@class="bioheading"][contains(text(),"Studio")]/following-sibling::p[@class="biodata"][1]//text()|//p[@class="bioheading"][contains(text(),"Distributor")]/following-sibling::p[@class="biodata"][1]//text()')
    m.studio = m.set_named_value("name",movie_studio)

    res = m.to_json()
    print(res)
    #log.debug(res)
    sys.exit(0)

frag = json.loads(sys.stdin.read())
#log.debug(json.dumps(frag))
mode = "performer"

if len(sys.argv)>1:
   if sys.argv[1] == "query":
        log.debug(f"searching for <{frag['name']}>")
        performer_query(frag['name'])
   if sys.argv[1] == "movie":
        mode = "movie"
   if sys.argv[1] == "scene":
        mode = "scene"

if not frag['url']:
    log.error('No URL entered.')
    sys.exit(1)

url = frag["url"]
log.debug(f"scraping {url}")
random.seed()
tree = scrape(url)

if mode == "movie":
    movie_from_tree(tree)

if mode == "scene":
    scene_from_tree(tree)

#by default performer scraper
performer_from_tree(tree)
