gallery-dl has a few options to also write out metadata while dowloading.

* `--write-info-json` will produce one file `info.json` per downloaded gallery, with gallery metadata
* `--write-metadata` will produce one file `<filename>.json` per downloaded file, with gallery and / or file metadata metadata

The structure appears to be generic enough, so that an attempt can be made to extract metadata from it.

Supports
* gallery metadata from `info.json` in gallery path
* image and scene metadata from `<filename>.json` for same or different extensions (for when downloaded png got optimized to jpg, for example)
* directory and archive-based (zip, cbz) paths
* the parsing of tags etc should be somehwat generic, but result may vary widely site to site, as provided data are implemented per site / extractor on their end
