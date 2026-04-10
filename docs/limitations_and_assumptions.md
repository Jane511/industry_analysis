# Limitations And Assumptions

## Current Build Constraints

- The local property build currently has staged `ABS Building Approvals (Non-residential)` and `RBA F1` data, but not staged local `ABS Building Activity`, `ABS Lending Indicators`, or `APRA` property-context files.
- The current `region_risk_table.csv` is therefore a national segment-level table rather than a true regional/state table.
- Missing optional property files are replaced with explicit proxies and labelled in `source_note`.

## Analytical Boundaries

- This repo is a reference layer, not a final PD, LGD, or EL model.
- The downturn-overlay table is illustrative and should not be presented as a calibrated prudential stress framework.
- The retained legacy industry workflow still includes synthetic borrower archetypes and deterministic proxy benchmarks.

## Expected Next Data Upgrades

To move the reference layer closer to the intended target architecture, the next staged additions should be:

- `ABS Building Activity`
- `ABS Lending Indicators`
- `RBA` arrears commentary extract
- `APRA` property / banking context extract

Once those files are staged locally, rerun `python scripts/run_reference_layer.py` or `python scripts/run_pipeline.py`.
