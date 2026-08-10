A scraper that pulls metadata from the files itself.

Right now, the following sources are supported:
* JPEG EXIF data
* JPEG IPTC data
* JPEG XMP data

== Installation ==
This scraper requires certain python dependencies, it should automatically install them.

Internally, the prefered source is pyexiv2. If, however, this module fails to load (for example, it requires a failry recent GLIBC that can be a problem on very long support cycle Linux Distributions), it will fall back to a wrapper around exiftool. But this will require exiftool to be available in the PATH, so you might want to install it manually in these scenarios.

== Configuration ==

This scraper supports an optional config file ```config.py```, to enable some maybe unwanted features.

If your Stash installation uses Authentication, make sure the API key is configured in the ```config.ini``` in ```py_common```:

Some other things that can be enabled
| Setting | Description |
| -------- | ------- |
| ```skip_ensure_requirements = False``` | enable skip dependency install / check, makes scraper much faster, but should not be enabled untile scrapper has successfully run once |
| ```details_date_fields = False``` | enable to add all seen date field values to details (since the scraper has to potentially pick from one of several conflicting fields and might be wrong) |
| ```details_title_fields = False``` | enable to add all senn title field values to details (since the scraper has to potentially pick from one of several conflicting fields and might be wrong) |
| ```details_author_fields = False``` | enable to add all seen studio / photographer field values to details (since the scraper has to potentially pick from one of several conflicting fields and might be wrong) |
| ```details_camera_infos = False``` | enable to add camera make, model and lens make and model as one line to details |
| ```details_upprocessed_fields = False``` | enable to add fields to explicitly process and not ignored to details |
| ```details_upprocessed_fields_ignored = []``` | additional fields to not add to details (default list is already quite extensive and should ignore most boring stuff like camera settings) |
| ```details_upprocessed_fields_unignored = []``` | fields to add to details that are on the default ignore list (default list is already quite extensive and should ignore most boring stuff like camera settings) |

== Metadata fields ==
exiv2 has a very comprehensive documentation on EXIF, IPTC and XMP tags, which can be found under https://exiv2.org/metadata.html