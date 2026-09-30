import pandas as pd

file_path = r'C:\Users\Isaiah\Downloads\linkedinautomation.xlsx'
df = pd.read_excel(file_path)
print(f'ACTUAL_ROWS: {len(df)}')

if 'Status' not in df.columns:
    df['Status'] = 'Pending'

df.loc[df.index[-20:], 'Status'] = 'Contacted'
df.to_excel(file_path, index=False)
print('Done!')
