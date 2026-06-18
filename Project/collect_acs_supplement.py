"""
Supplemental ACS pull for TransitIQ processing layer.

Fetches ACS fields that were missing from the initial collect_acs.py run:
  - Actual disabled population (B18101 "with disability" cells, not the universe)
  - Elderly population 65+ (B01001 age bands)
  - Single-parent households (B11003)
  - School-age population 5-17 (B01001 age bands, for education cost component)

Merges results into acs_tracts.csv and master_tract_data.csv in place.
Run once; output is cached.  Re-run only if source data needs refresh.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from census import Census

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_KEY = "f3e335b1add470c10bfd90b58a01c40a5211df77"
STATE   = "39"
COUNTY  = "049"

PROJECT_DIR = Path(__file__).resolve().parent
PROCESSED   = PROJECT_DIR / "data" / "processed"
OUTPUTS     = PROJECT_DIR / "data" / "outputs"

ACS_PATH    = PROCESSED / "acs_tracts.csv"
MASTER_PATH = OUTPUTS   / "master_tract_data.csv"

# ---------------------------------------------------------------------------
# ACS fields to pull
# ---------------------------------------------------------------------------
# B18101 — Sex by Age by Disability Status
# Each "with disability" cell is at position 3n+1 within each sex group.
# Male group offset starts at B18101_003E; Female at B18101_022E.
DISABILITY_FIELDS = (
    "B18101_004E",  # Male, Under 5, with disability
    "B18101_007E",  # Male, 5-17, with disability
    "B18101_010E",  # Male, 18-34, with disability
    "B18101_013E",  # Male, 35-64, with disability
    "B18101_016E",  # Male, 65-74, with disability
    "B18101_019E",  # Male, 75+, with disability
    "B18101_023E",  # Female, Under 5, with disability
    "B18101_026E",  # Female, 5-17, with disability
    "B18101_029E",  # Female, 18-34, with disability
    "B18101_032E",  # Female, 35-64, with disability
    "B18101_035E",  # Female, 65-74, with disability
    "B18101_038E",  # Female, 75+, with disability
)

# B01001 — Sex by Age (used for elderly 65+ and school-age 5-17)
# Male age bands: _003=U5, _004=5-9, _005=10-14, _006=15-17, ..., _020=65-66,
#                 _021=67-69, _022=70-74, _023=75-79, _024=80-84, _025=85+
# Female bands start 24 later: _027=U5, _028=5-9, _029=10-14, _030=15-17, ...,
#                                _044=65-66, _045=67-69, _046=70-74, _047=75-79,
#                                _048=80-84, _049=85+
AGE_FIELDS = (
    # School-age 5-17 (male)
    "B01001_004E",  # Male 5-9
    "B01001_005E",  # Male 10-14
    "B01001_006E",  # Male 15-17
    # School-age 5-17 (female)
    "B01001_028E",  # Female 5-9
    "B01001_029E",  # Female 10-14
    "B01001_030E",  # Female 15-17
    # Elderly 65+ (male)
    "B01001_020E",  # Male 65-66
    "B01001_021E",  # Male 67-69
    "B01001_022E",  # Male 70-74
    "B01001_023E",  # Male 75-79
    "B01001_024E",  # Male 80-84
    "B01001_025E",  # Male 85+
    # Elderly 65+ (female)
    "B01001_044E",  # Female 65-66
    "B01001_045E",  # Female 67-69
    "B01001_046E",  # Female 70-74
    "B01001_047E",  # Female 75-79
    "B01001_048E",  # Female 80-84
    "B01001_049E",  # Female 85+
)

# B11003 — Family Type by Presence and Age of Own Children Under 18
# B11003_010E: Male householder, no wife, with own children < 18
# B11003_016E: Female householder, no husband, with own children < 18
FAMILY_FIELDS = (
    "B11003_010E",
    "B11003_016E",
)

ALL_FIELDS = ("NAME",) + DISABILITY_FIELDS + AGE_FIELDS + FAMILY_FIELDS

# ---------------------------------------------------------------------------
# Census null sentinels
# ---------------------------------------------------------------------------
NULL_VALS = {-666666666, -999999999, -888888888, -222222222, -333333333}


def fetch_supplement() -> pd.DataFrame:
    print("Connecting to Census API …")
    c = Census(API_KEY)

    print(f"Pulling {len(ALL_FIELDS)-1} supplemental ACS fields for Franklin County tracts …")
    raw = c.acs5.state_county_tract(
        fields=ALL_FIELDS,
        state_fips=STATE,
        county_fips=COUNTY,
        tract="*",
    )
    print(f"  Retrieved {len(raw)} tracts")

    df = pd.DataFrame(raw)
    df["GEOID"] = df["state"] + df["county"] + df["tract"]
    df = df.drop(columns=["state", "county", "tract", "NAME"])

    for col in df.columns:
        if col != "GEOID":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for null_val in NULL_VALS:
        df.replace(null_val, float("nan"), inplace=True)

    # -- Roll-ups --
    df["disability_actual"] = df[list(DISABILITY_FIELDS)].clip(lower=0).sum(axis=1)

    school_age_male   = ["B01001_004E", "B01001_005E", "B01001_006E"]
    school_age_female = ["B01001_028E", "B01001_029E", "B01001_030E"]
    df["school_age_pop_5_17"] = (
        df[school_age_male + school_age_female].clip(lower=0).sum(axis=1)
    )

    elderly_male   = ["B01001_020E","B01001_021E","B01001_022E",
                      "B01001_023E","B01001_024E","B01001_025E"]
    elderly_female = ["B01001_044E","B01001_045E","B01001_046E",
                      "B01001_047E","B01001_048E","B01001_049E"]
    df["elderly_65plus"] = (
        df[elderly_male + elderly_female].clip(lower=0).sum(axis=1)
    )

    df["single_parent_hh"] = (
        df[["B11003_010E", "B11003_016E"]].clip(lower=0).sum(axis=1)
    )

    # Keep only derived columns + GEOID
    keep = ["GEOID", "disability_actual", "school_age_pop_5_17",
            "elderly_65plus", "single_parent_hh"]
    return df[keep]


def patch_csv(path: Path, supplement: pd.DataFrame, label: str) -> None:
    if not path.exists():
        print(f"  SKIP: {path} not found")
        return

    base = pd.read_csv(path)
    base["GEOID"] = base["GEOID"].astype(str).str.zfill(11)
    supplement["GEOID"] = supplement["GEOID"].astype(str).str.zfill(11)

    # Drop columns that will be replaced
    for col in ["disability_actual", "school_age_pop_5_17", "elderly_65plus", "single_parent_hh"]:
        if col in base.columns:
            base = base.drop(columns=[col])

    merged = base.merge(supplement, on="GEOID", how="left")
    merged.to_csv(path, index=False)
    print(f"  Patched {label}: {len(merged)} rows, {len(merged.columns)} columns")
    nulls = merged[["disability_actual","elderly_65plus","single_parent_hh"]].isnull().sum()
    if nulls.any():
        print(f"  Null counts: {nulls[nulls>0].to_dict()}")
    else:
        print("  No nulls in new columns.")


def main() -> None:
    supplement = fetch_supplement()

    print("\nSummary of new columns:")
    print(supplement[["disability_actual","elderly_65plus","single_parent_hh","school_age_pop_5_17"]].describe().round(1))

    print(f"\nPatching {ACS_PATH} …")
    patch_csv(ACS_PATH, supplement, "acs_tracts.csv")

    print(f"\nPatching {MASTER_PATH} …")
    patch_csv(MASTER_PATH, supplement, "master_tract_data.csv")

    print("\nDone. Re-run create_master.py if you want a fresh full merge, "
          "or run process_transit_iq.py directly — both now have the new columns.")


if __name__ == "__main__":
    main()
