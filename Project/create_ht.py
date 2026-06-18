import pandas as pd
import os

os.makedirs('data/processed', exist_ok=True)

print("Calculating H+T Index from ACS data...")

acs = pd.read_csv('data/processed/acs_tracts.csv')
print(f"Loaded {len(acs)} tracts")

# --- Housing cost ratio ---
acs['annual_rent'] = acs['median_gross_rent'] * 12
acs['housing_cost_ratio'] = (
    acs['annual_rent'] / acs['median_income']
).clip(0, 1)

# --- Transport cost proxy ---
# No-vehicle households: ~$2,000/year (transit + rideshare)
# Vehicle households: ~$10,000/year (AAA 2023 average)
AAA_CAR_COST_ANNUAL = 10000
TRANSIT_COST_ANNUAL = 2000

acs['est_transport_cost'] = (
    (1 - acs['pct_no_vehicle']) * AAA_CAR_COST_ANNUAL +
    acs['pct_no_vehicle'] * TRANSIT_COST_ANNUAL
)

acs['transport_cost_ratio'] = (
    acs['est_transport_cost'] / acs['median_income']
).clip(0, 1)

# --- Combined H+T ratio ---
acs['ht_combined_ratio'] = (
    acs['housing_cost_ratio'] + acs['transport_cost_ratio']
).clip(0, 1)

# --- Flag tracts above 45% threshold ---
acs['ht_above_threshold'] = acs['ht_combined_ratio'] > 0.45

# --- Output only H+T columns ---
ht_index = acs[[
    'GEOID',
    'housing_cost_ratio',
    'transport_cost_ratio',
    'ht_combined_ratio',
    'ht_above_threshold'
]].copy()

ht_index.to_csv('data/processed/ht_index_tracts.csv', index=False)

above = ht_index['ht_above_threshold'].sum()
total = len(ht_index)

print(f"\n SUCCESS!")
print(f" Saved to data/processed/ht_index_tracts.csv")
print(f" Tracts above 45% H+T threshold: {above} of {total} ({above/total*100:.1f}%)")
print(f"\n Preview (highest burden tracts):")
print(ht_index.sort_values('ht_combined_ratio', ascending=False).head(5))