
import json
import sys

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

class multiscrape:

    url="http://localhost:9999/graphql"
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "DNT": "1"
    }

    '''
    update the below config in the preferred order for each field.
    If there are no results for that performer and field it will use the results of the next scraper in the list and cache the results.'''
    config ={
        "gender": ['stash-sqlite'],
        "url" : ['Babepedia','stash-sqlite','FreeonesCommunity','Brazzers','Pornhub'],
        "twitter":['Babepedia','stash-sqlite'],
        "instagram": ['Babepedia'],
        "birthdate": ['IMBD','FreeonesCommunity','Babepedia','stash-sqlite'],
         "ethnicity":  ['Babepedia','stash-sqlite'],
         "country": ['Babepedia','stash-sqlite'],
         "eye_color": ['Babepedia','stash-sqlite'],
         "height":['Babepedia','Pornhub','stash-sqlite'],
         "measurements":['Babepedia','Pornhub','FreeonesCommunity','stash-sqlite'],
        "fake_tits":['Babepedia','stash-sqlite'],
        "career_length": ['Pornhub','Babepedia','stash-sqlite'],
        "tattoos":['Babepedia','stash-sqlite'],
        "piercings": ['Babepedia','stash-sqlite'],
        "aliases": ['Babepedia','stash-sqlite'],
        "tags": ['Babepedia'],
        "details": ['FreeonesCommunity','Babepedia','Brazzers'],
        "death_date": ['Babepedia'],
        "hair_color": ['Babepedia'],
        "weight":['Babepedia','FreeonesCommunity'],
        "image": ['performer-image-dir','Babepedia','FreeonesCommunity']
    }


    def __log(self,levelChar, s):
        if levelChar == "":
            return

        print(self.__prefix(levelChar) + s + "\n", file=sys.stderr, flush=True)

    def trace(self,s):
        self.__log(b't', s)

    def debug(self,s):
        self.__log(b'd', s)

    def info(self,s):
        self.__log(b'i', s)

    def warning(self,s):
        self.__log(b'w', s)

    def error(self,s):
        self.__log(b'e', s)



    def __callGraphQL(self, query, variables=None):
        json = {}
        json['query'] = query
        if variables != None:
            json['variables'] = variables

        # handle cookies
        response = requests.post(self.url, json=json, headers=self.headers)

        if response.status_code == 200:
            result = response.json()
            if result.get("error", None):
                for error in result["error"]["errors"]:
                    raise Exception("GraphQL error: {}".format(error))
            if result.get("data", None):
                return result.get("data")
        else:
            raise Exception(
                "GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(response.status_code, response.content, query, variables))


    def list_scrapers(self, type):
        query = """query listPerformerScrapers {
      listPerformerScrapers {
        id
        name
        performer{
          supported_scrapes
        }
      }
    }"""
        ret = []
        result = self.__callGraphQL(query)
        for r in result["listSceneScrapers"]:
            if type in r["scene"]["supported_scrapes"]:
                ret.append(r["id"])
        return ret

    def scrape_performer_list(self, scraper_id, performer):
        query = """query scrapePerformerList($scraper_id: ID!, $performer: String!) {
      scrapePerformerList(scraper_id: $scraper_id, query: $performer) {
        name
        url
        gender
        twitter
        instagram
        birthdate
        ethnicity
        country
        eye_color
        height
        measurements
        fake_tits
        career_length
        tattoos
        piercings
        aliases
        image
        }
    }"""

        variables = {'scraper_id': scraper_id, 'performer': performer}
        result = self.__callGraphQL(query, variables)
        if result is not None:
            return result["scrapePerformerList"]
        return None

    def scrape_performer(self, scraper_id, performer):
        query = """query scrapePerformer($scraper_id: ID!, $performer: ScrapedPerformerInput!) {
  scrapePerformer(scraper_id: $scraper_id, scraped_performer: $performer) {
    name
    url
    gender
    twitter
    instagram
    birthdate
    ethnicity
    country
    eye_color
    height
    measurements
    fake_tits
    career_length
    tattoos
    piercings
    aliases
    image
    }
}"""
        variables = {'scraper_id': scraper_id, 'performer': performer}
        result = self.__callGraphQL(query, variables)
        return result["scrapePerformer"]

    def requred_scrapers(self):
        scrapers=[]
        for key in self.config.keys():
            for s in self.config.get(key):
                if s not in scrapers:
                    scrapers.append(s)
        return scrapers


    def query_performers(self,name):
        ret=[]

        for scraper in self.requred_scrapers():
            print("Querying performers "+ scraper, file=sys.stderr)
            tmp=self.scrape_performer_list(scraper,name)
            if tmp is not None:
                for s in tmp:
                    found=False
                    for t in ret:
                        if s["name"]==t["name"]:
                            found=True
                    if not found:
                        ret.append(s)
        return ret

    def fetch_performer(self,name):
        ret={"name":name}

        scraper_cache={}

        for field in self.config.keys():
            found=False
            for s in self.config[field]:
                if s in scraper_cache.keys():
                    if field in scraper_cache[s]:
                        ret[field]=scraper_cache[s][field]
                        print("updating field from cache using scraper: " + s +" for field: " +field, file=sys.stderr)
                        found=True
                if s not in scraper_cache.keys() and not found:
                    print("Running scraper: " + s +" " +field, file=sys.stderr)
                    spl=self.scrape_performer_list(s, name)
                    if spl is not None:
                        for spli in spl:
                            if spli["name"].lower()==name.lower():
                                r=self.scrape_performer(s, {"name":spli["name"], "url":spli["url"]})
                                if r is not None:
                                    scraper_cache[s]=r
                                    found=True
                                    break;
                    if found:
                        print("Saving results from scraper: " +field + " " +s,file=sys.stderr)
                        if field in scraper_cache[s]:
                            ret[field]=scraper_cache[s][field]
                        else:
                            found=False
                    else:
                        scraper_cache[s]={}
        return ret



if sys.argv[1] == "query":
    fragment = json.loads(sys.stdin.read())
    print("input: " + json.dumps(fragment),file=sys.stderr)
    scraper=multiscrape()
    result = scraper.query_performers(fragment['name'])
    if not result:
        print(f"Could not determine details for performer: `{fragment['name']}`",file=sys.stderr)
        print("{}")
    else:
        print (json.dumps(result))

if sys.argv[1] == "fetch":
    fragment = json.loads(sys.stdin.read())
    print("input: " + json.dumps(fragment),file=sys.stderr)
    scraper=multiscrape()
    result = scraper.fetch_performer(fragment['name'])
    if not result:
        print(f"Could not determine details for performer: `{fragment['name']}`",file=sys.stderr)
        print("{}")
    else:
        True
        print (json.dumps(result))



if sys.argv[1] == "test":
    scraper=multiscrape()
    scrapers=scraper.requred_scrapers()
    print(scrapers)


