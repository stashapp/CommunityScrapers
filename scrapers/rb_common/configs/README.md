# Common Configs

## Adding your settings to an existing config

Various ruby scrapers will use these configs so that each one doesn't separately need to ask for your api keys and endpoints. For example if you want to configure your stash instance you can open the `stash_config.rb` with any text editor and in the `USER_CONFIG`, add your details. For example you might change:

```Ruby
USER_CONFIG = {
    endpoint: "http://localhost:9999",
    api_key: ""
}
```

to (made up endpoint and key for example):

```Ruby
USER_CONFIG = {
    endpoint: "http://192.168.0.99:6969",
    api_key: "thisIsAFakeAPIKeyTheRealOneIsMuchLonger"
}
```

## Calling these configs in your scraper

The config values have been defined as class methods, so calling them in your scraper is as simple as requiring the config file either directly with something like `require_relative "rb_common/configs/stash_config"` or generally by requiring all the common interfaces with something like `require_relative "rb_common/rb_common"`.

Once required your scrupt can access them via calls like `Config::Stash.api_key` and `Config::Stash.endpoint`.

## Creating a new config

If you are looking to create a new common configuration for use with your scrapers here are the important things to know about the implimentation.

You will first need to require and inherit from the base config. The existing configs have been namespaced under `Config::`, this is not mantority but it is suggested for consistency. You can see this in the other configs with:

```Ruby
require_relative "config_base"

module Config
  class Stash < ConfigBase
```

From there the base class expects you to define a `USER_CONFIG` hash. The base class contains `endpoint` and `api_key` methods that look for keys of the same name in the `USER_CONFIG`. If the keys are not present in the `USER_CONFIG`, the methods will just return nil. You are free to ad more than the default two keys to your `USER_CONFIG`, but you will need to define their accessor methods on your child class.
