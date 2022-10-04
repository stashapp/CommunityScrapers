# frozen_string_literal: true

require_relative "config_base"

module Config
  class StashDB < ConfigBase
    # Tweak user settings below. An API Key can be generated in StashDB's user page
    USER_CONFIG = {
      endpoint: "https://stashdb.org/graphql",
      api_key: ""
    }
  end
end
