import pandas as pd

file_path = r'C:\Users\Isaiah\Downloads\autoationlistcoerrect vesio.xlsx'
try:
    df = pd.read_excel(file_path)
    print(f'Total rows read: {len(df)}')
    print('Row 0:', df.iloc[0].to_dict() if len(df) > 0 else 'Empty')
    print('Row 1:', df.iloc[1].to_dict() if len(df) > 1 else 'Empty')
    
    # Let's fix it up and mark last 20 as Contacted
    if 'Status' not in df.columns:
        df['Status'] = 'Pending'
    if len(df) >= 20:
        df.loc[df.index[-20:], 'Status'] = 'Contacted'
    df.to_excel(file_path, index=False)
    print("Marked last 20 as contacted.")
except Exception as e:
    print(f"Error reading file: {e}")
