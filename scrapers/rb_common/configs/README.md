# Common Configs

## Adding your settings to an existing config

Various ruby scrapers will use these configs so that each one doesn't separately need to ask for your api keys and endpoints. For example if you want to configure your stash instance you can open the `stash_config.rb` with any text editor and in the relevant attributes in the `initialize` method to add your details. For example you might change:

```Ruby
def initialize
  @endpoint = "http://localhost:9999"
  @api_key = ""
end
```

to (made up endpoint and key for example):

```Ruby
def initialize
  @endpoint = "http://192.168.0.99:6969"
  @api_key = "thisIsAFakeAPIKeyTheRealOneIsMuchLonger"
end
```

## Calling these configs in your scraper

Calling them in your scraper is as simple as requiring the config file either directly with something like `require_relative "rb_common/configs/stash_config"` or generally by requiring all the common interfaces with something like `require_relative "rb_common/rb_common"`.

Once required your scrupt can access them via calls by initializing an instance of the config and calling for the attribute like:

```Ruby
stash_config = Config::Stash.new
stash_config.api_key
stash_config.endpoint
```

## Creating a new config

If you are looking to create a new common configuration for use with your scrapers here are the important things to know about the implimentation.

You will first need to require and inherit from the base config. The existing configs have been namespaced under `Config::`, this is not mantority but it is suggested for consistency. You can see this in the other configs with:

```Ruby
require_relative "config_base"

module Config
  class Stash < ConfigBase
```

Inheriting from `ConfigBase` will add reader and writer methods for `endpoint` and `api_key` to an instance of your class. It is suggested that you definte an initialize method that sets the defaults for these attributes. If no defaults are defined in your class they will return nil when called. You are free to ad more than the default two attributes to your class, but you will need to define their accessor methods on your child class.
