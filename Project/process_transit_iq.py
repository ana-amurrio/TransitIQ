"""
Processing layer for TransitIQ.

Builds tract-level dependency, hardship, vulnerability segment, and cost-of-
inaction outputs from the cached data-layer master file. The script is designed
for demos: it reads only local files and writes reproducible CSV/JSON artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import config
except ImportError:  # pragma: no cover - helpful when called from repo root
    from Project import config


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "outputs"

MASTER_PATH = PROJECT_DIR / config.MASTER_DATA

OUTPUTS = {
    "dependency": PROCESSED_DIR / "transit_dependency_weights.csv",
    "hardship": PROCESSED_DIR / "transit_hardship_index.csv",
    "segments": PROCESSED_DIR / "vulnerability_segments.csv",
    "costs": PROCESSED_DIR / "cost_of_inaction_by_tract.csv",
    "results": OUTPUT_DIR / "processing_layer_results.csv",
    "summary": OUTPUT_DIR / "processing_layer_summary.csv",
    "metadata": OUTPUT_DIR / "processing_layer_metadata.json",
}

COMMUTE_BIN_MIDPOINTS = {
    "commute_30_34min": 32,
    "commute_35_39min": 37,
    "commute_40_44min": 42,
    "commute_45_59min": 52,
    "commute_60_89min": 75,
    "commute_90plus_min": 100,
}

SEGMENT_NAMES = {
    0: "Lower-risk, better-served",
    1: "Moderate hardship",
    2: "High-need transit burden",
}


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    return (numerator / denominator).replace([np.inf, -np.inf], np.nan).fillna(0)


def _minmax(series: pd.Series, invert: bool = False) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    values = values.fillna(values.median() if values.notna().any() else 0)
    min_value = values.min()
    max_value = values.max()

    if pd.isna(min_value) or pd.isna(max_value) or max_value == min_value:
        scaled = pd.Series(0.0, index=values.index)
    else:
        scaled = (values - min_value) / (max_value - min_value)

    return 1 - scaled if invert else scaled


def _weighted_index(df: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    total_weight = sum(weights.values())
    if total_weight == 0:
        return pd.Series(0.0, index=df.index)

    score = pd.Series(0.0, index=df.index)
    for column, weight in weights.items():
        score += df[column] * weight
    return score / total_weight


def _standardize(frame: pd.DataFrame) -> pd.DataFrame:
    clean = frame.replace([np.inf, -np.inf], np.nan)
    clean = clean.fillna(clean.median(numeric_only=True)).fillna(0)
    std = clean.std(ddof=0).replace(0, 1)
    return (clean - clean.mean()) / std


def _row_max(*series: pd.Series) -> pd.Series:
    return pd.concat(series, axis=1).max(axis=1)


def _deterministic_kmeans(features: pd.DataFrame, k: int = 3, max_iter: int = 100) -> np.ndarray:
    """K-means clustering using scikit-learn with k-means++ initialization."""
    from sklearn.cluster import KMeans

    matrix = _standardize(features).to_numpy(dtype=float)
    if len(matrix) == 0:
        return np.array([], dtype=int)

    k = min(k, len(matrix))
    km = KMeans(n_clusters=k, init="k-means++", n_init=10, max_iter=max_iter, random_state=42)
    return km.fit_predict(matrix)


def load_master(path: Path = MASTER_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing master data at {path}. Run Project/create_master.py first."
        )

    df = pd.read_csv(path)
    df["GEOID"] = df["GEOID"].astype(str).str.zfill(11)
    return df


def add_base_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in [
        "median_income",
        "total_population",
        "total_households",
        "workers_16plus",
        "commute_mode_total",
        "total_commuters",
    ]:
        fallback = result[column].median() if result[column].notna().any() else 0
        result[column] = result[column].fillna(fallback)

    result["household_size_estimate"] = _safe_divide(
        result["total_population"], result["total_households"]
    ).clip(lower=1, upper=6)
    result["no_vehicle_household_rate"] = _safe_divide(
        result["households_no_vehicle"], result["total_households"]
    ).clip(0, 1)
    result["no_vehicle_worker_rate"] = _safe_divide(
        result["workers_no_vehicle"], result["workers_16plus"]
    ).clip(0, 1)
    result["transit_commuter_rate"] = _safe_divide(
        result["transit_commuters"], result["commute_mode_total"]
    ).clip(0, 1)
    result["rent_burden_rate"] = _safe_divide(
        result["rent_burden_35_39pct"]
        + result["rent_burden_40_49pct"]
        + result["rent_burden_50plus_pct"],
        result["total_households"],
    ).clip(0, 1)
    result["rent_burdened_households_estimate"] = (
        result["rent_burden_35_39pct"]
        + result["rent_burden_40_49pct"]
        + result["rent_burden_50plus_pct"]
    ).clip(lower=0, upper=result["total_households"])
    result["severe_rent_burden_rate"] = _safe_divide(
        result["rent_burden_50plus_pct"], result["total_households"]
    ).clip(0, 1)

    long_commute_count = sum(result[col] for col in COMMUTE_BIN_MIDPOINTS)
    result["long_commute_share"] = _safe_divide(
        long_commute_count, result["total_commuters"]
    ).clip(0, 1)
    result["estimated_long_commute_minutes"] = _safe_divide(
        sum(result[col] * midpoint for col, midpoint in COMMUTE_BIN_MIDPOINTS.items()),
        long_commute_count,
    )
    result["estimated_mean_commute_min"] = (
        result["estimated_long_commute_minutes"] * result["long_commute_share"]
        + config.BENCHMARK_COMMUTE_MIN * (1 - result["long_commute_share"])
    )
    result["excess_commute_minutes"] = (
        result["estimated_mean_commute_min"] - config.BENCHMARK_COMMUTE_MIN
    ).clip(lower=0)

    result["income_vulnerability_score"] = _minmax(result["median_income"], invert=True)
    result["transit_access_gap_score"] = _minmax(result["transit_score"], invert=True)
    result["commute_burden_score"] = _minmax(result["excess_commute_minutes"])
    result["rent_burden_score"] = _minmax(result["rent_burden_rate"])
    result["job_need_score"] = _minmax(result["total_jobs"])

    return result


def add_transit_dependency(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    result = df.copy()
    notes: list[str] = []

    result["no_vehicle_dependency_component"] = _minmax(
        result["no_vehicle_household_rate"]
    )

    # Use disability_actual (B18101 with-disability cells) if available; fall back
    # to the universe total with a median guard that catches the old bad data.
    if "disability_actual" in result.columns:
        disability_rate = _safe_divide(result["disability_actual"], result["total_population"])
        notes.append("Using disability_actual (B18101 with-disability cells) for dependency weight.")
    else:
        disability_rate = _safe_divide(result["disability_pop"], result["total_population"])

    if disability_rate.median() > 0.80:
        notes.append(
            "ACS disability field appears to be the B18101 universe total, "
            "not disabled population; disability component set to zero."
        )
        result["disability_dependency_component"] = 0.0
    else:
        result["disability_dependency_component"] = _minmax(disability_rate.clip(0, 1))

    if "elderly_65plus" in result.columns:
        elderly_rate = _safe_divide(result["elderly_65plus"], result["total_population"])
        result["elderly_dependency_component"] = _minmax(elderly_rate.clip(0, 1))
        notes.append("Elderly population (B01001, 65+) included in dependency weight.")
    else:
        result["elderly_dependency_component"] = 0.0
        notes.append("Elderly population field not present; elderly component set to zero.")

    if "single_parent_hh" in result.columns:
        single_parent_rate = _safe_divide(result["single_parent_hh"], result["total_households"])
        result["single_parent_dependency_component"] = _minmax(single_parent_rate.clip(0, 1))
        notes.append("Single-parent households (B11003) included in dependency weight.")
    else:
        result["single_parent_dependency_component"] = 0.0
        notes.append("Single-parent household field not present; component set to zero.")

    weights = {
        "no_vehicle_dependency_component": 0.50,
        "disability_dependency_component": 0.25,
        "elderly_dependency_component": 0.15,
        "single_parent_dependency_component": 0.10,
    }
    result["transit_dependency_score"] = _weighted_index(result, weights).clip(0, 1)
    result["transit_dependency_weight"] = (1 + result["transit_dependency_score"]).round(4)

    return result, notes


def add_hardship_index(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    weights = {
        "transit_dependency_score": 0.30,
        "income_vulnerability_score": 0.20,
        "transit_access_gap_score": 0.20,
        "commute_burden_score": 0.15,
        "rent_burden_score": 0.10,
        "job_need_score": 0.05,
    }
    result["transit_hardship_index"] = (_weighted_index(result, weights) * 100).round(2)
    return result


def add_segments(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    features = result[
        [
            "transit_hardship_index",
            "income_vulnerability_score",
            "no_vehicle_household_rate",
            "transit_access_gap_score",
            "commute_burden_score",
            "rent_burden_rate",
        ]
    ]
    raw_labels = _deterministic_kmeans(features, k=3)
    result["_cluster_raw"] = raw_labels

    cluster_order = (
        result.groupby("_cluster_raw")["transit_hardship_index"]
        .mean()
        .sort_values()
        .index.tolist()
    )
    remap = {raw: rank for rank, raw in enumerate(cluster_order)}
    result["vulnerability_segment_id"] = result["_cluster_raw"].map(remap).astype(int)
    result["vulnerability_segment"] = result["vulnerability_segment_id"].map(SEGMENT_NAMES)
    return result.drop(columns=["_cluster_raw"])


ATTENDANCE_LOSS_FACTOR = 0.03        # 3% attendance loss in transit deserts (Chetty proxy)
LIFETIME_EARNINGS_DISCOUNT = 14_000  # Discounted lifetime earnings impact per child (PV)
K12_YEARS = 13                       # K-12 school years; converts PV to annual cohort cost


def add_education_component(df: pd.DataFrame) -> pd.DataFrame:
    """
    Education access cost (3.4): transit deserts suppress attendance, which
    depresses lifetime earnings. Method from Chetty / Minneapolis Student Pass.

    Annual framing: each year of inaction permanently affects one new entering
    cohort (school_age_pop / K12_YEARS). The lifetime earnings hit per cohort
    child is ATTENDANCE_LOSS_FACTOR × LIFETIME_EARNINGS_DISCOUNT.
    Only tracts with transit_access_gap_score > 0.5 are treated as meaningfully
    access-deficient for the education pathway.
    """
    result = df.copy()

    if "school_age_pop_5_17" in result.columns:
        # Annual cohort = children newly entering the pipeline each year
        annual_cohort = result["school_age_pop_5_17"] / K12_YEARS
        # Apply only where transit access is genuinely deficient (gap > 0.5)
        access_deficient = (result["transit_access_gap_score"] > 0.5).astype(float)
        school_age_affected = annual_cohort * access_deficient
    else:
        school_age_affected = pd.Series(0.0, index=result.index)

    result["education_annual"] = (
        school_age_affected
        * ATTENDANCE_LOSS_FACTOR
        * LIFETIME_EARNINGS_DISCOUNT
        * result["transit_dependency_weight"]
    ).round(2)

    return result


def add_cost_engine(
    df: pd.DataFrame,
    missed_care_rate: float,
    cost_per_missed_episode: float,
    growth_rate: float,
    average_commute_distance_miles: float,
) -> pd.DataFrame:
    result = df.copy()

    hourly_wage = result["hourly_wage_estimate"].fillna(
        config.COLUMBUS_MEDIAN_HOURLY_WAGE
    )
    transit_commuters = result["transit_commuters"].fillna(0)
    workers_no_vehicle = result["workers_no_vehicle"].fillna(0)
    result["affected_workers_estimate"] = _row_max(
        transit_commuters, workers_no_vehicle
    ).clip(upper=result["commute_mode_total"])
    result["affected_workers_weighted"] = (
        result["affected_workers_estimate"] * result["transit_dependency_weight"]
    )
    result["annual_excess_commute_hours"] = (
        result["excess_commute_minutes"] / 60 * 2 * config.ANNUAL_WORK_DAYS
    )
    result["lost_wages_annual"] = (
        result["annual_excess_commute_hours"]
        * hourly_wage
        * config.USDOT_TRAVEL_TIME_FACTOR
        * result["affected_workers_weighted"]
    ).round(2)

    people_without_vehicle = (
        result["households_no_vehicle"].fillna(0) * result["household_size_estimate"]
    )
    result["transit_dependent_population_estimate"] = (
        _row_max(people_without_vehicle, transit_commuters)
        .clip(upper=result["total_population"])
    ).clip(upper=result["total_population"])
    adjusted_missed_care_rate = (
        missed_care_rate
        + (config.MISSED_CARE_RATE_NO_VEHICLE - missed_care_rate)
        * result["no_vehicle_household_rate"]
    ).clip(0, config.MISSED_CARE_RATE_NO_VEHICLE)
    result["healthcare_annual"] = (
        result["transit_dependent_population_estimate"]
        * adjusted_missed_care_rate
        * cost_per_missed_episode
        * result["transit_dependency_weight"]
    ).round(2)

    non_transit_commuters = (
        result["commute_mode_total"].fillna(0) - result["transit_commuters"].fillna(0)
    ).clip(lower=0)
    result["forced_drive_commuters_estimate"] = (
        pd.concat(
            [
                non_transit_commuters,
                result["affected_workers_estimate"] * result["transit_access_gap_score"],
            ],
            axis=1,
        )
        .min(axis=1)
        .round(2)
    )
    access_penalty = 1 + result["transit_access_gap_score"] * 0.25
    result["excess_car_vmt_annual"] = (
        result["forced_drive_commuters_estimate"]
        * average_commute_distance_miles
        * 2
        * config.ANNUAL_WORK_DAYS
        * access_penalty
    )
    result["environment_annual"] = (
        result["excess_car_vmt_annual"]
        * config.EPA_CO2_PER_MILE
        * config.EPA_SOCIAL_COST_CARBON
    ).round(2)

    excess_ht_ratio = (
        result["ht_combined_ratio"].fillna(config.HT_AFFORDABILITY_THRESHOLD)
        - config.HT_AFFORDABILITY_THRESHOLD
    ).clip(lower=0)
    result["ht_burdened_households_estimate"] = _row_max(
        result["rent_burdened_households_estimate"].fillna(0),
        result["households_no_vehicle"].fillna(0),
    ).clip(upper=result["total_households"])
    result["forgone_affordability_annual"] = (
        result["ht_burdened_households_estimate"]
        * result["median_income"].fillna(result["median_income"].median())
        * excess_ht_ratio
        * result["transit_dependency_weight"]
    ).round(2)

    result["cost_of_inaction_annual"] = (
        result["lost_wages_annual"]
        + result["healthcare_annual"]
        + result["environment_annual"]
        + result["education_annual"]
        + result["forgone_affordability_annual"]
    ).round(2)

    # Per-component growth rates for time-series forecast (linear trend)
    component_rates = {
        "lost_wages_annual": config.WAGE_INFLATION_RATE,
        "healthcare_annual": 0.045,        # Healthcare inflation ~4.5%/yr
        "environment_annual": growth_rate,
        "education_annual": config.POPULATION_GROWTH_RATE,
        "forgone_affordability_annual": 0.03,
    }

    for year in range(1, 6):
        yearly_total = pd.Series(0.0, index=result.index)
        for component, rate in component_rates.items():
            yearly_total += result[component] * (1 + rate) ** year
        result[f"annual_cost_year_{year}"] = yearly_total.round(2)

    for delay_years in (1, 3, 5):
        columns = [f"annual_cost_year_{year}" for year in range(1, delay_years + 1)]
        result[f"cumulative_delay_{delay_years}yr_cost"] = result[columns].sum(axis=1).round(2)

    result["safety_warning_score"] = (
        _minmax(result["crash_count"]) * result["transit_dependency_score"] * 100
    ).round(2)
    result["displacement_risk_score"] = (
        (
            0.50 * result["rent_burden_score"]
            + 0.30 * result["income_vulnerability_score"]
            + 0.20 * result["transit_hardship_index"] / 100
        )
        * 100
    ).round(2)

    return result


def write_outputs(df: pd.DataFrame, metadata: dict) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dependency_columns = [
        "GEOID",
        "no_vehicle_dependency_component",
        "disability_dependency_component",
        "elderly_dependency_component",
        "single_parent_dependency_component",
        "transit_dependency_score",
        "transit_dependency_weight",
    ]
    hardship_columns = [
        "GEOID",
        "estimated_mean_commute_min",
        "excess_commute_minutes",
        "income_vulnerability_score",
        "transit_access_gap_score",
        "commute_burden_score",
        "rent_burden_score",
        "transit_hardship_index",
    ]
    segment_columns = [
        "GEOID",
        "vulnerability_segment_id",
        "vulnerability_segment",
        "transit_hardship_index",
    ]
    cost_columns = [
        "GEOID",
        "affected_workers_estimate",
        "lost_wages_annual",
        "transit_dependent_population_estimate",
        "healthcare_annual",
        "forced_drive_commuters_estimate",
        "environment_annual",
        "education_annual",
        "ht_burdened_households_estimate",
        "forgone_affordability_annual",
        "cost_of_inaction_annual",
        "annual_cost_year_1",
        "annual_cost_year_2",
        "annual_cost_year_3",
        "annual_cost_year_4",
        "annual_cost_year_5",
        "cumulative_delay_1yr_cost",
        "cumulative_delay_3yr_cost",
        "cumulative_delay_5yr_cost",
        "safety_warning_score",
        "displacement_risk_score",
    ]
    result_columns = [
        "GEOID",
        "median_income",
        "total_population",
        "total_households",
        "transit_score",
        "is_transit_desert",
        "transit_dependency_score",
        "transit_dependency_weight",
        "transit_hardship_index",
        "vulnerability_segment",
        "affected_workers_estimate",
        "transit_dependent_population_estimate",
        "forced_drive_commuters_estimate",
        "ht_burdened_households_estimate",
        "lost_wages_annual",
        "healthcare_annual",
        "environment_annual",
        "education_annual",
        "forgone_affordability_annual",
        "cost_of_inaction_annual",
        "cumulative_delay_1yr_cost",
        "cumulative_delay_3yr_cost",
        "cumulative_delay_5yr_cost",
        "safety_warning_score",
        "displacement_risk_score",
    ]

    df[dependency_columns].to_csv(OUTPUTS["dependency"], index=False)
    df[hardship_columns].to_csv(OUTPUTS["hardship"], index=False)
    df[segment_columns].to_csv(OUTPUTS["segments"], index=False)
    df[cost_columns].to_csv(OUTPUTS["costs"], index=False)
    df[result_columns].to_csv(OUTPUTS["results"], index=False)

    summary = (
        df.groupby("vulnerability_segment", as_index=False)
        .agg(
            tracts=("GEOID", "count"),
            population=("total_population", "sum"),
            avg_hardship=("transit_hardship_index", "mean"),
            annual_cost=("cost_of_inaction_annual", "sum"),
            delay_3yr_cost=("cumulative_delay_3yr_cost", "sum"),
            delay_5yr_cost=("cumulative_delay_5yr_cost", "sum"),
        )
        .sort_values("avg_hardship")
    )
    summary[["avg_hardship", "annual_cost", "delay_3yr_cost", "delay_5yr_cost"]] = summary[
        ["avg_hardship", "annual_cost", "delay_3yr_cost", "delay_5yr_cost"]
    ].round(2)
    summary.to_csv(OUTPUTS["summary"], index=False)

    with OUTPUTS["metadata"].open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def build_processing_layer(args: argparse.Namespace) -> pd.DataFrame:
    df = load_master(args.master)
    df = add_base_features(df)
    df, dependency_notes = add_transit_dependency(df)
    df = add_hardship_index(df)
    df = add_segments(df)
    df = add_education_component(df)
    df = add_cost_engine(
        df,
        missed_care_rate=args.missed_care_rate,
        cost_per_missed_episode=args.cost_per_missed_episode,
        growth_rate=args.growth_rate,
        average_commute_distance_miles=args.average_commute_distance_miles,
    )

    metadata = {
        "source_master": str(args.master),
        "tract_count": int(len(df)),
        "assumptions": {
            "missed_care_rate": args.missed_care_rate,
            "cost_per_missed_episode": args.cost_per_missed_episode,
            "growth_rate": args.growth_rate,
            "average_commute_distance_miles": args.average_commute_distance_miles,
            "components": [
                "lost_wages",
                "healthcare",
                "environment",
                "education",
                "forgone_affordability",
            ],
            "forecasting": (
                "Per-component linear trend with differentiated rates: "
                "wages use BLS wage inflation, healthcare uses 4.5%/yr, "
                "education uses Census population growth, environment and "
                "affordability use the blended growth rate."
            ),
            "overlap_adjustment": (
                "Potentially overlapping ACS groups use conservative max/min proxies "
                "instead of additive counts. Affected workers use max(transit "
                "commuters, workers without vehicles). Healthcare population uses "
                "max(no-vehicle household population, transit commuters). Forced "
                "drive commuters are capped by non-transit commuters and scaled to "
                "the affected-worker estimate. H+T affordability burden uses a "
                "household-count proxy instead of applying tract-level excess cost "
                "to every household."
            ),
        },
        "data_quality_notes": dependency_notes,
        "outputs": {name: str(path) for name, path in OUTPUTS.items()},
    }
    write_outputs(df, metadata)
    return df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build TransitIQ processing-layer outputs.")
    parser.add_argument("--master", type=Path, default=MASTER_PATH)
    parser.add_argument("--missed-care-rate", type=float, default=config.MISSED_CARE_RATE_BASE)
    parser.add_argument(
        "--cost-per-missed-episode",
        type=float,
        default=config.COST_PER_MISSED_EPISODE,
    )
    parser.add_argument("--growth-rate", type=float, default=config.COMBINED_GROWTH_RATE)
    parser.add_argument(
        "--average-commute-distance-miles",
        type=float,
        default=getattr(config, "AVERAGE_COMMUTE_DISTANCE_MILES", 7.5),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = build_processing_layer(args)
    total_annual = df["cost_of_inaction_annual"].sum()
    total_5yr = df["cumulative_delay_5yr_cost"].sum()

    print("TransitIQ processing layer complete")
    print(f"Tracts processed: {len(df):,}")
    print(f"Annual cost of inaction: ${total_annual:,.0f}")
    print(f"Cumulative 5-year delay cost: ${total_5yr:,.0f}")
    print(f"Main output: {OUTPUTS['results']}")


if __name__ == "__main__":
    main()
