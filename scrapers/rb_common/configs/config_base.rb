# frozen_string_literal: true

class ConfigBase
  class << self
    def endpoint
      return nil unless self::USER_CONFIG[:endpoint]
      self::USER_CONFIG[:endpoint]
    end

    def api_key
      return nil unless self::USER_CONFIG[:api_key]
      self::USER_CONFIG[:api_key]
    end
  end
end
