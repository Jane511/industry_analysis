# Methodology: Arrears

## Objective

`base_arrears_environment.csv` provides one reusable macro housing-risk row that downstream repos can read directly.

## Inputs

- staged `RBA F1` cash-rate series
- optional staged `RBA` housing-arrears context extract
- optional staged `APRA` property-context extract

## Logic

1. Use the staged RBA cash-rate series to build the current macro rate backdrop.
2. If a staged RBA arrears-context extract exists, use it as the primary qualitative arrears setting.
3. If no extract exists, default to a transparent local qualitative baseline based on the March 2026 FSR summary referenced in the repo transformation instructions.
4. If an APRA property-context extract exists, append that context to the notes.
5. Convert the qualitative setting plus the cash-rate backdrop into `macro_housing_risk_score` and `macro_housing_risk_band`.

## Output Fields

- `as_of_date`
- `arrears_environment_level`
- `arrears_trend`
- `macro_housing_risk_band`
- `macro_housing_risk_score`
- `notes`
- `source_note`
