import os
import random
import time
import json
import subprocess
import requests
import pandas as pd
from playwright.sync_api import sync_playwright
from google import genai
from google.genai import types
from dotenv import load_dotenv
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load .env file from same directory as this script
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

DEBUG_PORT = 9223

# --- Required config ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not GEMINI_API_KEY:
    raise EnvironmentError(
        "\n\n❌ GEMINI_API_KEY is not set!\n"
        "Please open your .env file and add:\n"
        "  GEMINI_API_KEY=your_key_here\n"
        "Get a free key at: https://aistudio.google.com/app/apikey\n"
    )

# --- Sender identity (personalizes messages) ---
SENDER_NAME     = os.environ.get("SENDER_NAME", "the team").strip()
PRODUCT_NAME    = os.environ.get("PRODUCT_NAME", "our platform").strip()
PRODUCT_INTRO   = os.environ.get("PRODUCT_INTRO", f"building {PRODUCT_NAME}, a tool that helps professionals stand out and get hired faster").strip()
CANDIDATE_VALUE = os.environ.get("CANDIDATE_VALUE_PROP", "helping professionals build credibility and unlock better job opportunities").strip()

# --- Chrome user-data-dir (auto-detects current user's home directory, no hardcoded paths) ---
CHROME_USER_DATA = os.path.join(os.path.expanduser("~"), "chrome_automation")

def fallback_clean(raw_role):
    if not isinstance(raw_role, str) or len(raw_role) < 3:
        return "Tech Professional"
    raw = raw_role.strip()
    for delim in [' and ', '&', ',', '|', '-']:
        if delim in raw:
            raw = raw.split(delim)[0]
    return raw.strip()

def batch_enrich_leads(leads_data):
    print(f"Sending batch of {len(leads_data)} leads to Gemini for deep classification & enrichment...")
    
    payload = {str(i): leads_data[i] for i in range(len(leads_data))}
    
    prompt = f"""
    You are an expert Nigerian recruitment and cultural intelligence specialist.
    Analyze each lead and return a JSON object mapping each numeric ID to its enriched data.
    
    For each lead, evaluate:
    1. "clean_role": Standard 1-3 word professional job title (e.g., 'Talent Acquisition Lead', 'Software Engineer', 'Head of People').
    2. "persona": "HR" if the person is in HR, Talent Acquisition, Recruitment, People Operations, or is a Hiring Manager. Otherwise "CANDIDATE".
    3. "gender": "male", "female", or "unknown" inferred strictly from their first/full name (especially Nigerian/African names like Victor, Oluwatobi, Amina, Chukwuma, Blessing, Ngozi, Dami, Taiwo, Uchenna, etc.).
    4. "title": "Mr" if male, "Miss" or "Ms" if female, or "" if unknown.
    5. "honorific": "sir" if male, "ma" if female, or "" if unknown.
    6. "is_nigerian": boolean (true/false) indicating if the person's name or title strongly suggests Nigerian origin/context.

    Input Leads:
    {json.dumps(payload)}
    """
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        models_to_try = ['gemini-flash-latest', 'gemini-flash-lite-latest', 'gemini-2.5-flash']
        response = None
        for m in models_to_try:
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                if response and response.text:
                    break
            except Exception:
                continue
        
        if not response or not response.text:
            raise Exception("All Gemini models failed to return a response.")
        
        enriched_dict = json.loads(response.text)
        results = []
        for i in range(len(leads_data)):
            item = enriched_dict.get(str(i), {})
            clean_r = item.get("clean_role") or fallback_clean(leads_data[i].get("role", ""))
            persona = item.get("persona") or ("HR" if any(k in clean_r.lower() for k in ['hr', 'talent', 'recruit', 'people', 'hiring']) else "CANDIDATE")
            gender = item.get("gender", "unknown")
            title = item.get("title", "Mr" if gender == "male" else ("Miss" if gender == "female" else ""))
            honorific = item.get("honorific", "sir" if gender == "male" else ("ma" if gender == "female" else ""))
            is_nigerian = item.get("is_nigerian", True)
            
            results.append({
                "clean_role": clean_r,
                "persona": persona,
                "gender": gender,
                "title": title,
                "honorific": honorific,
                "is_nigerian": is_nigerian
            })
            
        print("✅ Batch enrichment & Nigerian classification successful!")
        return results
        
    except Exception as e:
        print(f"❌ Batch LLM enrichment failed: {e}. Using offline fallback.")
        fallback_results = []
        for lead in leads_data:
            clean_r = fallback_clean(lead.get("role", ""))
            is_hr = any(k in clean_r.lower() for k in ['hr', 'talent', 'recruit', 'people', 'hiring'])
            fallback_results.append({
                "clean_role": clean_r,
                "persona": "HR" if is_hr else "CANDIDATE",
                "gender": "unknown",
                "title": "",
                "honorific": "",
                "is_nigerian": True
            })
        return fallback_results

