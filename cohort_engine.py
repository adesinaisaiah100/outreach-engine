"""
cohort_engine.py - CoreCV Founding Cohort Dispatch & Dynamic Ratio Engine
Strictly aligned with: 'corecvfouningcohortstrategy.pdf'

Handles:
1. Dynamic message generation for Candidates, Recruiters (Track B), and Founders (Track A)
2. Character-safe connection notes (<280 chars)
3. Dynamic queue interleaving (e.g. 70% Candidates / 20% Recruiters / 10% Founders)
"""

import os
import re
import random
import pandas as pd
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

SENDER_NAME = os.environ.get("SENDER_NAME", "Oluwatimileyin").strip()
PRODUCT_NAME = os.environ.get("PRODUCT_NAME", "CoreCV").strip()

def build_candidate_copy(first_name: str, rule9_proof: str, role: str = "engineer", is_connect_note: bool = False) -> str:
    """Founding Professional outreach message (from PDF Pages 7-8)."""
    proof_fragment = rule9_proof.strip() if rule9_proof else f"noticed your technical background in {role}"
    # Ensure smooth grammar if proof already starts with 'noticed' or 'saw'
    if proof_fragment.lower().startswith("noticed ") or proof_fragment.lower().startswith("saw "):
        proof_intro = proof_fragment
    else:
        proof_intro = f"noticed your work in {proof_fragment}"

    if is_connect_note:
        note = (
            f"Hi {first_name}, I {proof_intro}. "
            f"Building CoreCV: testing an evidence-backed record (projects, code, contributions) "
            f"for professionals to get discovered by hiring partners. Would love to send cohort details!"
        )
        return note[:280]

    return (
        f"Hi {first_name},\n\n"
        f"I came across your profile and {proof_intro}.\n\n"
        f"I'm building {PRODUCT_NAME} around a problem I keep seeing with early-career and growing tech "
        f"professionals: a traditional CV often doesn't capture the actual work you've done.\n\n"
        f"We're putting together a small founding cohort where professionals will build an "
        f"evidence-backed professional record - projects, contributions, skills, and supporting "
        f"proof - rather than relying only on a traditional CV.\n\n"
        f"The strongest completed records will be made available for consideration by participating "
        f"hiring partners.\n\n"
        f"I thought your background would make you a strong fit for the cohort. "
        f"Would you like me to send you the details?\n\n"
        f"Best,\n{SENDER_NAME}"
    )

def build_founder_copy(first_name: str, company: str, rule9_proof: str = "", is_connect_note: bool = False) -> str:
    """Hiring Partner Discovery message for Founders/CTOs/Heads of Eng (PDF Page 10)."""
    clean_company = company.strip() if company else "your company"
    
    if is_connect_note:
        note = (
            f"Hi {first_name}, I'm {SENDER_NAME}, building CoreCV. "
            f"We're launching a founding cohort of tech professionals with verified project evidence. "
            f"Looking for growing teams like {clean_company} as free founding hiring partners. "
            f"Open to a 15-min chat?"
        )
        return note[:280]

    return (
        f"Hi {first_name},\n\n"
        f"I'm {SENDER_NAME}, building {PRODUCT_NAME}.\n\n"
        f"We're putting together a small founding cohort of early-career tech professionals who will "
        f"spend the next few weeks building evidence-backed professional records - projects, "
        f"contributions, skills and supporting proof - rather than relying only on traditional CVs.\n\n"
        f"We're looking for a few growing technology companies like {clean_company} to participate "
        f"as founding hiring partners.\n\n"
        f"There is no cost during the founding program. The idea is to let companies evaluate a "
        f"small pool of candidates through the evidence they've built and help us understand "
        f"whether this makes candidate discovery and evaluation easier.\n\n"
        f"I'd first love to understand how your team currently hires technical talent and where the "
        f"process becomes difficult.\n\n"
        f"Would you be open to a 15-minute conversation?\n\n"
        f"Best,\n{SENDER_NAME}"
    )

