name: Mylked
sceneByURL:
  - action: scrapeXPath
    url:
      - mylked.com/videos/
    scraper: sceneScraper
xPathScrapers:
  sceneScraper:
    scene:
     Title:
        selector: //div[@class="pull-left"]/h5
        postProcess:
          - replace:
              - regex: ^(.*)[—]\s+
     Date:
        selector: //div[@class="pull-left"]//span/text()
        postProcess:
          - replace:
            - regex: ^-\s(\w+)\s(\d{1,2}),\s(\d{4})$
              with: $1 $2 $3
          - parseDate: January 2 2006
     Performers:
      Name: //div[@class="pull-left"]//a/text()
     Details: //div[@class="title-bottom"]/p
     Image: //video[@id="my-video"]/@poster
     Studio:
        Name:
          fixed: Mylked
# Last Updated February 19, 2021
