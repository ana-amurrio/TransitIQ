# TransitIQ Processing Layer Handoff

Audience: dashboard/UI developer

Status: implemented and regenerated from the local cached data layer.

## What This Layer Produces

The processing layer converts `data/outputs/master_tract_data.csv` into dashboard-ready tract outputs for Columbus / Franklin County. It does not call live APIs. It reads cached CSVs from the data layer and writes local CSV/JSON artifacts.

Primary script:

```bash
python3 process_transit_iq.py
```

Run from:

```bash
Project/
```

Main dashboard input:

```text
data/outputs/processing_layer_results.csv
```

This file has one row per tract and is the best starting point for Streamlit maps, cost cards, timeline charts, and scenario comparison.

## Current Headline Results

Latest generated run:

- Tracts: 328
- Annual cost of inaction: $178,687,292.94
- 1-year delay cost: $184,098,385.03
- 3-year delay cost: $569,213,352.89
- 5-year delay cost: $978,083,430.61

Component totals:

| Component | Annual total |
| --- | ---: |
| Lost wages | $19,177,223.76 |
| Healthcare | $10,752,180.80 |
| Environment | $9,348,214.63 |
| Education | $8,886,358.97 |
| Forgone affordability | $130,523,314.78 |

Segment totals:

| Segment | Tracts | Population | Avg hardship | Annual cost | 5-year delay cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lower-risk, better-served | 48 | 202,751 | 39.14 | $3,510,954.75 | $18,917,927.60 |
| Moderate hardship | 173 | 760,811 | 48.85 | $25,139,504.43 | $137,288,374.03 |
| High-need transit burden | 107 | 369,486 | 57.49 | $150,036,833.76 | $821,877,128.98 |

## Output Files

Use these files for the dashboard:

- `data/outputs/processing_layer_results.csv`: all key tract-level fields for map, cards, and charts.
- `data/outputs/processing_layer_summary.csv`: pre-aggregated segment summary.
- `data/outputs/processing_layer_metadata.json`: assumptions, data quality notes, and output paths.
- `data/processed/cost_of_inaction_by_tract.csv`: detailed cost fields and year-by-year forecast.
- `data/processed/transit_dependency_weights.csv`: dependency weight internals.
- `data/processed/transit_hardship_index.csv`: hardship index internals.
- `data/processed/vulnerability_segments.csv`: segment labels by tract.

For map geometry, join dashboard results to:

```text
data/geospatial/franklin_tracts.geojson
```

Join key:

```text
GEOID
```

Keep `GEOID` as an 11-character string.

## Main Dashboard Columns

`processing_layer_results.csv` currently contains:

```text
GEOID
median_income
total_population
total_households
transit_score
is_transit_desert
transit_dependency_score
transit_dependency_weight
transit_hardship_index
vulnerability_segment
affected_workers_estimate
transit_dependent_population_estimate
forced_drive_commuters_estimate
ht_burdened_households_estimate
lost_wages_annual
healthcare_annual
environment_annual
education_annual
forgone_affordability_annual
cost_of_inaction_annual
cumulative_delay_1yr_cost
cumulative_delay_3yr_cost
cumulative_delay_5yr_cost
safety_warning_score
displacement_risk_score
```

Recommended dashboard mappings:

- Choropleth color: `transit_hardship_index`
- Segment label/color: `vulnerability_segment`
- Main KPI for delay selector:
  - 1 year: `cumulative_delay_1yr_cost`
  - 3 years: `cumulative_delay_3yr_cost`
  - 5 years: `cumulative_delay_5yr_cost`
- Cost breakdown chart:
  - `lost_wages_annual`
  - `healthcare_annual`
  - `environment_annual`
  - `education_annual`
  - `forgone_affordability_annual`
- Safety overlay: `safety_warning_score`
- Displacement overlay: `displacement_risk_score`

## Method Summary

### Transit Dependency Weight

The dependency score prioritizes residents who are less able to substitute car travel. It uses normalized components:

- No-vehicle households
- Disability population
- Elderly population, age 65+
- Single-parent households

The output includes both:

- `transit_dependency_score`: normalized 0-1 score
- `transit_dependency_weight`: multiplier used in cost components

### Transit Hardship Index

The hardship index is a 0-100 tract score combining:

- Transit dependency
- Income vulnerability
- Transit access gap
- Commute burden
- Rent burden
- Job need

Use this as the primary map color scale.

### Vulnerability Segments

The layer creates three explainable K-means-style segments:

- `Lower-risk, better-served`
- `Moderate hardship`
- `High-need transit burden`

These are useful for the Equity tab and map legends.

### Cost Components

The annual cost engine includes five components:

1. Lost wages
2. Healthcare burden
3. Environmental cost
4. Education access
5. Forgone affordability

The cumulative delay columns apply per-component forecasting rates:

- Wages: wage inflation rate
- Healthcare: healthcare growth rate
- Education: population growth rate
- Environment: blended growth rate
- Affordability: blended growth rate

## Important Math Fixes

The cost engine now avoids known overlap inflation:

- `transit_commuters` and `workers_no_vehicle` are not added together. The wage component uses `max(transit_commuters, workers_no_vehicle)`.
- Healthcare uses `max(no_vehicle_household_population, transit_commuters)` rather than adding both groups.
- Environmental VMT does not assume every non-transit commuter is a forced car trip. It is capped by an affected-commuter estimate.
- Forgone affordability does not apply H+T excess costs to every household in a tract. It uses `ht_burdened_households_estimate`.

The dashboard should display the outputs as modeled estimates, not audited budget actuals.

## Assumptions To Surface In UI

Current defaults:

- Missed-care rate: 5%
- Cost per missed care episode: $1,200
- Average commute distance proxy: 7.5 miles
- EPA social cost of carbon: $190 per metric ton CO2
- EPA CO2 per mile: 0.000404 metric tons
- Benchmark commute: 25 minutes

The UI should expose at least:

- Delay years: 1 / 3 / 5
- Missed-care rate
- Cost per missed care episode
- Growth rate or scenario preset
- Investment amount
- Target tracts

## Suggested Dashboard Build Order

1. Load `processing_layer_results.csv`.
2. Load `franklin_tracts.geojson`.
3. Join on `GEOID`.
4. Build the map tab:
   - color by `transit_hardship_index`
   - tooltip with segment, population, hardship, annual cost, 5-year cost
   - overlays for `safety_warning_score` and `displacement_risk_score`
5. Build Cost of Inaction tab:
   - headline KPI from selected delay column
   - stacked bar for the five annual components
   - timeline from `cost_of_inaction_by_tract.csv`
6. Build Equity tab:
   - group by `vulnerability_segment`
   - use `processing_layer_summary.csv`
7. Build Scenario Compare:
   - compare invest-now amount against selected delay cost
   - show avoided cost and displacement warning

## Caveats

- The processing layer is built for hackathon/demo decision support.
- Some formulas use proxy estimates because the data layer does not contain every cross-tab needed to observe overlap exactly.
- `transit_dependency_weight` intentionally scales affected-population terms, so it is a model weighting decision rather than a literal person count.
- Costs are directional estimates intended to help planners compare delay scenarios and identify high-need tracts.

## Quick QA Checks

After running `python3 process_transit_iq.py`, verify:

```bash
python3 -m py_compile process_transit_iq.py config.py
```

Expected output files should have 328 rows for tract-level CSVs and zero nulls in dashboard-critical fields.
