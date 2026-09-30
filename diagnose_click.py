"""
DIAGNOSTIC: Connects to your running Chrome, visits ONE LinkedIn profile,
dumps every button it can see, tries to click Message, and reports exactly
what happens at each step. Run this WHILE Chrome is open with LinkedIn logged in.
"""
import time
import sys
import json
import subprocess
import requests
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

DEBUG_PORT = 9223
TEST_URL = "https://www.linkedin.com/in/ojojosh/"  # Joshua Ojo - known test profile

def main():
    print("=" * 70)
    print("  CORECV ACTION DISPATCHER DIAGNOSTIC")
    print("=" * 70)

    # Step 0: Check if Chrome is running with debugging
    print("\n[STEP 0] Checking Chrome CDP connection...")
    try:
        resp = requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=3)
        info = resp.json()
        print(f"  ✅ Chrome connected: {info.get('Browser', 'unknown')}")
    except Exception:
        print(f"  ❌ No Chrome on port {DEBUG_PORT}. Launching now...")
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        subprocess.Popen([
            chrome_path,
            f"--remote-debugging-port={DEBUG_PORT}",
            r"--user-data-dir=C:\Users\Isaiah\chrome_automation",
            "--no-default-browser-check",
            "--disable-infobars",
            "https://www.linkedin.com"
        ])
        print("  Waiting 8s for Chrome to start...")
        time.sleep(8)

    with sync_playwright() as p:
        print("\n[STEP 1] Connecting Playwright to Chrome via CDP...")
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}", timeout=15000)
        context = browser.contexts[0]
        
        # Try using an EXISTING page instead of creating a new one
        pages = context.pages
        print(f"  Found {len(pages)} existing tab(s)")
        
        if pages:
            page = pages[0]
            print(f"  Using existing tab: {page.url[:80]}...")
        else:
            page = context.new_page()
            print(f"  Created new tab")

        print(f"\n[STEP 2] Navigating to {TEST_URL}...")
        page.goto(TEST_URL, timeout=45000, wait_until="domcontentloaded")
        print(f"  Page loaded. Waiting 5s for full render...")
        time.sleep(5)
        print(f"  Current URL: {page.url}")

        # Step 3: Dump ALL visible buttons
        print(f"\n[STEP 3] Scanning ALL buttons/links on page...")
        buttons = page.evaluate("""() => {
            const results = [];
            const allEls = Array.from(document.querySelectorAll('a, button'));
            for (const el of allEls) {
                const txt = (el.innerText || '').trim().substring(0, 40);
                const aria = (el.getAttribute('aria-label') || '').trim().substring(0, 40);
                const rect = el.getBoundingClientRect();
                const inAside = !!(el.closest('aside') || el.closest('.scaffold-layout__aside'));
                const visible = rect.width > 0 && rect.height > 0;
                
                if (!visible) continue;
                if (!txt && !aria) continue;
                
                // Only log buttons in the header area
                if (rect.top > 0 && rect.top < 900) {
                    results.push({
                        tag: el.tagName,
                        text: txt,
                        aria: aria,
                        top: Math.round(rect.top),
                        left: Math.round(rect.left),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                        inAside: inAside,
                        classes: (el.className || '').substring(0, 60)
                    });
                }
            }
            return results;
        }""")

        message_candidates = []
        print(f"\n  {'TAG':<8} {'TEXT':<25} {'ARIA':<25} {'TOP':<5} {'LEFT':<5} {'WxH':<10} {'ASIDE':<6}")
        print(f"  {'-'*8} {'-'*25} {'-'*25} {'-'*5} {'-'*5} {'-'*10} {'-'*6}")
        for b in buttons:
            is_msg = 'message' in b['text'].lower() or 'message' in b['aria'].lower()
            marker = " ⬅️ MESSAGE" if is_msg else ""
            print(f"  {b['tag']:<8} {b['text']:<25} {b['aria']:<25} {b['top']:<5} {b['left']:<5} {b['width']}x{b['height']:<5} {str(b['inAside']):<6}{marker}")
            if is_msg:
                message_candidates.append(b)

        print(f"\n  Total visible buttons in header zone: {len(buttons)}")
        print(f"  Message button candidates: {len(message_candidates)}")

        if not message_candidates:
            print("\n  ❌ NO Message button found on page at all!")
            print("  Possible reasons:")
            print("    - Not connected to this person (only Connect available)")
            print("    - LinkedIn requires premium to message")
            print("    - Page didn't fully load")
            
            # Take screenshot for evidence
            ss_path = r"C:\Users\Isaiah\corecv_outreach\diagnostic_screenshot.png"
            page.screenshot(path=ss_path, full_page=False)
            print(f"\n  📸 Screenshot saved: {ss_path}")
            return

        # Step 4: Try clicking Message with MULTIPLE methods
        print(f"\n[STEP 4] Attempting to click Message button...")
        
        # Method A: Playwright locator with text
        print("\n  --- Method A: page.locator('button:has-text(\"Message\")').click() ---")
        try:
            msg_btns = page.locator('button:has-text("Message")').all()
            print(f"  Found {len(msg_btns)} button(s) matching 'Message'")
            for i, btn in enumerate(msg_btns):
                box = btn.bounding_box()
                is_visible = btn.is_visible()
                print(f"    [{i}] visible={is_visible}, box={box}")
            
            if msg_btns:
                # Click the first visible one
                for btn in msg_btns:
                    if btn.is_visible():
                        box = btn.bounding_box()
                        if box and box['y'] > 80 and box['y'] < 850:
                            print(f"  Clicking button at y={box['y']:.0f}...")
                            btn.click(timeout=5000)
                            print(f"  ✅ Method A click dispatched!")
                            break
        except Exception as e:
            print(f"  ❌ Method A failed: {e}")

        # Wait and check for chat box
        print(f"\n[STEP 5] Waiting 4s then checking for chat box...")
        time.sleep(4)

        chat_check = page.evaluate("""() => {
            const selectors = [
                "div.msg-form__contenteditable[role='textbox']",
                "div[role='textbox'][aria-label*='Write a message']",
                "div.msg-form__message-texteditor div[role='textbox']",
                "div.msg-form__contenteditable",
                "div[contenteditable='true'][role='textbox']",
                "div.msg-overlay-conversation-bubble",
                "div.msg-convo-wrapper",
                "div[class*='msg-form']",
                "div[class*='msg-overlay']"
            ];
            const found = {};
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                const visible = Array.from(els).filter(e => {
                    const r = e.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                });
                if (els.length > 0) {
                    found[sel] = { total: els.length, visible: visible.length };
                }
            }
            return found;
        }""")

        if chat_check:
            print(f"\n  Chat-related elements found:")
            for sel, counts in chat_check.items():
                status = "✅" if counts['visible'] > 0 else "👻 (hidden)"
                print(f"    {status} {sel}: {counts['total']} total, {counts['visible']} visible")
        else:
            print(f"\n  ❌ ZERO chat-related elements found on page after click!")
        
        # Method B fallback: direct keyboard approach
        if not chat_check:
            print(f"\n  --- Method B: Trying keyboard shortcut / focus + Enter ---")
            try:
                # Some LinkedIn profiles respond to focusing the button and pressing Enter
                msg_btn = page.locator('button:has-text("Message")').first
                msg_btn.focus()
                time.sleep(0.3)
                page.keyboard.press("Enter")
                print(f"  Dispatched focus + Enter")
                time.sleep(3)
                
                chat_check2 = page.evaluate("""() => {
                    const el = document.querySelector("div[role='textbox'][contenteditable='true']");
                    if (el) {
                        const r = el.getBoundingClientRect();
                        return { found: true, visible: r.width > 0 && r.height > 0 };
                    }
                    return { found: false };
                }""")
                if chat_check2.get('found'):
                    print(f"  ✅ Method B WORKED! Chat box appeared!")
                else:
                    print(f"  ❌ Method B also failed")
            except Exception as e:
                print(f"  ❌ Method B error: {e}")

        # Take final screenshot
        ss_path = r"C:\Users\Isaiah\corecv_outreach\diagnostic_screenshot.png"
        page.screenshot(path=ss_path, full_page=False)
        print(f"\n  📸 Final screenshot saved: {ss_path}")
        
        print("\n" + "=" * 70)
        print("  DIAGNOSTIC COMPLETE — Share the output above")
        print("=" * 70)

if __name__ == "__main__":
    main()
