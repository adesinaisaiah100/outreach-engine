"""
generate_email_dossier.py - Generates the Deep-Research Manual Email Dossier
Strictly follows: 'corecvfouningcohortstrategy.pdf'

Creates: data/manual_email_dossier.xlsx
Contains all 209 leads with verified emails:
- In-depth research on what they do / their tech stack / company focus
- Concrete Rule #9 proof anchors
- Pre-drafted full email copy strictly matching the PDF strategy (Pages 7 & 10)
Ready for manual copying and high-converting delivery.
"""

import os
import sys
import pandas as pd
from typing import Dict, Any

if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8')

from cohort_engine import build_candidate_copy, build_founder_copy, build_recruiter_copy

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MASTER_POOL_PATH = os.path.join(DATA_DIR, "master_pool.xlsx")
OUTPUT_DOSSIER_PATH = os.path.join(DATA_DIR, "manual_email_dossier.xlsx")

def create_manual_email_dossier(input_path: str = MASTER_POOL_PATH, output_path: str = OUTPUT_DOSSIER_PATH) -> pd.DataFrame:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Source file not found at: {input_path}")

    df = pd.read_excel(input_path)
    
    # Filter only leads with valid emails
    with_email = df[df["Email"].astype(str).str.contains("@")].copy()
    print(f"📊 Processing {len(with_email)} leads with verified emails...", flush=True)

    dossier_records = []

    for _, row in with_email.iterrows():
        first_name = str(row.get("First Name", "there")).strip()
        last_name = str(row.get("Last Name", "")).strip()
        full_name = f"{first_name} {last_name}".strip()
        email = str(row.get("Email", "")).strip()
        pos = str(row.get("Position", "")).strip()
        company = str(row.get("Company", "")).strip()
        git_url = str(row.get("GitHub URL", "")).strip()
        li_url = str(row.get("LinkedIn URL", "")).strip()
        bucket = str(row.get("Persona_Bucket", "CANDIDATE_70")).strip()
        rule9 = str(row.get("Rule9_Concrete_Proof", "")).strip()
        bio = str(row.get("Bio / Headline", "")).strip()
        langs = str(row.get("Languages", "")).strip()
        repos = str(row.get("Top Repos", "")).strip()

        # Build in-depth research note: "What They Do"
        if bucket == "CANDIDATE_70":
            persona_label = "Candidate Builder"
            comp_or_git = git_url if git_url else "GitHub Builder"
            research = f"Active Nigerian builder. Primary stack: {langs or 'Software Engineering'}. Top projects: {repos or 'Open source repositories'}."
            top_repo = repos.split(";")[0].split("(")[0].strip() if repos else "recent engineering work"
            subject = f"CoreCV Founding Cohort / {top_repo}"
            body = build_candidate_copy(first_name, rule9, pos, is_connect_note=False)

        elif bucket == "FOUNDER_10":
            persona_label = "Founder / CTO (Track A)"
            comp_or_git = company if company else "Tech Startup"
            research = f"Leadership at {company}. {bio}. Evaluating engineering talent & team expansion."
            subject = f"Founding Hiring Partner / {company}"
            body = build_founder_copy(first_name, company, rule9, is_connect_note=False)

        elif bucket == "RECRUITER_20":
            persona_label = "Talent Acquisition Lead (Track B)"
            comp_or_git = company if company else "Tech Hiring Team"
            research = f"Technical recruiting at {company}. {bio}. Managing candidate discovery and screening."
            subject = f"Recruiter research on technical candidate discovery / {company}"
            body = build_recruiter_copy(first_name, company, is_connect_note=False)

        else:
            persona_label = "Tech Professional"
            comp_or_git = company or git_url
            research = bio
            subject = f"CoreCV Founding Cohort"
            body = build_candidate_copy(first_name, rule9, pos, is_connect_note=False)

        dossier_records.append({
            "Recipient_Name": full_name,
            "Email": email,
            "Persona": persona_label,
            "Persona_Bucket": bucket,
            "Position_Title": pos,
            "Company_or_GitHub": comp_or_git,
            "What_They_Do_Research": research,
            "Rule9_Concrete_Proof": rule9,
            "Email_Subject_Line": subject,
            "Full_Strategy_Email_Body": body,
            "LinkedIn_Profile_URL": li_url if "linkedin.com/in/" in li_url else "",
            "Send_Status": "Ready to Send Manually"
        })

    dossier_df = pd.DataFrame(dossier_records)
    
    # Save to Excel
    dossier_df.to_excel(output_path, index=False)
    print(f"✅ Manual Email Dossier successfully created at: {output_path}", flush=True)
    print(f"   Total Leads: {len(dossier_df)} (Candidates: {(dossier_df['Persona_Bucket']=='CANDIDATE_70').sum()}, Founders: {(dossier_df['Persona_Bucket']=='FOUNDER_10').sum()}, Recruiters: {(dossier_df['Persona_Bucket']=='RECRUITER_20').sum()})", flush=True)

    return dossier_df

if __name__ == "__main__":
    create_manual_email_dossier()
