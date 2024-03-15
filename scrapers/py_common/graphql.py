import requests

import py_common.log as log
from py_common.config import get_config
from py_common.util import dig


config = get_config(
    default="""
# URL for your local Stash server
url = http://localhost:9999

# API key can be generated in Stash's settings page: `Settings > Security > Authentication`
api_key =
"""
)


# GraphQL introspection
#
# if a graphQL API changes, you can use this as the query string value to
# discover available API fields, queries, etc.
GRAPHQL_INTROSPECTION = """
    fragment FullType on __Type {
    kind
    name
    fields(includeDeprecated: true) {
        name
        args {
        ...InputValue
        }
        type {
        ...TypeRef
        }
        isDeprecated
        deprecationReason
    }
    inputFields {
        ...InputValue
    }
    interfaces {
        ...TypeRef
    }
    enumValues(includeDeprecated: true) {
        name
        isDeprecated
        deprecationReason
    }
    possibleTypes {
        ...TypeRef
    }
    }
    fragment InputValue on __InputValue {
    name
    type {
        ...TypeRef
    }
    defaultValue
    }
    fragment TypeRef on __Type {
    kind
    name
    ofType {
        kind
        name
        ofType {
        kind
        name
        ofType {
            kind
            name
            ofType {
            kind
            name
            ofType {
                kind
                name
                ofType {
                kind
                name
                ofType {
                    kind
                    name
                }
                }
            }
            }
        }
        }
    }
    }
    query IntrospectionQuery {
    __schema {
        queryType {
        name
        }
        mutationType {
        name
        }
        types {
        ...FullType
        }
        directives {
        name
        locations
        args {
            ...InputValue
        }
        }
    }
    }
"""


