import pandas as pd
import os

os.makedirs('data/processed', exist_ok=True)

print("Loading BLS OEWS MSA file...")
df = pd.read_excel('data/raw/bls_oews/oesm24ma/MSA_M2024_dl.xlsx', dtype=str)
print(f"Total rows: {len(df)}")
print(f"Columns: {list(df.columns)}")

# --- Filter to Columbus MSA ---
columbus = df[df['AREA'] == '17140'].copy()
print(f"Columbus MSA occupations: {len(columbus)}")

# --- Keep needed columns ---
columbus = columbus[['AREA_TITLE', 'OCC_CODE', 'OCC_TITLE', 'H_MEAN', 'H_MEDIAN', 'A_MEAN', 'A_MEDIAN']].copy()

# --- Replace BLS suppression codes ---
columbus = columbus.replace(['*', '#', '**'], pd.NA)

# --- Convert to numeric ---
for col in ['H_MEAN', 'H_MEDIAN', 'A_MEAN', 'A_MEDIAN']:
    columbus[col] = pd.to_numeric(columbus[col], errors='coerce')

# --- Print all-occupations median wage ---
all_occ = columbus[columbus['OCC_CODE'] == '00-0000']
if len(all_occ) > 0:
    print(f"\n Columbus median hourly wage (all occupations): ${all_occ['H_MEDIAN'].values[0]}")
    print(f" Columbus median annual wage (all occupations): ${all_occ['A_MEDIAN'].values[0]:,.0f}")

# --- Save ---
columbus.to_csv('data/processed/bls_wages_columbus.csv', index=False)

print(f"\n SUCCESS!")
print(f" Saved to data/processed/bls_wages_columbus.csv")
print(f"\n Preview:")
print(columbus[['OCC_TITLE', 'H_MEDIAN', 'A_MEDIAN']].head(5))