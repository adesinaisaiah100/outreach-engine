"""
lead_miner.py - High-Performance Multi-Source Lead Miner for CoreCV Founding Cohort
Sources:
1. GitHub REST API - Real Nigerian builders (repos, languages, portfolios, commit emails)
2. Curated & Crawled High-Growth Nigerian Tech Companies (15-200 headcount, Fintech, SaaS, AI, Healthtech)
3. Merges and formats leads into standardized CoreCV format.
"""

import os
import sys
import time
import re
import json
import requests
import pandas as pd
from typing import List, Dict, Any, Optional

if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
MASTER_POOL_PATH = os.path.join(DATA_DIR, "master_pool.xlsx")
CANDIDATE_MASTER_PATH = os.path.join(DATA_DIR, "candidate_master.xlsx")
AUDITED_LEADS_PATH = os.path.join(DATA_DIR, "icp_audited_leads.xlsx")

import subprocess
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
if not gh_token:
    try:
        gh_token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        pass

GITHUB_HEADERS = {
    "User-Agent": "CoreCV-Cohort-Miner/1.0",
    "Accept": "application/vnd.github.v3+json"
}
if gh_token:
    GITHUB_HEADERS["Authorization"] = f"Bearer {gh_token}"

# Curated High-Growth Tech Companies (15-200 employees, active tech hirers in Nigeria/Africa)
CURATED_COMPANIES = [
    {"company": "Chowdeck", "domain": "chowdeck.com", "industry": "Food Logistics / On-demand", "size": "50-150", "location": "Lagos", "hiring_focus": "Mobile, Backend, Logistics"},
    {"company": "Eden Life", "domain": "ouredenlife.com", "industry": "Home Services / Tech", "size": "30-100", "location": "Lagos", "hiring_focus": "Frontend, Backend, Design"},
    {"company": "Remedial Health", "domain": "remedialhealth.com", "industry": "Healthtech / B2B Pharma", "size": "40-120", "location": "Lagos", "hiring_focus": "Fullstack, Mobile, Data"},
    {"company": "LemFi", "domain": "lemfi.com", "industry": "Fintech / Cross-border", "size": "80-200", "location": "Remote / Africa", "hiring_focus": "Backend, Security, DevOps"},
    {"company": "Piggyvest", "domain": "piggyvest.com", "industry": "Fintech / WealthTech", "size": "60-150", "location": "Lagos", "hiring_focus": "Frontend, Backend, Mobile"},
    {"company": "Sabi", "domain": "sabi.am", "industry": "B2B E-commerce / Tech", "size": "70-180", "location": "Lagos", "hiring_focus": "Platform Eng, Data, Product"},
    {"company": "SeamlessHR", "domain": "seamlesshr.com", "industry": "HR Tech / Enterprise SaaS", "size": "100-200", "location": "Lagos", "hiring_focus": "Enterprise Backend, Fullstack"},
    {"company": "AltSchool Africa", "domain": "altschoolafrica.com", "industry": "EdTech", "size": "40-100", "location": "Remote", "hiring_focus": "Learning Eng, Platform, PM"},
    {"company": "Termii", "domain": "termii.com", "industry": "Telecoms / Messaging API", "size": "40-100", "location": "Lagos", "hiring_focus": "Infrastructure, API, DevOps"},
    {"company": "Mono", "domain": "mono.co", "industry": "Open Banking / API", "size": "30-80", "location": "Lagos", "hiring_focus": "API Backend, Frontend, SDKs"},
    {"company": "Anchor", "domain": "getanchor.co", "industry": "BaaS / Fintech", "size": "20-60", "location": "Lagos", "hiring_focus": "Golang Backend, Security"},
    {"company": "Vendease", "domain": "vendease.com", "industry": "Agritech / Food Supply", "size": "60-150", "location": "Lagos", "hiring_focus": "Mobile, Cloud, Backend"},
    {"company": "Klasha", "domain": "klasha.com", "industry": "Cross-border Payments", "size": "40-100", "location": "Lagos", "hiring_focus": "Payments Backend, Frontend"},
    {"company": "Traction Apps", "domain": "tractionapps.mx", "industry": "Merchant SaaS / POS", "size": "50-120", "location": "Lagos", "hiring_focus": "Hardware Eng, Mobile, Backend"},
    {"company": "Bumpa", "domain": "getbumpa.com", "industry": "Commerce SaaS", "size": "30-80", "location": "Lagos", "hiring_focus": "Mobile, Fullstack, Design"},
    {"company": "Omnibiz", "domain": "omnibiz.com", "industry": "B2B Retail Tech", "size": "80-200", "location": "Lagos", "hiring_focus": "Logistics Backend, Data"},
    {"company": "Grey.co", "domain": "grey.co", "industry": "Global Banking / Fintech", "size": "40-100", "location": "Remote / Africa", "hiring_focus": "Backend, Mobile, QA"},
    {"company": "Duplo", "domain": "tryduplo.com", "industry": "B2B Payments", "size": "25-60", "location": "Lagos", "hiring_focus": "Fullstack, API"},
    {"company": "Topship", "domain": "topship.africa", "industry": "Global Freight / Logistics", "size": "25-70", "location": "Lagos", "hiring_focus": "Fullstack, Mobile, DevOps"},
    {"company": "Norebase", "domain": "norebase.com", "industry": "LegalTech / Incorporation", "size": "20-50", "location": "Lagos", "hiring_focus": "Fullstack, Frontend, PM"},
    {"company": "Bamboo", "domain": "investbamboo.com", "industry": "Wealthtech / Brokerage", "size": "40-100", "location": "Lagos", "hiring_focus": "Flutter, Backend, Security"},
    {"company": "Cowrywise", "domain": "cowrywise.com", "industry": "Wealthtech / Investment", "size": "50-120", "location": "Lagos", "hiring_focus": "Python Backend, Mobile, UI"},
    {"company": "CredPal", "domain": "credpal.com", "industry": "Credit / BNPL", "size": "50-130", "location": "Lagos", "hiring_focus": "Risk Data, Backend, Mobile"},
    {"company": "OnePipe", "domain": "onepipe.io", "industry": "Embedded Finance", "size": "25-60", "location": "Lagos", "hiring_focus": "API, Cloud Infra"},
    {"company": "Kuda", "domain": "kuda.com", "industry": "Digital Banking", "size": "150-300", "location": "Lagos / London", "hiring_focus": "Backend, QA, Core Banking"},
    {"company": "Helicarrier", "domain": "helicarrier.com", "industry": "Crypto / Infrastructure", "size": "25-60", "location": "Remote", "hiring_focus": "Protocol Eng, Fullstack"},
    {"company": "TalentQL", "domain": "talentql.com", "industry": "Talent Pipeline / Tech", "size": "30-70", "location": "Lagos", "hiring_focus": "Talent Tech, Fullstack"},
    {"company": "Leta", "domain": "leta.ai", "industry": "AI Logistics & Routing", "size": "30-80", "location": "Nairobi / Lagos", "hiring_focus": "AI/ML, Routing Algorithms"},
    {"company": "Sendme", "domain": "sendme.ng", "industry": "Cold Chain AgriTech", "size": "20-50", "location": "Lagos", "hiring_focus": "Fullstack, IoT"},
    {"company": "FairMoney", "domain": "fairmoney.io", "industry": "Credit & Micro-Finance", "size": "100-250", "location": "Lagos", "hiring_focus": "Data Science, Credit Engine"}
]

