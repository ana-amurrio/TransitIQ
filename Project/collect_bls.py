import pandas as pd
import urllib.request
import zipfile
import os

os.makedirs('data/raw', exist_ok=True)
os.makedirs('data/processed', exist_ok=True)

print("Downloading BLS OEWS metro area data...")
url = "https://www.bls.gov/oes/special.requests/oesm24ma.zip"
urllib.request.urlretrieve(url, "data/raw/oesm24ma.zip")
print("Download complete. Extracting...")

# --- Check what's inside ---
with zipfile.ZipFile("data/raw/oesm24ma.zip", 'r') as z:
    print(f"Files in zip: {z.namelist()}")
    # Extract all
    z.extractall("data/raw/bls_oews/")
print("Extracted.")

# --- Find the metro area file ---
import glob
files = glob.glob("data/raw/bls_oews/*.xlsx") + glob.glob("data/raw/bls_oews/*.csv")
print(f"Found files: {files}")

# --- Load metro file ---
# BLS OEWS metro file is typically an xlsx
metro_file = [f for f in files if 'MSA' in f.upper() or 'metro' in f.lower() or 'ma' in f.lower()]
print(f"Metro file: {metro_file}")

df = pd.read_excel(metro_file[0], dtype=str)
print(f"Total rows: {len(df)}")
print(f"Columns: {list(df.columns[:8])}")

# --- Filter to Columbus MSA (area code 17140) ---
columbus = df[df['area'].astype(str) == '17140'].copy()
print(f"Columbus MSA occupations: {len(columbus)}")

# --- Keep needed columns ---
columbus = columbus[['area_title', 'occ_code', 'occ_title', 'h_mean', 'h_median', 'a_mean', 'a_median']].copy()

# --- Replace BLS suppression codes ---
columbus = columbus.replace(['*', '#', '**'], pd.NA)

# --- Convert wages to numeric ---
for col in ['h_mean', 'h_median', 'a_mean', 'a_median']:
    columbus[col] = pd.to_numeric(columbus[col], errors='coerce')

# --- Extract all-occupations median hourly wage ---
all_occ = columbus[columbus['occ_code'] == '00-0000']
if len(all_occ) > 0:
    median_hourly = all_occ['h_median'].values[0]
    print(f"\n Columbus median hourly wage (all occupations): ${median_hourly}")

# --- Save ---
columbus.to_csv('data/processed/bls_wages_columbus.csv', index=False)

print(f"\n SUCCESS!")
print(f" Saved to data/processed/bls_wages_columbus.csv")
print(f"\n Preview:")
print(columbus[['occ_title', 'h_median', 'a_median']].head(5))