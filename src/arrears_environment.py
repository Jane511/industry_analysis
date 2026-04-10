"""Reference-layer arrears and housing macro environment."""

from __future__ import annotations

import pandas as pd

from src.utils import clamp, risk_band


DEFAULT_QUALITATIVE_NOTE = (
    "No staged RBA housing-arrears or APRA property-context extract was found. "
    "The qualitative baseline therefore follows the March 2026 Financial Stability Review summary referenced "
    "in the local transformation instructions: housing arrears are low and have continued to decline, "
    "with vulnerability still concentrated among more leveraged and lower-income borrowers."
)


def _latest_optional_context(df: pd.DataFrame) -> pd.Series | None:
    if df.empty:
        return None
    context = df.copy()
    context["as_of_date"] = pd.to_datetime(context["as_of_date"], errors="coerce")
    context = context.sort_values("as_of_date")
    return context.iloc[-1]


def _derive_macro_housing_risk_score(
    level: str,
    trend: str,
    cash_rate_latest_pct: float,
    cash_rate_change_1y_pctpts: float,
) -> float:
    base_score = {
        "low": 2.0,
        "moderate": 3.0,
        "elevated": 4.0,
        "high": 5.0,
    }.get(str(level).lower(), 3.0)

    trend_adjustment = {
        "improving": -0.35,
        "stable": 0.0,
        "deteriorating": 0.4,
    }.get(str(trend).lower(), 0.0)

    rate_level_adjustment = 0.25 if cash_rate_latest_pct >= 3.5 else 0.0
    rate_change_adjustment = 0.25 if cash_rate_change_1y_pctpts > 0 else -0.15 if cash_rate_change_1y_pctpts < 0 else 0.0

    return round(
        clamp(base_score + trend_adjustment + rate_level_adjustment + rate_change_adjustment, 1.0, 5.0),
        2,
    )


def build_base_arrears_environment(
    cash_rate_summary: pd.DataFrame,
    rba_context: pd.DataFrame,
    apra_context: pd.DataFrame,
) -> pd.DataFrame:
    cash_row = cash_rate_summary.iloc[0]
    rba_row = _latest_optional_context(rba_context)
    apra_row = _latest_optional_context(apra_context)

    if rba_row is not None:
        level = str(rba_row["arrears_environment_level"])
        trend = str(rba_row["arrears_trend"])
        notes = str(rba_row["notes"])
        source_note = str(rba_row["source_note"])
        as_of_date = str(rba_row["as_of_date"].date())
    else:
        level = "Low"
        trend = "Improving"
        notes = DEFAULT_QUALITATIVE_NOTE
        source_note = "RBA F1 cash-rate table plus local transformation-instruction baseline"
        as_of_date = str(cash_row["as_of_date"])

    if apra_row is not None:
        notes = f"{notes} APRA context: {apra_row['notes']}"
        source_note = f"{source_note}; {apra_row['source_note']}"
        as_of_date = max(pd.to_datetime(as_of_date), apra_row["as_of_date"]).date().isoformat()

    score = _derive_macro_housing_risk_score(
        level,
        trend,
        float(cash_row["cash_rate_latest_pct"]),
        float(cash_row["cash_rate_change_1y_pctpts"]),
    )

    return pd.DataFrame(
        [
            {
                "as_of_date": as_of_date,
                "arrears_environment_level": level,
                "arrears_trend": trend,
                "macro_housing_risk_band": risk_band(score),
                "macro_housing_risk_score": score,
                "notes": notes,
                "source_note": source_note,
            }
        ]
    )
