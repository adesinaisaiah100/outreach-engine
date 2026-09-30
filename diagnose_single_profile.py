from playwright.sync_api import sync_playwright
import time
import sys
import json
import os

sys.stdout.reconfigure(encoding='utf-8')

TARGET_URL = "https://www.linkedin.com/in/ojojosh"
SCREENSHOT_DIR = r"C:\Users\Isaiah\.gemini\antigravity-cli\brain\5450a6af-2de1-478c-baef-b1f96bb64313"

with sync_playwright() as p:
    try:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9223")
        page = browser.contexts[0].pages[0]
        
        print(f"Navigating to {TARGET_URL}...")
        page.goto(TARGET_URL, timeout=45000, wait_until="domcontentloaded")
        time.sleep(4)
        
        # Take screenshot of loaded profile
        screenshot_1 = os.path.join(SCREENSHOT_DIR, "step1_loaded.png")
        page.screenshot(path=screenshot_1)
        print(f"📸 Saved screenshot 1: {screenshot_1}")
        
        # Inspect all buttons and links in the DOM
        dom_report = page.evaluate("""() => {
            const items = [];
            const els = Array.from(document.querySelectorAll('a, button, div[role="button"]'));
            for (const el of els) {
                const txt = (el.innerText || '').trim().replace(/\\n/g, ' ');
                const aria = (el.getAttribute('aria-label') || '').trim();
                const rect = el.getBoundingClientRect();
                
                // If it mentions message, connect, more, follow, or invite
                if (/message|connect|more|invite|follow/i.test(txt) || /message|connect|more|invite|follow/i.test(aria)) {
                    items.push({
                        tag: el.tagName,
                        text: txt,
                        aria: aria,
                        top: rect.top,
                        left: rect.left,
                        width: rect.width,
                        height: rect.height,
                        is_visible: rect.width > 0 && rect.height > 0,
                        in_aside: !!(el.closest('aside') || el.closest('.scaffold-layout__aside')),
                        outer_html: el.outerHTML.substring(0, 180)
                    });
                }
            }
            return items;
        }""")
        
        print(f"\n--- DOM REPORT ({len(dom_report)} candidates) ---")
        for i, it in enumerate(dom_report):
            print(f"[{i}] {it['tag']} | Text: '{it['text']}' | Aria: '{it['aria']}' | Top: {it['top']:.1f} | Visible: {it['is_visible']} | InAside: {it['in_aside']}")
            print(f"    HTML: {it['outer_html']}")
            
        # Test our action_dispatcher
        from action_dispatcher import trigger_profile_action
        action_res = trigger_profile_action(page)
        print(f"\n👉 trigger_profile_action result: {action_res}")
        
        time.sleep(2)
        screenshot_2 = os.path.join(SCREENSHOT_DIR, "step2_after_action.png")
        page.screenshot(path=screenshot_2)
        print(f"📸 Saved screenshot 2: {screenshot_2}")
        
        # Check chat box
        chat_box = page.locator("div.msg-form__contenteditable[role='textbox'], div[role='textbox']").all()
        print(f"Chat box count: {len(chat_box)}")
        
        # Check connection modal
        modal = page.locator("div.artdeco-modal").all()
        print(f"Modal count: {len(modal)}")
        
    except Exception as e:
        print(f"❌ Error in diagnostic: {e}")
