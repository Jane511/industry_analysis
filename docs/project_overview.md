# Project Overview

## Positioning

This repository is now structured as an Australian property and industry risk reference layer.

Its purpose is to build reusable public-data tables that downstream repos can consume for:

- property-backed PD overlays
- LGD overlays
- expected-loss scenario testing
- portfolio monitoring and credit commentary

It is not positioned as a final loan-level model.

## Current Output Set

The current reference-layer outputs are:

- `data/output/region_risk/region_risk_table.csv`
- `data/output/property_cycle/property_cycle_table.csv`
- `data/output/arrears_environment/base_arrears_environment.csv`
- `data/output/downturn_overlays/property_downturn_overlays.csv`

## Current Data Status

The current local build uses staged:

- `ABS Building Approvals (Non-residential)` through `February 2026`
- `RBA F1 cash-rate data` with the latest staged observation dated `16 March 2026`

The following property inputs are not yet staged locally:

- `ABS Building Activity`
- `ABS Lending Indicators`
- `APRA` property-context files

Because of that, the live build currently produces national segment-level property reference tables rather than full state/regional tables. Missing optional files are replaced with explicit proxy logic and labelled in `source_note`.

## Build Flow

1. Load staged ABS approvals and RBA cash-rate data.
2. Load any optional ABS/APRA/RBA property extracts if they exist locally.
3. Build processed summaries in `data/processed/property/`.
4. Export the final reference tables in `data/output/`.
5. Leave final PD/LGD/EL modelling to downstream repos.

## Legacy Layer

The original industry-analysis workflow remains in the repo under `src/`, `output/`, and `METHODOLOGY.md`. It is retained as a legacy analytical layer and reviewer-facing report pack.
