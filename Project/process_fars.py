import pandas as pd
import geopandas as gpd
import os

os.makedirs('data/raw', exist_ok=True)
os.makedirs('data/processed', exist_ok=True)

# --- Load full FARS file ---
print("Loading FARS 2023...")
df = pd.read_csv('data/raw/FARS2023NationalCSV/accident.csv', encoding='latin-1')
print(f"Total US crashes: {len(df)}")

# --- Filter to Franklin County, Ohio ---
franklin = df[(df['STATE'] == 39) & (df['COUNTY'] == 49)].copy()
print(f"Franklin County crashes: {len(franklin)}")

# --- Clean coordinates ---
franklin = franklin[
    (franklin['LATITUDE'] < 90) &
    (franklin['LONGITUD'] < 0) &
    (franklin['LATITUDE'].notna()) &
    (franklin['LONGITUD'].notna())
].copy()
print(f"Valid coordinates: {len(franklin)}")

# --- Keep needed columns ---
franklin = franklin[['ST_CASE', 'YEAR', 'LATITUDE', 'LONGITUD', 'FATALS']].copy()
franklin.to_csv('data/raw/fars_franklin_raw.csv', index=False)
print("Saved raw filtered file")

# --- Create GeoDataFrame ---
print("Creating spatial data...")
gdf = gpd.GeoDataFrame(
    franklin,
    geometry=gpd.points_from_xy(franklin['LONGITUD'], franklin['LATITUDE']),
    crs='EPSG:4326'
)

# --- Load tracts ---
print("Loading tracts...")
tracts = gpd.read_file('data/geospatial/franklin_tracts.geojson')

# --- Spatial join ---
print("Joining crashes to tracts...")
crashes_in_tracts = gpd.sjoin(gdf, tracts, how='left', predicate='within')

# --- Aggregate ---
crashes_per_tract = (
    crashes_in_tracts.groupby('GEOID')
    .agg(
        crash_count=('ST_CASE', 'count'),
        total_fatalities=('FATALS', 'sum')
    )
    .reset_index()
)

# --- Merge with all tracts ---
all_tracts = tracts[['GEOID']].copy()
fars_full = all_tracts.merge(crashes_per_tract, on='GEOID', how='left').fillna(0)

# --- Save ---
fars_full.to_csv('data/processed/fars_crashes_per_tract.csv', index=False)

print(f"\n SUCCESS!")
print(f" Saved to data/processed/fars_crashes_per_tract.csv")
print(f" Tracts with crashes: {(fars_full['crash_count'] > 0).sum()}")
print(f" Total fatalities: {fars_full['total_fatalities'].sum()}")
print(f"\n Preview (most dangerous tracts):")
print(fars_full.sort_values('crash_count', ascending=False).head(5))