def get_candidate_message(first_name, role, is_connect_note=False):
    if is_connect_note:
        return (
            f"Hi {first_name},\n"
            f"Noticed your background as a {role}. We're {CANDIDATE_VALUE}.\n"
            f"We're inviting founding users before our public launch — would love to have you onboard!"
        )
    return (
        f"Hi {first_name},\n\n"
        f"I noticed your background as a {role} and thought you might find this interesting. "
        f"We're {CANDIDATE_VALUE}.\n\n"
        f"We're currently inviting founding users before we launch publicly, and I think you'd be a great fit."
    )

def get_hr_message(first_name, title, is_connect_note=False):
    title_str = f" {title}" if title else ""
    greeting = f"Hello{title_str} {first_name},"
    closing = "Thank you very much."

    if is_connect_note:
        return (
            f"{greeting}\n"
            f"My name is {SENDER_NAME}, {PRODUCT_INTRO}. "
            f"We're researching how recruiters evaluate candidates beyond resumes before we ship.\n"
            f"Your hiring perspective would be invaluable — would appreciate 15 mins to learn from you.\n"
            f"{closing}"
        )
    return (
        f"{greeting}\n"
        f"My name is {SENDER_NAME} and I am {PRODUCT_INTRO}. "
        f"We are currently trying to understand how recruiters and hiring managers actually evaluate candidates "
        f"beyond the resume before we ship the product.\n"
        f"Your perspective as someone who hires candidates would be genuinely helpful. "
        f"I would really appreciate 15 minutes of your time to learn from your experience.\n"
        f"{closing}"
    )

