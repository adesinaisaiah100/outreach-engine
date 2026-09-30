from playwright.sync_api import sync_playwright
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    try:
        browser = p.chromium.connect_over_cdp('http://127.0.0.1:9223')
        for ctx in browser.contexts:
            for page in ctx.pages:
                if 'linkedin.com/in/' in page.url:
                    print(f"Inspecting Profile: {page.url} ({page.title()})")
                    
                    # 1. Top card actions container
                    top_card = page.locator("section.artdeco-card").first
                    print(f"Top card count: {page.locator('section.artdeco-card').count()}")
                    
                    # Search inside top card specifically!
                    print("\n--- Buttons/Links inside Profile Top Card ---")
                    top_card_buttons = page.locator("div.ph5 a, div.ph5 button, section.artdeco-card a, section.artdeco-card button")
                    cnt = top_card_buttons.count()
                    print(f"Total elements in top card: {cnt}")
                    for i in range(cnt):
                        el = top_card_buttons.nth(i)
                        txt = el.inner_text().strip().replace('\n', ' ')
                        aria = el.get_attribute('aria-label') or ''
                        href = el.get_attribute('href') or ''
                        tag = el.evaluate("e => e.tagName")
                        cls = el.get_attribute('class') or ''
                        box = el.bounding_box()
                        print(f"[{i}] Tag: {tag} | Text: '{txt}' | Aria: '{aria}' | Href: '{href[:30]}' | Class: '{cls[:40]}' | Box: {box}")
                        
    except Exception as e:
        print(f"Error: {e}")
