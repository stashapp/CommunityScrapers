name: xes.pl
sceneByURL:
  - action: scrapeXPath
    url:
      - xes.pl
    scraper: sceneScraper
xPathScrapers:
  sceneScraper:
    scene:
      Title: //div[@class="video-page"]/div/h1
      Details:
        selector: //div[@class="video-article-wrap"]/article/p
        concat: "\n\n"
      Performers:
        Name: //div[@class="details_hidden"]/table/tbody/tr/td[text()="Aktorzy:"]/following-sibling::td/ul/li/a/text()
      Studio:
        Name:
          selector: //div[@class="details_hidden"]/table/tbody/tr/td[text()="Produkcja:"]/following-sibling::td
      Date: 
        selector: //div[@class="details"]/table/tbody/tr/td[text()="Data dodania:"]/following-sibling::td
      Tags:
        Name: //div[@class="details_hidden"]/table/tbody/tr/td[text()="Kategorie:"]/following-sibling::td/ul/li/a
      Image: //div[@class="video-type-select"]/picture/img/@src

# Last Updated August 22, 2022