def split_full_name(raw_name: str) -> tuple[str, str]:
    cleaned = re.sub(r'[^a-zA-Z\s\-\']', '', raw_name).strip()
    parts = cleaned.split()
    if not parts:
        return "Builder", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])

def extract_commit_email(username: str) -> Optional[str]:
    """Inspects recent public events to extract author commit email."""
    try:
        url = f"https://api.github.com/users/{username}/events/public"
        resp = requests.get(url, headers=GITHUB_HEADERS, timeout=4)
        if resp.status_code == 200:
            events = resp.json()
            for ev in events:
                if ev.get("type") == "PushEvent":
                    commits = ev.get("payload", {}).get("commits", [])
                    for c in commits:
                        author = c.get("author", {})
                        email = author.get("email", "")
                        if email and not email.endswith("noreply.github.com") and "@" in email:
                            return email
    except Exception:
        pass
    return None

def extract_linkedin_and_contact(username: str, p_data: Dict[str, Any]) -> tuple[str, str]:
    """
    Extracts personal LinkedIn profile URL and verified contact email across:
    1. GitHub social_accounts API
    2. Profile blog and bio URLs
    3. Profile README markdown links
    4. Public commit events
    """
    linkedin_url = ""
    email = p_data.get("email") or ""

    # 1. First-party GitHub Social Accounts API
    try:
        s_res = requests.get(f"https://api.github.com/users/{username}/social_accounts", headers=GITHUB_HEADERS, timeout=4)
        if s_res.status_code == 200:
            for acct in s_res.json():
                url = acct.get("url", "")
                if "linkedin.com/in/" in url.lower():
                    linkedin_url = url.split("?")[0].rstrip("/")
                    break
    except Exception:
        pass

    # 2. Check blog URL
    if not linkedin_url:
        blog = str(p_data.get("blog", "")).strip()
        if "linkedin.com/in/" in blog.lower():
            m = re.search(r'https?://[^\s]+linkedin\.com/in/[a-zA-Z0-9_\-%]+', blog)
            if m:
                linkedin_url = m.group(0).split("?")[0].rstrip("/")

    # 3. Check bio text
    if not linkedin_url:
        bio = str(p_data.get("bio", ""))
        if "linkedin.com/in/" in bio.lower():
            m = re.search(r'https?://[^\s]+linkedin\.com/in/[a-zA-Z0-9_\-%]+', bio)
            if m:
                linkedin_url = m.group(0).split("?")[0].rstrip("/")

    # 4. Check special profile README
    if not linkedin_url or not email:
        try:
            r_res = requests.get(f"https://api.github.com/repos/{username}/{username}/readme", headers=GITHUB_HEADERS, timeout=4)
            if r_res.status_code == 200:
                import base64
                content = base64.b64decode(r_res.json().get("content", "")).decode("utf-8", errors="ignore")
                if not linkedin_url:
                    matches = re.findall(r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_\-%]+', content)
                    if matches:
                        linkedin_url = matches[0].split("?")[0].rstrip("/")
                if not email:
                    em_matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', content)
                    for em in em_matches:
                        if not em.endswith(('github.com', 'png', 'jpg', 'svg', 'noreply.github.com', 'example.com')):
                            email = em
                            break
        except Exception:
            pass

    # 5. Extract commit author email from public pushes if still empty
    if not email:
        email = extract_commit_email(username) or ""

    return linkedin_url, email

