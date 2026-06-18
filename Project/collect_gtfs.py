import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import urllib.request
import zipfile
import os

os.makedirs('data/raw', exist_ok=True)
os.makedirs('data/transit', exist_ok=True)
os.makedirs('data/geospatial', exist_ok=True)

# --- Download COTA GTFS ---
print("Downloading COTA GTFS feed...")
url = "https://www.cota.com/COTA/media/COTAContent/OpenGTFSData.zip"
urllib.request.urlretrieve(url, "data/raw/cota_gtfs.zip")
print("Download complete. Extracting...")

# --- Extract needed files ---
with zipfile.ZipFile("data/raw/cota_gtfs.zip", 'r') as z:
    z.extract('stops.txt', 'data/transit/')
    z.extract('routes.txt', 'data/transit/')
    z.extract('trips.txt', 'data/transit/')
    z.extract('stop_times.txt', 'data/transit/')
print("Extracted stops, routes, trips, stop_times")

# --- Load stops ---
stops = pd.read_csv('data/transit/stops.txt')
print(f"Total COTA stops: {len(stops)}")
print(f"Stops columns: {list(stops.columns)}")

# --- Create GeoDataFrame for stops ---
stops_gdf = gpd.GeoDataFrame(
    stops,
    geometry=gpd.points_from_xy(stops.stop_lon, stops.stop_lat),
    crs='EPSG:4326'
)

# --- Load Franklin County tracts ---
tracts = gpd.read_file('data/geospatial/franklin_tracts.geojson')

# --- Spatial join: assign each stop to a tract ---
print("Joining stops to tracts...")
stops_in_tracts = gpd.sjoin(
    stops_gdf,
    tracts,
    how='inner',
    predicate='within'
)
print(f"Stops within Franklin County tracts: {len(stops_in_tracts)}")

# --- Count stops per tract ---
stops_per_tract = (
    stops_in_tracts.groupby('GEOID')
    .size()
    .reset_index(name='stop_count')
)

# --- Count unique routes per tract ---
stop_times = pd.read_csv('data/transit/stop_times.txt')
trips = pd.read_csv('data/transit/trips.txt')

# Join stop_times -> trips -> routes to get route per stop
stop_route = stop_times.merge(
    trips[['trip_id', 'route_id']], on='trip_id'
).merge(
    stops_in_tracts[['stop_id', 'GEOID']], on='stop_id'
)

routes_per_tract = (
    stop_route.groupby('GEOID')['route_id']
    .nunique()
    .reset_index(name='route_count')
)

# --- Merge into transit access per tract ---
transit = stops_per_tract.merge(routes_per_tract, on='GEOID', how='left')

# Normalize transit score 0-1
transit['transit_score'] = (
    (transit['stop_count'] * transit['route_count']) /
    (transit['stop_count'] * transit['route_count']).max()
).round(4)

transit['is_transit_desert'] = transit['transit_score'] == 0

# --- Merge with ALL tracts (tracts with zero stops get 0) ---
all_tracts = tracts[['GEOID']].copy()
transit_full = all_tracts.merge(transit, on='GEOID', how='left').fillna(0)
transit_full['is_transit_desert'] = transit_full['stop_count'] == 0

# --- Save ---
transit_full.to_csv('data/transit/transit_access_per_tract.csv', index=False)

# Save stops as GeoJSON for dashboard map
stops_gdf.to_file('data/geospatial/cota_stops.geojson', driver='GeoJSON')

print(f"\n SUCCESS!")
print(f" Transit access saved: data/transit/transit_access_per_tract.csv")
print(f" COTA stops GeoJSON saved: data/geospatial/cota_stops.geojson")
print(f" Tracts with zero stops (transit deserts): {transit_full['is_transit_desert'].sum()}")
print(f"\n Preview:")
print(transit_full.sort_values('transit_score', ascending=False).head(5))