import pandas as pd
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

MASTER_EXCEL = r'C:\Users\Isaiah\Downloads\autoationlistcoerrect vesio.xlsx'
ACTIVE_LEDGER = r'C:\Users\Isaiah\corecv_outreach\data\active_leads.xlsx'
AUDIT_JSON = r'C:\Users\Isaiah\corecv_outreach\audit_classified_leads.json'

with open(AUDIT_JSON, 'r', encoding='utf-8') as f:
    audit_data = json.load(f)

irrelevant_rows = {item['row']: item for item in audit_data['irrelevant']}

def prune_file(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return 0, 0
        
    df = pd.read_excel(file_path)
    pruned_count = 0
    
    for idx, row in df.iterrows():
        status = str(row.get('Status', 'Pending'))
        if idx in irrelevant_rows and status == 'Pending':
            reason = irrelevant_rows[idx].get('reason', 'Non-tech role')
            df.at[idx, 'Status'] = f"Skipped: Non-Tech ({reason})"
            pruned_count += 1
            
    df.to_excel(file_path, index=False)
    
    # Calculate remaining stats
    pending_df = df[df['Status'] == 'Pending']
    return pruned_count, len(pending_df), len(df)

print("Starting leads pruning...")
master_pruned, master_pending, master_total = prune_file(MASTER_EXCEL)
print(f"✅ Master Excel ({MASTER_EXCEL}):")
print(f"   • Pruned: {master_pruned} irrelevant pending leads")
print(f"   • Remaining Active Pending: {master_pending} leads")
print(f"   • Total Rows: {master_total}")

active_pruned, active_pending, active_total = prune_file(ACTIVE_LEDGER)
print(f"✅ Active Dashboard Ledger ({ACTIVE_LEDGER}):")
print(f"   • Pruned: {active_pruned} irrelevant pending leads")
print(f"   • Remaining Active Pending: {active_pending} leads")
print(f"   • Total Rows: {active_total}")

print("\n🎉 Pruning complete! The bot will now ONLY message verified Tech & HR professionals.")
