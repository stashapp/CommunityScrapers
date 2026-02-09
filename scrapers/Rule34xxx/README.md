# Rule34xxx Stash Scraper

This scrapes the html to isolate performers from tags and artists.

Some things to be aware of:

- This scraper works for files named with their md5 hash, or files named in the general format of `r34_{post_id_number}_{...}.{ext}`.
- Meta, Copyright, and General tags get collapsed into normal stashapp tags.
- Stash does not support multiple studios (artists) on the same media, so this scraper will discard any artists that look like voice actors, and then use the first artist it finds as the studio.
- Rate limits and failures will return empty `{}`
- This scraper was created by Claude Code (Sonnet, Jan 2026)
