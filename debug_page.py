from playwright.sync_api import sync_playwright
import sys

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    try:
        browser = p.chromium.connect_over_cdp('http://127.0.0.1:9223')
        contexts = browser.contexts
        print(f'Connected to CDP! Open contexts: {len(contexts)}')
        for ctx in contexts:
            for page in ctx.pages:
                print(f'\n========================================')
                print(f'Page URL: {page.url}')
                print(f'Title: {page.title()}')
                if 'linkedin.com' in page.url:
                    print('--- Testing Buttons on current page ---')
                    test_selectors = [
                        "main button:has-text('Message')",
                        "main a:has-text('Message')",
                        "main button:has-text('Connect')",
                        "button.pvs-profile-actions__action:has-text('Message')",
                        "button.pvs-profile-actions__action:has-text('Connect')",
                        "button[aria-label^='Message']",
                        "a[aria-label^='Message']",
                        "button:has-text('More')",
                        "button[aria-label*='More actions']"
                    ]
                    for sel in test_selectors:
                        loc = page.locator(sel)
                        cnt = loc.count()
                        print(f"Selector: '{sel}' -> Count: {cnt}")
                        for i in range(min(cnt, 3)):
                            el = loc.nth(i)
                            try:
                                is_v = el.is_visible()
                                tag = el.evaluate("el => el.tagName")
                                outer = el.evaluate("el => el.outerHTML[:120]")
                                print(f"   [{i}] is_visible={is_v} tag={tag} html={outer}")
                            except Exception as ex:
                                print(f"   [{i}] Error: {ex}")
    except Exception as e:
        print(f'Could not connect to CDP: {e}')
