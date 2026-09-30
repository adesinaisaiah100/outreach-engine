from playwright.sync_api import sync_playwright
import sys

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9223')
    for ctx in browser.contexts:
        for page in ctx.pages:
            if 'linkedin.com/in/' in page.url:
                print(f"\nTarget Page: {page.url}")
                
                # Find all buttons and links on the entire page
                els = page.locator("a, button").all()
                print(f"Total a/button elements: {len(els)}")
                
                for el in els:
                    try:
                        txt = el.inner_text().strip().replace('\n', ' ')
                        aria = el.get_attribute('aria-label') or ''
                        href = el.get_attribute('href') or ''
                        tag = el.evaluate("e => e.tagName")
                        cls = el.get_attribute('class') or ''
                        box = el.bounding_box()
                        
                        # Filter to Message, Connect, More, Follow
                        if any(k in txt.lower() or k in aria.lower() for k in ['message', 'connect', 'more', 'follow', 'invite']):
                            print(f"\n--- Match Found ---")
                            print(f"Tag: {tag} | Text: '{txt}' | Aria: '{aria}' | Href: '{href[:50]}'")
                            print(f"Class: {cls}")
                            print(f"Parent Class: {el.evaluate('e => e.parentElement ? e.parentElement.className : null')}")
                            print(f"Bounding Box: {box}")
                            print(f"Is Visible: {el.is_visible()}")
                    except Exception:
                        pass
