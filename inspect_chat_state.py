from playwright.sync_api import sync_playwright
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9223')
    page = browser.contexts[0].pages[0]
    print('Testing chat box on:', page.url)
    
    chat_selectors = [
        "div.msg-form__contenteditable[role='textbox']",
        "div[role='textbox'][aria-label*='Write a message']",
        "div.msg-form__message-texteditor div[role='textbox']",
        "div.msg-form__contenteditable",
        "div[contenteditable='true'][role='textbox']"
    ]
    
    found = False
    for c_sel in chat_selectors:
        loc = page.locator(c_sel).locator('visible=true')
        cnt = loc.count()
        print(f"Selector '{c_sel}' count: {cnt}")
        if cnt > 0:
            found = True
            
    # Check overlays
    overlays = page.locator("div.msg-overlay-conversation-bubble").count()
    print(f"Overlay conversation bubbles count: {overlays}")
    
    # Check all contenteditable elements
    ce = page.locator("[contenteditable='true']").all()
    print(f"Total contenteditable elements: {len(ce)}")
    for i, el in enumerate(ce):
        print(f"  [{i}] tag={el.evaluate('e => e.tagName')} aria={el.get_attribute('aria-label')} role={el.get_attribute('role')} is_visible={el.is_visible()}")
