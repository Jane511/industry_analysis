# Methodology: Property Cycle

## Objective

`property_cycle_table.csv` summarises where each property segment sits in the current cycle and how soft the segment looks for downstream credit overlays.

## Inputs

- staged `ABS Building Approvals (Non-residential)` series
- optional staged building-activity extract for commencements/completions

## Logic

1. Calculate approvals change and approvals momentum for each staged property segment.
2. If building-activity extracts are staged, calculate separate commencements and completions signals.
3. If no activity file is staged, proxy both signals from the approvals trend and label that explicitly.
4. Combine the approvals and activity signals into a cycle score.
5. Blend the cycle score with structural segment sensitivity to derive `market_softness_score`.
6. Map the cycle score into `growth`, `neutral`, `slowing`, or `downturn`.

## Output Fields

- `region`
- `property_segment`
- `approvals_change_pct`
- `commencements_signal`
- `completions_signal`
- `cycle_stage`
- `market_softness_score`
- `market_softness_band`
- `as_of_date`
- `source_note`
