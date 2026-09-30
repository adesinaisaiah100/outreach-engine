from playwright.sync_api import sync_playwright
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9223')
    for ctx in browser.contexts:
        for page in ctx.pages:
            if 'linkedin.com/in/' in page.url:
                print(f"URL: {page.url}")
                data = page.evaluate("""() => {
                    const results = [];
                    const allEls = document.querySelectorAll('a, button');
                    for (const el of allEls) {
                        const txt = (el.innerText || '').trim();
                        const aria = el.getAttribute('aria-label') || '';
                        const href = el.getAttribute('href') || '';
                        const rect = el.getBoundingClientRect();
                        
                        if (/message|connect|more|invite/i.test(txt) || /message|connect|more|invite/i.test(aria)) {
                            results.push({
                                tag: el.tagName,
                                text: txt,
                                aria: aria,
                                href: href.substring(0, 50),
                                className: el.className,
                                parentClass: el.parentElement ? el.parentElement.className : '',
                                top: rect.top,
                                left: rect.left,
                                width: rect.width,
                                height: rect.height,
                                isVisible: (rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).display !== 'none')
                            });
                        }
                    }
                    return results;
                }""")
                print(f"Found {len(data)} candidate elements:")
                for i, item in enumerate(data):
                    print(f"[{i}] {item['tag']} | Text: '{item['text']}' | Aria: '{item['aria']}' | Visible: {item['isVisible']} | Top: {item['top']:.1f} | Class: {item['className'][:40]} | Parent: {item['parentClass'][:40]}")
