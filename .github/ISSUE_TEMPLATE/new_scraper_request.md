name: New scraper request
description: Request a new scraper for a site that is not currently supported.
labels: ["new-scraper"]
body:
  - type: input
    id: domain
    attributes:
      label: Domain of the site you want scraped
      description: Provide the domain of the site you want scraped, without "www" or "https://". For example, "example.com".
    validations:
      required: true
  - type: dropdown
    id: scraper-type
    attributes:
      label: Which scraper types are you requesting?
      description: You can select more than one.
      options:
        - performerByName
        - performerByFragment
        - performerByURL
        - sceneByName
        - sceneByQueryFragment
        - sceneByFragment
        - sceneByURL
        - groupByURL
        - galleryByFragment
        - galleryByURL
        - imageByFragment
        - imageByURL
    validations:
      required: true
  - type: textarea
    id: scraper-type-details
    attributes:
      label: Scraper type specific details
      description: |
        Please provide additional details that may be relevant. For example:
        For "<object>ByURL" scrapers, please provide an example URL that you would expect to be able to scrape with that scraper.
        For "<object>ByFragment" scrapers, please provide the details about which fragment you would want that scraper to use.
        For "<object>ByName" scrapers, please provide an example of an <object> name that you would expect to be able to scrape with that scraper.
    validations:
      required: false
  - type: textarea
    id: site-details
    attributes:
      label: Site specific details
      description: |
        Please provide any additional details about the site that may be relevant for writing a scraper. For example, does the site require an account to access content? Does it belong to a larger network? Does it have an API? Anything else you think may be relevant.
    validations:
      required: false
  - type: checkboxes
    id: confirm-search
    attributes:
      label: Have you looked at existing scraper requests?
      description: |
        Please ensure you have first [searched existing scraper requests](https://github.com/stashapp/CommunityScrapers/issues?q=is%3Aissue%20label%3Anew-scraper) to make sure your request is not a duplicate.
      options:
        - label: I have searched the existing scraper requests.
          required: true