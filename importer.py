import re
import io
import pandas as pd
import json

def fuzzy_find_column(columns, candidates):
    """Finds the best matching column name from a list of candidates."""
    cols_clean = {c: re.sub(r'[^a-z0-9]', '', str(c).lower()) for c in columns}
    for cand in candidates:
        cand_clean = re.sub(r'[^a-z0-9]', '', cand.lower())
        for orig_col, clean_col in cols_clean.items():
            if cand_clean == clean_col or cand_clean in clean_col:
                return orig_col
    return None

def normalize_leads_file(file_content_or_path, filename=""):
    """
    Ingests ANY messy Excel or CSV file, detects columns intelligently,
    splits full names, adds Status ledger, and returns a clean DataFrame.
    """
    is_csv = filename.lower().endswith('.csv') or (isinstance(file_content_or_path, str) and file_content_or_path.lower().endswith('.csv'))
    
    if isinstance(file_content_or_path, bytes):
        buffer = io.BytesIO(file_content_or_path)
        if is_csv:
            try:
                raw_df = pd.read_csv(buffer, encoding='utf-8')
            except Exception:
                buffer.seek(0)
                raw_df = pd.read_csv(buffer, encoding='latin1')
        else:
            raw_df = pd.read_excel(buffer)
    else:
        if is_csv:
            try:
                raw_df = pd.read_csv(file_content_or_path, encoding='utf-8')
            except Exception:
                raw_df = pd.read_csv(file_content_or_path, encoding='latin1')
        else:
            raw_df = pd.read_excel(file_content_or_path)
            
    # Check for LinkedIn Export 3-row disclaimers
    if len(raw_df) > 0 and (str(raw_df.columns[0]).startswith("Notes:") or str(raw_df.iloc[0, 0]).startswith("When exporting")):
        if isinstance(file_content_or_path, bytes):
            buffer.seek(0)
            raw_df = pd.read_excel(buffer, skiprows=3) if not is_csv else pd.read_csv(buffer, skiprows=3)
        else:
            raw_df = pd.read_excel(file_content_or_path, skiprows=3) if not is_csv else pd.read_csv(file_content_or_path, skiprows=3)

    cols = list(raw_df.columns)
    
    # 1. Detect LinkedIn URL Column
    url_col = fuzzy_find_column(cols, [
        'linkedinurl', 'linkedinprofile', 'profileurl', 'linkedinlink', 
        'profilelink', 'linkedin', 'url', 'link', 'webprofile'
    ])
    
    # 2. Detect First Name / Full Name
    fname_col = fuzzy_find_column(cols, ['firstname', 'first_name', 'fname', 'givenname', 'first'])
    lname_col = fuzzy_find_column(cols, ['lastname', 'last_name', 'lname', 'surname', 'familyname', 'last'])
    fullname_col = fuzzy_find_column(cols, ['fullname', 'full_name', 'name', 'contact_name', 'candidate_name', 'person'])
    
    # 3. Detect Position / Job Title
    pos_col = fuzzy_find_column(cols, [
        'position', 'jobtitle', 'title', 'role', 'headline', 
        'occupation', 'designation', 'currentposition', 'job'
    ])
    
    clean_df = pd.DataFrame()
    
    # Build First Name and Last Name
    if fname_col and lname_col:
        clean_df['First Name'] = raw_df[fname_col].fillna('').astype(str).str.strip()
        clean_df['Last Name'] = raw_df[lname_col].fillna('').astype(str).str.strip()
    elif fullname_col:
        full_names = raw_df[fullname_col].fillna('').astype(str).str.strip()
        clean_df['First Name'] = full_names.apply(lambda x: x.split()[0] if len(x.split()) > 0 else "")
        clean_df['Last Name'] = full_names.apply(lambda x: " ".join(x.split()[1:]) if len(x.split()) > 1 else "")
    elif fname_col:
        clean_df['First Name'] = raw_df[fname_col].fillna('').astype(str).str.strip()
        clean_df['Last Name'] = ""
    else:
        # Fallback to first text column
        clean_df['First Name'] = raw_df.iloc[:, 0].fillna('').astype(str).str.strip()
        clean_df['Last Name'] = ""
        
    # Build LinkedIn URL
    if url_col:
        clean_df['LinkedIn URL'] = raw_df[url_col].fillna('').astype(str).str.strip()
    else:
        clean_df['LinkedIn URL'] = ""
        
    # Build Position
    if pos_col:
        clean_df['Position'] = raw_df[pos_col].fillna('').astype(str).str.strip()
    else:
        clean_df['Position'] = "Professional"
        
    # Preserve or Initialize Status & Timestamp
    status_col = fuzzy_find_column(cols, ['status', 'outreach_status', 'state'])
    if status_col:
        clean_df['Status'] = raw_df[status_col].fillna('Pending').astype(str).str.strip()
    else:
        clean_df['Status'] = 'Pending'
        
    contacted_col = fuzzy_find_column(cols, ['contactedat', 'contacted_at', 'date_contacted', 'timestamp'])
    if contacted_col:
        clean_df['Contacted_At'] = raw_df[contacted_col].fillna('').astype(str)
    else:
        clean_df['Contacted_At'] = ''
        
    # Filter empty or completely invalid rows
    clean_df = clean_df[clean_df['LinkedIn URL'].str.contains('linkedin.com', case=False, na=False)].copy()
    clean_df.reset_index(drop=True, inplace=True)
    
    # Calculate quick stats
    hr_keywords = ['hr', 'talent', 'recruit', 'people', 'hiring', 'human resource']
    hr_count = int(clean_df['Position'].str.lower().apply(lambda x: any(k in str(x) for k in hr_keywords)).sum())
    tech_count = len(clean_df) - hr_count
    
    mapping_report = {
        "detected_url_col": str(url_col or "Inferred"),
        "detected_name_col": str(fname_col or fullname_col or "Inferred"),
        "detected_pos_col": str(pos_col or "Inferred"),
        "total_valid_leads": len(clean_df),
        "hr_leads": hr_count,
        "tech_leads": tech_count
    }
    
    return clean_df, mapping_report
