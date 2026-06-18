
# TransitIQ Configuration
# All constants and file paths for the project

# --- EPA Constants ---
EPA_SOCIAL_COST_CARBON = 190        # USD per metric ton CO2 (2023 EPA figure)
EPA_CO2_PER_MILE = 0.000404         # Metric tons CO2 per vehicle mile (EPA)

# --- BLS Wage Constants (Columbus MSA 2024) ---
COLUMBUS_MEDIAN_HOURLY_WAGE = 23.31   # USD/hour (BLS OEWS 2024)
COLUMBUS_MEDIAN_ANNUAL_WAGE = 48490   # USD/year (BLS OEWS 2024)
USDOT_TRAVEL_TIME_FACTOR = 0.50       # USDOT: personal travel valued at 50% of wage
ANNUAL_WORK_DAYS = 260                # Working days per year
ANNUAL_WORK_HOURS = 2080              # Work hours per year

# --- Benchmark Commute Time ---
BENCHMARK_COMMUTE_MIN = 25            # USDOT reasonable commute benchmark (minutes)

# --- Healthcare Constants ---
MISSED_CARE_RATE_BASE = 0.05          # 5% baseline missed care rate (Urban Institute)
MISSED_CARE_RATE_NO_VEHICLE = 0.20    # 20% for zero-vehicle households
COST_PER_MISSED_EPISODE = 1200        # USD per missed care episode (default)

# --- Affordability Threshold ---
HT_AFFORDABILITY_THRESHOLD = 0.45    # 45% of income = unaffordable (H+T standard)
HOUSING_AFFORDABILITY_THRESHOLD = 0.30

# --- Compounding Growth Rates ---
POPULATION_GROWTH_RATE = 0.012        # 1.2% annual (Columbus Census trend)
WAGE_INFLATION_RATE = 0.035           # 3.5% annual (BLS CPI trend)
COMBINED_GROWTH_RATE = 0.025          # Blended growth rate for compounding
AVERAGE_COMMUTE_DISTANCE_MILES = 7.5  # Local commute distance proxy for VMT estimate

# --- File Paths ---
ACS_TRACTS = "data/processed/acs_tracts.csv"
FRANKLIN_GEOJSON = "data/geospatial/franklin_tracts.geojson"
COTA_STOPS_GEOJSON = "data/geospatial/cota_stops.geojson"
TRANSIT_ACCESS = "data/transit/transit_access_per_tract.csv"
FARS_CRASHES = "data/processed/fars_crashes_per_tract.csv"
LODES_JOBS = "data/processed/lodes_tract_jobs.csv"
BLS_WAGES = "data/processed/bls_wages_columbus.csv"
HT_INDEX = "data/processed/ht_index_tracts.csv"
MASTER_DATA = "data/outputs/master_tract_data.csv"
TRANSIT_DEPENDENCY_WEIGHTS = "data/processed/transit_dependency_weights.csv"
TRANSIT_HARDSHIP_INDEX = "data/processed/transit_hardship_index.csv"
VULNERABILITY_SEGMENTS = "data/processed/vulnerability_segments.csv"
COST_OF_INACTION = "data/processed/cost_of_inaction_by_tract.csv"
PROCESSING_LAYER_RESULTS = "data/outputs/processing_layer_results.csv"
PROCESSING_LAYER_SUMMARY = "data/outputs/processing_layer_summary.csv"
PROCESSING_LAYER_METADATA = "data/outputs/processing_layer_metadata.json"

# --- Data Vintage (for documentation) ---
ACS_VINTAGE = "2019-2023 ACS 5-Year"
LODES_VINTAGE = "LEHD LODES 2021"
FARS_VINTAGE = "NHTSA FARS 2023"
BLS_VINTAGE = "BLS OEWS 2024"
GTFS_VINTAGE = "COTA GTFS 2025"
