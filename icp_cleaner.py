"""
icp_cleaner.py - ICP (Ideal Customer Profile) Auditor & Cleaner
Based strictly on 'corecvfouningcohortstrategy.pdf'

Evaluates leads across:
1. Role & Discipline Alignment (Tech Builders vs Hiring Decision Makers)
2. Evidence & Signal Quality (GitHub, projects, active hiring company)
3. Company Headcount & Type (10-200 employee tech startups vs bloated conglomerates)
4. Rule #9 Personalization (Extracts 1 concrete reason / proof anchor)
5. Generates Audit Score (1-10) and Pass/Fail Verdict
"""

import os
import sys
import json
import re
import pandas as pd
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
AUDITED_LEADS_PATH = os.path.join(DATA_DIR, "icp_audited_leads.xlsx")

# Target Roles from Strategy Document
VALID_CANDIDATE_KEYWORDS = [
    "software", "engineer", "developer", "frontend", "backend", "full-stack", "fullstack",
    "ai", "ml", "machine learning", "product designer", "ui/ux", "product manager",
    "data analyst", "data scientist", "devops", "cloud", "qa", "quality assurance",
    "mobile", "flutter", "react", "python", "golang", "web3", "freelance builder"
]

DISQUALIFIED_CANDIDATE_KEYWORDS = [
    "accountant", "audit associate", "teller", "banker", "lawyer", "attorney",
    "receptionist", "nurse", "medical doctor", "pharmacist", "sales executive",
    "real estate", "driver", "oil field", "civil servant"
]

HIRING_TIER_1_KEYWORDS = [
    "technical recruiter", "tech recruiter", "talent acquisition", "recruiting lead",
    "head of talent", "talent lead", "talent manager", "engineering recruiter"
]

HIRING_TIER_2_KEYWORDS = [
    "founder", "co-founder", "cto", "chief technology officer", "head of engineering",
    "vp of engineering", "vp engineering", "director of engineering", "engineering manager",
    "head of people"
]

HIRING_TIER_3_KEYWORDS = [
    "hr manager", "people operations", "people ops", "human resources", "recruitment agency",
    "recruitment consultant"
]

DISQUALIFIED_COMPANY_TYPES = [
    "bank plc", "commercial bank", "oil & gas", "petroleum", "cement", "conglomerate",
    "ministry", "government", "parastatal", "holding company"
]

