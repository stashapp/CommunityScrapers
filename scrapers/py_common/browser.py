from playwright.sync_api import sync_playwright

def get_html(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(url, timeout=60000)
            # Handle age verification popups if they exist
            if page.query_selector('.agepop'):
                page.click('.agebuttons a:has-text("Yes")')
            content = page.content()
        finally:
            browser.close()
        return content

def get_iframe_content(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(url, timeout=60000)
            iframe = page.frame_locator("iframe")
            content = iframe.locator("video").get_attribute("poster")
        finally:
            browser.close()
        return content
