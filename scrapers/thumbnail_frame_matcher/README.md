# Thumbnail Frame Matcher

This scraper was mainly designed with Clips4Sale in mind but I'm sure there are plenty of other studios with similar issues. This scraper takes uses an existing thumbnail for a scene to find the matching frame in the scene and extract that frame.

This enables better quality thumbnails for sites like Clips4Sale who use a **lot** of JPG compression, and very small resolutions.

## Example

Before:

![low-res-high-compression-thumb](https://user-images.githubusercontent.com/1358708/187532608-c6a17efb-2853-4415-a039-40304d543657.jpg)

After:
![extracted-frame](https://user-images.githubusercontent.com/1358708/187532616-4a74dc54-20b8-4cb5-8b75-30b24ea93ac3.jpg)

Video example of the scraper in action [here](https://monosnap.com/file/RJ88MqUUFYZdwAhdIc7uIVozkc4YU3)

## FAQ

### The scraper is taking a long time to load

The scraper runs an FFMPEG process which depending on the files size / resolution / how bad the reference image / etc, can take a while to load for some files.

Also while the first matching attempt tries to match at a 95% rate, if that does not match, the scraper tries stepping down and attempts again with 5% less accuracy, to a minimum of 70% before it gives up.

### The scraper returns a frame that was close but not identical

While this scraper has a great success rate, in some cases a frame may have hit the minimum match criteria on the wrong frame (especially if the only part that is wrong is minor, like an eye blinking). You can always try to manually match frames for these scenes but starting/pausing till you find the frame and using the Stash feature `Generate thumbnail from current`.
