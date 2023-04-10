import re, sys, copy, json

# local modules
try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file=sys.stderr)
    sys.exit()

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

def parse_response(json_input):
  if isinstance(json_input, dict):
    for key, value in json_input.items():
      if isinstance(value, dict):
        json_input[key] = transform_type(value)
        parse_response(json_input[key])
      else:
        parse_response(value)
  elif isinstance(json_input, list):
      for item in json_input:
          parse_response(item)


def transform_type(value):
  if value.get("__typename") == "Media":
    if value.get("isS3") == True:
      return f'https://cdn.traxxx.me/{value.get("path")}'
    if value.get("isS3") == False:
      return f'https://traxxx.me/media/{value.get("path")}'
  return value


class TraxxxInterface:
  port = ""
  url = ""
  headers = {
    "Content-Type": "application/json",
    "User-Agent": "stash/1.0.0"
  }
  cookies = {}

  def __init__(self, fragments={}):
    scheme = "https"
    domain = 'www.traxxx.me'

    if self.port:
      domain = f'{domain}:{self.port}'

    # Stash GraphQL endpoint
    self.url = f'{scheme}://{domain}/graphql'
    log.debug(f"Using GraphQl endpoint at {self.url}")

    self.fragments = fragments
    self.fragments.update(traxxx_gql_fragments)

  def __resolveFragments(self, query):
    fragmentReferences = list(set(re.findall(r'(?<=\.\.\.)\w+', query)))
    fragments = []
    for ref in fragmentReferences:
      fragments.append({
        "fragment": ref,
        "defined": bool(re.search("fragment {}".format(ref), query))
      })

    if all([f["defined"] for f in fragments]):
      return query
    else:
      for fragment in [f["fragment"] for f in fragments if not f["defined"]]:
        if fragment not in self.fragments:
          raise Exception(f'GraphQL error: fragment "{fragment}" not defined')
        query += self.fragments[fragment]
      return self.__resolveFragments(query)

  def __callGraphQL(self, query, variables=None):
    query = self.__resolveFragments(query)

    json_request = {'query': query}
    if variables is not None:
      json_request['variables'] = variables

    response = requests.post(self.url, json=json_request, headers=self.headers, cookies=self.cookies)
    
    if response.status_code == 200:
      result = response.json()
      if result.get("errors"):
        for error in result["errors"]:
          log.error(f"GraphQL error: {error}")
      if result.get("error"):
        for error in result["error"]["errors"]:
          log.error(f"GraphQL error: {error}")
      if result.get("data"):
        data = result['data']
        parse_response(data)
        return data
    elif response.status_code == 401:
      sys.exit("HTTP Error 401, Unauthorized. Cookie authentication most likely failed")
    else:
      raise ConnectionError(
        "GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(
          response.status_code, response.content, query, variables)
      )

  def search_scenes(self, search, numResults=20):
    query = """
      query SearchReleases(
        $query: String!
        $limit: Int = 20
      ) {
        scenes: searchReleases(
          query: $query
          first: $limit
          orderBy: RANK_DESC
          filter: {
            rank: {
              greaterThan: 0.045
            }
          }
        ) {
          release {
            ...traxScene
          }
          rank
        }
      }
    """

    variables = {
      'query': search,
      'limit': int(numResults)
    }
    result = self.__callGraphQL(query, variables)
    log.info(f'scene search "{search}" returned {len(result["scenes"])} results')

    return [s["release"] for s in result["scenes"]]

  def search_performers(self, search, numResults=20):
    query = """
      query SearchActors(
        $query: String!
        $limit: Int = 20
      ) {
        actors: searchActors(
          query: $query
          first: $limit
        ) {
          ...traxActor
        }
      }
    """

    variables = {
      'query': search,
      'limit': int(numResults)
    }

    results = self.__callGraphQL(query, variables).get("actors")
    log.info(f'performer search "{search}" returned {len(results)} results')
    return [p for p in results]

  # shootID refers to a media sources uniqueID e.x. a LegalPorno shootID might be "GIO0001"
  def get_scene_by_shootID(self, shootId):
    query = """
      query Releases(
        $idList: [String!]
      ){ releases( filter: {shootId: { in:$idList } }
        ){
          ...traxScene
        }
      }
    """

    variables = {'idList': [shootId]}

    response = self.__callGraphQL(query, variables).get("releases")

    log.info(f'scene shootID lookup "{shootId}" returned {len(response)} results')

    if len(response) > 0:
      return response[0]
    else:
      return None

  def get_scene(self, traxxx_scene_id):
    query = """
      query Releases(
        $sceneId: Int!
      ) {
        releases(
          filter:{id:{equalTo:$sceneId}}
        ) {
          ...traxScene
        }
      }
    """

    variables = {'sceneId': int(traxxx_scene_id)}

    response = self.__callGraphQL(query, variables).get("releases")

    log.info(f'scene traxxxID lookup "{traxxx_scene_id}" returned {len(response)} results')

    if len(response) > 0:
      return response[0]
    else:
      return None

  def get_performer(self, traxxx_performer_id):
    query = """
      query Actors(
        $actorId: Int!
      ) {
       actors: actors(
            filter:{id:{equalTo:$actorId}}
          ) {
            ...traxActor
          }
        }
    """

    variables = {'actorId': int(traxxx_performer_id)}

    response = self.__callGraphQL(query, variables).get("actors")

    log.info(f'performer traxxxID lookup "{traxxx_performer_id}" returned {len(response)} results')

    if len(response) > 0:
      return response[0]
    else:
      return None

  def parse_to_stash_scene_search(self, s):
    fragment = {}

    if s.get("poster"):
      if s["poster"].get("image"):
        fragment["image"] = s["poster"]["image"]

    # search returns url as traxxx url for later parsing by scene parser
    if s.get("slug"):
      fragment["url"] = f'https://traxxx.me/scene/{s["id"]}/{s["slug"]}/'

    if s.get("shootId"):
      fragment["code"] = s["shootId"]

    if s.get("date"):
      fragment["date"] = s["date"].split("T")[0]

    if s.get("title"):
      fragment["title"] = s["title"]

    if s.get("entity"):
        if s["entity"].get("name"):
          fragment["studio"] = { "name": s["entity"]["name"] }

    if s.get("description"):
      fragment["details"] = s["description"]

    # #tags take too much space in the results page
    #if s.get("tags"):
    #  fragment["tags"] = [{"name": t["tag"]["name"]} for t in s.get("tags",{}) if t["tag"] and t["tag"].get("name")]
    
    if s.get("actors"):
      fragment["performers"] = [{"name": a["actor"]["name"]} for a in s["actors"] if a["actor"] and a["actor"].get("name")]
    
    return fragment

  def parse_to_stash_scene(self, s):
    fragment = {}

    if s.get("shootId"):
      fragment["code"] = s["shootId"]

    if s.get("title"):
      fragment["title"] = s["title"]

    if s.get("description"):
      fragment["details"] = s["description"]

    if s.get("url"):
      fragment["url"] = s.get("url")

    if s.get("date"):
      fragment["date"] = s["date"].split("T")[0]

    if s.get("poster"):
      if s["poster"].get("image"):
        fragment["image"] = s["poster"]["image"]


    if s.get("tags"):
      fragment["tags"] = [{"name": t["tag"]["name"]} for t in s.get("tags",{}) if t["tag"] and t["tag"].get("name")]
    
    if s.get("actors"):
      fragment["performers"] = [{"name": a["actor"]["name"]} for a in s["actors"] if a["actor"] and a["actor"].get("name")]
    
    if s.get("movies"):
      movies = []
      for m in s["movies"]:
        m = m["movie"]

        if m.get("title"):
          movie = {
            "name": m["title"]
          }
          if m.get["date"]:
            movie["date"] = m["date"]
          if m.get("url"):
            movie["url"] = m["url"]
          if m.get("description"):
            movie["synopsis"] = m["description"]

          if m.get["covers"]:
            if len(m.covers) >= 1:
              movie["frontImage"] = m["covers"][0]
            if len(m.covers) >= 2:
              movie["backImage"] = m["covers"][1]

          movies.append(movie)
      fragment["movies"] = movies

    if s.get("entity"):
      if s["entity"].get("name"):
        studio = {'name':s["entity"]["name"]}
        if s["entity"].get("url"):
          studio['url'] = s["entity"]["url"]
        fragment["studio"] = studio

    return fragment

  def parse_to_stash_performer_search(self, p):
    fragment = {}

    if p.get("name"):
      fragment["name"] = p["name"]

    if p.get("slug"):
      fragment["url"] = f'https://traxxx.me/actor/{p["id"]}/{p["slug"]}/'

    fragment["images"] = []

    if p.get("image"):
      fragment["images"].append( p["image"] )

    for profile in p["profiles"]:
      if profile.get("image"):
        fragment["images"].append( profile["image"] )

    return fragment

  def parse_to_stash_performer(self, p):
    fragment = {}

    if p.get("name"):
      fragment["name"] = p["name"]

    if p.get("slug"):
      fragment["url"] = f'https://traxxx.me/actor/{p["id"]}/{p["slug"]}/'

    if p.get("gender"):
      fragment["gender"] = p["gender"]

    if p.get("birthdate"):
      fragment["birthdate"] = p["birthdate"]

    if p.get("dateOfDeath"):
      fragment["death_date"] = p["dateOfDeath"]

    if p.get("eyes"):
      fragment["eye_color"] = p["eyes"]

    if p.get("hairColor"):
      fragment["hair_color"] = p["hairColor"]

    if p.get("heightMetric"):
      fragment["height"] = p["heightMetric"]

    if p.get("weightMetric"):
      fragment["weight"] = p["weightMetric"]

    if p.get("tattoos"):
      fragment["tattoos"] = p["tattoos"]

    if p.get("piercings"):
      fragment["piercings"] = p["piercings"]

    if p["naturalBoobs"] == False:
      fragment["fake_tits"] = "Augmented"
    if p["naturalBoobs"] == True:
      fragment["fake_tits"] = "Natural"

    if all( k in p for k in ['cup','bust','waist','hip'] ):
      fragment['measurements'] = f"{p['bust']}{p['cup']}-{p['waist']}-{p['hip']}"

    if p.get("ethnicity"):
      fragment["ethnicity"] = p["ethnicity"]

    if p.get("birthCountry"):
        if p["birthCountry"].get("alpha2"):
          country = p["birthCountry"]["alpha2"]
          fragment["country"] = country

    fragment["images"] = []

    if p.get("image"):
      fragment["images"].append( p["image"] )

    for profile in p["profiles"]:
      if profile.get("image"):
        fragment["images"].append( profile["image"] )

    # descriptions = []
    # for profile in p["profiles"]:
    #   if profile.get("description"):
    #      if profile.get("entity"):
    #          if profile["entity"].get("name"):
    #             descriptions.append(f'{profile["entity"]["name"]}:\n{profile["description"]}')

    # if descriptions != []:
    #   fragment["description"] = "\n\n".join(descriptions)

    if p.get("aliasFor"):
      # TODO: when traxxx has any performers with an alias
      # fragment["aliases"]
      pass

    if p.get("socials"):
      # TODO: when traxxx has more data to work with
      # fragment["twitter"]
      # fragment["instagram"]
      pass

    #  TODO: implement this if traxxx ever adds career data to performers
    # if p.get("careerLength")
    #   fragment["career_length"] = p["careerLength"]

    return fragment

