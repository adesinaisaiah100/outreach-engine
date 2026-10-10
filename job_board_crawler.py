"""
job_board_crawler.py - Live Job Board Crawler for Pure-Play Nigerian Startups
Sources:
1. LinkedIn Public Jobs Search API (keywords: Software, Frontend, Backend, Flutter, AI, Design in Nigeria)
2. MyJobMag Nigeria ICT / Software listings

Extracts:
- Active Company Name
- Exact Open Job Title
- Location & Job URL
Filters out massive conglomerates (banks, telcos, oil & gas) to isolate authentic pure-play startups.
"""

import os
import sys
import time
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Set

if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Massive corporations to filter out (leaving only agile pure-play startups)
CORPORATE_BLACKLIST = [
    "access bank", "zenith bank", "guaranty trust", "gtbank", "first bank", "uba",
    "stanbic", "fidelity bank", "wema bank", "fcmb", "ecobank", "polaris",
    "mtn", "airtel", "glo", "9mobile", "dangote", "bua", "lafarge", "shell",
    "chevron", "totalenergies", "exxonmobil", "nlng", "oando", "seplat",
    "churchgate", "pwc", "kpmg", "deloitte", "ernst & young", "ey",
    "united nations", "unicef", "who", "federal government", "state government"
]

TECH_KEYWORDS = [
    "Software Engineer",
    "Frontend Developer",
    "Backend Engineer",
    "Full Stack Engineer",
    "Flutter Developer",
    "Mobile Developer",
    "React Developer",
    "Python Developer",
    "AI Engineer",
    "Product Designer",
    "DevOps Engineer"
]

def is_blacklisted(company_name: str) -> bool:
    c = company_name.lower().strip()
    return any(b in c for b in CORPORATE_BLACKLIST)

def crawl_linkedin_jobs(queries: List[str] = None, max_pages_per_query: int = 2) -> List[Dict[str, Any]]:
    """
    Crawls LinkedIn's public search guest endpoint across multiple developer keywords in Nigeria.
    """
    if queries is None:
        queries = TECH_KEYWORDS[:6]

    results = []
    seen_companies = set()

    for query in queries:
        print(f"🔎 Crawling LinkedIn Jobs for '{query}' in Nigeria...")
        for page in range(max_pages_per_query):
            start = page * 25
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={query.replace(' ', '+')}&location=Nigeria&start={start}"
            
            try:
                resp = requests.get(url, headers=HEADERS, timeout=10)
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')
                cards = soup.find_all('div', class_='base-search-card')
                if not cards:
                    break

                for c in cards:
                    t_tag = c.find('h3', class_='base-search-card__title')
                    co_tag = c.find('h4', class_='base-search-card__subtitle')
                    loc_tag = c.find('span', class_='job-search-card__location')
                    link_tag = c.find('a', class_='base-card__full-link')

                    job_title = t_tag.text.strip() if t_tag else ""
                    company = co_tag.text.strip() if co_tag else ""
                    location = loc_tag.text.strip() if loc_tag else "Nigeria"
                    job_url = link_tag['href'].split('?')[0] if link_tag and 'href' in link_tag.attrs else ""

                    if not company or is_blacklisted(company):
                        continue

                    comp_key = re.sub(r'[^a-z0-9]', '', company.lower())
                    if comp_key in seen_companies:
                        continue
                    seen_companies.add(comp_key)

                    results.append({
                        "company": company,
                        "job_title": job_title,
                        "location": location,
                        "job_url": job_url,
                        "source": "LinkedIn Jobs"
                    })

                time.sleep(1.0)
            except Exception as e:
                print(f"⚠️ Error querying '{query}' on page {page}: {e}")
                time.sleep(2.0)

    print(f"✅ Extracted {len(results)} active hiring companies from LinkedIn Jobs.")
    return results

def crawl_myjobmag_tech(max_pages: int = 3) -> List[Dict[str, Any]]:
    """
    Crawls MyJobMag Nigeria Information Technology section for tech hiring companies.
    """
    results = []
    seen_companies = set()
    print("🔎 Crawling MyJobMag Nigeria Tech / IT listings...")

    for page in range(1, max_pages + 1):
        url = f"https://www.myjobmag.com/jobs-by-field/information-technology/{page}" if page > 1 else "https://www.myjobmag.com/jobs-by-field/information-technology"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.find_all('li', class_='job-list-li')
            for item in items:
                h2 = item.find('h2')
                if not h2:
                    continue
                a_tag = h2.find('a')
                raw_title = a_tag.text.strip() if a_tag else h2.text.strip()

                # Parse "Role at Company"
                company = ""
                job_title = raw_title
                if " at " in raw_title:
                    parts = raw_title.rsplit(" at ", 1)
                    job_title = parts[0].strip()
                    company = parts[1].strip()

                # Also try link extraction
                comp_link = item.find('a', href=lambda h: h and '/jobs-at/' in h)
                if comp_link and comp_link.text.strip():
                    company = comp_link.text.strip()

                if not company or "reputable" in company.lower() or "confidential" in company.lower():
                    continue

                if is_blacklisted(company):
                    continue

                comp_key = re.sub(r'[^a-z0-9]', '', company.lower())
                if comp_key in seen_companies:
                    continue
                seen_companies.add(comp_key)

                results.append({
                    "company": company,
                    "job_title": job_title,
                    "location": "Nigeria",
                    "job_url": f"https://www.myjobmag.com{a_tag['href']}" if a_tag and 'href' in a_tag.attrs else "",
                    "source": "MyJobMag"
                })

            time.sleep(1.0)
        except Exception as e:
            print(f"⚠️ Error crawling MyJobMag page {page}: {e}")
            break

    print(f"✅ Extracted {len(results)} active hiring companies from MyJobMag.")
    return results

def get_active_hiring_startups(target_count: int = 50) -> List[Dict[str, Any]]:
    """
    Runs combined crawl, filters out non-startups, and returns unique active startups.
    """
    li_jobs = crawl_linkedin_jobs(queries=TECH_KEYWORDS, max_pages_per_query=2)
    mj_jobs = crawl_myjobmag_tech(max_pages=3)

    combined = []
    seen = set()

    for item in li_jobs + mj_jobs:
        comp_key = re.sub(r'[^a-z0-9]', '', item["company"].lower())
        if comp_key not in seen:
            seen.add(comp_key)
            combined.append(item)
        if len(combined) >= target_count:
            break

    print(f"🎯 Total unique active-hiring companies discovered: {len(combined)}")
    return combined

if __name__ == "__main__":
    startups = get_active_hiring_startups(target_count=40)
    for i, s in enumerate(startups[:15]):
        print(f"{i+1}. {s['company']} | Hiring: {s['job_title']} | Loc: {s['location']}")
