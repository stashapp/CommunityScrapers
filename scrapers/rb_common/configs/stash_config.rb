# frozen_string_literal: true

require_relative "config_base"

module Config
  class Stash < ConfigBase
    # Tweak user settings below. An API Key can be generated in Stash's setting page
    # ( Settings > Security > Authentication )
    USER_CONFIG = {
      endpoint: "http://localhost:9999",
      api_key: ""
    }
  end
end
