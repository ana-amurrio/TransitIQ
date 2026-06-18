import pandas as pd
import os

os.makedirs('data/outputs', exist_ok=True)

print("Loading all processed datasets...")

acs     = pd.read_csv('data/processed/acs_tracts.csv')
transit = pd.read_csv('data/transit/transit_access_per_tract.csv')
fars    = pd.read_csv('data/processed/fars_crashes_per_tract.csv')
lodes   = pd.read_csv('data/processed/lodes_tract_jobs.csv')
ht      = pd.read_csv('data/processed/ht_index_tracts.csv')

print(f"ACS:     {len(acs)} tracts")
print(f"Transit: {len(transit)} tracts")
print(f"FARS:    {len(fars)} tracts")
print(f"LODES:   {len(lodes)} tracts")
print(f"H+T:     {len(ht)} tracts")

# --- Ensure GEOID is string with consistent format ---
for df in [acs, transit, fars, lodes, ht]:
    df['GEOID'] = df['GEOID'].astype(str).str.zfill(11)

# --- Join everything on GEOID ---
print("\nJoining all datasets on GEOID...")
master = acs.copy()
master = master.merge(transit, on='GEOID', how='left')
master = master.merge(fars,    on='GEOID', how='left')
master = master.merge(lodes,   on='GEOID', how='left')
master = master.merge(ht,      on='GEOID', how='left')

print(f"Master rows: {len(master)}")
print(f"Master columns: {len(master.columns)}")

# --- Fill zeros for count columns ---
master['crash_count']       = master['crash_count'].fillna(0)
master['total_fatalities']  = master['total_fatalities'].fillna(0)
master['stop_count']        = master['stop_count'].fillna(0)
master['route_count']       = master['route_count'].fillna(0)
master['transit_score']     = master['transit_score'].fillna(0)
master['total_jobs']        = master['total_jobs'].fillna(0)
master['is_transit_desert'] = master['is_transit_desert'].fillna(True)
master['ht_above_threshold']= master['ht_above_threshold'].fillna(False)

# --- Save master file ---
master.to_csv('data/outputs/master_tract_data.csv', index=False)

print(f"\n SUCCESS!")
print(f" Saved to data/outputs/master_tract_data.csv")
print(f" Shape: {master.shape[0]} rows x {master.shape[1]} columns")

# --- Summary stats ---
print(f"\n SUMMARY STATISTICS:")
print(f" Total population covered:     {master['total_population'].sum():,.0f}")
print(f" Median income range:          ${master['median_income'].min():,.0f} - ${master['median_income'].max():,.0f}")
print(f" Transit desert tracts:        {master['is_transit_desert'].sum()}")
print(f" H+T unaffordable tracts:      {master['ht_above_threshold'].sum()}")
print(f" Fatal crash tracts:           {(master['crash_count'] > 0).sum()}")
print(f" Avg transit score:            {master['transit_score'].mean():.3f}")

print(f"\n NULL COUNTS (columns with missing data):")
nulls = master.isnull().sum()
print(nulls[nulls > 0])

print(f"\n Preview:")
print(master[['GEOID', 'median_income', 'transit_score',
              'crash_count', 'ht_combined_ratio',
              'total_jobs']].head(5))