import geopandas as gpd
import os
import urllib.request

print("Downloading Ohio tract shapefiles...")
url = "https://www2.census.gov/geo/tiger/TIGER2023/TRACT/tl_2023_39_tract.zip"
os.makedirs('data/raw', exist_ok=True)
os.makedirs('data/geospatial', exist_ok=True)

urllib.request.urlretrieve(url, "data/raw/ohio_tracts.zip")
print("Download complete. Loading...")

gdf = gpd.read_file("zip://data/raw/ohio_tracts.zip")
print(f"Ohio total tracts: {len(gdf)}")

# Filter to Franklin County only
franklin = gdf[gdf['COUNTYFP'] == '049'].copy()
print(f"Franklin County tracts: {len(franklin)}")

# Keep only needed columns
franklin = franklin[['GEOID', 'geometry']]

# Reproject to WGS84 (required for pydeck/folium)
franklin = franklin.to_crs(epsg=4326)

# Save as GeoJSON
output_path = "data/geospatial/franklin_tracts.geojson"
franklin.to_file(output_path, driver='GeoJSON')

print(f"\n SUCCESS!")
print(f" Saved {len(franklin)} tracts to {output_path}")
print(f" CRS: {franklin.crs}")
print(f" Preview:\n{franklin.head(3)}")