## DO NOT EDIT/RENAME THIS FILE
## Copy it to "mg_config.py" and adjust that file instead if needed.
## You only need to edit any non default values all the rest will be loaded from this file.

SETTINGS = {
# Ratio similarity to consider the scene as matched (between Title and API Title)
"SET_RATIO": 0.75,
# File used to store key to connect the API.
"STOCKAGE_FILE_APIKEY": "MindGeekAPI.ini",
# This file will be used for search by name. It can be useful if you only want to search on a specific site. (Like only putting Parent studio and not Child)
# Copy MindGeekAPI.ini to another name (then put the name in the var below), then edit the file to remove the site  you don't want to search.
"STOCKAGE_FILE_APIKEY_SEARCH": "",

# Marker
# If you want to create marker in same time as Scraping.
# Marker creation is only available when scraping by fragment (Scrape With...)
"CREATE_MARKER": False,
# Only create marker if the duration matches (API vs Stash's DB)
"MARKER_DURATION_MATCH": True,
# Sometime the API duration is 0/1, so we can't really know if this matches. True if you want to create anyways
"MARKER_DURATION_UNSURE": False,
# The max difference between Stash Length & API Length to consider it a match.
"MARKER_SEC_DIFF": 10,

# Extra tag you may want to add to the scene
"FIXED_TAG": "",

# Only return female peformers
"FEMALE_ONLY": False,

# Save JSONs to disk
# If enabled JSON Files will be saved in scrapers/scraperJSON/MindGeekAPI, where scrapers is stash's scraper directory
"MG_SAVE_JSON": False,

# USER AGENT to use when scraping
"USER_AGENT":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0",
}