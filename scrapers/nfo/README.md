# .nfo Scraper
This is a simple scraper that uses `.nfo` files alongside your scenes.

The scraper tries to read `.nfo` files in the same directory of the video with the same filename, but with the `.nfo` extension.
OR `.nfo` file with the same filename but in the `.nfo/` **directory** within the video's directory.

So so, `C:\video1.mp4` nfo file can be `C:\video1.nfo` or `C:\.nfo\video1.nfo`

Scraping is easy peasy, because it uses Scrape by Fragment, you don't need to input search query or anything, and stash can do it in bulk.

## Variables
Variables in `.nfo` files: They're useful when you want to for example mix a title with the studio and the filename, so the `.nfo` file may have title element as `[%studio_name%] %filename%`

These are not standard and not recognizable by other `.nfo` file readers, but here we have them and trying to keep them simple to provide flexibility with simplicity.

Supported variables at this time are:

- `title` - The title found in .nfo file, otherwise the title in scene fragment
- `filename` - The filename of the scene, without extension
- `fileextension` - The scene's file extension, e.g .mp4
- `studio_name` - The studio's name found in .nfo file, otherwise the studio in scene fragment
- `date` - The date found in .nfo file, otherwise the date in scene fragment

## Folder .nfo
`folder.nfo` is useful when you have a folder that belongs to specific studio or a movie so you can set studio, date and more via that single `.nfo` file for all the scenes in the movie/folder.

`folder.nfo` files are just `.nfo` files, nothing special about them, but can just be made to assign specific `metadatas` to all the scenes in the folder.
example `folder.nfo` file:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<movie>
    <title>[%studio_name%] %filename%</title>
    <studio>Example</studio>
</movie>
```
The `nfo` file above will set scene title for all the scenes in the folder like `[Example] %filename%` and the studio as Example.

the data from `folder.nfo` files will not be passed to stash immediately, the scraper will try to look `.nfo` files dedicated for the scene after that. if exists, it will set the data that exists in the scene's `.nfo` file and leave them that doesn't exists as is set by `folder.nfo`. So you may also look at them as a default metadata template.


## Side Notes
#### Images
The scraper will not try to load the images and pass them to stash if the image is as URL in the `.nfo` file, thus, exported `.nfo` files are better to include images as base64 if it's going to include any.

This way, everyone will have the image correctly set, not just an inaccessible URL for the image.


#### Date
The scraper is built for Stash assuming there's also a dedicated `.nfo` file exporter/creator built/built-in for Stash.
Then the dates has to be in the format that Stash supports, not anything else.

----
##### Why does it matter?
Well, You will not need to use several scrapers and spend hours trying find and set metadatas for the scene, movie or even megapack you did downloaded, only if `.nfo` files are provided by your download source. You can figure them all in one or two clicks.

As an uploader, you will help a lot all the downloaders and yourself most probably in future if you provide `.nfo` files with your uploads.