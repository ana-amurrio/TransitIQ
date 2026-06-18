import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import urllib.request
import zipfile
import os

os.makedirs('data/raw', exist_ok=True)
os.makedirs('data/processed', exist_ok=True)

# --- Download FARS 2023 ---
print("Downloading NHTSA FARS 2023 national data...")
url = "https://static.nhtsa.gov/nhtsa/downloads/FARS/2023/National/FARS2023NationalCSV.zip"
urllib.request.urlretrieve(url, "data/raw/FARS2023NationalCSV.zip")
print("Download complete. Extracting...")

# --- Extract accident.csv only ---
with zipfile.ZipFile("data/raw/FARS2023NationalCSV.zip", 'r') as z:
    z.extract('FARS2023NationalCSV/accident.csv', 'data/raw/')
print("Extracted accident.CSV")

# --- Load and filter to Ohio / Franklin County ---
df = pd.read_csv('data/raw/FARS2023NationalCSV/accident.csv', encoding='latin-1')
print(f"Total US fatal crashes: {len(df)}")

ohio = df[df['STATE'] == 39].copy()
print(f"Ohio fatal crashes: {len(ohio)}")

franklin = ohio[ohio['COUNTY'] == 49].copy()
print(f"Franklin County fatal crashes: {len(franklin)}")

# --- Clean coordinates ---
franklin = franklin[
    (franklin['LATITUDE'] < 90) &
    (franklin['LONGITUD'] < 0) &
    (franklin['LATITUDE'].notna()) &
    (franklin['LONGITUD'].notna())
].copy()
print(f"Franklin crashes with valid coordinates: {len(franklin)}")

# --- Keep only needed columns ---
franklin = franklin