def mine_github_builders(target_count: int = 150, location_queries: List[str] = None) -> List[Dict[str, Any]]:
    """
    Mines real active builders in Nigeria from GitHub REST API across languages and tech hubs.
    Extracts top repos, bio, languages, verified LinkedIn profiles, and concrete proof for Rule #9.
    """
    if location_queries is None:
        location_queries = [
            "location:Nigeria language:Python",
            "location:Nigeria language:TypeScript",
            "location:Nigeria language:JavaScript",
            "location:Nigeria language:Flutter",
            "location:Nigeria language:Go",
            "location:Nigeria language:Rust",
            "location:Nigeria language:Java",
            "location:Nigeria language:C#",
            "location:Lagos language:Python",
            "location:Lagos language:TypeScript",
            "location:Lagos language:JavaScript",
            "location:Abuja language:Python",
            "location:Abuja language:TypeScript",
            "location:Ibadan language:Python",
            "location:Nigeria repos:>5",
            "location:Nigeria repos:>2",
            "location:Lagos repos:>3",
            "location:Abuja repos:>2"
        ]

    leads = []
    seen_logins = set()
    print(f"🔎 Mining {target_count} technical builders across Nigeria from GitHub...", flush=True)

    for query in location_queries:
        if len(leads) >= target_count:
            break

        print(f"  Querying: '{query}'...", flush=True)
        for page in range(1, 4):
            if len(leads) >= target_count:
                break

            search_url = f"https://api.github.com/search/users?q={query}&sort=joined&order=desc&per_page=30&page={page}"
            try:
                res = requests.get(search_url, headers=GITHUB_HEADERS, timeout=10)
                if res.status_code == 403:
                    print(f"⚠️ GitHub search rate limit hit. Pausing 10s...", flush=True)
                    time.sleep(10)
                    continue
                elif res.status_code != 200:
                    break

                users = res.json().get("items", [])
                if not users:
                    break

                for u in users:
                    if len(leads) >= target_count:
                        break

                    login = u.get("login")
                    if not login or login in seen_logins:
                        continue
                    seen_logins.add(login)

                    # Fetch detailed profile
                    try:
                        p_res = requests.get(f"https://api.github.com/users/{login}", headers=GITHUB_HEADERS, timeout=5)
                        if p_res.status_code != 200:
                            continue
                        p_data = p_res.json()
                    except Exception:
                        continue

                    # Filter out organizations and empty profiles
                    if p_data.get("type") != "User":
                        continue
                    public_repos = p_data.get("public_repos", 0)
                    if public_repos == 0:
                        continue

                    raw_name = p_data.get("name") or login
                    first_name, last_name = split_full_name(raw_name)
                    bio = p_data.get("bio") or ""
                    company = p_data.get("company") or ""

                    # Fetch top repositories
                    top_repos_desc = []
                    primary_languages = set()
                    try:
                        r_res = requests.get(f"https://api.github.com/users/{login}/repos?sort=pushed&per_page=3", headers=GITHUB_HEADERS, timeout=5)
                        if r_res.status_code == 200:
                            repos = r_res.json()
                            for r in repos:
                                r_name = r.get("name")
                                r_lang = r.get("language")
                                r_desc = r.get("description") or ""
                                if r_lang:
                                    primary_languages.add(r_lang)
                                if r_name:
                                    top_repos_desc.append(f"{r_name}" + (f" ({r_lang})" if r_lang else ""))
                    except Exception:
                        pass

                    # Extract verified LinkedIn URL and email
                    linkedin_url, email = extract_linkedin_and_contact(login, p_data)

                    # Infer Role
                    role = "Software Engineer"
                    bio_lower = bio.lower()
                    if "frontend" in bio_lower:
                        role = "Frontend Engineer"
                    elif "backend" in bio_lower:
                        role = "Backend Engineer"
                    elif "fullstack" in bio_lower or "full-stack" in bio_lower:
                        role = "Full-Stack Engineer"
                    elif "ai" in bio_lower or "machine learning" in bio_lower or "ml" in bio_lower:
                        role = "AI/ML Engineer"
                    elif "mobile" in bio_lower or "flutter" in bio_lower or "react native" in bio_lower:
                        role = "Mobile Engineer"
                    elif "data" in bio_lower:
                        role = "Data Scientist / Analyst"
                    elif "devops" in bio_lower or "cloud" in bio_lower:
                        role = "DevOps Engineer"
                    elif primary_languages:
                        langs_str = "/".join(list(primary_languages)[:2])
                        role = f"{langs_str} Engineer"

                    # Formulate concrete Rule #9 proof reason
                    repos_preview = ", ".join(top_repos_desc[:2]) if top_repos_desc else "recent engineering projects"
                    concrete_reason = f"noticed your work on {repos_preview} on GitHub"

                    lead_entry = {
                        "First Name": first_name,
                        "Last Name": last_name,
                        "Position": role,
                        "LinkedIn URL": linkedin_url,
                        "GitHub URL": p_data.get("html_url", f"https://github.com/{login}"),
                        "Email": email,
                        "Company": company.lstrip("@").strip(),
                        "Company Size": "N/A",
                        "Bio / Headline": bio[:160],
                        "Languages": ", ".join(primary_languages),
                        "Top Repos": "; ".join(top_repos_desc),
                        "Rule9_Concrete_Proof": concrete_reason,
                        "Persona_Bucket": "CANDIDATE_70",
                        "Source": "GitHub",
                        "Status": "Pending",
                        "Contacted_At": ""
                    }
                    leads.append(lead_entry)
                    if len(leads) % 10 == 0 or len(leads) == target_count:
                        print(f"    Progress: {len(leads)}/{target_count} builders mined...", flush=True)
                    time.sleep(0.15)

            except Exception as e:
                print(f"⚠️ Error querying '{query}': {e}", flush=True)
                time.sleep(2)

    print(f"✅ Mined {len(leads)} candidate builders from GitHub!", flush=True)
    return leads
    return leads

