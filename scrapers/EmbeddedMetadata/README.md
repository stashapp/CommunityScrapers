A scraper that pulls metadata from the image files themselves.

Right now, the following sources are supported:
* EXIF data
* IPTC data
* XMP data

Metadata is read with [Pillow](https://python-pillow.org), so any image format it can open works, as long as the file carries one of these blocks (IPTC is only read from JPEG and TIFF).

== Installation ==
This scraper requires Pillow, which it installs automatically on first run.

== Configuration ==

The first run creates a ```config.ini``` next to the scraper, where some maybe unwanted features can be enabled:

| Setting | Description |
| -------- | ------- |
| ```details_date_fields = False``` | enable to add all seen date field values to details (since the scraper has to potentially pick from one of several conflicting fields and might be wrong) |
| ```details_title_fields = False``` | enable to add all seen title field values to details (since the scraper has to potentially pick from one of several conflicting fields and might be wrong) |
| ```details_author_fields = False``` | enable to add all seen studio / photographer field values to details (since the scraper has to potentially pick from one of several conflicting fields and might be wrong) |
| ```details_camera_infos = False``` | enable to add camera make, model and lens make and model as one line to details |
| ```details_unprocessed_fields = False``` | enable to add all fields the scraper doesn't otherwise use, and that aren't ignored, to details |
| ```details_unprocessed_fields_ignored =``` | comma-separated additional fields to not add to details (the default list is already quite extensive and should ignore most boring stuff like camera settings) |
| ```details_unprocessed_fields_unignored =``` | comma-separated fields to add to details that are on the default ignore list |

== Metadata fields ==
exiv2 has a very comprehensive documentation on EXIF, IPTC and XMP tags, which can be found under https://exiv2.org/metadata.html
