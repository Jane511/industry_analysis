# Data Dictionary - industry-analysis

| Field | Description |
| --- | --- |
| `borrower_id` | Synthetic borrower identifier. |
| `facility_id` | Synthetic facility identifier. |
| `segment` | Portfolio segment. |
| `industry` | Australian industry grouping. |
| `product_type` | Facility or product type. |
| `limit` | Approved or committed exposure limit. |
| `drawn` | Current drawn balance. |
| `pd` | Demonstration PD input. |
| `lgd` | Demonstration LGD input. |
| `ead` | Demonstration EAD input. |

## Output files

- `outputs/tables/industry_risk_score_table.csv`
- `outputs/tables/benchmark_ratio_reference_table.csv`
- `outputs/tables/downturn_overlay_table.csv`
- `outputs/tables/market_softness_overlay.csv`
- `outputs/tables/concentration_support_table.csv`
