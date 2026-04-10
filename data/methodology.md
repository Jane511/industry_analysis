# Methodology — Data Sources, Derivation Logic, and Output Reference

This document explains every output table produced by the pipeline: what each metric means, which public dataset it comes from, and exactly how it is calculated.

The methodology is designed for structured analysis. It is APRA-informed, but it does not claim to reproduce any internal industry model, borrower risk grading system, pricing engine, or concentration reporting stack. Where public data does not contain an internal credit field directly, the pipeline uses transparent proxy logic or synthetic assumptions.

---

## Public Data Sources Used

| ID | Dataset | File | Publisher | Period |
|----|---------|------|-----------|--------|
| **ABS-AI** | Australian Industry 2023-24 | `81550DO001_202324.xlsx` (Table_1) | Australian Bureau of Statistics | FY 2022-23 and FY 2023-24 |
| **ABS-BI-22** | Business Indicators — Gross Operating Profit / Sales Ratio | `56760022_dec2025_profit_ratio.xlsx` (Data1) | ABS | Quarterly time series to Dec 2025 |
| **ABS-BI-23** | Business Indicators — Inventories / Sales Ratio | `56760023_dec2025_inventory_ratio.xlsx` (Data1) | ABS | Quarterly time series to Dec 2025 |
| **ABS-LF** | Labour Force, Australia, Detailed | `6291004_feb2026_labour_force_industry.xlsx` (Data1) | ABS | Monthly time series to Feb 2026 |
| **ABS-BA** | Building Approvals — Non-Residential | `87310051_feb2026_building_approvals_nonres.xlsx` (Data1) | ABS | Monthly time series to Feb 2026 |
| **RBA-F1** | Interest Rates and Yields — Money Market | `rba_f1_data.csv` | RBA | Daily to current |
| **PTRS** | Payment Times Reporting Scheme multi-cycle AR/AP workbook reconstructed from official PDFs | `PTRS_MultiCycle_AR_Days_Model_Official.xlsx` | Payment Times Reporting Regulator | Cycle 8 and Cycle 9 official publications |

ABS, RBA, and PTRS source URLs are documented in `src/config.py`. The PTRS workbook is rebuilt automatically from the downloaded official publications rather than being maintained as a manual input file.

### Current source vintages staged in this repo

- `ABS-AI`: FY `2022-23` and FY `2023-24` annual values from the `2023-24` release
- `ABS-BI-22`: quarterly series through `December 2025`
- `ABS-BI-23`: quarterly series through `December 2025`
- `ABS-LF`: monthly series through `February 2026`
- `ABS-BA`: monthly series through `February 2026`
- `RBA-F1`: local CSV snapshot published `2 April 2026`, with the latest staged observation dated `16 March 2026`
- `PTRS`: Cycle `8` (`July 2025`) and Cycle `9` (`January 2026`) official publications, plus `March 2025` guidance

Recommended update cadence:

- `ABS-AI`: annual
- `ABS-BI-22` and `ABS-BI-23`: quarterly
- `ABS-LF` and `ABS-BA`: monthly
- `RBA-F1`: whenever a newer local snapshot is staged or the policy-rate series changes
- `PTRS`: whenever a new cycle publication is released, then rebuild the workbook and rerun the pipeline

---

## Pipeline Overview

```
ABS Australian Industry ─┬─► Stage 1: Foundation (classification scores)
                          │
ABS Business Indicators ──┤
ABS Labour Force ─────────┼─► Stage 2: Macro View (economic signal scores)
ABS Building Approvals ───┤
RBA Cash Rate ────────────┘
                               │
                               ├─► Stage 3: Benchmarks (generated financial benchmarks)
                               │
                               ├─► Stage 4: Working Capital (AR/AP/inventory and PD-scorecard-LGD overlays)
                               │
                               ├─► Stage 5: Bottom-Up (archetype borrower vs benchmark)
                               │
                               ├─► Stage 6: Scorecard (final weighted risk score)
                               │
                               ├─► Stage 7: Credit Application (pricing, policy, concentration)
                               │
                               ├─► Stage 8: Practice Alignment (appetite, stress test, ESG)
                               │
                               └─► Stage 9: Portfolio Monitoring and Reporting
```

---

## Output Table 1: `industry_classification_foundation.csv`

**Purpose:** Assign structural risk characteristics to each ANZSIC industry division using public financial data.

**Source:** ABS-AI (Table_1) — FY 2022-23 and FY 2023-24

### How the ABS file is parsed