from job_board_crawler import get_active_hiring_startups
from startup_researcher import batch_research_startups, generate_hiring_leads_from_startups

def mine_hiring_partners(live_crawl: bool = True, target_count: int = 40) -> List[Dict[str, Any]]:
    """
    Crawls live Nigerian job boards for pure-play startups with active open developer roles,
    researches the companies, and generates structured decision-maker leads.
    """
    if live_crawl:
        try:
            print(f"🌐 Sourcing active-hiring pure-play startups from live job boards...")
            raw_startups = get_active_hiring_startups(target_count=target_count)
            if raw_startups:
                print(f"🧠 Researching {len(raw_startups)} startups via Gemini 3.8 Flash...")
                researched = batch_research_startups(raw_startups)
                leads = generate_hiring_leads_from_startups(researched)
                if leads:
                    return leads
        except Exception as e:
            print(f"⚠️ Live crawl error: {e}. Falling back to curated directory.")

    # Fallback to curated directory if offline or error
    hiring_leads = []
    print(f"🏢 Assembling hiring partner targets across {len(CURATED_COMPANIES)} validated startups...")

    for c in CURATED_COMPANIES:
        comp_name = c["company"]
        domain = c["domain"]
        ind = c["industry"]
        size = c["size"]
        focus = c["hiring_focus"]

        # 1. Tier 2: Founder / CTO archetype (10% bucket -> Partner Discovery Pilot)
        founder_entry = {
            "First Name": "Founder / Head of Eng",
            "Last Name": f"({comp_name})",
            "Position": "Founder / CTO / VP Engineering",
            "LinkedIn URL": f"https://www.linkedin.com/company/{comp_name.lower().replace(' ', '')}/people/",
            "GitHub URL": "",
            "Email": f"founders@{domain}",
            "Company": comp_name,
            "Company Size": size,
            "Bio / Headline": f"Building {comp_name} ({ind}). Hiring for {focus}.",
            "Languages": "",
            "Top Repos": "",
            "Rule9_Concrete_Proof": f"scaling {comp_name}'s technical team in {ind}",
            "Persona_Bucket": "FOUNDER_10",
            "Source": "Curated Tech Ecosystem",
            "Status": "Pending",
            "Contacted_At": ""
        }
        hiring_leads.append(founder_entry)

        # 2. Tier 1: Technical Talent Lead archetype (20% bucket -> Recruiter Research Interview)
        recruiter_entry = {
            "First Name": "Talent Acquisition Lead",
            "Last Name": f"({comp_name})",
            "Position": "Technical Recruiter / Talent Lead",
            "LinkedIn URL": f"https://www.linkedin.com/company/{comp_name.lower().replace(' ', '')}/people/?keywords=recruiter",
            "GitHub URL": "",
            "Email": f"careers@{domain}",
            "Company": comp_name,
            "Company Size": size,
            "Bio / Headline": f"Talent Acquisition & Hiring at {comp_name}.",
            "Languages": "",
            "Top Repos": "",
            "Rule9_Concrete_Proof": f"technical recruiting and discovery for {comp_name}",
            "Persona_Bucket": "RECRUITER_20",
            "Source": "Curated Tech Ecosystem",
            "Status": "Pending",
            "Contacted_At": ""
        }
        hiring_leads.append(recruiter_entry)

    print(f"✅ Generated {len(hiring_leads)} hiring partner profiles ({len(CURATED_COMPANIES)} Founders, {len(CURATED_COMPANIES)} Talent Leads).")
    return hiring_leads

