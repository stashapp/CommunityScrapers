# frozen_string_literal: true

# Loading dependancies in a begin block so that we can give nice errors if they are missing
begin
  # Logger should always be the first dependancy we try to load so that we know
  # if we can depend on it when logging other errors.
  require_relative "../logger"
  require 'faraday'
rescue LoadError => error
  if error.message.match?(/logger$/)
    # If the logger isn't present, manually insert the level character when
    # logging (this is what the logger class from the file would have done for us)
    error_level_char = "\x01e\x02"
    STDERR.puts(error_level_char + "[GraphQL] Missing 'logger.rb' file in the rb_common folder.")
    exit
  end

  logger = Stash::Logger
  if error.message.match?(/faraday$/)
    logger.error("[GraphQL] Faraday gem is not installed, please install it with 'gem install faraday'")
  else
    logger.error("[GraphQL] Unexpected error #{error.class} encountered: #{error.message}")
  end
  exit
end

class GraphQLBase
  def query(query, variables = nil)
    headers = standard_api_headers.merge(@extra_headers)
    connection = Faraday.new(url: @url, headers: headers)
    response = connection.post do |request|
      body = { "query" => query }
      body["variables"] = variables if variables

      request.body = body.to_json
    end

    case response.status
    when 200
      result = JSON.parse(response.body)
      if result["error"]
        result["error"]["errors"].each do |error|
          logger.error("GraphQL error: #{error}")
          exit!
        end
      else
        result["data"]
      end
    when 401
      logger.error("[GraphQL] HTTP Error 401, Unauthorized. Make sure you have added an API Key in the 'config.rb' in the 'rb_common/configs' folder")
      return nil
    else
      logger.error("[GraphQL] Query failed: #{response.status} - #{response.body}")
      return nil
    end
  end

  private

  def logger
    Stash::Logger
  end

  def standard_api_headers
    {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "DNT": "1",
    }
  end
end
