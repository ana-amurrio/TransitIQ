# TransitIQ Processing Layer

This layer turns the cached data-layer handoff into planner-ready tract outputs:

- Transit Dependency Weight
- Transit Hardship Index
- K-means-style vulnerability segments
- Cost of Inaction components for 1, 3, and 5 year delay scenarios
- Safety and displacement warning scores for dashboard overlays

Run it from the project folder:

```bash
python3 process_transit_iq.py
```

The script reads `data/outputs/master_tract_data.csv` and writes:

- `data/processed/transit_dependency_weights.csv`
- `data/processed/transit_hardship_index.csv`
- `data/processed/vulnerability_segments.csv`
- `data/processed/cost_of_inaction_by_tract.csv`
- `data/outputs/processing_layer_results.csv`
- `data/outputs/processing_layer_summary.csv`
- `data/outputs/processing_layer_metadata.json`

Adjustable assumptions are exposed as CLI flags:

```bash
python3 process_transit_iq.py \
  --missed-care-rate 0.08 \
  --cost-per-missed-episode 1500 \
  --growth-rate 0.03 \
  --average-commute-distance-miles 8
```

Math note: overlapping ACS groups are not treated as mutually exclusive. The
wage component uses `max(transit_commuters, workers_no_vehicle)` instead of
adding both counts. Healthcare uses the same idea for no-vehicle household
population and transit commuters. Environmental VMT is capped to an affected
commuter estimate instead of assuming every non-transit commuter is a forced
drive trip. Affordability uses a burdened-household proxy instead of applying a
tract-level H+T excess ratio to every household in the tract.

Data quality note: the current data layer does not include elderly population or
single-parent household fields, and the collected disability column appears to be
the B18101 universe total rather than disabled population. The processing layer
records this in metadata and only uses reliable available dependency inputs.