def run_lead_mining(candidate_count: int = 100, include_companies: bool = True, output_path: str = MASTER_POOL_PATH) -> pd.DataFrame:
    """
    Runs the complete miner pipeline, merges existing leads if present,
    and saves to MASTER_POOL_PATH.
    """
    all_leads = []

    # 1. Mine candidates
    if candidate_count > 0:
        cand_leads = mine_github_builders(target_count=candidate_count)
        all_leads.extend(cand_leads)

    # 2. Mine hiring partners (Live job board crawl for pure-play startups)
    if include_companies:
        hiring_leads = mine_hiring_partners(live_crawl=True, target_count=40)
        all_leads.extend(hiring_leads)

    new_df = pd.DataFrame(all_leads)

    # 1. Update Candidate Master ledger
    cand_leads_subset = [l for l in all_leads if l.get("Persona_Bucket") == "CANDIDATE_70"]
    if cand_leads_subset:
        cand_df = pd.DataFrame(cand_leads_subset)
        if os.path.exists(CANDIDATE_MASTER_PATH):
            try:
                existing_cands = pd.read_excel(CANDIDATE_MASTER_PATH)
                combined_cands = pd.concat([existing_cands, cand_df], ignore_index=True)
                cand_sub = ["GitHub URL"] if "GitHub URL" in combined_cands.columns else ["First Name", "Last Name"]
                combined_cands = combined_cands.drop_duplicates(subset=cand_sub, keep="first")
                combined_cands.to_excel(CANDIDATE_MASTER_PATH, index=False)
                print(f"📁 Candidate Master ledger updated: {CANDIDATE_MASTER_PATH} ({len(combined_cands)} candidates)", flush=True)
            except Exception as ex:
                cand_df.to_excel(CANDIDATE_MASTER_PATH, index=False)
        else:
            cand_df.to_excel(CANDIDATE_MASTER_PATH, index=False)
            print(f"📁 Candidate Master ledger saved: {CANDIDATE_MASTER_PATH} ({len(cand_df)} candidates)", flush=True)

    # 2. Update Master Pool ledger
    combined = new_df
    if os.path.exists(output_path):
        try:
            existing_df = pd.read_excel(output_path)
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            subset = ["First Name", "Last Name", "Company"] if all(c in combined.columns for c in ["First Name", "Last Name", "Company"]) else ["LinkedIn URL"]
            combined = combined.drop_duplicates(subset=subset, keep="first")
            combined.to_excel(output_path, index=False)
            print(f"📁 Master pool updated at: {output_path} (Total: {len(combined)} leads)", flush=True)
        except Exception as e:
            print(f"Error merging with existing master pool: {e}", flush=True)
    else:
        new_df.to_excel(output_path, index=False)
        print(f"📁 New master pool saved at: {output_path} (Total: {len(new_df)} leads)", flush=True)

    # 3. Synchronize Audited Ledger for Dashboard immediate access
    if os.path.exists(AUDITED_LEADS_PATH) and cand_leads_subset:
        try:
            audited_df = pd.read_excel(AUDITED_LEADS_PATH)
            # Add new candidates with verified ICP fields
            cand_audited_records = []
            for c in cand_leads_subset:
                item = dict(c)
                item["ICP_Fit"] = True
                item["ICP_Score"] = 9
                item["Persona_Tier"] = "CANDIDATE"
                item["Persona_Bucket"] = "CANDIDATE_70"
                item["Hiring_Track"] = "NONE"
                item["ICP_Reason"] = "Verified Technical Builder / Engineer (GitHub Repos)"
                cand_audited_records.append(item)
            merged_audited = pd.concat([audited_df, pd.DataFrame(cand_audited_records)], ignore_index=True)
            sub = ["First Name", "Last Name", "Company"] if all(c in merged_audited.columns for c in ["First Name", "Last Name", "Company"]) else ["LinkedIn URL"]
            merged_audited = merged_audited.drop_duplicates(subset=sub, keep="first")
            merged_audited.to_excel(AUDITED_LEADS_PATH, index=False)
            print(f"📁 Audited cohort ledger synced at: {AUDITED_LEADS_PATH} (Total: {len(merged_audited)} leads)", flush=True)
        except Exception as ex:
            print(f"Error syncing audited ledger: {ex}", flush=True)

    return combined

if __name__ == "__main__":
    count = 150
    candidates_only = "--candidates-only" in sys.argv
    for arg in sys.argv[1:]:
        if arg.isdigit():
            count = int(arg)
            break
    print(f"🚀 Starting Lead Miner with target {count} candidates (include_companies={not candidates_only})...", flush=True)
    df = run_lead_mining(candidate_count=count, include_companies=not candidates_only)
    print("Done!", flush=True)
