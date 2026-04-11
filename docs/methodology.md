# Methodology - industry-analysis

1. Load or generate synthetic demo data.
2. Standardise borrower, facility, exposure, collateral, and financial fields.
3. Build utilisation, margin, DSCR, leverage, liquidity, working-capital, and collateral coverage features.
4. Run the `industry` engine.
5. Validate and export CSV outputs.

## Output contract

- `outputs/tables/industry_risk_score_table.csv`
- `outputs/tables/benchmark_ratio_reference_table.csv`
- `outputs/tables/downturn_overlay_table.csv`
- `outputs/tables/market_softness_overlay.csv`
- `outputs/tables/concentration_support_table.csv`
