import time
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def safe_evaluate(page, script, retries=3, delay=1.5):
    """
    Executes page.evaluate with automatic retries if a client-side navigation
    or SPA hydration destroys the execution context.
    """
    for attempt in range(retries):
        try:
            return page.evaluate(script)
        except Exception as e:
            err_msg = str(e).lower()
            if "execution context was destroyed" in err_msg or "navigating" in err_msg or "target closed" in err_msg:
                time.sleep(delay)
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
            else:
                if attempt == retries - 1:
                    raise e
                time.sleep(delay)
    return None

def check_connection_status(page):
    """
    Detects if the user is already 1st degree, or has an invitation pending.
    Returns: '1st', 'pending', or 'not_connected'
    """
    script = """() => {
        const textContent = document.body ? document.body.innerText : '';
        
        // 1. Check for Pending invitation button
        const buttons = Array.from(document.querySelectorAll('main button, div.ph5 button, button'));
        for (const b of buttons) {
            const txt = (b.innerText || '').trim();
            const aria = (b.getAttribute('aria-label') || '').trim();
            if (txt === 'Pending' || /pending|withdraw invitation/i.test(aria)) {
                return 'pending';
            }
        }
        
        // 2. Check for 1st-degree connection badge
        const badges = Array.from(document.querySelectorAll('.dist-value, span.artdeco-hoverable-trigger, .member-badge'));
        for (const badge of badges) {
            const txt = (badge.innerText || '').trim();
            if (txt === '1st' || txt.includes('1st degree')) {
                return '1st';
            }
        }
        
        return 'not_connected';
    }"""
    return safe_evaluate(page, script) or 'not_connected'

def extract_connect_button(page):
    """
    Finds and clicks the Connect button on a LinkedIn profile.
    1. Checks the primary action buttons in the top card.
    2. If not visible, checks the 'More' (...) dropdown menu.
    Returns 'connect' if successfully clicked, None otherwise.
    """
    MARKER = 'data-corecv-target'
    
    # 1. Clean previous markers
    safe_evaluate(page, f"""() => {{
        const old = document.querySelectorAll('[{MARKER}]');
        old.forEach(el => el.removeAttribute('{MARKER}'));
    }}""")
    
    # 2. Check for direct Connect button
    detect_script = f"""() => {{
        const allEls = Array.from(document.querySelectorAll('main a, main button, div.ph5 a, div.ph5 button, a, button'));
        
        for (const el of allEls) {{
            const txt = (el.innerText || '').trim();
            const aria = (el.getAttribute('aria-label') || '').trim();
            const rect = el.getBoundingClientRect();
            
            // Spatial check: Main hero area, not sidebar, not footer
            if (rect.top > 80 && rect.top < 850 && rect.width > 30 && rect.height > 20) {{
                if (el.closest('aside') || el.closest('.scaffold-layout__aside')) continue;
                
                // Direct Connect button
                if (txt === 'Connect' || /invite.*connect/i.test(aria) || aria === 'Connect') {{
                    el.scrollIntoView({{ behavior: 'instant', block: 'center' }});
                    el.setAttribute('{MARKER}', 'true');
                    return {{ found: true, type: 'direct' }};
                }}
            }}
        }}
        
        // If direct connect not found, find the 'More' button
        for (const el of allEls) {{
            const txt = (el.innerText || '').trim();
            const aria = (el.getAttribute('aria-label') || '').trim();
            const rect = el.getBoundingClientRect();
            
            if (rect.top > 80 && rect.top < 850 && rect.width > 20 && rect.height > 20) {{
                if (el.closest('aside') || el.closest('.scaffold-layout__aside')) continue;
                
                if (txt === 'More' || aria.includes('More actions') || aria === 'More' || /more actions/i.test(aria)) {{
                    el.scrollIntoView({{ behavior: 'instant', block: 'center' }});
                    el.setAttribute('{MARKER}', 'true');
                    return {{ found: true, type: 'more' }};
                }}
            }}
        }}
        
        return {{ found: false }};
    }}"""
    
    result = safe_evaluate(page, detect_script)
    if not result or not result.get('found'):
        return None
    
    btn_type = result.get('type')
    
    # Click target
    try:
        target = page.locator(f'[{MARKER}="true"]').first
        target.wait_for(state="visible", timeout=3000)
        target.click(force=True, timeout=5000)
    except Exception:
        safe_evaluate(page, f"""() => {{
            const el = document.querySelector('[{MARKER}]');
            if (el) el.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true, view: window }}));
        }}""")
    
    time.sleep(0.6)
    
    if btn_type == 'direct':
        return 'connect'
    
    # If we clicked 'More', search for Connect inside the opened dropdown menu
    if btn_type == 'more':
        time.sleep(1.0)
        dropdown_script = f"""() => {{
            const old = document.querySelectorAll('[{MARKER}]');
            old.forEach(el => el.removeAttribute('{MARKER}'));
            
            const dropdownItems = Array.from(document.querySelectorAll(
                'div.artdeco-dropdown__content *, div[role="menu"] *, div[role="dialog"] *'
            ));
            
            for (const item of dropdownItems) {{
                const txt = (item.innerText || '').trim();
                const aria = (item.getAttribute('aria-label') || '').trim();
                if (txt === 'Connect' || /invite.*to connect|invite.*connect/i.test(aria)) {{
                    item.setAttribute('{MARKER}', 'true');
                    return true;
                }}
            }}
            return false;
        }}"""
        
        found_in_dropdown = safe_evaluate(page, dropdown_script)
        if found_in_dropdown:
            try:
                connect_item = page.locator(f'[{MARKER}="true"]').first
                connect_item.click(force=True, timeout=3000)
                return 'connect'
            except Exception:
                safe_evaluate(page, f"""() => {{
                    const el = document.querySelector('[{MARKER}]');
                    if (el) el.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true, view: window }}));
                }}""")
                return 'connect'
                
    return None

