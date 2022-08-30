# frozen_string_literal: true

# Loading dependancies in a begin block so that we can give nice errors if they are missing
begin
  require_relative "graphql_base"
  require_relative "../configs/stash_config"
rescue LoadError => error
  logger = Stash::Logger
  if error.message.match?(/graphql_base$/)
    logger.error("[GraphQL] Missing 'graphql/graphql_base.rb' file in the rb_common folder.")
  elsif error.message.match?(/configs\/stash_config$/)
    logger.error("[GraphQL] Missing 'configs/stash_config.rb' file in the rb_common folder.")
  else
    logger.error("[GraphQL] Unexpected error #{error.class} encountered: #{error.message}")
  end
  exit
end

module GraphQL
  class Stash < GraphQLBase
    def initialize(referer: nil)
      @api_key = Config::Stash.api_key
      @url = Config::Stash.endpoint + "/graphql"
      @extra_headers = { "ApiKey": @api_key }
      @extra_headers["Referer"] = referer if referer
    end

    def configuration
      query(configuration_query)["configuration"]
    end

    def get_scene(scene_id)
      response = query(find_scene_query, id_variables(scene_id))["findScene"]
    end

    def get_gallery(gallery_id)
      query(find_gallery_query, id_variables(gallery_id))["findGallery"]
    end

    def get_gallery_path(gallery_id)
      query(gallery_path_query, id_variables(gallery_id))["findGallery"]
    end

    private

    def id_variables(id)
      variables = {
          "id": id
      }
    end

    def configuration_query
      <<-'GRAPHQL'
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
            trustedProxies
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
            scraperUserAgent
            scraperCertCheck
            scraperCDPPath
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
            slideshowDelay
            disabledDropdownCreate {
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
                useFileMetadata
                stripFileExtension
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
            stash_box_index
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
      GRAPHQL
    end

    def find_scene_query
      <<-'GRAPHQL'
        query FindScene($id: ID!, $checksum: String) {
            findScene(id: $id, checksum: $checksum) {
                ...SceneData
            }
        }
        fragment SceneData on Scene {
            id
            checksum
            oshash
            title
            details
            url
            date
            rating
            o_counter
            organized
            path
            phash
            interactive
            file {
                size
                duration
                video_codec
                audio_codec
                width
                height
                framerate
                bitrate
            }
            paths {
                screenshot
                preview
                stream
                webp
                vtt
                chapters_vtt
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
            checksum
            path
            title
            date
            url
            details
            rating
            organized
            image_count
            cover {
                file {
                    size
                    width
                    height
                }
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
                path
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
            rating
            aliases
        }
        fragment MovieData on Movie {
            id
            checksum
            name
            aliases
            duration
            date
            rating
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
                path
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
            checksum
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
            rating
            details
            death_date
            hair_color
            weight
        }
      GRAPHQL
    end

    def find_gallery_query
      <<-'GRAPHQL'
        query FindGallery($id: ID!) {
            findGallery(id: $id) {
                ...GalleryData
            }
        }
        fragment GalleryData on Gallery {
            id
            checksum
            path
            created_at
            updated_at
            title
            date
            url
            details
            rating
            organized
            images {
                ...SlimImageData
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
            checksum
            title
            rating
            organized
            o_counter
            path

            file {
                size
                width
                height
                }

            paths {
                thumbnail
                image
                }

            galleries {
                id
                path
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
            rating
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
            checksum
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
            rating
            details
            death_date
            hair_color
            weight
        }
        fragment SlimSceneData on Scene {
            id
            checksum
            oshash
            title
            details
            url
            date
            rating
            o_counter
            organized
            path
            phash
            interactive

            file {
                size
                duration
                video_codec
                audio_codec
                width
                height
                framerate
                bitrate
            }

            paths {
                screenshot
                preview
                stream
                webp
                vtt
                chapters_vtt
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
                path
                title
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
      GRAPHQL
    end

    def gallery_path_query
      <<-'GRAPHQL'
        query FindGallery($id: ID!) {
            findGallery(id: $id) {
                path
            }
        }
      GRAPHQL
    end
  end
end
