import pandas as pd
import glob
import os

print("Scanning for the 5000+ dataset...")
files = glob.glob(r'C:\Users\Isaiah\Downloads\*.xlsx') + glob.glob(r'C:\Users\Isaiah\Downloads\*.csv')

results = []
for f in files:
    try:
        if f.endswith('.xlsx'):
            df = pd.read_excel(f)
        else:
            df = pd.read_csv(f, on_bad_lines='skip', low_memory=False)
        count = len(df)
        if count > 0:
            results.append((os.path.basename(f), count))
    except Exception as e:
        pass

results.sort(key=lambda x: x[1], reverse=True)
for name, count in results:
    if count >= 1000:
        print(f"{name}: {count} rows")
