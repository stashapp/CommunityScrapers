# Ruby Common Files

The files in this folder are a shared codebase to be used by any scrapers written in Ruby. If you are using any Ruby scrapers, it is suggested to download this whole folder and include it alongside your scrapers in the same placement it currently sits in this repo.

## Ruby and Gems

Before you use files from this folder or any ruby script you will need to ensure you have installed Ruby in your instance, as well as the Faraday gem. If you are using docker you will need to open a console/shell for the container and run `apk add --no-cache ruby && gem install faraday`.

In a future version of Stash, Ruby and Faraday will be included and won't require a separate install.

## Configs

Navigate to the `/configs` folder to set any api_keys and endpoints that you may need to configure for your scrapers to work. There is a readme in that folder as well with more details.

## GraphQL

Navigate to the `/graphql` folder for more details on the shared GraphQL interfaces that your Ruby scrapers can leverage.

## Logger

The `logger.rb` file defines a shared class that Ruby scrapers can leverage to output logs at the correct log level instead of everything coming through as an error log.

Once required it is suggested to assign the logger to a variable so that you can call it in short form like:

```Ruby
logger = Stash::Logger
logger.info("This log will be output as an 'INFO' level log")
```

## Simple Mass Requirement

Your scraper can require all common interfaces files at once with something like `require_relative "rb_common/rb_common"`.
