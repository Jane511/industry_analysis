# Methodology: Region Risk

## Objective

`region_risk_table.csv` is designed to provide a reusable property-segment risk band for downstream overlays.

## Current Scope

Because the staged local property inputs are currently national rather than state/regional, the live table is a national segment-level reference table with:

- `region = Australia`
- `state = Australia`
- `property_segment` carrying the usable join key

## Inputs

- staged `ABS Building Approvals (Non-residential)` series
- optional staged building-activity extract
- optional staged lending-indicators extract
- staged `RBA F1` cash-rate series

## Logic

1. Build approvals trend metrics using year-on-year change and short-window momentum.
2. If a building-activity extract is staged, use it for construction-cycle confirmation.
3. If a lending-indicators extract is staged, use it for finance-demand confirmation.
4. If optional files are not staged, use transparent proxy labels instead:
   approvals proxy for missing activity
   cash-rate backdrop proxy for missing finance
5. Combine structural segment sensitivity with the current trend signals into `region_risk_score`.
6. Map the score into `region_risk_band` using the repo-wide risk-band thresholds.

## Output Fields

- `region`
- `state`
- `region_group`
- `property_segment`
- `building_approvals_trend`
- `building_activity_trend`
- `housing_finance_trend`
- `region_risk_score`
- `region_risk_band`
- `as_of_date`
- `source_note`