traxxx_gql_fragments = {
    "traxActorMin": """
      fragment traxActorMin on Actor {
        id
        slug
        name
        gender
        aliasFor: actorByAliasFor {
          id
          name
          slug
        }
      }
    """,
    "traxActor":"""
      fragment traxActor on Actor {
        id
        slug
        name
        gender
        dateOfBirth
        dateOfDeath
        ethnicity
        cup
        bust
        waist
        hip
        naturalBoobs
        heightMetric: height(units:METRIC)
        weightMetric: weight(units:METRIC)
        hairColor
        eyes
        hasTattoos
        tattoos
        hasPiercings
        piercings
        socials: actorsSocials {
            id
            url
            platform
        }
        description
        aliasFor: actorByAliasFor {
          id
          name
          slug
        }
        entity { ...traxEntity }
        image: avatarMedia {
          ...traxMedia
        }
        birthCountry: countryByBirthCountryAlpha2 {
          alpha2
          name
          alias
        }
        profiles: actorsProfiles(orderBy: PRIORITY_DESC) {
          ...traxActorProfile
        }
      }
    """,
    "traxActorProfile":"""
        fragment traxActorProfile on ActorsProfile {
          image: avatarMedia { ...traxMedia }
          description
          entity { ...traxEntity }
        }
    """,
    "traxScene":"""
      fragment traxScene on Release{
        id
        title
        date
        datePrecision
        slug
        shootId
        productionDate
        comment
        createdAt
        url
        actors: releasesActors(filter:{actor:{gender:{distinctFrom:"male"}}}) {
          actor {...traxActorMin}
        }
        tags: releasesTags(orderBy: TAG_BY_TAG_ID__PRIORITY_DESC) {
          tag {
            name
            priority
            __typename
          }
        }
        chapters: chapters(orderBy: CHAPTERS_POSTER_BY_CHAPTER_ID__CHAPTER_ID_DESC){
          title
          description
          duration
          time
          tags: chaptersTags{ tag { id, name, slug } }
          __typename
        }
        poster: releasesPoster {
          image: media{ ...traxMedia }
        }
        covers: releasesCovers(orderBy: MEDIA_BY_MEDIA_ID__INDEX_ASC) {
          image: media{ ...traxMedia }
        }
        photos: releasesPhotos(orderBy: MEDIA_BY_MEDIA_ID__INDEX_ASC) {
          image: media{ ...traxMedia }
        }
        isNew
        isFavorited
        entity { ...traxEntity }
        studio {
          id
          name
          slug
          url
          __typename
        }
        movies: moviesScenesBySceneId {
          movie {
            id
            title
            slug
            url
            description
            date
            datePrecision
            covers: moviesCovers(orderBy: MEDIA_BY_MEDIA_ID__INDEX_DESC) {
              media {
                ...traxMedia
              }
            }
            __typename
        }
        __typename
      }
      }
    """,
    "traxMedia":"""
      fragment traxMedia on Media {
            id
            index
            path
            thumbnail
            width
            height
            thumbnailWidth
            thumbnailHeight
            lazy
            isS3
            comment
            __typename
      }
    """,
    "traxEntity":"""
      fragment traxEntity on Entity {
          id
          name
          slug
          url
          type
          independent
          parent {
            id
            slug
            url
            type
            __typename
          }
          __typename
      }
    """,
}