The parser (`load_public_data.parse_australian_industry_totals`) reads Table_1, finds rows starting with "Total" (e.g., "Total Agriculture, Forestry and Fishing"), then reads the three following rows (three fiscal years) to extract: employment ('000), wages ($M), sales ($M), operating profit before tax ($M), EBITDA ($M), and industry value added ($M). From these it calculates:

- `ebitda_margin_pct` = EBITDA / Sales x 100
- `op_profit_margin_pct` = Operating Profit / Sales x 100
- `wages_to_sales_pct` = Wages / Sales x 100

### Metric derivations

| Column | Source | Derivation |


| `cyclical_score` | ABS-AI | Based on **sales growth %** (FY23-24 vs FY22-23). Negative growth = 5, 0-2% = 4, 2-6% = 3, 6-12% = 2, >12% = 1. Captures how volatile the sector's revenue is across business cycles. |

| `rate_sensitivity_score` | ABS-AI + sector anchor | Starts from EBITDA margin as a public proxy for earnings buffer against higher rates or tighter lending conditions. Lower margins score worse. That raw score is then blended with a sector structural anchor so defensive service sectors are not overstated as high risk simply because they are labour-intensive. |

| `demand_dependency_score` | ABS-AI + sector anchor | Starts from recent sales growth as a public proxy for demand resilience. Weak or negative growth scores worse. That raw score is then blended with a sector structural anchor so cyclical sectors such as Construction, Retail, Accommodation, Agriculture, and Manufacturing retain higher demand sensitivity than defensive sectors such as Health Care and Professional Services. |

| `external_shock_score` | ABS-AI + sector anchor | Uses a simple resilience signal based on thin margins and weak recent growth. This avoids treating absolute sector size or labour share as automatic risk drivers. The raw score is blended with a sector structural anchor to keep externally exposed and cyclical sectors higher than defensive service sectors. |

| `classification_risk_score` | Derived | **Mean** of the four component scores above. |

| `sales_growth_pct_foundation` | ABS-AI | (Sales FY23-24 / Sales FY22-23 - 1) x 100 |

| `ebitda_margin_pct_foundation` | ABS-AI | EBITDA / Sales x 100 for FY 2023-24 |

| `wages_to_sales_pct_foundation` | ABS-AI | Wages / Sales x 100 for FY 2023-24 |

| `employment_000_foundation` | ABS-AI | Employment in thousands for FY 2023-24 |

---

## Output Table 2: `industry_macro_view_public_signals.csv`

**Purpose:** Overlay current economic signals on top of the structural classification to detect which sectors are improving or deteriorating.

**Sources:** ABS-AI, ABS-BI-22, ABS-BI-23, ABS-LF, ABS-BA, RBA-F1

### Metric derivations

| Column | Source | Derivation |
|--------|--------|------------|
| `sales_m_latest` | ABS-AI | Total sales/service income ($M) for FY 2023-24 |

| `employment_000_latest` | ABS-AI | Employment at end of June 2024 ('000) |

| `ebitda_margin_pct_latest` | ABS-AI | EBITDA / Sales x 100 for FY 2023-24 |

| `ebitda_margin_change_pctpts` | ABS-AI | EBITDA margin FY23-24 minus EBITDA margin FY22-23 (percentage point change) |

| `sales_growth_pct` | ABS-AI | (Sales FY23-24 / Sales FY22-23 - 1) x 100 |

| `wages_to_sales_pct_latest` | ABS-AI | Wages / Sales x 100 for FY 2023-24 |

| `gross_operating_profit_to_sales_ratio_latest` | ABS-BI-22 | Most recent quarterly value from the time series. The ABS file has column headers in the format "Series ID ; Industry ; Measure". The parser extracts the industry name from the third semicolon-delimited segment, reads all quarterly data, and takes the latest non-null observation. |

| `gross_operating_profit_to_sales_ratio_yoy_change` | ABS-BI-22 | Latest value minus the value from 12 months earlier in the same time series. |

| `inventories_to_sales_ratio_latest` | ABS-BI-23 | Same parsing logic as ABS-BI-22, applied to the inventories/sales ratio file. Latest quarterly observation. |

| `inventories_to_sales_ratio_yoy_change` | ABS-BI-23 | Latest value minus value from 12 months prior. |

| `inventory_days_est` | ABS-BI-23 + ABS-BI-22 / ABS-AI | Estimated inventory days derived from the ABS quarterly inventories/sales ratio. The repo treats the ABS ratio as a quarterly ratio, so the conversion uses approximately one quarter of days rather than a full year: `inventory_days_est = inventories_to_sales_ratio x 91.25 / estimated_cogs_to_sales_ratio`, where `estimated_cogs_to_sales_ratio = clip(1 - margin_ratio, 0.45, 0.95)`. Margin ratio comes from gross operating profit/sales where available, otherwise EBITDA margin. |

| `inventory_days_yoy_change` | ABS-BI-23 + ABS-BI-22 / ABS-AI | Latest estimated inventory days minus estimated inventory days from the same quarter a year earlier, using the current-quarter ratio less the ABS YoY ratio change and the equivalent prior margin proxy. |

| `inventory_stock_build_risk` | Derived from ABS-AI, ABS-BI-22, ABS-BI-23, ABS-BA | Rule-based flag that identifies whether inventory looks to be building against weaker trading conditions. It considers the inventory-days level, YoY change in estimated days, YoY change in the inventory ratio, and whether those increases coincide with weak sales growth, weak demand, or weaker margins. |

| `employment_yoy_growth_pct` | ABS-LF | The parser reads monthly Trend series by industry division. For each industry: (latest month's employment / employment 12 months earlier - 1) x 100. |

| `demand_proxy_building_type` | ABS-BA | Each industry is mapped to a non-residential building type where a building-approvals series is considered directionally relevant (e.g., Construction → "Total Non-residential", Retail → "Retail and wholesale trade buildings"). This mapping is defined in `src/macro.py`. |

| `demand_yoy_growth_pct` | ABS-BA | For sectors where the proxy is considered usable: (latest month's approval value / value 12 months earlier - 1) x 100. Acts as a forward-looking demand proxy. For low-reliability mappings such as Health Care and Professional Services, the pipeline leaves the proxy score neutral rather than allowing a noisy capex series to dominate sector risk. |

| `cash_rate_latest_pct` | RBA-F1 | The "Cash Rate Target" column from the most recent row in the RBA CSV. |

| `cash_rate_change_1y_pctpts` | RBA-F1 | Latest cash rate minus the cash rate from 12 months earlier. |

### Scoring (all on 1-5 scale, 1 = low risk, 5 = high risk)

| Score Column | Input | Thresholds |
|-------------|-------|------------|
| `employment_score` | `employment_yoy_growth_pct` | <0% = 5, 0-1% = 4, 1-2.5% = 3, 2.5-4% = 2, >4% = 1. Missing = 3. |
| `margin_level_score` | `gross_operating_profit_to_sales_ratio_latest` (fallback: `ebitda_margin_pct_latest`) | <8% = 5, 8-12% = 4, 12-18% = 3, 18-25% = 2, >25% = 1. Handles both ratio (0-1) and percentage (0-100) scales. Missing = 3. |
| `margin_trend_score` | `gross_operating_profit_to_sales_ratio_yoy_change` (fallback: `ebitda_margin_change_pctpts`) | Large decline = 5, decline = 4, flat = 3, improvement = 2, strong improvement = 1. Handles both ratio and percentage scales. Missing = 3. |
| `inventory_score` | `inventory_days_est` plus `inventory_stock_build_risk` | Inventory risk is no longer scored directly from the raw ABS ratio. The level score is based on estimated inventory days (<10 = 1, 10-25 = 2, 25-40 = 3, 40-60 = 4, >60 = 5), then blended with the stock-build flag (`Low`, `Moderate`, `Elevated`, `High`) to capture whether inventories are rising into weaker conditions. Missing data defaults to a neutral 3. |
| `demand_score` | `demand_yoy_growth_pct` | <-20% = 5, -20% to -5% = 4, -5% to +5% = 3, 5-20% = 2, >20% = 1. Missing or intentionally suppressed low-reliability proxy = 3. |

### Composite scores

| Column | Derivation |
|--------|------------|
| `macro_risk_score` | Mean of the 5 component scores above |
| `industry_base_risk_score` | **55%** x classification_risk_score + **45%** x macro_risk_score |
| `industry_base_risk_level` | Low (score ≤ 2.0), Medium (≤ 3.0), Elevated (≤ 4.0), High (> 4.0) |

---

## Output Table 3: `industry_base_risk_scorecard.csv`

**Purpose:** Summary view of the 9 industries ranked by base risk score, combining classification and macro dimensions.

This is a filtered view of `industry_macro_view_public_signals.csv` sorted by `industry_base_risk_score` descending. All columns are derived in Stages 1 and 2 above.

| Column | Source stage |
|--------|-------------|
| `industry` | Stage 1 |
| `classification_risk_score` | Stage 1 (mean of 4 structural scores) |
| `macro_risk_score` | Stage 2 (mean of 5 signal scores) |
| `industry_base_risk_score` | Stage 2 (55/45 blend) |
| `industry_base_risk_level` | Stage 2 (risk band mapping) |
| `employment_yoy_growth_pct` | Stage 2 from ABS-LF |
| `ebitda_margin_pct_latest` | Stage 2 from ABS-AI |
| `gross_operating_profit_to_sales_ratio_latest` | Stage 2 from ABS-BI-22 |
| `inventories_to_sales_ratio_latest` | Stage 2 from ABS-BI-23 |
| `inventory_days_est` | Stage 2 estimated from ABS-BI-23 and margin proxy |
| `inventory_days_yoy_change` | Stage 2 estimated from ABS-BI-23 and prior-period margin proxy |
| `inventory_stock_build_risk` | Stage 2 rule-based inventory build flag |
| `demand_proxy_building_type` | Stage 2 mapping to ABS-BA building type |
| `demand_yoy_growth_pct` | Stage 2 from ABS-BA |
| `cash_rate_latest_pct` | Stage 2 from RBA-F1 |
| `cash_rate_change_1y_pctpts` | Stage 2 from RBA-F1 |

---

## Output Table 4: `industry_public_benchmarks.csv`

**Purpose:** Public macro metrics for each sector without risk scores — useful as a standalone reference table.

This table combines the direct public macro fields from Stage 2 with the derived inventory context fields (`inventory_days_est`, `inventory_days_yoy_change`, `inventory_stock_build_risk`) so the public benchmark pack shows both raw ABS ratios and the estimated turnover-days interpretation of those ratios.

---

## Output Table 5: `industry_generated_benchmarks.csv`

**Purpose:** Generate financial benchmark proxies (leverage, coverage, working capital) for each industry using public data and deterministic estimation rules, since public data does not directly provide all internal credit ratios directly.

**Source:** Stage 2 macro view plus PTRS when official source files have been downloaded and reconstructed

### Metric derivations

| Column | Primary Source | Derivation |
|--------|---------------|------------|
| `ebitda_margin_pct_latest` | ABS-AI or ABS-BI-22 | Direct from Stage 2. Priority: gross operating profit/sales ratio, then EBITDA margin. Converted to percentage if provided as ratio. |
| `inventory_days_benchmark` | ABS-BI-23, ABS-BI-22, ABS-AI | Uses `inventory_days_est` from Stage 2. Where the ABS quarterly inventories/sales ratio is available, the benchmark is derived from `inventories_to_sales_ratio x 91.25 / estimated_cogs_to_sales_ratio`, with `estimated_cogs_to_sales_ratio = clip(1 - margin_ratio, 0.45, 0.95)`. Where the ABS ratio is unavailable, the benchmark falls back to a transparent public-signal estimate based on sector inventory relevance, margins, sales growth, and demand conditions. |
| `inventory_days_yoy_change` | ABS-BI-23, ABS-BI-22, ABS-AI | Carries forward the Stage 2 YoY change in estimated inventory days so the benchmark pack shows not just the current days estimate but also whether inventory is building or unwinding. |
| `inventory_stock_build_risk` | Derived | Carries forward the Stage 2 stock-build flag (`Low`, `Moderate`, `Elevated`, `High`) so inventory risk can be interpreted in context rather than only by the current days estimate. |
| `ar_days_benchmark` | PTRS if available, otherwise derived | If the official PTRS source files have been downloaded and reconstructed, uses `Adjusted Base AR Days`, which is `MAX(Cycle 8 Avg Payment Time, Cycle 9 Avg Payment Time)` after any workbook conservative multiplier. If PTRS is unavailable, falls back to the proxy formula: `18 + inventory_days x 0.22 + classification_risk_score x 3.2 - profit_margin x 0.35`, with a lower-receivable adjustment for Retail and Accommodation. |
| `ar_days_stress_benchmark` | PTRS if available | `MAX(Cycle 8 80th pct, Cycle 9 80th pct)` after any workbook conservative multiplier. |
| `ar_days_severe_benchmark` | PTRS if available | `MAX(Cycle 8 95th pct, Cycle 9 95th pct)` after any workbook conservative multiplier. |
| `ap_days_benchmark` | PTRS if available, otherwise derived | If the official PTRS source files have been downloaded and reconstructed, uses the same official payment-time base series as the direct payer-side AP benchmark. If PTRS is unavailable, falls back to the proxy formula: `24 + inventory_days x 0.18 + macro_risk_score x 2.5 - profit_margin x 0.20`, clipped to 20-70 days. |
| `ap_days_stress_benchmark` | PTRS if available | `MAX(Cycle 8 80th pct, Cycle 9 80th pct)` after any workbook conservative multiplier. |
| `ap_days_severe_benchmark` | PTRS if available | `MAX(Cycle 8 95th pct, Cycle 9 95th pct)` after any workbook conservative multiplier. |
| `debt_to_ebitda_benchmark` | Derived | 1.2 + max(0, 18 - profit_margin) x 0.07 + classification_risk_score x 0.22 + macro_risk_score x 0.12 + inventory_days / 120. Lower-margin, higher-risk, inventory-heavy sectors carry more debt relative to earnings. Clipped to 1.5-4.5x. |
| `icr_benchmark` | Derived | 5.3 - (debt_to_ebitda x 0.75) + (profit_margin x 0.04) - (classification_risk_score - 3) x 0.10. Higher leverage means lower coverage; higher margins provide more earnings buffer. Clipped to 1.5-4.5x. |

**Design rationale:** PTRS provides a cleaner public proxy for both AR and AP timing than the generic benchmark formulas because it directly measures payment timing by ANZSIC division. It is more direct for AP, because it measures how reporting entities pay suppliers, and is still useful for AR as a supplier-side collection proxy. Inventory days are also no longer treated as a simplistic annualised placeholder: the repo estimates them from the ABS quarterly inventories/sales ratio using a quarter-length conversion and a margin-based COGS proxy. The remaining benchmarks use publicly observable industry characteristics (margins, inventory intensity, risk scores) as inputs to deterministic rules that approximate the type of sector benchmarking logic a credit team might use. They are not statistical estimates, observed benchmarks, or validated internal policy settings.

---

## Output Table 5A: `industry_working_capital_risk_metrics.csv`

**Purpose:** Separate AR, AP, inventory, and cash-conversion-cycle metrics into a dedicated working-capital pack that can later support borrower scorecards and provide indicative PD and LGD overlays.

**Sources:** Output Table 5 (`industry_generated_benchmarks.csv`), PTRS, ABS-BI-23, ABS-BI-22, ABS-AI

### Why this table exists

The benchmark table already contains the base AR, AP, and inventory fields. This extension table exists so those fields can be interpreted as distinct risk dimensions rather than staying embedded inside the general benchmark pack.

- `AR metrics` are used as a proxy for receivables collection pressure and receivables realisation quality.
- `AP metrics` are used as a proxy for supplier stretch and short-term funding pressure.
- `Inventory metrics` are used as a proxy for inventory liquidity and stock-build risk.
- `Cash conversion cycle` combines AR, AP, and inventory into one measure of working-capital lock-up.

The table does not claim to be a production PD model or LGD model. It provides transparent, rule-based overlays showing how public-data-derived working-capital signals could feed those later credit dimensions.

### Metric derivations

| Column | Primary Source | Derivation |
|--------|---------------|------------|
| `ar_days_benchmark` | PTRS or fallback formula from Table 5 | Carried from Table 5. |
| `ar_days_stress_benchmark` | PTRS or fallback | Carried from Table 5. |
| `ar_days_severe_benchmark` | PTRS or fallback | Carried from Table 5. |
| `ar_stress_uplift_days` | Derived | `ar_days_stress_benchmark - ar_days_benchmark` |
| `ar_severe_uplift_days` | Derived | `ar_days_severe_benchmark - ar_days_benchmark` |
| `ap_days_benchmark` | PTRS or fallback formula from Table 5 | Carried from Table 5. |
| `ap_days_stress_benchmark` | PTRS or fallback | Carried from Table 5. |
| `ap_days_severe_benchmark` | PTRS or fallback | Carried from Table 5. |
| `ap_stress_uplift_days` | Derived | `ap_days_stress_benchmark - ap_days_benchmark` |
| `ap_severe_uplift_days` | Derived | `ap_days_severe_benchmark - ap_days_benchmark` |
| `ptrs_paid_on_time_pct_latest` | PTRS | Latest available paid-on-time percentage, using Cycle 9 when available otherwise Cycle 8. |
| `inventory_days_benchmark` | ABS-BI-23, ABS-BI-22, ABS-AI | Carried from Table 5. Estimated inventory days from the ABS inventories/sales ratio or fallback public-signal logic. |
| `inventory_days_yoy_change` | ABS-BI-23, ABS-BI-22, ABS-AI | Carried from Table 5. |
| `inventory_stock_build_risk` | Derived | Carried from Table 5. Flag based on inventory-days level, YoY change, ratio change, and weak demand / margin conditions. |
| `cash_conversion_cycle_benchmark_days` | Derived | `ar_days_benchmark + inventory_days_benchmark - ap_days_benchmark` |
| `cash_conversion_cycle_stress_days` | Derived | `ar_days_stress_benchmark + inventory_days_benchmark - ap_days_benchmark` |
| `cash_conversion_cycle_uplift_days` | Derived | `cash_conversion_cycle_stress_days - cash_conversion_cycle_benchmark_days` |
| `ar_collection_score` | Derived | Mean of three 1-5 scores: AR benchmark-days score, AR stress-uplift score, and PTRS paid-on-time score. Longer AR days, larger uplift, and weaker paid-on-time performance score worse. |
| `receivables_realisation_score` | Derived | Mean of AR stress-uplift score, AR severe-uplift score, and PTRS paid-on-time score. Intended as a receivables realisation / recoverability overlay for later LGD thinking. |
| `ap_supplier_stretch_score` | Derived | Mean of AP benchmark-days score, AP stress-uplift score, and PTRS paid-on-time score. Longer payable cycles and larger stress extension score worse because they can indicate supplier stretch. |
| `inventory_liquidity_score` | Derived | 1-5 score from inventory days: `<=10 = 1`, `<=20 = 2`, `<=35 = 3`, `<=50 = 4`, `>50 = 5`. |
| `inventory_stock_build_score` | Derived | `Low = 1`, `Moderate = 3`, `Elevated = 4`, `High = 5`. |
| `cash_conversion_cycle_score` | Derived | 1-5 score from CCC days: `<=5 = 1`, `<=15 = 2`, `<=30 = 3`, `<=45 = 4`, `>45 = 5`. |
| `working_capital_scorecard_overlay_score` | Derived | Mean of `ar_collection_score`, `ap_supplier_stretch_score`, `inventory_liquidity_score`, and `cash_conversion_cycle_score`. Intended as a scorecard-use overlay. |
| `working_capital_pd_overlay_score` | Derived | Mean of `working_capital_scorecard_overlay_score`, `inventory_stock_build_score`, and `receivables_realisation_score`. Intended as a PD-oriented overlay. |
| `working_capital_lgd_overlay_score` | Derived | Mean of `receivables_realisation_score`, `inventory_liquidity_score`, and `inventory_stock_build_score`. Intended as an LGD-oriented overlay. |
| `scorecard_primary_driver` | Derived | Highest individual working-capital driver among AR collection pressure, AP supplier stretch, inventory liquidity, and CCC score. |
| `pd_primary_driver` | Derived | Highest driver among receivables realisation, inventory stock build, and CCC score. |
| `lgd_primary_driver` | Derived | Highest driver among receivables realisation, inventory liquidity, and inventory stock build. |

### Interpretation

- `Scorecard overlay` is the cleanest view for ongoing borrower risk scoring because it focuses on recurring operating working-capital pressure.
- `PD overlay` places more emphasis on deterioration dynamics such as stock build and collection slippage.
- `LGD overlay` places more emphasis on receivables realisation and inventory liquidity because those metrics matter more to recoverability under stress.

---

## Output Table 5B: `borrower_working_capital_risk_metrics.csv`

**Purpose:** Compare each synthetic borrower archetype to its sector working-capital benchmarks and overlay logic.

**Sources:** Output Table 6 (`borrower_benchmark_comparison.csv`) plus Output Table 5A (`industry_working_capital_risk_metrics.csv`)

### Metric derivations

| Column | Primary Source | Derivation |
|--------|---------------|------------|
| `ar_days`, `ap_days`, `inventory_days` | Synthetic borrower from Table 6 | Carried from the borrower archetype. |
| `ar_days_benchmark`, `ap_days_benchmark`, `inventory_days_benchmark` | Table 5 / Table 5A | Sector benchmark comparators. |
| `receivables_headroom_to_stress_days` | Derived | `ar_days_stress_benchmark - ar_days` |
| `payables_headroom_to_stress_days` | Derived | `ap_days_stress_benchmark - ap_days` |
| `cash_conversion_cycle_days` | Derived | `ar_days + inventory_days - ap_days` |
| `cash_conversion_cycle_benchmark_days` | Derived | `ar_days_benchmark + inventory_days_benchmark - ap_days_benchmark` |
| `cash_conversion_cycle_gap_days` | Derived | `cash_conversion_cycle_days - cash_conversion_cycle_benchmark_days` |
| `cash_conversion_cycle_score` | Derived | Gap score using the same "higher is worse" logic used elsewhere in the bottom-up table. |
| `receivables_realisation_score` | Derived | Headroom-to-stress score: `>=15 days = 1`, `>=10 = 2`, `>=5 = 3`, `>=0 = 4`, `<0 = 5`. |
| `supplier_stretch_score` | Derived | Same headroom-to-stress scoring logic applied to AP. |
| `working_capital_scorecard_metric_score` | Derived | Mean of borrower `ar_days_score`, `ap_days_score`, `inventory_days_score`, and `cash_conversion_cycle_score`. |
| `working_capital_pd_metric_score` | Derived | Mean of borrower scorecard metric score, industry PD overlay score, receivables realisation score, and inventory stock-build score. |
| `working_capital_lgd_metric_score` | Derived | Mean of receivables realisation score, borrower inventory-days score, and industry LGD overlay score. |

### Interpretation

This table is still synthetic because the borrower archetypes themselves are synthetic. Its purpose is not to estimate real borrower PD or LGD. Its purpose is to show how a later borrower scorecard, PD view, or LGD view could pull separately from:

- borrower-specific AR/AP/inventory gaps
- borrower cash-conversion-cycle gaps
- industry-level collection and stock-build overlays

---

## Output Table 6: `borrower_benchmark_comparison.csv`

**Purpose:** Generate one synthetic borrower archetype per industry, then score their financial ratios against the industry benchmark proxies from Table 5.

**Source:** Stage 2 macro view + Stage 3 benchmarks

### Archetype borrower generation

Each borrower is constructed as a synthetic "stressed version" of the industry benchmark proxy, simulating a borrower that is slightly weaker than the sector average:

| Borrower field | Derivation |
|---------------|------------|
| `revenue` | Industry total sales / 40,000 (scaled to a single mid-market company), clipped to $6M-$22M |
| `ebitda` | Revenue x margin, where margin = max(2%, EBITDA_margin - stress x 3.2) |
| `total_debt` | EBITDA x debt_to_ebitda_benchmark x (1 + stress x 0.22) |
| `interest_expense` | EBITDA / ICR, where ICR = max(1.1, ICR_benchmark - stress x 0.45) |
| `accounts_receivable` | Revenue x AR_days / 365, where AR_days = benchmark x (1 + stress x 0.10) |
| `accounts_payable` | COGS x AP_days / 365, where AP_days = benchmark x (1 + stress x 0.06) |
| `inventory` | COGS x inventory_days / 365, where inventory_days = benchmark x (1 + stress x 0.12) |

Where **stress factor** = max(0.15, (classification_score + macro_score) / 2 - 2.2) / 4. Higher-risk sectors generate borrowers that deviate further from benchmarks.

### Gap scoring (1-5 scale)

| Score column | Metric compared | Logic |
|-------------|----------------|-------|
| `ebitda_margin_score` | Actual margin vs industry EBITDA margin | "Lower is worse": ≥5pp above = 1, at benchmark = 2, up to 5pp below = 3, up to 10pp below = 4, >10pp below = 5 |
| `debt_to_ebitda_score` | Actual D/E vs benchmark | "Higher is worse": at or below = 1, up to 15% above = 2, up to 35% = 3, up to 60% = 4, >60% above = 5 |
| `icr_score` | Actual ICR vs benchmark | ≥benchmark+1.5x = 1, at benchmark = 2, down to -0.5x = 3, down to -1.0x = 4, lower = 5 |
| `ar_days_score` | Actual vs benchmark | Same "higher is worse" gap logic as D/E |
| `ap_days_score` | Actual vs benchmark | Same logic |
| `inventory_days_score` | Actual vs benchmark | Same logic |
| `bottom_up_risk_score` | — | **Mean** of the 6 scores above |

---

## Output Table 7: `borrower_industry_risk_scorecard.csv`

**Purpose:** Final integrated risk score combining all three risk dimensions.

### Final score derivation

```
final_industry_risk_score = 35% x classification_risk_score
                          + 30% x macro_risk_score
                          + 35% x bottom_up_risk_score
```

| Weight | Component | What it captures |
|--------|-----------|-----------------|
| 35% | Classification | Structural industry characteristics (cyclicality, rate sensitivity, demand dependency, external shock) |
| 30% | Macro | Current economic signals (employment, margins, inventory, demand, cash rate) |
| 35% | Bottom-up | Synthetic borrower financial health relative to sector benchmark proxies |

**Risk level mapping:**

| Score | Band | Meaning |
|-------|------|---------|
| ≤ 2.0 | Low | Structurally resilient sector, strong macro signals, borrower outperforming |
| 2.0 - 3.0 | Medium | Moderate sector risk, mixed signals, borrower near benchmark |
| 3.0 - 4.0 | Elevated | Structural weaknesses, deteriorating signals, or borrower underperforming |
| > 4.0 | High | High structural risk, weak macro, and significant borrower stress |

---

## Output Table 8: `industry_portfolio_proxy.csv`

**Purpose:** Estimate a proxy portfolio exposure mix using public economic data, since actual internal portfolio data is not public.

**Source:** ABS-AI (sales and employment by industry)

### Derivation

```
current_exposure_pct = (70% x sales_share + 30% x employment_share) x 100
```

Where:
- `sales_share` = industry sales / total sales across all 9 industries (from ABS-AI FY 2023-24)
- `employment_share` = industry employment / total employment across all 9 industries (from ABS-AI FY 2023-24)

**Rationale:** Commercial lending broadly tracks economic activity. Sales share reflects revenue-generating capacity (drives borrowing demand); employment share reflects workforce scale (correlated with business count and loan volume). The 70/30 weighting tilts toward revenue as the primary driver of credit demand.

---

## Output Table 9: `concentration_limits.csv`

**Purpose:** Compare the proxy portfolio exposure to illustrative risk-based concentration limits.

**Sources:** Stage 2 (risk levels) + Table 8 (portfolio proxy)

| Column | Derivation |
|--------|------------|
| `concentration_limit_pct` | Mapped from industry base risk level: Low = 25%, Medium = 20%, Elevated = 15%, High = 10%. This is an illustrative policy grid, not an observed internal concentration framework. |
| `current_exposure_pct` | From Table 8 (portfolio proxy) |
| `headroom_pct` | Limit - current exposure |
| `breach` | True if current exposure exceeds the limit |
| `utilisation_pct` | (Current exposure / limit) x 100 |

---

## Output Table 10: `pricing_grid.csv`

**Purpose:** Translate borrower risk levels into illustrative lending rates.

**Source:** Stage 5 scorecard (risk levels) + RBA-F1 (cash rate)

### Rate calculation

```
all_in_rate = cash_rate + base_margin + industry_loading
```

| Component | Source / Rule |
|-----------|-------------|
| `cash_rate_pct` | RBA-F1 latest cash rate target |
| `base_margin_pct` | Fixed at 2.50% (illustrative policy assumption) |
| `industry_loading_pct` | Mapped from risk level: Low = +0.00%, Medium = +0.25%, Elevated = +0.50%, High = +1.00%. This does not represent an internal pricing model. |
| `indicative_rate_pct` | base_margin + industry_loading (rate above cash rate) |
| `all_in_rate_pct` | cash_rate + indicative_rate (total borrower rate) |

---

## Output Table 11: `policy_overlay.csv`

**Purpose:** Define credit policy restrictions for each borrower based on their industry risk level.

**Source:** Stage 5 scorecard (risk levels)

| Risk Level | Max LVR | Review Frequency | Approval Authority | Additional Conditions |
|-----------|---------|-------------------|--------------------|-----------------------|
| Low | 80% | Annual | Standard delegated authority | None |
| Medium | 75% | Annual | Standard delegated authority | Industry section in credit memo required |
| Elevated | 65% | Semi-annual | Senior credit officer | Enhanced due diligence; stress-test cash flows |
| High | 50% | Quarterly | Credit committee | New lending subject to committee approval; mandatory collateral revaluation |

No public data is used directly. The rules are policy mappings applied to the risk levels derived from public data, intended to illustrate how sector risk can feed downstream approval settings.

---

## Output Table 12: `industry_credit_appetite_strategy.csv`

**Purpose:** Define a credit appetite framework for each sector, aligned to APRA prudential themes and public disclosure references.

**Source:** Stage 2 (industry base risk levels)

| Column | Derivation |
|--------|------------|
| `credit_appetite_stance` | Mapped from risk level: Low = "Grow", Medium = "Maintain", Elevated = "Selective", High = "Restrict" |
| `max_tenor_years` | Low = 7, Medium = 5, Elevated = 3, High = 2 |
| `covenant_intensity` | Low = "Standard", Medium = "Standard plus trigger monitoring", Elevated = "Enhanced covenant package", High = "Full covenant package with hard triggers" |
| `collateral_expectation` | Graduated from "Normal security standards" to "Cash dominion or strong collateral support expected" |
| `review_frequency` | Elevated and High = "Quarterly", Low and Medium = "Annual" |
| `esg_sensitive_sector` | True for Agriculture, Manufacturing, Construction, Accommodation, Transport (based on a defined sector map) |
| `esg_focus_area` | Specific ESG themes per sector (e.g., Agriculture = "Climate variability, water stress, land use") |

---

## Output Table 13: `industry_stress_test_matrix.csv`

**Purpose:** Test how each industry's risk score would change under four adverse scenarios.

**Source:** Stage 2 macro risk scores

### Scenarios

| Scenario | Shock applied to macro_risk_score |
|----------|----------------------------------|
| Rate shock | +0.35 |
| Employment decline | +0.40 |
| Margin squeeze | +0.45 |
| Demand shock | +0.50 |

These are simplified score shocks rather than full severe-but-plausible stress tests built from borrower cash flows or portfolio systems.

### Derivation

```
stressed_macro_risk_score = min(5.0, base_macro_risk_score + severity)
stressed_industry_risk_score = 55% x classification_risk_score + 45% x stressed_macro_risk_score
stress_delta = stressed_industry_risk_score - base_industry_risk_score
```

### Monitoring action mapping

| Stressed score | Action |
|---------------|--------|
| ≥ 3.5 | Escalate sector review |
| ≥ 3.0 | Maintain heightened monitoring |
| < 3.0 | Monitor through BAU cycle |

---

## Output Table 14: `industry_esg_sensitivity_overlay.csv`

**Purpose:** Flag sectors with elevated environmental, social, or governance risk that require additional credit review.

**Source:** Defined sector mapping (not data-driven)

| Sector | ESG Focus Area |
|--------|---------------|
| Agriculture | Climate variability, water stress, land use |
| Manufacturing | Energy intensity, waste, contamination |
| Construction | Contractor practices, embodied carbon, WHS |
| Accommodation & Food | Labour practices, energy and waste intensity |
| Transport | Fuel transition, fleet emissions, safety |
| All others | No elevated sector overlay |

ESG-sensitive sectors get "Enhanced ESG due diligence" at origination and annual review. Non-sensitive sectors receive "Standard ESG screening". This is a static sector overlay, not a substitute for transaction-level ESG review.

---

## Output Table 15: `watchlist_triggers.csv`

**Purpose:** Flag sectors that trip early-warning indicators requiring monitoring attention.

**Source:** Stage 2 macro view (scores and raw metrics)

### Trigger rules

| Trigger | Condition | Source metric |
|---------|-----------|--------------|
| Negative employment growth | `employment_yoy_growth_pct` < 0 | ABS-LF |
| Declining margin trend | `margin_trend_score` ≥ 4 | ABS-BI-22 / ABS-AI |
| Elevated base risk score | `industry_base_risk_score` ≥ 3.5 | Composite (Stage 2) |
| Extreme signal | Any of the 5 component scores = 5 | ABS-LF, ABS-BI-22, ABS-BI-23, ABS-BA |

Each trigger includes a `recommended_action` (e.g., "Review sector exposure", "Request updated financials", "Escalate to credit committee").

---

## Data Flow Summary

```
┌──────────────────────────────────────────────────────────────┐
│                    PUBLIC DATA SOURCES                        │
├──────────────┬──────────────┬─────────┬──────────┬───────────┤
│  ABS         │  ABS         │ ABS     │ ABS      │ RBA       │
│  Australian  │  Business    │ Labour  │ Building │ Cash Rate │
│  Industry    │  Indicators  │ Force   │ Approvals│ F1        │
│  (8155.0)    │  (5676.0)    │(6291.0) │ (8731.0) │           │
└──────┬───────┴──────┬───────┴────┬────┴─────┬────┴─────┬─────┘
       │              │            │          │          │
       ▼              │            │          │          │
  ┌─────────┐         │            │          │          │
  │ Stage 1 │         │            │          │          │
  │Foundation│         │            │          │          │
  │ 4 scores │         │            │          │          │
  └────┬─────┘         │            │          │          │
       │               ▼            ▼          ▼          ▼
       │         ┌───────────────────────────────────────────┐
       └────────►│              Stage 2: Macro View          │
                 │  5 signal scores + base risk score        │
                 └──────┬──────────────┬────────────────┬────┘
                        │              │                │
                        ▼              ▼                ▼
                 ┌────────────┐ ┌────────────┐  ┌──────────────┐
                 │  Stage 3   │ │  Stage 9   │  │   Stage 8    │
                 │ Benchmarks │ │ Monitoring │  │Practice Align│
                 │ (D/E, ICR, │ │ (watchlist)│  │(appetite,    │
                 │ AR/AP/Inv) │ │            │  │ stress, ESG) │
                 └─────┬──────┘ └────────────┘  └──────────────┘
                       │
                       ▼
                 ┌────────────┐
                 │  Stage 4   │
                 │ Working    │
                 │ Capital    │
                 │(AR/AP/Inv, │
                 │ PD/LGD ovl)│
                 └─────┬──────┘
                       │
                       ▼
                 ┌────────────┐
                 │  Stage 5   │
                 │ Bottom-Up  │
                 │(archetypes │
                 │ vs bench.) │
                 └─────┬──────┘
                       │
                       ▼
                 ┌────────────┐
                 │  Stage 6   │
                 │ Scorecard  │
                 │ (35/30/35) │
                 └─────┬──────┘
                       │
                       ▼
                 ┌──────────────┐
                 │   Stage 7    │
                 │Credit Appln. │
                 │(pricing,     │
                 │ policy,      │
                 │ concentration│
                 └──────────────┘
```

---

## Transparency Notes

1. **No manual input folder is required.** The live pipeline runs from downloaded public ABS/RBA files, downloaded PTRS publications reconstructed automatically into the repo workbook, and explicit proxy assumptions documented in the reporting pack.

2. **Benchmark estimation is deterministic, not statistical.** Where public data does not provide an internal credit metric directly (e.g., Debt/EBITDA or ICR), the pipeline uses transparent rule-based formulas that combine available public signals into plausible industry benchmark proxies. Inventory days are estimated from the ABS quarterly inventories/sales ratio rather than from a directly published official inventory-turnover-days series, and AR/AP days are anchored to official PTRS payment-times data when those source files have been downloaded. These rules are documented in `src/benchmarks.py`.

3. **Working-capital overlays are interpretive layers, not real PD/LGD models.** The AR, AP, inventory, and cash-conversion-cycle overlays are deterministic interpretations of the benchmark pack. They are included so the report can show how working-capital stress might feed later scorecard, PD, or LGD thinking. They are not calibrated default models or recovery models.

4. **Archetype borrowers are synthetic.** The bottom-up borrower profiles are generated from industry data, not from real company financials. They represent illustrative mid-market borrower archetypes in each sector, stressed slightly below the benchmark proxy to simulate a credit assessment scenario.

5. **Scoring thresholds are fixed policy rules.** The 1-5 scoring bands for each metric (e.g., employment growth, margin level) are defined as deterministic threshold tables in `src/utils.py`. They do not change with the data. They are illustrative policy settings used for consistency, not observed internal institutional thresholds.

6. **All weights are explicit.** Classification vs Macro = 55/45. Final score = 35% Classification + 30% Macro + 35% Bottom-Up. These weights are hardcoded and documented.