def callGraphQL(query: str, variables: dict | None = None):
    api_key = config.api_key
    url = config.url
    if not url:
        log.error("You need to set the URL in 'config.ini'")
        return None
    elif "stashdb.org" in url:
        log.error("You need to set the URL in 'config.ini' to your own stash server")
        return None

    stash_url = f"{url}/graphql"
    headers = {
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "DNT": "1",
        "ApiKey": api_key,
    }
    json = {"query": query}
    if variables:
        json["variables"] = variables  # type: ignore
    response = requests.post(stash_url, json=json, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if errors := result.get("error"):
            errors = "\n".join(errors)
            log.error(f"[GraphQL] {errors}")
        return result.get("data")
    elif response.status_code == 401:
        log.error(
            "[GraphQL] HTTP Error 401, Unauthorised. You can add a API Key in 'config.ini' in the 'py_common' folder"
        )
        return None
    elif response.status_code == 404:
        if "localhost:9999" in url:
            log.error(
                "[GraphQL] HTTP Error 404, Not Found. Your local stash server is your endpoint, but port 9999 did not respond. Did you change stash's port? Edit 'config.ini' in the 'py_common' folder to point at the correct port for stash!"
            )
        else:
            log.error(
                "[GraphQL] HTTP Error 404, Not Found. Make sure 'config.ini' in the 'py_common' folder points at the correct address and port!"
            )
        return None

    raise ConnectionError(
        f"[GraphQL] Query failed: {response.status_code} - {response.content}"
    )


def configuration() -> dict | None:
    query = """
    query Configuration {
        configuration {
            ...ConfigData
        }
    }
    fragment ConfigData on ConfigResult {
        general {
            ...ConfigGeneralData
        }
        interface {
            ...ConfigInterfaceData
        }
        dlna {
            ...ConfigDLNAData
        }
        scraping {
            ...ConfigScrapingData
        }
        defaults {
            ...ConfigDefaultSettingsData
        }
    }
    fragment ConfigGeneralData on ConfigGeneralResult {
        stashes {
            path
            excludeVideo
            excludeImage
        }
        databasePath
        generatedPath
        metadataPath
        cachePath
        calculateMD5
        videoFileNamingAlgorithm
        parallelTasks
        previewAudio
        previewSegments
        previewSegmentDuration
        previewExcludeStart
        previewExcludeEnd
        previewPreset
        maxTranscodeSize
        maxStreamingTranscodeSize
        writeImageThumbnails
        apiKey
        username
        password
        maxSessionAge
        logFile
        logOut
        logLevel
        logAccess
        createGalleriesFromFolders
        videoExtensions
        imageExtensions
        galleryExtensions
        excludes
        imageExcludes
        customPerformerImageLocation
        stashBoxes {
            name
            endpoint
            api_key
        }
    }
    fragment ConfigInterfaceData on ConfigInterfaceResult {
        menuItems
        soundOnPreview
        wallShowTitle
        wallPlayback
        maximumLoopDuration
        noBrowser
        autostartVideo
        autostartVideoOnPlaySelected
        continuePlaylistDefault
        showStudioAsText
        css
        cssEnabled
        language
        imageLightbox {
            slideshowDelay
            displayMode
            scaleUp
            resetZoomOnNav
            scrollMode
            scrollAttemptsBeforeChange
        }
        disableDropdownCreate {
            performer
            tag
            studio
        }
        handyKey
        funscriptOffset
    }
    fragment ConfigDLNAData on ConfigDLNAResult {
        serverName
        enabled
        whitelistedIPs
        interfaces
    }
    fragment ConfigScrapingData on ConfigScrapingResult {
        scraperUserAgent
        scraperCertCheck
        scraperCDPPath
        excludeTagPatterns
    }
    fragment ConfigDefaultSettingsData on ConfigDefaultSettingsResult {
        scan {
            scanGeneratePreviews
            scanGenerateImagePreviews
            scanGenerateSprites
            scanGeneratePhashes
            scanGenerateThumbnails
        }
        identify {
            sources {
                source {
                    ...ScraperSourceData
                }
                options {
                    ...IdentifyMetadataOptionsData
                }
            }
            options {
                ...IdentifyMetadataOptionsData
            }
        }
        autoTag {
            performers
            studios
            tags
            __typename
        }
        generate {
            sprites
            previews
            imagePreviews
            previewOptions {
                previewSegments
                previewSegmentDuration
                previewExcludeStart
                previewExcludeEnd
                previewPreset
            }
            markers
            markerImagePreviews
            markerScreenshots
            transcodes
            phashes
        }
        deleteFile
        deleteGenerated
    }
    fragment ScraperSourceData on ScraperSource {
        stash_box_endpoint
        scraper_id
    }
    fragment IdentifyMetadataOptionsData on IdentifyMetadataOptions {
        fieldOptions {
            ...IdentifyFieldOptionsData
        }
        setCoverImage
        setOrganized
        includeMalePerformers
    }
    fragment IdentifyFieldOptionsData on IdentifyFieldOptions {
        field
        strategy
        createMissing
    }
    """
    result = callGraphQL(query) or {}
    return dig(result, "configuration")


def getScene(scene_id: str | int) -> dict | None:
    query = """
    query FindScene($id: ID!, $checksum: String) {
        findScene(id: $id, checksum: $checksum) {
            ...SceneData
        }
    }
    fragment SceneData on Scene {
        id
        title
        code
        details
        urls
        date
        rating100
        o_counter
        organized
        interactive
        files {
            path
            size
            duration
            video_codec
            audio_codec
            width
            height
            frame_rate
            bit_rate
        }
        paths {
            screenshot
            preview
            stream
            webp
            vtt
            sprite
            funscript
        }
        scene_markers {
            ...SceneMarkerData
        }
        galleries {
            ...SlimGalleryData
        }
        studio {
            ...SlimStudioData
        }
        movies {
            movie {
                ...MovieData
            }
            scene_index
        }
        tags {
            ...SlimTagData
        }
        performers {
            ...PerformerData
        }
        stash_ids {
            endpoint
            stash_id
        }
    }
    fragment SceneMarkerData on SceneMarker {
        id
        title
        seconds
        stream
        preview
        screenshot
        scene {
            id
        }
        primary_tag {
            id
            name
            aliases
        }
        tags {
            id
            name
            aliases
        }
    }
    fragment SlimGalleryData on Gallery {
        id
        title
        code
        date
        urls
        details
        photographer
        rating100
        organized
        image_count
        cover {
            paths {
                thumbnail
            }
        }
        studio {
            id
            name
            image_path
        }
        tags {
            id
            name
        }
        performers {
            id
            name
            gender
            favorite
            image_path
        }
        scenes {
            id
            title
            files {
                path
                basename
            }
        }
    }
    fragment SlimStudioData on Studio {
        id
        name
        image_path
        stash_ids {
            endpoint
            stash_id
        }
        parent_studio {
            id
        }
        details
        rating100
        aliases
    }
    fragment MovieData on Movie {
        id
        name
        aliases
        duration
        date
        rating100
        director
        studio {
            ...SlimStudioData
        }
        synopsis
        url
        front_image_path
        back_image_path
        scene_count
        scenes {
            id
            title
            files {
                path
            }
        }
    }
    fragment SlimTagData on Tag {
        id
        name
        aliases
        image_path
    }
    fragment PerformerData on Performer {
        id
        name
        url
        gender
        twitter
        instagram
        birthdate
        ethnicity
        country
        eye_color
        height_cm
        measurements
        fake_tits
        career_length
        tattoos
        piercings
        alias_list
        favorite
        image_path
        scene_count
        image_count
        gallery_count
        movie_count
        tags {
            ...SlimTagData
        }
        stash_ids {
            stash_id
            endpoint
        }
        rating100
        details
        death_date
        hair_color
        weight
    }
    """
    variables = {"id": str(scene_id)}
    result = callGraphQL(query, variables) or {}
    return dig(result, "findScene")


def getSceneScreenshot(scene_id: str | int) -> str | None:
    query = """
    query FindScene($id: ID!, $checksum: String) {
        findScene(id: $id, checksum: $checksum) {
        id
        paths {
            screenshot
            }
        }
    }
    """
    variables = {"id": str(scene_id)}
    result = callGraphQL(query, variables) or {}
    return dig(result, "findScene", "paths", "screenshot")


def getSceneByPerformerId(performer_id: str | int) -> dict | None:
    query = """
query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType, $scene_ids: [Int!]) {
          findScenes(filter: $filter, scene_filter: $scene_filter, scene_ids: $scene_ids) {
            count
            filesize
            duration
            scenes {
              ...SceneData
              __typename
            }
            __typename
          }
        }
        
        fragment SceneData on Scene {
          id
          title
          details
          urls
          date
          rating100
          o_counter
          organized
          files {
              path
              size
              duration
              video_codec
              audio_codec
              width
              height
              frame_rate
              bit_rate
              __typename
          }
          interactive
          interactive_speed
          captions {
            language_code
            caption_type
            __typename
          }
          created_at
          updated_at
          paths {
            screenshot
            preview
            stream
            webp
            vtt
            sprite
            funscript
            interactive_heatmap
            caption
            __typename
          }
          scene_markers {
            ...SceneMarkerData
            __typename
          }
          galleries {
            ...SlimGalleryData
            __typename
          }
          studio {
            ...SlimStudioData
            __typename
          }
          movies {
            movie {
              ...MovieData
              __typename
            }
            scene_index
            __typename
          }
          tags {
            ...SlimTagData
            __typename
          }
          performers {
            ...PerformerData
            __typename
          }
          stash_ids {
            endpoint
            stash_id
            __typename
          }
          sceneStreams {
            url
            mime_type
            label
            __typename
          }
          __typename
        }
        
        fragment SceneMarkerData on SceneMarker {
          id
          title
          seconds
          stream
          preview
          screenshot
          scene {
            id
            __typename
          }
          primary_tag {
            id
            name
            aliases
            __typename
          }
          tags {
            id
            name
            aliases
            __typename
          }
          __typename
        }
        
        fragment SlimGalleryData on Gallery {
          id
          title
          code
          date
          urls
          details
          photographer
          rating100
          organized
          image_count
          cover {
            paths {
              thumbnail
              __typename
            }
            __typename
          }
          studio {
            id
            name
            image_path
            __typename
          }
          tags {
            id
            name
            __typename
          }
          performers {
            id
            name
            gender
            favorite
            image_path
            __typename
          }
          scenes {
            id
            title
            files {
                path
            }
            __typename
          }
          __typename
        }
        
        fragment SlimStudioData on Studio {
          id
          name
          image_path
          stash_ids {
            endpoint
            stash_id
            __typename
          }
          parent_studio {
            id
            __typename
          }
          details
          rating100
          aliases
          __typename
        }
        
        fragment MovieData on Movie {
          id
          name
          aliases
          duration
          date
          rating100
          director
          studio {
            ...SlimStudioData
            __typename
          }
          synopsis
          url
          front_image_path
          back_image_path
          scene_count
          scenes {
            id
            title
            files {
              path
            }
            __typename
          }
          __typename
        }
        
        fragment SlimTagData on Tag {
          id
          name
          aliases
          image_path
          __typename
        }
        
        fragment PerformerData on Performer {
          id
          name
          url
          gender
          twitter
          instagram
          birthdate
          ethnicity
          country
          eye_color
          height_cm
          measurements
          fake_tits
          career_length
          tattoos
          piercings
          alias_list
          favorite
          ignore_auto_tag
          image_path
          scene_count
          image_count
          gallery_count
          movie_count
          tags {
            ...SlimTagData
            __typename
          }
          stash_ids {
            stash_id
            endpoint
            __typename
          }
          rating100
          details
          death_date
          hair_color
          weight
          __typename
        }
    """
    variables = {
        "filter": {"page": 1, "per_page": 20, "sort": "title", "direction": "ASC"},
        "scene_filter": {
            "performers": {"value": [str(performer_id)], "modifier": "INCLUDES_ALL"}
        },
    }
    result = callGraphQL(query, variables) or {}
    return dig(result, "findScenes")


def getSceneIdByPerformerId(performer_id: str | int) -> dict | None:
    query = """
        query FindScenes($filter: FindFilterType, $scene_filter: SceneFilterType, $scene_ids: [Int!]) {
          findScenes(filter: $filter, scene_filter: $scene_filter, scene_ids: $scene_ids) {
            scenes {
                id
                title
                files {
                    path
                }
                paths {
                    screenshot
                    }
                }
          }
        }
    """
    variables = {
        "filter": {"page": 1, "per_page": 20, "sort": "id", "direction": "DESC"},
        "scene_filter": {
            "performers": {"value": [str(performer_id)], "modifier": "INCLUDES_ALL"}
        },
    }
    result = callGraphQL(query, variables) or {}
    return dig(result, "findScenes")


def getPerformersByName(performer_name: str) -> dict | None:
    query = """
        query FindPerformers($filter: FindFilterType, $performer_filter: PerformerFilterType) {
          findPerformers(filter: $filter, performer_filter: $performer_filter) {
            count
            performers {
              ...PerformerData
              __typename
            }
            __typename
          }
        }
        
        fragment PerformerData on Performer {
          id
          name
          url
          gender
          twitter
          instagram
          birthdate
          ethnicity
          country
          eye_color
          height_cm
          measurements
          fake_tits
          career_length
          tattoos
          piercings
          alias_list
          favorite
          ignore_auto_tag
          image_path
          scene_count
          image_count
          gallery_count
          movie_count
          tags {
            ...SlimTagData
            __typename
          }
          stash_ids {
            stash_id
            endpoint
            __typename
          }
          rating100
          details
          death_date
          hair_color
          weight
          __typename
        }
        
        fragment SlimTagData on Tag {
          id
          name
          aliases
          image_path
          __typename
        }
    """

    variables = {
        "filter": {
            "q": performer_name,
            "page": 1,
            "per_page": 20,
            "sort": "name",
            "direction": "ASC",
        },
        "performer_filter": {},
    }
    result = callGraphQL(query, variables) or {}
    return dig(result, "findPerformers")


def getPerformersIdByName(performer_name: str) -> dict | None:
    query = """
        query FindPerformers($filter: FindFilterType, $performer_filter: PerformerFilterType) {
          findPerformers(filter: $filter, performer_filter: $performer_filter) {
            count
            performers {
              ...PerformerData
            }
          }
        }
        
        fragment PerformerData on Performer {
          id
          name
          alias_list
          }
    """

    variables = {
        "filter": {
            "q": performer_name,
            "page": 1,
            "per_page": 20,
            "sort": "name",
            "direction": "ASC",
        },
        "performer_filter": {},
    }

    result = callGraphQL(query, variables) or {}
    return dig(result, "findPerformers")


def getGallery(gallery_id: str | int) -> dict | None:
    query = """
    query FindGallery($id: ID!) {
        findGallery(id: $id) {
            ...GalleryData
        }
    }
    fragment GalleryData on Gallery {
        id
        created_at
        updated_at
        title
        code
        date
        urls
        details
        photographer
        rating100
        organized
        folder {
            path
        }
        cover {
            ...SlimImageData
        }
        studio {
            ...SlimStudioData
        }
        tags {
            ...SlimTagData
        }
        performers {
            ...PerformerData
        }
        scenes {
            ...SlimSceneData
        }
    }
    fragment SlimImageData on Image {
        id
        title
        rating100
        organized
        o_counter
        visual_files {
            ... on ImageFile {
                path
                size
                height
                width
            }
        }

        paths {
            thumbnail
            image
            }

        galleries {
            id
            files {
                path
            }
            title
            }

        studio {
            id
            name
            image_path
            }

        tags {
            id
            name
            }

        performers {
            id
            name
            gender
            favorite
            image_path
            }
    }
    fragment SlimStudioData on Studio {
        id
        name
        image_path
        stash_ids {
        endpoint
        stash_id
        }
        parent_studio {
            id
        }
        details
        rating100
        aliases
    }
    fragment SlimTagData on Tag {
        id
        name
        aliases
        image_path
        }
    fragment PerformerData on Performer {
        id
        name
        url
        gender
        twitter
        instagram
        birthdate
        ethnicity
        country
        eye_color
        height_cm
        measurements
        fake_tits
        career_length
        tattoos
        piercings
        alias_list
        favorite
        image_path
        scene_count
        image_count
        gallery_count
        movie_count

        tags {
        ...SlimTagData
        }

        stash_ids {
        stash_id
        endpoint
        }
        rating100
        details
        death_date
        hair_color
        weight
    }
    fragment SlimSceneData on Scene {
        id
        title
        code
        details
        urls
        date
        rating100
        o_counter
        organized
        interactive

        files {
            path
            size
            duration
            video_codec
            audio_codec
            width
            height
            frame_rate
            bit_rate
        }

        paths {
            screenshot
            preview
            stream
            webp
            vtt
            sprite
            funscript
        }

        scene_markers {
            id
            title
            seconds
            }

        galleries {
            id
            title
            files {
                path
            }
        }

        studio {
            id
            name
            image_path
        }

        movies {
            movie {
            id
            name
            front_image_path
            }
            scene_index
        }

        tags {
            id
            name
            }

        performers {
            id
            name
            gender
            favorite
            image_path
        }

        stash_ids {
            endpoint
            stash_id
        }
    }
    """
    variables = {"id": gallery_id}
    result = callGraphQL(query, variables) or {}
    return dig(result, "findGallery")


def getGalleryPath(gallery_id: str | int) -> str | None:
    query = """
    query FindGallery($id: ID!) {
        findGallery(id: $id) {
            folder {
                path
            }
            files {
                path
            }
        }
    }
        """
    variables = {"id": gallery_id}
    result = callGraphQL(query, variables) or {}
    # Galleries can either be a folder full of files or a zip file
    return dig(result, "findGallery", "folder", "path") \
        or dig(result, "findGallery", "files", 0, "path")
