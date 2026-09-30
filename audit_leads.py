import pandas as pd
import re
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_excel(r'C:\Users\Isaiah\Downloads\autoationlistcoerrect vesio.xlsx')

def classify_position(pos):
    if not isinstance(pos, str) or not pos.strip():
        return 'IRRELEVANT', 'Empty / Missing Role'
    
    p = pos.lower().strip()
    
    # 1. HR Check
    hr_keywords = ['talent acquisition', 'head of people', 'people operations', 'human resources', 'recruiter', 'recruiting', 'hr manager', 'hr specialist', 'hr generalist', 'hr officer', 'hr lead', 'hr consultant', 'talent partner', 'hiring manager', 'people & culture', 'people and culture']
    if any(k in p for k in hr_keywords) or re.search(r'\bhr\b', p):
        return 'HR', 'HR / Talent Acquisition'
        
    # 2. Definite Tech Keywords
    tech_keywords = [
        'software', 'frontend', 'front-end', 'backend', 'back-end', 'fullstack', 'full-stack', 
        'full stack', 'developer', 'programmer', 'web dev', 'web engineer', 'data analyst', 
        'data scientist', 'data engineer', 'machine learning', 'deep learning', 'ai engineer', 
        'devops', 'cloud engineer', 'cloud architect', 'ui/ux', 'ux designer', 'ui designer', 
        'product designer', 'product manager', 'product owner', 'mobile developer', 'mobile app', 
        'ios developer', 'android developer', 'flutter', 'react native', 'qa engineer', 'quality assurance', 
        'test engineer', 'automation engineer', 'cybersecurity', 'security analyst', 'security engineer', 
        'embedded', 'firmware', 'solutions architect', 'systems architect', 'cto', 'chief technology officer', 
        'tech lead', 'technical lead', 'engineering manager', 'lead engineer', 'scrum master',
        'python', 'javascript', 'typescript', 'react', 'node', 'django', 'fastapi', 'golang', 'rust', 'java'
    ]
    
    # Non-Tech exclusion overrides (e.g. "Site Engineer", "Electrical Engineer", "Civil Engineer")
    non_tech_override = [
        'civil', 'site engineer', 'structural', 'refactory', 'wiring', 'technician', 
        'building', 'construction', 'reservoir', 'petroleum', 'drilling', 'estate', 
        'supply chain', 'logistics', 'procurement', 'accounting', 'auditor', 'audit', 
        'lawyer', 'legal', 'medical', 'nurse', 'doctor', 'physician', 'pharmacist', 
        'chemist', 'biologist', 'agriculture', 'farmer', 'media aide', 'chairman', 
        'internal affairs', 'sales rep', 'sales executive', 'marketing executive', 
        'business development', 'customer service', 'receptionist', 'admin assistant', 
        'virtual assistant', 'graphic artist', 'internship trainee', 'industrial training', 
        'trainee', 'awareness volunteer'
    ]
    
    for nk in non_tech_override:
        if nk in p and not any(tk in p for tk in ['software', 'frontend', 'backend', 'fullstack', 'data', 'devops', 'cloud', 'ui/ux']):
            return 'IRRELEVANT', f"Non-tech keyword matched: '{nk}'"
            
    for tk in tech_keywords:
        if tk in p:
            return 'TECH', f"Tech keyword matched: '{tk}'"
            
    # Generic "Engineer" without tech qualifier
    if 'engineer' in p and not any(k in p for k in ['software', 'cloud', 'devops', 'data', 'security', 'frontend', 'backend', 'fullstack', 'qa', 'test', 'systems', 'network', 'firmware', 'embedded', 'ai', 'ml', 'machine learning']):
        return 'IRRELEVANT', 'Generic/Non-tech Engineering title'
        
    return 'IRRELEVANT', 'Unrecognized non-tech role'

results = []
category_counts = {'TECH': 0, 'HR': 0, 'IRRELEVANT': 0}

for idx, row in df.iterrows():
    name = (str(row.get('First Name', '')) + ' ' + str(row.get('Last Name', ''))).strip()
    pos = str(row.get('Position', ''))
    stat = str(row.get('Status', 'Pending'))
    url = str(row.get('LinkedIn URL', row.get('URL', '')))
    
    cat, reason = classify_position(pos)
    category_counts[cat] += 1
    
    results.append({
        'row': idx,
        'name': name,
        'position': pos,
        'category': cat,
        'reason': reason,
        'status': stat,
        'url': url
    })

irrelevant_list = [r for r in results if r['category'] == 'IRRELEVANT']

print(f"==================================================")
print(f"📊 DATASET CLASSIFICATION AUDIT RESULTS")
print(f"==================================================")
print(f"Total Leads in Spreadsheet: {len(df)}")
print(f"💻 Verified Tech Professionals: {category_counts['TECH']}")
print(f"👔 Verified HR Decision Makers: {category_counts['HR']}")
print(f"❌ Irrelevant Non-Tech / Unrelated Roles: {category_counts['IRRELEVANT']}")
print(f"==================================================\n")

print(f"🚨 ALL {len(irrelevant_list)} IRRELEVANT LEADS IDENTIFIED:")
print(f"{'Row':<6} | {'Name':<30} | {'Status':<12} | {'Position'}")
print("-" * 85)
for item in irrelevant_list:
    print(f"{item['row']:<6} | {item['name'][:30]:<30} | {item['status'][:12]:<12} | {item['position']}")

# Save detailed JSON report
with open(r'C:\Users\Isaiah\corecv_outreach\audit_classified_leads.json', 'w', encoding='utf-8') as f:
    json.dump({'summary': category_counts, 'irrelevant': irrelevant_list}, f, indent=2)

print("\nAudit saved to audit_classified_leads.json")