def build_recruiter_copy(first_name: str, company: str = "", is_connect_note: bool = False) -> str:
    """Recruiter Research message for Technical Talent Acquisition (PDF Page 10)."""
    if is_connect_note:
        note = (
            f"Hi {first_name}, I'm {SENDER_NAME}, building CoreCV. "
            f"Researching how technical recruiters evaluate candidates beyond CVs (GitHub, code, proof). "
            f"Not selling anything - would love 15 mins to learn from your hiring experience!"
        )
        return note[:280]

    return (
        f"Hi {first_name},\n\n"
        f"I'm {SENDER_NAME}, building {PRODUCT_NAME}.\n\n"
        f"We're researching how recruiters and hiring teams actually evaluate technical candidates "
        f"beyond the CV - particularly when someone's experience is spread across GitHub, "
        f"projects, portfolios, freelance work and other evidence.\n\n"
        f"I'm not trying to sell you anything. I'd genuinely like to understand how you currently "
        f"discover and shortlist candidates and where establishing confidence in someone's ability "
        f"becomes difficult.\n\n"
        f"Would you be open to a short 15-minute conversation sometime this week?\n\n"
        f"Thank you,\n{SENDER_NAME}"
    )

def get_cohort_message(lead: Dict[str, Any], is_connect_note: bool = False) -> str:
    """Dispatches the exact cohort strategy copy based on audited persona bucket."""
    first_name = str(lead.get("First Name", "there")).strip()
    company = str(lead.get("Company", "")).strip()
    role = str(lead.get("Position", "developer")).strip()
    rule9 = str(lead.get("Rule9_Concrete_Proof", "")).strip()
    bucket = str(lead.get("Persona_Bucket", "CANDIDATE_70")).strip().upper()
    track = str(lead.get("Hiring_Track", "")).strip().upper()

    if bucket == "FOUNDER_10" or track == "PARTNER_PILOT":
        return build_founder_copy(first_name, company, rule9, is_connect_note)
    elif bucket == "RECRUITER_20" or track == "RECRUITER_RESEARCH":
        return build_recruiter_copy(first_name, company, is_connect_note)
    else:
        return build_candidate_copy(first_name, rule9, role, is_connect_note)

def interleave_cohort_batch(
    df: pd.DataFrame,
    candidate_pct: int = 70,
    recruiter_pct: int = 20,
    founder_pct: int = 10,
    daily_limit: int = 25
) -> pd.DataFrame:
    """
    Interleaves leads from the active pool to match the desired percentage ratio.
    Default: 70% Candidates, 20% Recruiters, 10% Founders.
    """
    # Filter pending
    def should_skip(status):
        if pd.isna(status):
            return False
        s = str(status).strip()
        return s == 'Contacted' or s == 'Invalid URL' or s.startswith('Failed:') or s.startswith('Skipped:')

    pending_df = df[~df['Status'].apply(should_skip)].copy()
    if pending_df.empty:
        return pending_df

    cand_pool = pending_df[pending_df['Persona_Bucket'] == 'CANDIDATE_70']
    rec_pool = pending_df[pending_df['Persona_Bucket'] == 'RECRUITER_20']
    fnd_pool = pending_df[pending_df['Persona_Bucket'] == 'FOUNDER_10']

    # Fallback if pools are empty: treat by role keywords
    if cand_pool.empty and rec_pool.empty and fnd_pool.empty:
        return pending_df.head(daily_limit)

    cand_target = max(1, int(daily_limit * (candidate_pct / 100.0)))
    rec_target = max(1, int(daily_limit * (recruiter_pct / 100.0)))
    fnd_target = max(1, daily_limit - cand_target - rec_target)

    selected_cands = cand_pool.head(cand_target)
    selected_recs = rec_pool.head(rec_target)
    selected_fnds = fnd_pool.head(fnd_target)

    # Combine and interleave evenly
    combined_list = []
    c_idx, r_idx, f_idx = 0, 0, 0
    c_len, r_len, f_len = len(selected_cands), len(selected_recs), len(selected_fnds)

    while len(combined_list) < daily_limit and (c_idx < c_len or r_idx < r_len or f_idx < f_len):
        # 7 candidates -> 2 recruiters -> 1 founder pattern
        for _ in range(7):
            if c_idx < c_len and len(combined_list) < daily_limit:
                combined_list.append(selected_cands.iloc[c_idx])
                c_idx += 1
        for _ in range(2):
            if r_idx < r_len and len(combined_list) < daily_limit:
                combined_list.append(selected_recs.iloc[r_idx])
                r_idx += 1
        for _ in range(1):
            if f_idx < f_len and len(combined_list) < daily_limit:
                combined_list.append(selected_fnds.iloc[f_idx])
                f_idx += 1

    if not combined_list:
        return pending_df.head(daily_limit)

    return pd.DataFrame(combined_list)
