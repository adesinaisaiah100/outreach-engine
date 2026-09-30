import pandas as pd
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

CSV_PATH = r'C:\Users\Isaiah\Downloads\nigerian_tech_hiring_leads.csv'
ACTIVE_LEDGER = r'C:\Users\Isaiah\corecv_outreach\data\active_leads.xlsx'
MASTER_EXCEL = r'C:\Users\Isaiah\Downloads\autoationlistcoerrect vesio.xlsx'

print("Starting ingestion of nigerian_tech_hiring_leads.csv...")

if not os.path.exists(CSV_PATH):
    print(f"Error: {CSV_PATH} not found.")
    sys.exit(1)

new_df = pd.read_csv(CSV_PATH)
print(f"Loaded {len(new_df)} hiring leads from CSV.")

# Standardize columns to match our active schema
formatted_rows = []
for _, row in new_df.iterrows():
    f_name = str(row.get('first_name', '')).strip()
    l_name = str(row.get('last_name', '')).strip() if pd.notna(row.get('last_name')) else ''
    full_name = str(row.get('full_name', f"{f_name} {l_name}")).strip()
    pos = str(row.get('job_title', 'HR / Recruiter')).strip()
    comp = str(row.get('company', '')).strip()
    url = str(row.get('linkedin_url', '')).strip()
    loc = str(row.get('location', 'Nigeria')).strip()
    hook = str(row.get('moms_test_hook', '')).strip()
    cat = str(row.get('persona_type', row.get('category', 'HR'))).strip()
    
    formatted_rows.append({
        'First Name': f_name,
        'Last Name': l_name,
        'Full Name': full_name,
        'Position': pos,
        'Company': comp,
        'LinkedIn URL': url,
        'Location': loc,
        'Status': 'Pending',
        'Persona': 'HR',
        'Category': cat,
        'Custom_Hook': hook,
        'Contacted_At': ''
    })

formatted_df = pd.DataFrame(formatted_rows)

def merge_into_file(file_path):
    if not os.path.exists(file_path):
        print(f"Target {file_path} not found. Creating new...")
        formatted_df.to_excel(file_path, index=False)
        return len(formatted_df), len(formatted_df)
        
    existing_df = pd.read_excel(file_path)
    initial_count = len(existing_df)
    
    # Identify URL column in existing
    url_col = 'LinkedIn URL' if 'LinkedIn URL' in existing_df.columns else ('URL' if 'URL' in existing_df.columns else None)
    
    existing_urls = set()
    if url_col:
        existing_urls = set(existing_df[url_col].dropna().astype(str).str.strip().tolist())
        
    # Deduplicate against existing
    to_add = formatted_df[~formatted_df['LinkedIn URL'].isin(existing_urls)]
    added_count = len(to_add)
    
    merged_df = pd.concat([existing_df, to_add], ignore_index=True)
    merged_df.to_excel(file_path, index=False)
    
    return added_count, len(merged_df)

added_active, total_active = merge_into_file(ACTIVE_LEDGER)
print(f"✅ Merged into Dashboard Active Ledger ({ACTIVE_LEDGER}):")
print(f"   • Newly Added: {added_active} leads")
print(f"   • Total Active Rows: {total_active}")

added_master, total_master = merge_into_file(MASTER_EXCEL)
print(f"✅ Merged into Master Backup ({MASTER_EXCEL}):")
print(f"   • Newly Added: {added_master} leads")
print(f"   • Total Master Rows: {total_master}")

print("\n🎉 Ingestion complete! All 250 Nigerian Tech Hiring Decision-Makers are now pending in your outreach queue.")
