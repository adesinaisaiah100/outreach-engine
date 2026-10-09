"""
startup_researcher.py - Researches Discovered Startups & Resolves Decision-Maker Leads
Powered by Gemini 3.8 Flash & Public Intelligence

Takes active-hiring startups from job_board_crawler.py and:
1. Verifies pure-play startup fit (5-80 employees, tech focus)
2. Predicts company domain and direct email patterns (careers@domain, founders@domain)
3. Creates Tier 2 Founder/CTO leads and Tier 1 Recruiter leads
4. Generates live role-aware outreach proof hooks
"""

import os
import sys
import json
import re
import pandas as pd
from typing import List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

def clean_company_name(raw: str) -> str:
    c = re.sub(r'\b(ltd|limited|plc|llc|inc|services|technologies|solutions|group)\b', '', raw, flags=re.IGNORECASE)
    return c.strip(' .,-')

def batch_research_startups(startups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Uses Gemini 3.8 Flash to research companies, verify pure-play startup status,
    predict domains, and build role-aware hooks.
    """
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY not set. Using algorithmic fallback.")
        researched = []
        for s in startups:
            comp = clean_company_name(s["company"])
            domain = f"{comp.lower().replace(' ', '')}.com"
            researched.append({
                "company": comp,
                "is_pure_startup": True,
                "industry": "Software & Digital Technology",
                "estimated_size": "10-50",
                "domain": domain,
                "founder_email": f"founders@{domain}",
                "recruiter_email": f"careers@{domain}",
                "job_title": s.get("job_title", "Software Engineer"),
                "location": s.get("location", "Nigeria"),
                "job_url": s.get("job_url", "")
            })
        return researched

    payload = []
    for i, s in enumerate(startups):
        payload.append({
            "id": i,
            "company": s["company"],
            "job_title": s.get("job_title", ""),
            "location": s.get("location", "Nigeria")
        })

    prompt = f"""
    You are a venture capital & talent researcher specializing in Nigerian and African tech startups.
    Analyze this list of companies that recently posted tech job openings in Nigeria.
    
    For each company:
    1. Determine if it is an authentic early-stage / growing tech startup, software studio, or SaaS/fintech lab (5-100 employees) vs a massive bank/conglomerate.
    2. Provide its most likely website domain (e.g., 'lorgarithm.com', 'produqtedge.com', 'finova.ng', 'zealightlabs.com').
    3. Categorize its tech industry (e.g., 'Fintech', 'Software Engineering Studio', 'EdTech', 'HealthTech', 'Logistics').
    4. Provide the company's estimated headcount (e.g. '10-30', '20-50', '30-80').
    5. Predict clean contact emails: founder_email ('founders@domain' or 'hello@domain') and recruiter_email ('careers@domain' or 'jobs@domain').
    
    Return a JSON object mapping numeric id (as string) to:
    {{
      "is_pure_startup": boolean,
      "clean_company": "Clean Brand Name",
      "domain": "company domain or best guess",
      "industry": "industry niche",
      "estimated_size": "10-50",
      "founder_email": "founders@domain",
      "recruiter_email": "careers@domain"
    }}
    
    Companies:
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
            researched = []
            for i, s in enumerate(startups):
                item = enriched.get(str(i), {})
                comp = item.get("clean_company") or clean_company_name(s["company"])
                dom = item.get("domain") or f"{comp.lower().replace(' ', '')}.com"
                researched.append({
                    "company": comp,
                    "is_pure_startup": item.get("is_pure_startup", True),
                    "industry": item.get("industry", "Software & Technology"),
                    "estimated_size": item.get("estimated_size", "15-50"),
                    "domain": dom,
                    "founder_email": item.get("founder_email", f"founders@{dom}"),
                    "recruiter_email": item.get("recruiter_email", f"careers@{dom}"),
                    "job_title": s.get("job_title", "Software Engineer"),
                    "location": s.get("location", "Nigeria"),
                    "job_url": s.get("job_url", "")
                })
            return researched
    except Exception as e:
        print(f"⚠️ Startup research LLM error: {e}")

    # Fallback
    researched = []
    for s in startups:
        comp = clean_company_name(s["company"])
        domain = f"{comp.lower().replace(' ', '')}.com"
        researched.append({
            "company": comp,
            "is_pure_startup": True,
            "industry": "Software & Digital Technology",
            "estimated_size": "10-50",
            "domain": domain,
            "founder_email": f"founders@{domain}",
            "recruiter_email": f"careers@{domain}",
            "job_title": s.get("job_title", "Software Engineer"),
            "location": s.get("location", "Nigeria"),
            "job_url": s.get("job_url", "")
        })
    return researched

def generate_hiring_leads_from_startups(researched_startups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transforms researched pure-play startups into structured Tier 2 Founder leads
    and Tier 1 Recruiter leads with live role-aware proof hooks.
    """
    generated_leads = []

    for s in researched_startups:
        if not s.get("is_pure_startup", True):
            continue

        comp = s["company"]
        dom = s["domain"]
        job_role = s["job_title"]
        loc = s["location"]
        size = s["estimated_size"]
        job_url = s["job_url"]

        # 1. Tier 2: Founder / CTO Lead (10% bucket -> Partner Pilot Track A)
        founder_proof = f"noticed you're currently hiring for a {job_role} at {comp}"
        founder_lead = {
            "First Name": "Founder / Head of Eng",
            "Last Name": f"({comp})",
            "Position": "Founder / CTO / Engineering Head",
            "LinkedIn URL": f"https://www.linkedin.com/company/{comp.lower().replace(' ', '')}/people/?keywords=founder",
            "GitHub URL": "",
            "Email": s["founder_email"],
            "Company": comp,
            "Company Size": size,
            "Bio / Headline": f"Leading {comp}. Currently hiring for {job_role}.",
            "Languages": "",
            "Top Repos": "",
            "Rule9_Concrete_Proof": founder_proof,
            "Persona_Bucket": "FOUNDER_10",
            "Persona_Tier": "HIRING_TIER_2",
            "Hiring_Track": "PARTNER_PILOT",
            "ICP_Fit": True,
            "ICP_Score": 10,
            "ICP_Reason": f"Active-hiring pure-play startup ({job_role})",
            "Active_Job_URL": job_url,
            "Source": "Live Job Board Crawl",
            "Status": "Pending",
            "Contacted_At": ""
        }
        generated_leads.append(founder_lead)

        # 2. Tier 1: Technical Talent Lead / Recruiter (20% bucket -> Research Track B)
        recruiter_proof = f"noticed your team at {comp} is currently evaluating candidates for {job_role}"
        recruiter_lead = {
            "First Name": "Talent Acquisition Lead",
            "Last Name": f"({comp})",
            "Position": "Technical Recruiter / Talent Lead",
            "LinkedIn URL": f"https://www.linkedin.com/company/{comp.lower().replace(' ', '')}/people/?keywords=recruiter",
            "GitHub URL": "",
            "Email": s["recruiter_email"],
            "Company": comp,
            "Company Size": size,
            "Bio / Headline": f"Talent Acquisition at {comp}. Screening candidates for {job_role}.",
            "Languages": "",
            "Top Repos": "",
            "Rule9_Concrete_Proof": recruiter_proof,
            "Persona_Bucket": "RECRUITER_20",
            "Persona_Tier": "HIRING_TIER_1",
            "Hiring_Track": "RECRUITER_RESEARCH",
            "ICP_Fit": True,
            "ICP_Score": 9,
            "ICP_Reason": f"Active recruiter screening for {job_role}",
            "Active_Job_URL": job_url,
            "Source": "Live Job Board Crawl",
            "Status": "Pending",
            "Contacted_At": ""
        }
        generated_leads.append(recruiter_lead)

    print(f"✅ Generated {len(generated_leads)} targeted hiring decision-maker leads from pure-play startups.")
    return generated_leads
