"""Quick diagnostic: extract the href from the Message <A> tag"""
import time, sys, requests, subprocess
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
DEBUG_PORT = 9223

with sync_playwright() as p:
    try:
        requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=3)
    except:
        print("Launch Chrome first!")
        sys.exit(1)
    
    browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}", timeout=15000)
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    
    page.goto("https://www.linkedin.com/in/ojojosh/", timeout=45000, wait_until="domcontentloaded")
    time.sleep(5)
    
    # Get ALL Message <A> tags with their href, text, aria, position
    links = page.evaluate("""() => {
        const results = [];
        const allA = Array.from(document.querySelectorAll('a'));
        for (const el of allA) {
            const txt = (el.innerText || '').trim();
            const aria = (el.getAttribute('aria-label') || '').trim();
            if (txt === 'Message' || aria.startsWith('Message')) {
                const rect = el.getBoundingClientRect();
                const inAside = !!(el.closest('aside') || el.closest('.scaffold-layout__aside'));
                results.push({
                    text: txt,
                    aria: aria,
                    href: el.href || el.getAttribute('href') || 'NONE',
                    top: Math.round(rect.top),
                    left: Math.round(rect.left),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    inAside: inAside,
                    outerHTML: el.outerHTML.substring(0, 300)
                });
            }
        }
        return results;
    }""")
    
    print(f"\nFound {len(links)} Message <A> tags:\n")
    for i, l in enumerate(links):
        print(f"--- [{i}] ---")
        print(f"  Text: {l['text']}")
        print(f"  Aria: {l['aria']}")
        print(f"  Href: {l['href']}")
        print(f"  Position: top={l['top']}, left={l['left']}, {l['width']}x{l['height']}")
        print(f"  In Aside: {l['inAside']}")
        print(f"  HTML: {l['outerHTML'][:200]}")
        print()
