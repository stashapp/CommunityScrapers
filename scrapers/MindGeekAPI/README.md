# MindGeek API Python scraper 

## Features
Supports scraping by URL for scenes. Scene by name queries are also supported.

## Installation
### Python
As this is a python scraper make sure that python (python3) is installed.
- The official stash docker container already contains python and all needed modules.
- For Windows systems install python from [python.org](https://www.python.org/downloads/windows/) ([instructions](https://phoenixnap.com/kb/how-to-install-python-3-windows)), NOT from the Windows store.
- For Linux systems please consult the relevant distro instructions.
- For Μac systems either use homebrew eg `brew install python3` or use the python.org installer ([instructions](https://www.lifewire.com/how-to-install-python-on-mac-4781318))
### Scraper
Copy the `MindGeeksAPI` directory inside stash's `scrapers` directory.

If you don't already have a `py_common` folder in the `scrapers` directory copy that as well from the community repo page (adjust `config.py` if needed).

You should have at least the following files/folders in your `stash` config folder
```
config.yml
stash-go.sqlite
scrapers
└─── MindGeeksAPI
└─── py_common
```
Use `pip` (or `pip3` ) to install the required modules listed in `requirements.txt`.
```
pip install -r requirements.txt
```

## Configuration
The `mg_default_config.py` contains a list of configuration options you can override. Do not edit the file directly. Instead copy the file to a new `mg_config.py` and edit/override any options there.