def run_outreach():
    print("Reading Excel file...")
    
    # Read raw Excel
    raw_df = pd.read_excel(EXCEL_PATH)
    
    # LinkedIn exports have 3 rows of disclaimers. 
    # Let's check if it's a raw linkedin export by looking at the first cell
    is_linkedin_export = str(raw_df.columns[0]).startswith("Notes:") or str(raw_df.iloc[0, 0]).startswith("When exporting")
    
    if is_linkedin_export:
        print("Detected raw LinkedIn export format. Adjusting headers...")
        df = pd.read_excel(EXCEL_PATH, skiprows=3)
    else:
        df = pd.read_excel(EXCEL_PATH)

    if 'Status' not in df.columns:
        df['Status'] = 'Pending'
    if 'Contacted_At' not in df.columns:
        df['Contacted_At'] = ''
    
    # Skip Contacted, Invalid, and ALL permanent failures (anything starting with 'Failed:')
    # Only Pending and connectivity Errors get retried
    def should_skip(status):
        if pd.isna(status):
            return False
        s = str(status)
        return s == 'Contacted' or s == 'Invalid URL' or s.startswith('Failed:')
    
    pending_users = df[~df['Status'].apply(should_skip)]
    
    daily_limit = random.randint(30, 50)
    print(f"Daily limit set to {daily_limit} profiles.")
    
    batch = pending_users.head(daily_limit).copy()
    if batch.empty:
        print("No pending users left!")
        return

    # Extract leads payload for deep LLM classification
    leads_payload = []
    for _, row in batch.iterrows():
        raw_name = str(row.get('First Name', row.get('Name', '')))
        raw_role = str(row.get('Position', row.get('Role', row.get('Title', ''))))
        leads_payload.append({"name": raw_name, "role": raw_role})

    enriched_leads = batch_enrich_leads(leads_payload)
    
    batch['Clean_Role'] = [e['clean_role'] for e in enriched_leads]
    batch['Persona'] = [e['persona'] for e in enriched_leads]
    batch['Title'] = [e['title'] for e in enriched_leads]
    batch['Honorific'] = [e['honorific'] for e in enriched_leads]
    batch['Is_Nigerian'] = [e['is_nigerian'] for e in enriched_leads]

    with sync_playwright() as p:
        try:
            # Step 1: Kill any zombie Chrome processes
            print("Killing any existing Chrome processes...")
            subprocess.call("taskkill /F /IM chrome.exe /T", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
            
            # Step 2: Launch fresh Chrome with debugging port
            print(f"Starting fresh Chrome on port {DEBUG_PORT}...")
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            chrome_args = [
                chrome_path,
                f"--remote-debugging-port={DEBUG_PORT}",
                f"--user-data-dir={CHROME_USER_DATA}",
                "--restore-last-session=false",
                "--no-default-browser-check",
                "--disable-crash-reporter",
                "--disable-infobars",
                "https://www.linkedin.com"
            ]
            subprocess.Popen(chrome_args)
            
            # Step 3: Wait until Chrome is fully ready to accept CDP connections
            print("Waiting for Chrome to be ready...")
            for i in range(20):
                try:
                    resp = requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=2)
                    if resp.status_code == 200:
                        print("Chrome is ready!")
                        break
                except Exception:
                    pass
                time.sleep(1)
            else:
                print("Chrome did not start in time. Exiting.")
                return
            
            time.sleep(3)  # Extra buffer for page to load
            
            # Step 4: Connect
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}", timeout=30000)
            context = browser.contexts[0]
            page = context.new_page()
            
            count = 0
            for index, row in batch.iterrows():
                name = str(row.get('First Name', row.get('Name', '')))
                linkedin_url = row.get('URL', row.get('Profile URL', row.get('LinkedIn', row.get('LinkedIn URL', ''))))
                clean_r = row['Clean_Role']
                persona = row['Persona']
                title = row['Title']
                honorific = row['Honorific']
                is_nigerian = row['Is_Nigerian']
                
                if pd.isna(linkedin_url) or 'linkedin.com' not in str(linkedin_url):
                    print(f"Skipping {name}: Invalid or missing LinkedIn URL")
                    df.at[index, 'Status'] = 'Invalid URL'
                    continue
                
                if not is_nigerian:
                    print(f"Skipping {name}: Classified as non-Nigerian by Gemini.")
                    df.at[index, 'Status'] = 'Skipped: Non-Nigerian'
                    df.to_excel(EXCEL_PATH, index=False)
                    continue
                
                first_name = name.split(' ')[0] if name else "there"
                if first_name.lower() in ["mr", "mr.", "miss", "mrs", "mrs.", "dr", "dr."]:
                    parts = name.split(' ')
                    first_name = parts[1] if len(parts) > 1 else parts[0]
                
                # Build persona-specific messages
                if persona == 'HR':
                    dm_msg = get_hr_message(first_name, title, is_connect_note=False)
                    note_msg = get_hr_message(first_name, title, is_connect_note=True)
                else:
                    dm_msg = get_candidate_message(first_name, clean_r, is_connect_note=False)
                    note_msg = get_candidate_message(first_name, clean_r, is_connect_note=True)
                
                print(f"\n[{count+1}/{daily_limit}] Processing {name} ({persona} | Role: {clean_r} | Title: {title or 'None'}) at {linkedin_url}...")
                
                try:
                    # Close any open LinkedIn chat windows from previous profile
                    close_btns = page.locator(
                        "button.msg-overlay-bubble-header__control--close, "
                        "button[data-control-name='overlay.close_conversation_window'], "
                        "button[aria-label*='Close'][class*='msg-']"
                    ).all()
                    for btn in close_btns:
                        try:
                            btn.click(timeout=1000)
                            time.sleep(0.3)
                        except Exception:
                            pass
                    
                    page.goto(linkedin_url, timeout=45000, wait_until="domcontentloaded")
                    time.sleep(random.uniform(3, 6))
                    
                    # Fast spatial & JS-based profile action trigger (immune to hashed CSS classes & sidebar clones)
                    from action_dispatcher import trigger_profile_action
                    action_res = trigger_profile_action(page)
                    action_taken = action_res.get('action')

                    if not action_taken:
                        print("Could not find Message or Connect button. Skipping.")
                        df.at[index, 'Status'] = 'Failed: No Action Buttons'
                        continue
                        
                    time.sleep(random.uniform(2, 4))
                    
                    if action_taken == 'connect':
                        # Look for 'Add a note' with robust multi-selectors
                        add_note_selectors = [
                            "div.artdeco-modal button:has-text('Add a note')",
                            "button:has-text('Add a note')",
                            "button[aria-label*='Add a note']",
                            "button.artdeco-button:has-text('Add a note')"
                        ]
                        
                        add_note_clicked = False
                        for sel in add_note_selectors:
                            try:
                                btn = page.locator(sel).locator("visible=true").first
                                if btn.is_visible(timeout=1500):
                                    btn.click(force=True)
                                    add_note_clicked = True
                                    break
                            except Exception:
                                continue
                                
                        if add_note_clicked:
                            time.sleep(1)
                            note_msg_safe = note_msg[:299]
                            try:
                                textarea = page.locator("textarea[name='message'], textarea#custom-message, div.artdeco-modal textarea").locator("visible=true").first
                                textarea.fill(note_msg_safe)
                                time.sleep(1)
                                
                                send_selectors = [
                                    "div.artdeco-modal button:has-text('Send')",
                                    "button:has-text('Send')",
                                    "button[aria-label*='Send']",
                                    "button.artdeco-button--primary:has-text('Send')"
                                ]
                                for s_sel in send_selectors:
                                    try:
                                        s_btn = page.locator(s_sel).locator("visible=true").first
                                        if s_btn.is_visible(timeout=1500):
                                            s_btn.click(force=True)
                                            break
                                    except Exception:
                                        continue
                                        
                                print(f"✅ Connection request WITH custom note sent to {first_name}!")
                                df.at[index, 'Status'] = 'Contacted'
                                df.at[index, 'Contacted_At'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                                df.to_excel(EXCEL_PATH, index=False)
                                print(f"💾 Saved to Excel.")
                            except Exception as ex:
                                print(f"⚠️ Note box issue ({ex}), falling back to direct connect...")
                                add_note_clicked = False

                        if not add_note_clicked:
                            # Fallback: Click 'Send without a note' / 'Send' so connection is still delivered!
                            send_without_note_selectors = [
                                "div.artdeco-modal button:has-text('Send without a note')",
                                "button:has-text('Send without a note')",
                                "div.artdeco-modal button[aria-label*='Send without a note']",
                                "div.artdeco-modal button:has-text('Send')",
                                "button.artdeco-button--primary:has-text('Send')"
                            ]
                            sent_fallback = False
                            for s_sel in send_without_note_selectors:
                                try:
                                    s_btn = page.locator(s_sel).locator("visible=true").first
                                    if s_btn.is_visible(timeout=2000):
                                        s_btn.click(force=True)
                                        sent_fallback = True
                                        break
                                except Exception:
                                    continue

                            if sent_fallback:
                                print(f"✅ Connection request sent to {first_name} (Direct invite - note limit/bypass fallback)!")
                                df.at[index, 'Status'] = 'Contacted'
                                df.at[index, 'Contacted_At'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                                df.to_excel(EXCEL_PATH, index=False)
                                print(f"💾 Saved to Excel.")
                            else:
                                print(f"⚠️ Could not complete connect modal for {first_name} (Requires email verification).")
                                df.at[index, 'Status'] = 'Failed: Connect requires email'

                    elif action_taken == 'message':
                        chat_selectors = [
                            "div.msg-form__contenteditable[role='textbox']",
                            "div[role='textbox'][aria-label*='Write a message']",
                            "div.msg-form__message-texteditor div[role='textbox']",
                            "div.msg-form__contenteditable",
                            "div[contenteditable='true'][role='textbox']"
                        ]
                        
                        chat_box = None
                        for _ in range(8):
                            for c_sel in chat_selectors:
                                try:
                                    loc = page.locator(c_sel).locator("visible=true")
                                    if loc.count() > 0:
                                        chat_box = loc.last
                                        break
                                except Exception:
                                    continue
                            if chat_box:
                                break
                            time.sleep(0.5)

                        if not chat_box:
                            print(f"Could not locate chat box for {first_name}. Skipping.")
                            df.at[index, 'Status'] = 'Failed: No Chat Box'
                            continue
                        
                        # ✅ Check for actual message bubbles ONLY inside the active (last opened) chat window
                        time.sleep(1.5)
                        # Get the last/topmost overlay window (the one just opened for this person)
                        active_overlay = page.locator("div.msg-overlay-conversation-bubble").last
                        existing_msgs = 0
                        try:
                            if active_overlay.is_visible(timeout=2000):
                                existing_msgs = active_overlay.locator(
                                    "div.msg-s-event-listitem__message-bubble, "
                                    "p.msg-s-event-listitem__body"
                                ).count()
                        except Exception:
                            pass
                        
                        if existing_msgs > 0:
                            print(f"💬 Existing conversation detected with {first_name}. Marking as Contacted and skipping.")
                            df.at[index, 'Status'] = 'Contacted'
                            df.at[index, 'Contacted_At'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                            df.to_excel(EXCEL_PATH, index=False)
                            count += 1
                            wait_time = random.uniform(10, 20)
                            print(f"Waiting {int(wait_time)} seconds...")
                            time.sleep(wait_time)
                            continue
                            
                        try:
                            chat_box.focus()
                        except Exception:
                            chat_box.click(force=True)
                            
                        time.sleep(1)
                        page.keyboard.insert_text(dm_msg)
                        time.sleep(random.uniform(2, 5))
                        
                        send_btn_selectors = [
                            "button.msg-form__send-button",
                            "button[type='submit']:has-text('Send')",
                            "button.msg-form__send-btn",
                            "button[aria-label*='Send message']"
                        ]
                        sent = False
                        for s_sel in send_btn_selectors:
                            try:
                                s_loc = page.locator(s_sel).locator("visible=true")
                                if s_loc.count() > 0:
                                    s_btn = s_loc.last
                                    if s_btn.is_enabled():
                                        s_btn.click(force=True)
                                        sent = True
                                        break
                            except Exception:
                                continue

                        if sent:
                            print(f"✅ Direct message sent to {first_name}!")
                            df.at[index, 'Status'] = 'Contacted'
                            df.at[index, 'Contacted_At'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                            df.to_excel(EXCEL_PATH, index=False)
                            print(f"💾 Saved to Excel.")
                        else:
                            print(f"❌ Send button disabled or not found for {first_name}")
                            df.at[index, 'Status'] = 'Failed: Send button disabled'
                        
                except Exception as e:
                    err_str = str(e)
                    print(f"Error processing {name}: {err_str}")
                    if "INTERNET_DISCONNECTED" in err_str or "ERR_NAME_NOT_RESOLVED" in err_str or "net::ERR" in err_str:
                        # Connectivity issue — reset to Pending so it gets retried next run
                        df.at[index, 'Status'] = 'Pending'
                        print(f"⚠️ Connectivity error for {name} — will retry next run.")
                    elif "Connection closed" in err_str or "TargetClosedError" in err_str:
                        df.at[index, 'Status'] = 'Pending'
                        print("CRITICAL: Playwright connection lost (browser crashed). Stopping script!")
                        df.to_excel(EXCEL_PATH, index=False)
                        return
                    else:
                        df.at[index, 'Status'] = 'Error'
                    df.to_excel(EXCEL_PATH, index=False)
                
                count += 1
                
                wait_time = random.uniform(60, 180)
                print(f"Waiting {int(wait_time)} seconds before next profile...")
                time.sleep(wait_time)
                
        except Exception as e:
            print(f"Failed to connect to browser: {str(e)}")
            print("Make sure you started Chrome with: chrome.exe --remote-debugging-port=9222")

    print("\nBatch complete! Excel file updated.")

if __name__ == "__main__":
    run_outreach()
