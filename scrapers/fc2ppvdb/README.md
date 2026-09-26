# FC2CMADB python scraper

## Requirements

Requires a valid login session. Copy the `fc2cmadb-session` cookie from your browser after logging into fc2cmadb.com.  

Rate limits: **1 request/second**, burst up to 30/min, 250/hour.  

Note: As of 2026-08, the hourly limit appears to be 300 requests. Exceeding this will invalidate the session and temporarily block re‑login for a cooldown period.  

## Configuration

`config.ini` is created automatically on first run.  

**fc2cmadb_session**  
Value of the `fc2cmadb-session` cookie (mandatory).  

**scrape_scene_image**  
`True` (default) to import scene image, `False` to skip.  

**unique_performer_name**  
`False` (default). If True, adds id to performer name `Name_[ID]` to keep the name unique. Unique names help to pick the right performer when using autotagger (vs duplicate names with disambiguation).  

**disambiguation_prefix**  
Default `fc2cmadb-`. If set, performer disambiguation is filled with this prefix + ID. Empty to disable.  

Example `config.ini`:
```ini
fc2cmadb_session = eyJpdiI6...
scrape_scene_image = True
unique_performer_name = False
disambiguation_prefix = fc2cmadb-
```

### Getting the cookie
1. Log in to fc2cmadb.com.
2. Open Developer Tools (F12), then go to the **Cookies** section:
   - Chromium browsers (Chrome, Edge): **Application** → **Cookies**
   - Firefox: **Storage** → **Cookies**
3. Find the cookie named **`fc2cmadb-session`** and copy its **value**.
4. Paste that value into the `fc2cmadb_session` setting.

## Troubleshooting

Check Stash logs for debug output.

If you get login errors (in log), refresh the cookie in your browser and update `config.ini`.  

If the filename lacks a 5+ digit ID, scraping fails – rename the file or provide the URL manually.  