def extract_message_href(page):
    """
    Extracts genuine 1st-degree Message href if user is already connected.
    """
    result = safe_evaluate(page, """() => {
        const allA = Array.from(document.querySelectorAll('main a, div.ph5 a, a'));
        for (const el of allA) {
            const txt = (el.innerText || '').trim();
            const aria = (el.getAttribute('aria-label') || '').trim();
            const rect = el.getBoundingClientRect();
            
            if (rect.top > 80 && rect.top < 850 && rect.width > 35 && rect.height > 20) {
                if (el.closest('aside') || el.closest('.scaffold-layout__aside')) continue;
                
                // Exclude locked InMail buttons
                if (txt === 'Message' && !aria.includes('Premium') && !aria.includes('InMail') && !aria.includes('Lock')) {
                    const href = el.href || el.getAttribute('href') || '';
                    if (href.includes('/messaging/compose')) {
                        return { found: true, href: href };
                    }
                }
            }
        }
        return { found: false };
    }""")
    
    if result and result.get('found'):
        return result['href']
    return None

def get_compose_url(href):
    if not href:
        return None
    parsed = urlparse(href)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params.pop('interop', None)
    params.pop('screenContext', None)
    new_query = urlencode(params, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

def trigger_profile_action(page):
    """
    Main Action Dispatcher:
    1. Check if profile is already 'Pending' (invitation already sent).
    2. PRIORITY 1: Look for 'Connect' button (top card OR 'More' dropdown).
    3. PRIORITY 2: If confirmed 1st degree or no connect exists, look for direct 'Message'.
    """
    # Step 0: Check connection status
    status = check_connection_status(page)
    if status == 'pending':
        return {'action': 'already_pending', 'success': True}
    
    # Step 1: PRIORITY 1 — Try to Connect
    connect_result = extract_connect_button(page)
    if connect_result == 'connect':
        return {'action': 'connect', 'success': True}
    
    # Step 2: PRIORITY 2 — If not connected and no connect button, check if already 1st degree
    href = extract_message_href(page)
    if href:
        compose_url = get_compose_url(href)
        return {'action': 'message', 'success': True, 'href': href, 'compose_url': compose_url}
    
    return {'action': None, 'success': False}
