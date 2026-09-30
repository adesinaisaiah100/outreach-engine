import os
import pandas as pd
import re

def extract_clean_hr():
    active_path = r"C:\Users\Isaiah\corecv_outreach\data\active_leads.xlsx"
    df = pd.read_excel(active_path)

    # Filter HRs
    hr_keywords = [
        'hr', 'human resource', 'talent', 'recruit', 'people', 
        'hiring', 'headhunter', 'staffing', 'talent acquisition',
        'people operations', 'talent lead', 'recruitment', 'hrbp'
    ]
    
    is_persona_hr = df['Persona'].astype(str).str.upper() == 'HR'
    has_hr_title = df['Position'].astype(str).str.lower().apply(lambda x: any(k in x for k in hr_keywords))
    hr_mask = is_persona_hr | has_hr_title
    hr_df = df[hr_mask].copy()

    # Clean text columns
    for col in ['First Name', 'Last Name', 'Position', 'Company', 'Location']:
        if col in hr_df.columns:
            hr_df[col] = hr_df[col].fillna('').astype(str).str.strip()
        else:
            hr_df[col] = ''

    # Clean Full Name
    if 'Full Name' not in hr_df.columns or hr_df['Full Name'].str.len().sum() == 0:
        hr_df['Full Name'] = hr_df.apply(lambda r: f"{r['First Name']} {r['Last Name']}".strip(), axis=1)

    # Validate & Clean LinkedIn URLs
    hr_df['LinkedIn URL'] = hr_df['LinkedIn URL'].fillna('').astype(str).str.strip()
    hr_df = hr_df[hr_df['LinkedIn URL'].str.contains('linkedin.com', case=False, na=False)].copy()

    # Deduplicate by LinkedIn URL
    hr_df['clean_url'] = hr_df['LinkedIn URL'].str.lower().str.rstrip('/').str.split('?').str[0]
    hr_df = hr_df.drop_duplicates(subset=['clean_url']).copy()
    hr_df.drop(columns=['clean_url'], inplace=True)

    # Clean Status & Contacted_At
    if 'Status' not in hr_df.columns:
        hr_df['Status'] = 'Pending'
    else:
        hr_df['Status'] = hr_df['Status'].fillna('Pending')

    if 'Contacted_At' not in hr_df.columns:
        hr_df['Contacted_At'] = ''
    else:
        hr_df['Contacted_At'] = hr_df['Contacted_At'].fillna('')

    # Clean column ordering
    base_cols = ['First Name', 'Last Name', 'Full Name', 'Position', 'Company', 'Location', 'LinkedIn URL', 'Status', 'Contacted_At']
    extra_cols = ['Category', 'Custom_Hook', 'moms_test_hook']
    
    final_cols = [c for c in base_cols if c in hr_df.columns]
    for c in extra_cols:
        if c in hr_df.columns and c not in final_cols:
            final_cols.append(c)

    final_df = hr_df[final_cols].reset_index(drop=True)

    out_downloads = r"C:\Users\Isaiah\Downloads\CoreCV_Nigerian_Tech_HR_Recruiter_Leads.xlsx"
    out_data = r"C:\Users\Isaiah\corecv_outreach\data\hr_leads.xlsx"

    final_df.to_excel(out_downloads, index=False)
    final_df.to_excel(out_data, index=False)

    print(f"[SUCCESS] Extracted and cleaned {len(final_df)} HR & Talent Acquisition Leads.")
    print(f"[SAVED] Exported to: {out_downloads}")
    print(f"[SAVED] Outreach Cache: {out_data}")
    return len(final_df)

if __name__ == '__main__':
    extract_clean_hr()
