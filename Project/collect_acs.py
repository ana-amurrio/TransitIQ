from census import Census
import pandas as pd
import os

# --- Config ---
API_KEY = "f3e335b1add470c10bfd90b58a01c40a5211df77"
STATE = '39'
COUNTY = '049'

# --- All required ACS columns ---
FIELDS = (
    'NAME',
    'B19013_001E',  # Median household income
    'B08303_001E',  # Total commuters
    'B08303_008E',  # 30-34 min commute
    'B08303_009E',  # 35-39 min commute
    'B08303_010E',  # 40-44 min commute
    'B08303_011E',  # 45-59 min commute
    'B08303_012E',  # 60-89 min commute
    'B08303_013E',  # 90+ min commute
    'B08141_001E',  # Total workers 16+
    'B08141_002E',  # No vehicle available
    'B08301_001E',  # Total commute mode
    'B08301_010E',  # Public transit commuters
    'B18101_001E',  # Total disability population
    'C27007_001E',  # Total Medicaid enrollment
    'C27007_004E',  # Medicaid - below poverty
    'C27007_007E',  # Medicaid - above poverty
    'B25064_001E',  # Median gross rent
    'B25070_007E',  # Rent burden 35-39%
    'B25070_008E',  # Rent burden 40-49%
    'B25070_009E',  # Rent burden 50%+
    'B25070_010E',  # Rent burden not computed
    'B01001_001E',  # Total population
    'B14001_002E',  # School enrollment public
    'B15003_001E',  # Educational attainment base
    'B08201_001E',  # Total households
    'B08201_002E',  # Households no vehicle
)

# --- Pull data ---
print("Connecting to Census API...")
c = Census(API_KEY)

print("Pulling ACS 5-Year data for Franklin County tracts...")
data = c.acs5.state_county_tract(
    fields=FIELDS,
    state_fips=STATE,
    county_fips=COUNTY,
    tract='*'
)
print(f"Retrieved {len(data)} tracts")

# --- Convert to DataFrame ---
df = pd.DataFrame(data)

# --- Build GEOID (join key for everything else) ---
df['GEOID'] = df['state'] + df['county'] + df['tract']

# --- Drop redundant columns ---
df = df.drop(columns=['state', 'county', 'tract', 'NAME'])

# --- Convert all data columns to numeric (handles NAs cleanly) ---
for col in df.columns:
    if col != 'GEOID':
        df[col] = pd.to_numeric(df[col], errors='coerce')

# --- Replace Census null sentinels with NaN ---
NULLS = [-666666666, -999999999, -888888888, -222222222, -333333333]
for null_val in NULLS:
    df = df.replace(null_val, float('nan'))

# --- Rename columns to human-readable ---
df = df.rename(columns={
    'B19013_001E': 'median_income',
    'B08303_001E': 'total_commuters',
    'B08303_008E': 'commute_30_34min',
    'B08303_009E': 'commute_35_39min',
    'B08303_010E': 'commute_40_44min',
    'B08303_011E': 'commute_45_59min',
    'B08303_012E': 'commute_60_89min',
    'B08303_013E': 'commute_90plus_min',
    'B08141_001E': 'workers_16plus',
    'B08141_002E': 'workers_no_vehicle',
    'B08301_001E': 'commute_mode_total',
    'B08301_010E': 'transit_commuters',
    'B18101_001E': 'disability_pop',
    'C27007_001E': 'medicaid_total',
    'C27007_004E': 'medicaid_below_poverty',
    'C27007_007E': 'medicaid_above_poverty',
    'B25064_001E': 'median_gross_rent',
    'B25070_007E': 'rent_burden_35_39pct',
    'B25070_008E': 'rent_burden_40_49pct',
    'B25070_009E': 'rent_burden_50plus_pct',
    'B25070_010E': 'rent_burden_not_computed',
    'B01001_001E': 'total_population',
    'B14001_002E': 'school_enrollment_public',
    'B15003_001E': 'educational_attainment_base',
    'B08201_001E': 'total_households',
    'B08201_002E': 'households_no_vehicle',
})

# --- Derived columns (safe division with numeric columns) ---
df['pct_transit_commuters'] = (
    df['transit_commuters'] / df['commute_mode_total']
).round(4)

df['pct_no_vehicle'] = (
    df['workers_no_vehicle'] / df['workers_16plus']
).round(4)

df['pct_rent_burdened_severe'] = (
    df['rent_burden_50plus_pct'] / df['total_households']
).round(4)

df['hourly_wage_estimate'] = (
    df['median_income'] / 2080
).round(2)

# --- Put GEOID first ---
cols = ['GEOID'] + [c for c in df.columns if c != 'GEOID']
df = df[cols]

# --- Save ---
os.makedirs('data/processed', exist_ok=True)
output_path = 'data/processed/acs_tracts.csv'
df.to_csv(output_path, index=False)

print(f"\n SUCCESS!")
print(f" Saved {len(df)} tracts to {output_path}")
print(f" Columns: {len(df.columns)}")
print(f"\n Preview:")
print(df[['GEOID', 'median_income', 'transit_commuters',
          'pct_transit_commuters', 'total_population']].head(5))
print(f"\n Null counts (top 5 columns with nulls):")
null_counts = df.isnull().sum()
print(null_counts[null_counts > 0].head(5))