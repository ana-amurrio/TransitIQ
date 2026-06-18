import pandas as pd
import os

os.makedirs('data/raw', exist_ok=True)
os.makedirs('data/processed', exist_ok=True)

print("Downloading Ohio LODES OD file (this may take 1-2 minutes)...")
url = "https://lehd.ces.census.gov/data/lodes/LODES8/oh/od/oh_od_main_JT00_2021.csv.gz"

import urllib.request
urllib.request.urlretrieve(url, "data/raw/oh_od_main_JT00_2021.csv.gz")
print("Download complete. Loading...")

# --- Load and filter to Franklin County home tracts ---
df = pd.read_csv('data/raw/oh_od_main_JT00_2021.csv.gz', compression='gzip')
print(f"Total Ohio OD pairs: {len(df)}")

# --- Filter: home block starts with 39049 (Franklin County) ---
df['h_geocode'] = df['h_geocode'].astype(str).str.zfill(15)
franklin = df[df['h_geocode'].str.startswith('39049')].copy()
print(f"Franklin County home workers: {len(franklin)}")

# --- Extract tract GEOID from block code (first 11 digits) ---
franklin['GEOID'] = franklin['h_geocode'].str[:11]

# --- Aggregate jobs by home tract ---
tract_jobs = (
    franklin.groupby('GEOID')
    .agg(total_jobs=('S000', 'sum'))
    .reset_index()
)

print(f"Franklin tracts with job data: {len(tract_jobs)}")

# --- Save ---
tract_jobs.to_csv('data/processed/lodes_tract_jobs.csv', index=False)

print(f"\n SUCCESS!")
print(f" Saved to data/processed/lodes_tract_jobs.csv")
print(f" Total workers tracked: {tract_jobs['total_jobs'].sum():,.0f}")
print(f"\n Preview:")
print(tract_jobs.sort_values('total_jobs', ascending=False).head(5))