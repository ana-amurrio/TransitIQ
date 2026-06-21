"""
build_tract_names.py
--------------------
Reverse-geocode Franklin County census tract centroids using Nominatim (OSM).
Outputs: data/processed/tract_neighborhood_names.csv

Columns:
  GEOID           - 11-digit census tract ID
  neighborhood    - best available place name (neighbourhood > suburb > quarter > city_district)
  display_name    - short display label, e.g. "Linden · Tract 1234.56"

Rate limit: 1 request/second (Nominatim policy).
Runtime: ~6 minutes for 328 tracts.
"""

import geopandas as gpd
import pandas as pd
import requests
import time
import re
import os

GEOJSON = "data/geospatial/franklin_tracts.geojson"
OUT_CSV = "data/processed/tract_neighborhood_names.csv"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
HEADERS = {"User-Agent": "TransitIQ-Hackathon/1.0 (saransakthi.v@gmail.com)"}


def geoid_to_tract_number(geoid: str) -> str:
    """Convert 11-digit GEOID to readable tract number e.g. '390490012345' -> 'Tract 123.45'"""
    raw = str(geoid).zfill(11)
    tract_raw = raw[5:]          # last 6 digits = tract code
    major = int(tract_raw[:4])   # first 4 digits = major
    minor = int(tract_raw[4:])   # last 2 digits = minor (decimal)
    if minor == 0:
        return f"Tract {major}"
    else:
        return f"Tract {major}.{minor:02d}"


def best_name(result: dict) -> str:
    """Extract most specific neighborhood name from Nominatim response."""
    addr = result.get("address", {})
    for field in ["neighbourhood", "suburb", "quarter", "city_district", "hamlet", "village", "town"]:
        val = addr.get(field)
        if val:
            return val
    return ""


def main():
    os.makedirs("data/processed", exist_ok=True)

    print("Loading GeoJSON...")
    gdf = gpd.read_file(GEOJSON)
    gdf["GEOID"] = gdf["GEOID"].astype(str).str.zfill(11)

    # Compute centroids (already in EPSG:4326)
    gdf["centroid"] = gdf.geometry.centroid
    gdf["lat"] = gdf["centroid"].y
    gdf["lon"] = gdf["centroid"].x

    results = []
    total = len(gdf)

    print(f"Reverse geocoding {total} tracts (1 req/sec, ~{total//60+1} min)...")

    for i, row in gdf.iterrows():
        geoid = row["GEOID"]
        lat, lon = row["lat"], row["lon"]
        tract_num = geoid_to_tract_number(geoid)

        try:
            resp = requests.get(
                NOMINATIM_URL,
                params={"lat": lat, "lon": lon, "format": "json", "addressdetails": 1, "zoom": 14},
                headers=HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            name = best_name(data)
        except Exception as e:
            print(f"  [{i+1}/{total}] {geoid} — ERROR: {e}")
            name = ""

        display = f"{name} · {tract_num}" if name else tract_num

        results.append({
            "GEOID": geoid,
            "neighborhood": name,
            "display_name": display,
        })

        if (len(results)) % 25 == 0:
            print(f"  {len(results)}/{total} done...")

        time.sleep(1.1)  # Nominatim: max 1 req/sec

    out_df = pd.DataFrame(results)
    out_df.to_csv(OUT_CSV, index=False)

    filled = (out_df["neighborhood"] != "").sum()
    print(f"\nDone. {filled}/{total} tracts have neighborhood names.")
    print(f"Saved to {OUT_CSV}")
    print("\nSample:")
    print(out_df[out_df["neighborhood"] != ""].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
