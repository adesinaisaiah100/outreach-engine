from playwright.sync_api import sync_playwright
import time
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

TARGET_URL = "https://www.linkedin.com/in/ojojosh"
SCREENSHOT_DIR = r"C:\Users\Isaiah\.gemini\antigravity-cli\brain\5450a6af-2de1-478c-baef-b1f96bb64313"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9223")
    
    # Find the LinkedIn tab
    page = None
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if 'linkedin.com' in pg.url:
                page = pg
                break
        if page:
            break
            
    if not page:
        page = browser.contexts[0].new_page()
        
    print(f"Targeting LinkedIn tab: {page.url}")
    if 'in/ojojosh' not in page.url:
        page.goto(TARGET_URL, timeout=45000, wait_until="domcontentloaded")
        time.sleep(3)
        
    from action_dispatcher import trigger_profile_action
    res = trigger_profile_action(page)
    print(f"trigger_profile_action result: {res}")
    
    time.sleep(2)
    s2 = os.path.join(SCREENSHOT_DIR, "step2_after_action.png")
    page.screenshot(path=s2)
    print(f"📸 Saved screenshot 2: {s2}")
