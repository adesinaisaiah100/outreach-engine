from playwright.sync_api import sync_playwright
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9223')
    for ctx in browser.contexts:
        for page in ctx.pages:
            if 'linkedin.com/in/' in page.url:
                print(f"Testing click on: {page.url}")
                
                # Test JS-powered button finder that finds the primary profile action button
                # (ignores top nav and ignores right sidebar recommendations)
                clicked = page.evaluate("""() => {
                    const allLinksAndButtons = Array.from(document.querySelectorAll('main a, main button, a, button'));
                    
                    // Filter to elements inside main content area with text Message or Connect
                    for (const el of allLinksAndButtons) {
                        const txt = (el.innerText || '').trim();
                        const aria = el.getAttribute('aria-label') || '';
                        const rect = el.getBoundingClientRect();
                        
                        // Main profile action buttons are always within top 150px to 800px on initial load
                        // and width > 50px
                        if (rect.top > 100 && rect.top < 850 && rect.width > 50) {
                            if (txt === 'Message' || aria.startsWith('Message')) {
                                el.scrollIntoView({ behavior: 'instant', block: 'center' });
                                el.click();
                                return { success: true, action: 'message', text: txt, top: rect.top };
                            }
                        }
                    }
                    return { success: false };
                }""")
                print(f"Click Result: {clicked}")
                time.sleep(2)
                
                # Check if chat box opened
                chat_visible = page.locator("div.msg-form__contenteditable[role='textbox'], div[role='textbox']").locator("visible=true").count()
                print(f"Chat box visible count: {chat_visible}")
