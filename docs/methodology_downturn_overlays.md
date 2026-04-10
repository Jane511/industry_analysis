# Methodology: Downturn Overlays

## Objective

`property_downturn_overlays.csv` provides a direct scenario table for downstream PD, LGD, and EL engines.

## Inputs

- `base_arrears_environment.csv`
- `property_cycle_table.csv`

## Logic

1. Read the current arrears backdrop and the average market-softness score.
2. Use those two signals only as light anchoring inputs.
3. Export four illustrative scenarios:
   `base`
   `mild`
   `moderate`
   `severe`
4. Publish scenario multipliers for:
   `pd_multiplier`
   `lgd_multiplier`
   `ccf_multiplier`
   `property_value_haircut`

The scenario multipliers are intentionally simple and transparent. They are portfolio assumptions, not calibrated regulatory stress parameters.