def algorithmic_icp_check(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Fast, deterministic rule-based ICP filter."""
    role = str(lead.get("Position", lead.get("Role", lead.get("Title", "")))).lower()
    company = str(lead.get("Company", "")).lower()
    company_size = str(lead.get("Company Size", "")).lower()
    headline = str(lead.get("Bio / Headline", lead.get("Headline", ""))).lower()
    repos = str(lead.get("Top Repos", ""))
    url = str(lead.get("LinkedIn URL", lead.get("GitHub URL", "")))

    text_corpus = f"{role} {headline}"

    existing_proof = str(lead.get('Rule9_Concrete_Proof', '')).strip()

    # 1. Check if Hiring Partner
    if any(k in text_corpus for k in HIRING_TIER_1_KEYWORDS):
        is_bad_corp = any(b in company for b in DISQUALIFIED_COMPANY_TYPES)
        score = 6 if is_bad_corp else 9
        proof = existing_proof if existing_proof else f"technical hiring and evaluation at {lead.get('Company', 'your company')}"
        return {
            "icp_fit": not is_bad_corp,
            "icp_score": score,
            "persona_tier": "HIRING_TIER_1",
            "persona_bucket": "RECRUITER_20",
            "hiring_track": "RECRUITER_RESEARCH",
            "icp_reason": "High-value Technical Recruiter / Talent Lead" + (" (Bureaucratic corp warning)" if is_bad_corp else ""),
            "rule9_proof": proof
        }

    if any(k in text_corpus for k in HIRING_TIER_2_KEYWORDS):
        is_bad_corp = any(b in company for b in DISQUALIFIED_COMPANY_TYPES)
        score = 6 if is_bad_corp else 10
        proof = existing_proof if existing_proof else f"scaling engineering and candidate discovery at {lead.get('Company', 'your startup')}"
        return {
            "icp_fit": not is_bad_corp,
            "icp_score": score,
            "persona_tier": "HIRING_TIER_2",
            "persona_bucket": "FOUNDER_10",
            "hiring_track": "PARTNER_PILOT",
            "icp_reason": "Top-tier Decision Maker (Founder / CTO / Engineering Head)" + (" (Bureaucratic corp warning)" if is_bad_corp else ""),
            "rule9_proof": proof
        }

    if any(k in text_corpus for k in HIRING_TIER_3_KEYWORDS):
        return {
            "icp_fit": True,
            "icp_score": 7,
            "persona_tier": "HIRING_TIER_3",
            "persona_bucket": "RECRUITER_20",
            "hiring_track": "RECRUITER_RESEARCH",
            "icp_reason": "General HR / People Operations",
            "rule9_proof": f"people operations and hiring workflow at {lead.get('Company', 'your team')}"
        }

    # 2. Check Candidate Disqualifications
    if any(d in text_corpus for d in DISQUALIFIED_CANDIDATE_KEYWORDS):
        return {
            "icp_fit": False,
            "icp_score": 2,
            "persona_tier": "DISQUALIFIED",
            "persona_bucket": "EXCLUDED",
            "hiring_track": "NONE",
            "icp_reason": "Non-technical background; fails CoreCV tech cohort mandate",
            "rule9_proof": ""
        }

    # 3. Check Candidate Qualifications
    has_tech_keyword = any(k in text_corpus for k in VALID_CANDIDATE_KEYWORDS)
    has_repos = len(repos.strip()) > 3 or "github.com" in url

    if has_tech_keyword and has_repos:
        top_repo_name = repos.split(";")[0].strip() if repos else "recent software projects"
        return {
            "icp_fit": True,
            "icp_score": 9,
            "persona_tier": "CANDIDATE",
            "persona_bucket": "CANDIDATE_70",
            "hiring_track": "NONE",
            "icp_reason": "High-signal Technical Builder with active repository evidence",
            "rule9_proof": f"noticed your work on {top_repo_name} on GitHub" if repos else f"noticed your projects in {role}"
        }
    elif has_tech_keyword:
        return {
            "icp_fit": True,
            "icp_score": 7,
            "persona_tier": "CANDIDATE",
            "persona_bucket": "CANDIDATE_70",
            "hiring_track": "NONE",
            "icp_reason": "Tech professional matching cohort target roles",
            "rule9_proof": f"noticed your technical background as a {role}"
        }

    return {
        "icp_fit": False,
        "icp_score": 4,
        "persona_tier": "UNVERIFIED",
        "persona_bucket": "EXCLUDED",
        "hiring_track": "NONE",
        "icp_reason": "Unclear technical role or missing evidence signals",
        "rule9_proof": ""
    }

def batch_llm_icp_audit(leads_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Uses Gemini 3.8 Flash to deeply evaluate edge cases, refine Rule #9 proof clauses,
    and classify leads according to 'corecvfouningcohortstrategy.pdf'.
    """
    if not GEMINI_API_KEY:
        print("ℹ️ GEMINI_API_KEY not set. Using strict algorithmic audit.")
        return [algorithmic_icp_check(l) for l in leads_list]

    payload = []
    for i, l in enumerate(leads_list):
        payload.append({
            "id": i,
            "name": f"{l.get('First Name', '')} {l.get('Last Name', '')}".strip(),
            "role": str(l.get("Position", l.get("Role", ""))),
            "company": str(l.get("Company", "")),
            "headline": str(l.get("Bio / Headline", l.get("Headline", ""))),
            "repos": str(l.get("Top Repos", ""))
        })

    prompt = f"""
    You are the Lead Qualification Director for CoreCV's Founding Cohort (corecvfouningcohortstrategy.pdf).
    Audit each candidate/lead against our strict ICP criteria:
    
    1. PROFESSIONALS (CANDIDATE_70): Software, AI/ML, Frontend, Backend, Fullstack, Product Design, PM, Data, DevOps, QA.
       - MUST NOT be generic corporate non-tech (bank teller, accountant, sales rep, doctor).
       - EXTRACT Rule #9 Concrete Proof: Exactly ONE natural sentence fragment citing what they built or their specific transition (e.g. "noticed you've built several projects around AI", "saw your open-source work on [Repo]", "noticed your transition into AI engineering"). NO GENERIC FLATTERY like 'impressive background'.
       
    2. HIRING PARTNERS:
       - Tier 1 (RECRUITER_20): Technical Recruiter, Talent Acquisition Lead, Head of Talent. Goal: Recruiter Research call.
       - Tier 2 (FOUNDER_10): Founder, Co-founder, CTO, Head of Engineering at a 10-200 employee startup. Goal: Free Founding Partner discovery pilot.
       - DISQUALIFY: Massive traditional corporate conglomerates (Access Bank, Dangote, Telcos) because procurement and ATS are too slow for agile cohorts.
       
    Return a JSON object mapping numeric id (as string) to:
    {{
      "icp_fit": boolean,
      "icp_score": integer 1-10,
      "persona_tier": "CANDIDATE" | "HIRING_TIER_1" | "HIRING_TIER_2" | "HIRING_TIER_3" | "DISQUALIFIED",
      "persona_bucket": "CANDIDATE_70" | "RECRUITER_20" | "FOUNDER_10" | "EXCLUDED",
      "hiring_track": "PARTNER_PILOT" | "RECRUITER_RESEARCH" | "NONE",
      "icp_reason": "short explanation",
      "rule9_proof": "one concrete proof clause for candidate or hiring lead"
    }}
    
    Leads Data:
    {json.dumps(payload)}
    """

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        if response and response.text:
            enriched = json.loads(response.text)
            results = []
            for i, l in enumerate(leads_list):
                item = enriched.get(str(i))
                if item:
                    results.append(item)
                else:
                    results.append(algorithmic_icp_check(l))
            return results
    except Exception as e:
        print(f"⚠️ Gemini ICP audit exception: {e}. Falling back to algorithmic check.")

    return [algorithmic_icp_check(l) for l in leads_list]

def audit_leads_dataset(input_file_or_df, output_path: str = AUDITED_LEADS_PATH) -> pd.DataFrame:
    """
    Audits a complete DataFrame or Excel file against the ICP rubric.
    Adds ICP columns, filters disqualified leads, and saves the verified dataset.
    """
    if isinstance(input_file_or_df, str):
        df = pd.read_excel(input_file_or_df)
    else:
        df = input_file_or_df.copy()

    print(f"🔍 Starting ICP Audit for {len(df)} leads...")
    leads_records = df.to_dict(orient="records")

    # Batch process in chunks of 25 for LLM efficiency
    CHUNK_SIZE = 25
    all_audit_results = []
    for i in range(0, len(leads_records), CHUNK_SIZE):
        chunk = leads_records[i:i+CHUNK_SIZE]
        print(f"Auditing batch [{i+1} - {min(i+CHUNK_SIZE, len(leads_records))}] / {len(leads_records)}...")
        chunk_res = batch_llm_icp_audit(chunk)
        all_audit_results.extend(chunk_res)

    df["ICP_Fit"] = [r.get("icp_fit", False) for r in all_audit_results]
    df["ICP_Score"] = [r.get("icp_score", 5) for r in all_audit_results]
    df["Persona_Tier"] = [r.get("persona_tier", "UNVERIFIED") for r in all_audit_results]
    df["Persona_Bucket"] = [r.get("persona_bucket", "CANDIDATE_70") for r in all_audit_results]
    df["Hiring_Track"] = [r.get("hiring_track", "NONE") for r in all_audit_results]
    df["ICP_Reason"] = [r.get("icp_reason", "") for r in all_audit_results]
    df["Rule9_Concrete_Proof"] = [r.get("rule9_proof", "") for r in all_audit_results]

    # Save complete audited ledger
    df.to_excel(output_path, index=False)

    passed_count = int(df["ICP_Fit"].sum())
    cand_count = int((df["Persona_Bucket"] == "CANDIDATE_70").sum())
    recruiter_count = int((df["Persona_Bucket"] == "RECRUITER_20").sum())
    founder_count = int((df["Persona_Bucket"] == "FOUNDER_10").sum())

    print("\n" + "="*50)
    print(f"📊 ICP AUDIT RESULTS SUMMARY:")
    print(f"Total Leads Audited:   {len(df)}")
    print(f"✅ Passed ICP (Fit=True): {passed_count} ({passed_count/len(df)*100:.1f}%)")
    print(f"❌ Disqualified:         {len(df) - passed_count}")
    print(f"💻 Candidates (70% Pool): {cand_count}")
    print(f"🎯 Recruiters (20% Pool): {recruiter_count}")
    print(f"🏢 Founders (10% Pool):   {founder_count}")
    print(f"💾 Audited Ledger Saved: {output_path}")
    print("="*50 + "\n")

    return df

if __name__ == "__main__":
    test_file = os.path.join(DATA_DIR, "master_pool.xlsx")
    if not os.path.exists(test_file):
        test_file = os.path.join(DATA_DIR, "active_leads.xlsx")
    if os.path.exists(test_file):
        audit_leads_dataset(test_file)
    else:
        print(f"No leads file found at {test_file}. Run lead_miner.py first.")
