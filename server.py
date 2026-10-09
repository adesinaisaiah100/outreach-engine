import os
import sys
import time
import json
import random
import re
import threading
import queue
import subprocess
import requests
import pandas as pd
from typing import Optional
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env before any other imports that depend on env vars
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Import our modular engines
from importer import normalize_leads_file
from cohort_engine import (
    get_cohort_message,
    interleave_cohort_batch,
    build_candidate_copy,
    build_founder_copy,
    build_recruiter_copy
)
from lead_miner import run_lead_mining
from icp_cleaner import audit_leads_dataset, AUDITED_LEADS_PATH
from outreach import (
    batch_enrich_leads,
    DEBUG_PORT,
    CHROME_USER_DATA,
)
import webbrowser
from playwright.sync_api import sync_playwright

app = FastAPI(title="CoreCV Outreach Dashboard")

@app.on_event("startup")
def auto_open_dashboard():
    def _open():
        time.sleep(1.2)
        try:
            webbrowser.open("http://127.0.0.1:8000")
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
CURRENT_LEDGER_PATH = os.path.join(DATA_DIR, "active_leads.xlsx")

class BotState:
    def __init__(self):
        self.is_running = False
        self.stop_requested = False
        self.total_leads = 0
        self.contacted_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.current_lead = ""
        self.log_queue = queue.Queue()
        self.active_df: Optional[pd.DataFrame] = None
        self.mapping_report = {}
        
    def log(self, message: str, level: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        entry = {"time": timestamp, "msg": message, "level": level}
        self.log_queue.put(entry)
        print(f"[{timestamp}] [{level.upper()}] {message}")

state = BotState()

# Auto-load audited ledger or active ledger if it exists from a previous session
target_load_path = AUDITED_LEADS_PATH if os.path.exists(AUDITED_LEADS_PATH) else CURRENT_LEDGER_PATH
if os.path.exists(target_load_path):
    try:
        state.active_df = pd.read_excel(target_load_path)
        state.total_leads = len(state.active_df)
        hr_keywords = ['hr', 'talent', 'recruit', 'people', 'hiring', 'human resource']
        hr_count = int(state.active_df['Position'].astype(str).str.lower().apply(lambda x: any(k in x for k in hr_keywords)).sum())
        cands_count = int((state.active_df.get('Persona_Bucket', '') == 'CANDIDATE_70').sum()) if 'Persona_Bucket' in state.active_df.columns else (state.total_leads - hr_count)
        recs_count = int((state.active_df.get('Persona_Bucket', '') == 'RECRUITER_20').sum()) if 'Persona_Bucket' in state.active_df.columns else hr_count
        fnds_count = int((state.active_df.get('Persona_Bucket', '') == 'FOUNDER_10').sum()) if 'Persona_Bucket' in state.active_df.columns else 0
        state.mapping_report = {
            "detected_url_col": "LinkedIn URL",
            "detected_name_col": "First Name",
            "detected_pos_col": "Position",
            "total_valid_leads": len(state.active_df),
            "hr_leads": hr_count,
            "tech_leads": len(state.active_df) - hr_count,
            "candidates": cands_count,
            "recruiters": recs_count,
            "founders": fnds_count
        }
        loaded_name = os.path.basename(target_load_path)
        state.log(f"📁 Loaded Ledger ({loaded_name}): {state.total_leads} leads ready ({cands_count} Cands, {recs_count} Recs, {fnds_count} Founders).", "success")
    except Exception as e:
        print(f"Error loading ledger: {e}")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>CoreCV Outreach Dashboard - Loading static UI...</h1>"

@app.post("/api/upload")
async def upload_leads_file(file: UploadFile = File(...)):
    """Receives any messy CSV or Excel file, normalizes it, and saves active ledger."""
    contents = await file.read()
    try:
        clean_df, report = normalize_leads_file(contents, file.filename)
        state.active_df = clean_df
        state.mapping_report = report
        state.total_leads = len(clean_df)
        
        # Save standardized ledger
        clean_df.to_excel(CURRENT_LEDGER_PATH, index=False)
        state.log(f"📁 Ingested '{file.filename}': Found {report['total_valid_leads']} valid leads ({report['hr_leads']} HRs, {report['tech_leads']} Candidates).", "success")
        
        # Return sample preview (first 10 rows)
        preview_rows = clean_df.head(10).fillna('').to_dict(orient="records")
        return {
            "status": "success",
            "filename": file.filename,
            "report": report,
            "preview": preview_rows
        }
    except Exception as e:
        state.log(f"❌ Failed to parse uploaded file: {str(e)}", "error")
        return {"status": "error", "message": str(e)}

class CampaignConfig(BaseModel):
    daily_limit: int = 25
    min_delay: int = 45
    max_delay: int = 120
    target_mode: str = "dynamic_cohort"  # "dynamic_cohort", "candidates_only", "hr_only", "all"
    candidate_pct: int = 70
    recruiter_pct: int = 20
    founder_pct: int = 10

def is_hr_lead(row):
    persona = str(row.get('Persona', '')).strip().upper()
    bucket = str(row.get('Persona_Bucket', '')).strip().upper()
    if persona == 'HR' or bucket in ['RECRUITER_20', 'FOUNDER_10']:
        return True
    hr_keywords = [
        'hr', 'human resource', 'talent', 'recruit', 'people', 
        'hiring', 'headhunter', 'staffing', 'talent acquisition',
        'people operations', 'talent lead', 'recruitment', 'hrbp'
    ]
    pos = str(row.get('Position', '')).lower()
    return any(k in pos for k in hr_keywords)

def run_outreach_worker(config: CampaignConfig):
    state.is_running = True
    state.stop_requested = False
    state.log("🚀 Starting CoreCV Outreach Engine...", "info")
    
    if state.active_df is None or state.active_df.empty:
        state.log("❌ No leads dataset loaded. Please drop an Excel/CSV file first.", "error")
        state.is_running = False
        return

    df = state.active_df
    
    # Filter pending leads
    def should_skip(status):
        if pd.isna(status):
            return False
        s = str(status).strip()
        return s == 'Contacted' or s == 'Invalid URL' or s.startswith('Failed:') or s.startswith('Skipped:')
    
    pending_mask = ~df['Status'].apply(should_skip)
    
    # Smart Persona Target Filtering
    if config.target_mode == "dynamic_cohort":
        mode_label = f"⚡ Dynamic Cohort ({config.candidate_pct}% Cand / {config.recruiter_pct}% Rec / {config.founder_pct}% Fnd)"
        batch = interleave_cohort_batch(
            df,
            candidate_pct=config.candidate_pct,
            recruiter_pct=config.recruiter_pct,
            founder_pct=config.founder_pct,
            daily_limit=config.daily_limit
        )
    elif config.target_mode == "hr_only":
        mode_mask = df.apply(is_hr_lead, axis=1)
        mode_label = "🎯 HR / Recruiters Only (Priority)"
        matched_indices = df[pending_mask & mode_mask].index
        if len(matched_indices) == 0:
            state.log(f"🎉 No pending leads remaining for mode: {mode_label}!", "success")
            state.is_running = False
            return
        batch_indices = matched_indices[:config.daily_limit]
        batch = df.loc[batch_indices].copy()
    elif config.target_mode == "candidates_only":
        mode_mask = ~df.apply(is_hr_lead, axis=1)
        mode_label = "💻 Tech Candidates Only"
        matched_indices = df[pending_mask & mode_mask].index
        if len(matched_indices) == 0:
            state.log(f"🎉 No pending leads remaining for mode: {mode_label}!", "success")
            state.is_running = False
            return
        batch_indices = matched_indices[:config.daily_limit]
        batch = df.loc[batch_indices].copy()
    else:
        mode_mask = pd.Series(True, index=df.index)
        mode_label = "🌐 All Leads (Sequential)"
        matched_indices = df[pending_mask & mode_mask].index
        if len(matched_indices) == 0:
            state.log(f"🎉 No pending leads remaining for mode: {mode_label}!", "success")
            state.is_running = False
            return
        batch_indices = matched_indices[:config.daily_limit]
        batch = df.loc[batch_indices].copy()

    if batch.empty:
        state.log(f"🎉 No pending leads remaining for mode: {mode_label}!", "success")
        state.is_running = False
        return

    state.log(f"🎯 Mode [{mode_label}] | Processing {len(batch)} targeted profiles (Cap: {config.daily_limit}).", "info")

    # Step 1: Deep Gemini Enrichment (Names, Gender, Title, Nigerian Origin, Persona)
    leads_payload = []
    for _, row in batch.iterrows():
        raw_name = str(row.get('First Name', '')) + " " + str(row.get('Last Name', ''))
        raw_role = str(row.get('Position', ''))
        leads_payload.append({"name": raw_name.strip(), "role": raw_role.strip()})

    state.log("🤖 Running Gemini Cultural & Gender Classification...", "info")
    enriched_leads = batch_enrich_leads(leads_payload)

    batch['Clean_Role'] = [e['clean_role'] for e in enriched_leads]
    batch['Persona'] = [e['persona'] for e in enriched_leads]
    batch['Title'] = [e['title'] for e in enriched_leads]
    batch['Is_Nigerian'] = [e['is_nigerian'] for e in enriched_leads]

    with sync_playwright() as p:
        try:
            state.log("🧹 Closing previous Chrome sessions...", "info")
            subprocess.call("taskkill /F /IM chrome.exe /T", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)

            state.log(f"🌐 Launching local Chrome with debugging on port {DEBUG_PORT}...", "info")
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            chrome_cmd = f'"{chrome_path}" --remote-debugging-port={DEBUG_PORT} --user-data-dir="{CHROME_USER_DATA}" --no-default-browser-check --disable-crash-reporter --disable-infobars https://www.linkedin.com'
            subprocess.Popen(chrome_cmd, shell=True)

            # Wait for CDP ready
            cdp_ready = False
            for attempt in range(25):
                try:
                    resp = requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=2)
                    if resp.status_code == 200:
                        state.log(f"✅ Chrome CDP ready on port {DEBUG_PORT} (attempt {attempt+1}).", "info")
                        cdp_ready = True
                        break
                except Exception:
                    pass
                time.sleep(1)

            if not cdp_ready:
                state.log("❌ Chrome failed to start with CDP. Aborting.", "error")
                state.is_running = False
                return

            time.sleep(3)
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}", timeout=30000)
            context = browser.contexts[0]
            
            # Use existing tab (LinkedIn loaded) instead of creating a new one
            if context.pages:
                page = context.pages[0]
                state.log(f"📄 Using existing Chrome tab: {page.url[:60]}...", "info")
            else:
                page = context.new_page()
                state.log("📄 Created new Chrome tab.", "info")

            processed_count = 0
            for idx, row in batch.iterrows():
                if state.stop_requested:
                    state.log("⏹️ Campaign paused/stopped by user.", "warning")
                    break

                first_name = str(row.get('First Name', 'there')).strip()
                last_name = str(row.get('Last Name', '')).strip()
                full_name = f"{first_name} {last_name}".strip()
                linkedin_url = str(row.get('LinkedIn URL', '')).strip()
                clean_r = row['Clean_Role']
                persona = row['Persona']
                title = row['Title']
                is_nigerian = row['Is_Nigerian']

                state.current_lead = full_name

                # Normalize and sanitize LinkedIn URL
                raw_url = str(row.get('LinkedIn URL', '')).strip()
                if not raw_url or 'linkedin.com/in/' not in raw_url:
                    state.log(f"⏭️ Skipping {full_name}: Not a profile link ({raw_url[:40]}...)", "warning")
                    df.at[idx, 'Status'] = 'Invalid URL'
                    df.to_excel(CURRENT_LEDGER_PATH, index=False)
                    continue

                # Standardize regional subdomains (e.g. ng.linkedin.com -> www.linkedin.com)
                clean_url = re.sub(r'https?://[a-z]{2,3}\.linkedin\.com', 'https://www.linkedin.com', raw_url)
                if not clean_url.startswith('http'):
                    clean_url = 'https://' + clean_url
                clean_url = clean_url.split('?')[0].rstrip('/')

                if not is_nigerian:
                    state.log(f"⏭️ Skipping {full_name}: Classified non-Nigerian by Gemini.", "info")
                    df.at[idx, 'Status'] = 'Skipped: Non-Nigerian'
                    df.to_excel(CURRENT_LEDGER_PATH, index=False)
                    state.skipped_count += 1
                    continue

                # Prepare cohort strategy persona messages
                dm_msg = get_cohort_message(row, is_connect_note=False)
                note_msg = get_cohort_message(row, is_connect_note=True)

                state.log(f"[{processed_count+1}/{len(batch)}] Visiting {full_name} ({persona} | Role: {clean_r} | Title: {title or 'None'})...", "info")

                try:
                    # Close existing chat bubbles
                    close_btns = page.locator("button.msg-overlay-bubble-header__control--close, button[aria-label*='Close'][class*='msg-']").all()
                    for b in close_btns:
                        try:
                            b.click(timeout=1000)
                        except Exception:
                            pass

                    # Navigate safely with retry
                    nav_ok = False
                    for nav_try in range(2):
                        try:
                            page.goto(clean_url, timeout=45000, wait_until="domcontentloaded")
                            time.sleep(random.uniform(3, 5))
                            try:
                                page.wait_for_selector("main, div.ph5, section.artdeco-card", timeout=6000)
                            except Exception:
                                pass
                            nav_ok = True
                            break
                        except Exception as n_err:
                            state.log(f"⚠️ Navigation retry {nav_try+1} for {full_name}: {str(n_err)[:60]}", "warning")
                            time.sleep(2)

                    if not nav_ok:
                        state.log(f"❌ Failed to load profile for {full_name}. Skipping.", "error")
                        df.at[idx, 'Status'] = 'Failed: Network Error'
                        df.to_excel(CURRENT_LEDGER_PATH, index=False)
                        state.failed_count += 1
                        continue

                    # Detect available action (Connect priority or Message)
                    from action_dispatcher import trigger_profile_action
                    action_res = trigger_profile_action(page)
                    action_taken = action_res.get('action')

                    if action_taken == 'already_pending':
                        state.log(f"ℹ️ Invitation already pending for {full_name}. Marking as Contacted.", "info")
                        df.at[idx, 'Status'] = 'Contacted'
                        df.at[idx, 'Contacted_At'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                        df.to_excel(CURRENT_LEDGER_PATH, index=False)
                        state.contacted_count += 1
                        continue

                    if not action_taken:
                        state.log(f"⚠️ No Connect or Message button found for {full_name}. Skipping.", "warning")
                        df.at[idx, 'Status'] = 'Failed: No Action Buttons'
                        df.to_excel(CURRENT_LEDGER_PATH, index=False)
                        state.failed_count += 1
                        continue

                    state.log(f"🎯 Executing '{action_taken}' action for {full_name}...", "info")
                    time.sleep(random.uniform(1, 2))

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
                            note_msg_safe = note_msg[:280]
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
                                        
                                state.log(f"✅ Connection request WITH custom note sent to {full_name}!", "success")
                                df.at[idx, 'Status'] = 'Contacted'
                                df.at[idx, 'Contacted_At'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                                df.to_excel(CURRENT_LEDGER_PATH, index=False)
                                state.contacted_count += 1
                            except Exception as ex:
                                state.log(f"⚠️ Note box issue ({ex}), falling back to direct connect...", "warning")
                                add_note_clicked = False

                        if not add_note_clicked:
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
                                state.log(f"✅ Connection request sent to {full_name} (Direct invite)!", "success")
                                df.at[idx, 'Status'] = 'Contacted'
                                df.at[idx, 'Contacted_At'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                                df.to_excel(CURRENT_LEDGER_PATH, index=False)
                                state.contacted_count += 1
                            else:
                                state.log(f"⚠️ Could not complete connect modal for {full_name} (Email verification required).", "warning")
                                df.at[idx, 'Status'] = 'Failed: Connect requires email'
                                df.to_excel(CURRENT_LEDGER_PATH, index=False)
                                state.failed_count += 1

                    elif action_taken == 'message':
                        # Navigate directly to full messaging compose page (no button click needed!)
                        compose_url = action_res.get('compose_url') or action_res.get('href', '')
                        if not compose_url:
                            state.log(f"⚠️ No compose URL for {full_name}. Skipping.", "warning")
                            df.at[idx, 'Status'] = 'Failed: No compose URL'
                            state.failed_count += 1
                            continue

                        state.log(f"📨 Navigating to messaging page for {full_name}...", "info")
                        page.goto(compose_url, timeout=45000, wait_until="domcontentloaded")
                        time.sleep(random.uniform(3, 5))

                        # Full messaging page textbox selectors
                        msg_textbox_selectors = [
                            "div.msg-form__contenteditable[role='textbox']",
                            "div[role='textbox'][aria-label*='Write a message']",
                            "div[role='textbox'][contenteditable='true']",
                            "div.msg-form__message-texteditor div[role='textbox']",
                            "div.msg-form__contenteditable",
                            "div[contenteditable='true'][aria-label*='message']",
                            "div[contenteditable='true'][data-artdeco-is-focused]",
                        ]

                        msg_box = None
                        for attempt in range(15):
                            for sel in msg_textbox_selectors:
                                try:
                                    loc = page.locator(sel).locator("visible=true")
                                    if loc.count() > 0:
                                        msg_box = loc.last
                                        break
                                except Exception:
                                    continue
                            if msg_box:
                                state.log(f"💬 Message box found on attempt {attempt+1}/15.", "info")
                                break
                            time.sleep(0.75)

                        if not msg_box:
                            state.log(f"⚠️ Could not find message textbox for {full_name}. Skipping.", "warning")
                            try:
                                page.screenshot(path=os.path.join(DATA_DIR, f"debug_{full_name.replace(' ','_')}.png"))
                            except Exception:
                                pass
                            df.at[idx, 'Status'] = 'Failed: No Message Box'
                            state.failed_count += 1
                            continue

                        # Check for existing conversation
                        existing_msgs = 0
                        try:
                            msg_items = page.locator("li.msg-s-message-list__event, div.msg-s-event-listitem, li[class*='msg-s-message']")
                            existing_msgs = msg_items.count()
                        except Exception:
                            pass

                        if existing_msgs > 0:
                            state.log(f"💬 Existing conversation ({existing_msgs} msgs) with {full_name}. Marking as Contacted.", "info")
                            df.at[idx, 'Status'] = 'Contacted'
                            df.at[idx, 'Contacted_At'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                            df.to_excel(CURRENT_LEDGER_PATH, index=False)
                            state.contacted_count += 1
                            continue

                        # Type the message
                        try:
                            msg_box.focus()
                        except Exception:
                            msg_box.click(force=True)

                        time.sleep(0.5)
                        page.keyboard.insert_text(dm_msg)
                        time.sleep(random.uniform(2, 4))

                        # Click Send
                        send_btn_selectors = [
                            "button.msg-form__send-button",
                            "button.msg-form__send-btn",
                            "button[type='submit']:has-text('Send')",
                            "button[aria-label*='Send']",
                            "button:has-text('Send')",
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
                            state.log(f"✅ Direct message sent to {full_name}!", "success")
                            df.at[idx, 'Status'] = 'Contacted'
                            df.at[idx, 'Contacted_At'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                            df.to_excel(CURRENT_LEDGER_PATH, index=False)
                            state.contacted_count += 1
                        else:
                            state.log(f"❌ Send button not found/disabled for {full_name}", "error")
                            df.at[idx, 'Status'] = 'Failed: Send button disabled'
                            state.failed_count += 1

                except Exception as ex:
                    state.log(f"❌ Error processing {full_name}: {str(ex)}", "error")
                    df.at[idx, 'Status'] = 'Error'
                    df.to_excel(CURRENT_LEDGER_PATH, index=False)

                processed_count += 1
                delay = random.uniform(config.min_delay, config.max_delay)
                state.log(f"⏳ Waiting {int(delay)}s safety interval before next lead...", "info")
                time.sleep(delay)

        except Exception as e:
            state.log(f"🚨 Playwright engine error: {str(e)}", "error")
        finally:
            state.is_running = False
            state.current_lead = ""
            state.log("🏁 Campaign batch session completed!", "success")

@app.post("/api/start")
async def start_campaign(config: CampaignConfig, background_tasks: BackgroundTasks):
    if state.is_running:
        return {"status": "error", "message": "Campaign is already running!"}
    background_tasks.add_task(run_outreach_worker, config)
    return {"status": "success", "message": "Campaign launched in background worker."}

@app.post("/api/stop")
async def stop_campaign():
    if not state.is_running:
        return {"status": "error", "message": "No campaign is running."}
    state.stop_requested = True
    state.log("🛑 Stop requested. Finishing current profile then pausing...", "warning")
    return {"status": "success", "message": "Stop signal sent."}

@app.get("/api/status")
async def get_status():
    return {
        "is_running": state.is_running,
        "total_leads": state.total_leads,
        "contacted_count": state.contacted_count,
        "skipped_count": state.skipped_count,
        "failed_count": state.failed_count,
        "current_lead": state.current_lead,
        "mapping_report": state.mapping_report
    }

@app.get("/api/logs")
async def stream_logs():
    def event_stream():
        while True:
            try:
                item = state.log_queue.get(timeout=25)
                yield f"data: {json.dumps(item)}\n\n"
            except queue.Empty:
                yield f": keep-alive\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/api/download")
async def download_active_ledger():
    if os.path.exists(CURRENT_LEDGER_PATH):
        with open(CURRENT_LEDGER_PATH, "rb") as f:
            content = f.read()
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=corecv_outreach_leads_updated.xlsx"}
        )
    return {"status": "error", "message": "No active ledger file found."}

@app.get("/api/download_hr")
async def download_hr_ledger():
    hr_path = os.path.join(DATA_DIR, "hr_leads.xlsx")

    if not os.path.exists(hr_path) and state.active_df is not None:
        try:
            from extract_hr import extract_clean_hr
            extract_clean_hr()
        except Exception:
            pass

    if os.path.exists(hr_path):
        with open(hr_path, "rb") as f:
            content = f.read()
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=hr_recruiter_leads.xlsx"}
        )
    return {"status": "error", "message": "HR leads file not found."}

@app.get("/api/download_candidates")
async def download_candidates_ledger():
    cand_path = os.path.join(DATA_DIR, "candidate_master.xlsx")

    # If candidate_master does not exist yet, extract it on the fly
    if not os.path.exists(cand_path) and os.path.exists(AUDITED_LEADS_PATH):
        try:
            df = pd.read_excel(AUDITED_LEADS_PATH)
            cands = df[df.get('Persona_Bucket', '') == 'CANDIDATE_70']
            cands.to_excel(cand_path, index=False)
        except Exception:
            pass

    if os.path.exists(cand_path):
        with open(cand_path, "rb") as f:
            content = f.read()
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=candidate_master.xlsx"}
        )
    return {"status": "error", "message": "Candidate master file not found."}

@app.post("/api/load_preset")
async def load_preset_file(preset: str = "hr"):
    try:
        if preset == "candidates" or preset == "candidate":
            cand_path = os.path.join(DATA_DIR, "candidate_master.xlsx")
            if not os.path.exists(cand_path) and os.path.exists(AUDITED_LEADS_PATH):
                df = pd.read_excel(AUDITED_LEADS_PATH)
                cands = df[df.get('Persona_Bucket', '') == 'CANDIDATE_70']
                cands.to_excel(cand_path, index=False)
            if os.path.exists(cand_path):
                state.active_df = pd.read_excel(cand_path)
                state.total_leads = len(state.active_df)
                state.log(f"📁 Loaded Preset: Candidate Master List ({state.total_leads} Builders ready).", "success")
                return {"status": "success", "message": f"Loaded Candidates ({state.total_leads} leads)"}
        elif preset == "hr":
            hr_path = os.path.join(DATA_DIR, "hr_leads.xlsx")
            if not os.path.exists(hr_path):
                from extract_hr import extract_clean_hr
                extract_clean_hr()
            clean_df, report = normalize_leads_file(hr_path, "hr_leads.xlsx")
            state.active_df = clean_df
            state.mapping_report = report
            state.total_leads = len(clean_df)
            clean_df.to_excel(CURRENT_LEDGER_PATH, index=False)
            state.log(f"📁 Loaded Preset: HR / Recruiter Specialist List ({len(clean_df)} Leads ready).", "success")
            return {"status": "success", "message": f"Loaded HR list ({len(clean_df)} leads)", "report": report}
        elif preset == "cohort_audited" or preset == "audited":
            if os.path.exists(AUDITED_LEADS_PATH):
                state.active_df = pd.read_excel(AUDITED_LEADS_PATH)
                state.total_leads = len(state.active_df)
                state.log(f"📁 Loaded Cohort Audited Pool: {state.total_leads} leads ready.", "success")
                return {"status": "success", "message": f"Loaded Audited Cohort Pool ({state.total_leads} leads)"}
    except Exception as e:
        state.log(f"❌ Failed to load preset '{preset}': {str(e)}", "error")
        return {"status": "error", "message": str(e)}
    return {"status": "error", "message": "Invalid preset name."}

@app.post("/api/mine_leads")
async def api_mine_leads(count: int = 50, background_tasks: BackgroundTasks = None):
    """Triggers background lead mining from GitHub and Nigerian Tech Directory."""
    def _worker():
        try:
            state.log(f"🔎 Mining {count} technical builders & startup hiring partners...", "info")
            mined_df = run_lead_mining(candidate_count=count, include_companies=True)
            state.active_df = mined_df
            state.total_leads = len(mined_df)
            state.log(f"✅ Lead mining completed! Active pool now has {len(mined_df)} leads.", "success")
        except Exception as ex:
            state.log(f"❌ Lead mining error: {str(ex)}", "error")

    threading.Thread(target=_worker, daemon=True).start()
    return {"status": "started", "message": f"Lead miner started in background for {count} candidates + hiring partners."}

@app.post("/api/audit_icp")
async def api_audit_icp(background_tasks: BackgroundTasks = None):
    """Triggers background ICP auditing based on corecvfouningcohortstrategy.pdf."""
    if state.active_df is None or state.active_df.empty:
        return {"status": "error", "message": "No active dataset loaded to audit."}

    def _worker():
        try:
            state.log(f"🔍 Auditing {len(state.active_df)} leads against Strategy ICP rubric...", "info")
            audited_df = audit_leads_dataset(state.active_df)
            state.active_df = audited_df
            state.total_leads = len(audited_df)
            passed = int(audited_df["ICP_Fit"].sum())
            state.log(f"✅ ICP Audit Complete! {passed}/{len(audited_df)} leads qualified. Audited ledger ready.", "success")
        except Exception as ex:
            state.log(f"❌ ICP audit error: {str(ex)}", "error")

    threading.Thread(target=_worker, daemon=True).start()
    return {"status": "started", "message": "ICP Audit started in background."}

@app.get("/api/leads")
async def get_leads(
    mode: str = "all",      # "all", "hr", "candidate", "pending", "contacted"
    search: str = "",
    limit: int = 100,
    offset: int = 0
):
    if state.active_df is None or state.active_df.empty:
        return {"total": 0, "leads": [], "stats": {"total": 0, "hr": 0, "candidate": 0, "pending": 0, "contacted": 0}}

    df = state.active_df.copy()
    
    # Classify Persona for display
    hr_mask = df.apply(is_hr_lead, axis=1)
    df['Display_Persona'] = hr_mask.apply(lambda is_h: 'HR' if is_h else 'Candidate')

    # Fill NaN values for JSON serialization
    df['Company'] = df['Company'].fillna('') if 'Company' in df.columns else ''
    df['Location'] = df['Location'].fillna('Nigeria') if 'Location' in df.columns else 'Nigeria'
    df['Contacted_At'] = df['Contacted_At'].fillna('') if 'Contacted_At' in df.columns else ''
    df['Status'] = df['Status'].fillna('Pending')

    # Global counts
    total_count = len(df)
    hr_count = int(hr_mask.sum())
    candidate_count = total_count - hr_count
    pending_count = int((df['Status'] == 'Pending').sum())
    contacted_count = int((df['Status'] == 'Contacted').sum())

    filtered = df

    # Search filter
    if search:
        s = search.lower().strip()
        search_mask = (
            filtered['First Name'].astype(str).str.lower().str.contains(s) |
            filtered['Last Name'].astype(str).str.lower().str.contains(s) |
            filtered['Position'].astype(str).str.lower().str.contains(s) |
            filtered['Company'].astype(str).str.lower().str.contains(s) |
            filtered['LinkedIn URL'].astype(str).str.lower().str.contains(s)
        )
        filtered = filtered[search_mask]

    # Category filter
    if mode == "hr":
        filtered = filtered[filtered['Display_Persona'] == 'HR']
    elif mode == "candidate":
        filtered = filtered[filtered['Display_Persona'] == 'Candidate']
    elif mode == "pending":
        filtered = filtered[filtered['Status'] == 'Pending']
    elif mode == "contacted":
        filtered = filtered[filtered['Status'] == 'Contacted']

    filtered_total = len(filtered)
    page_leads = filtered.iloc[offset:offset + limit].fillna('').to_dict(orient="records")

    return {
        "total": filtered_total,
        "leads": page_leads,
        "stats": {
            "total": total_count,
            "hr": hr_count,
            "candidate": candidate_count,
            "pending": pending_count,
            "contacted": contacted_count
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)


