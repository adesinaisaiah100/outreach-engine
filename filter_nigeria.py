import os
import time
import subprocess
import requests
import pandas as pd
from playwright.sync_api import sync_playwright
import sys

sys.stdout.reconfigure(encoding='utf-8')

EXCEL_PATH = r"C:\Users\Isaiah\Downloads\corecv_hr_leads_aggressive.xlsx"
OUTPUT_PATH = r"C:\Users\Isaiah\Downloads\corecv_hr_leads_nigeria.xlsx"
DEBUG_PORT = 9223

def filter_nigerian_hrs():
    df = pd.read_excel(EXCEL_PATH)
    nigerian_leads = []
    
    # We only have 30 rows, so we can check all
    with sync_playwright() as p:
        print("Killing any existing Chrome processes...")
        subprocess.call("taskkill /F /IM chrome.exe /T", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        
        print(f"Starting fresh Chrome on port {DEBUG_PORT}...")
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        chrome_args = [
            chrome_path,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir=C:\\Users\\Isaiah\\chrome_automation",
            "--restore-last-session=false",
            "--no-default-browser-check",
            "--disable-crash-reporter",
            "--disable-infobars",
            "https://www.linkedin.com"
        ]
        subprocess.Popen(chrome_args)
        
        print("Waiting for Chrome to be ready...")
        for i in range(20):
            try:
                resp = requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=2)
                if resp.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(1)
        
        time.sleep(3)
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}", timeout=30000)
        context = browser.contexts[0]
        page = context.new_page()
        
        nigeria_keywords = ['nigeria', 'lagos', 'abuja', 'ibadan', 'port harcourt', 'kano', 'enugu']
        
        for index, row in df.iterrows():
            url = row['LinkedIn URL']
            if not isinstance(url, str) or 'linkedin.com' not in url:
                continue
                
            # If it's a post URL, we can't easily extract profile location without clicking through, 
            # but we can check if the URL itself has 'ng.linkedin' or if the post text is Nigerian
            if 'ng.linkedin.com' in url or any(k in str(url).lower() for k in nigeria_keywords):
                print(f"[FAST MATCH] URL implies Nigeria: {url}")
                nigerian_leads.append(row)
                continue
                
            print(f"[{index+1}/{len(df)}] Visiting {url} ...")
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(3)
                
                # Check page text for Nigerian locations
                # This works for both profiles and posts
                page_text = page.locator("body").inner_text().lower()
                
                is_nigerian = any(k in page_text for k in nigeria_keywords)
                
                if is_nigerian:
                    print("✅ Found Nigerian location markers.")
                    
                    # Try to extract real name if on a profile page
                    try:
                        name_el = page.locator("h1").first
                        if name_el.is_visible(timeout=2000):
                            full_name = name_el.inner_text().strip()
                            parts = full_name.split()
                            if len(parts) >= 2:
                                row['First Name'] = parts[0]
                                row['Last Name'] = " ".join(parts[1:])
                    except Exception:
                        pass
                        
                    nigerian_leads.append(row)
                else:
                    print("❌ Not Nigeria.")
                    
            except Exception as e:
                print(f"Error visiting {url}: {e}")
                
        # Save filtered results
        if nigerian_leads:
            final_df = pd.DataFrame(nigerian_leads)
            final_df.to_excel(OUTPUT_PATH, index=False)
            print(f"\nSaved {len(final_df)} Nigerian HR decision-makers to {OUTPUT_PATH}")
        else:
            print("\nFound 0 Nigerian HR decision-makers in this batch.")

if __name__ == '__main__':
    filter_nigerian_hrs()
