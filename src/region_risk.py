"""Reference-layer region and segment risk banding."""

from __future__ import annotations

import pandas as pd

from src.utils import average_scores, classify_directional_trend, risk_band


def _rate_backdrop_score(cash_rate_latest_pct: float, cash_rate_change_1y_pctpts: float) -> tuple[float, str]:
    score = 3.0
    if cash_rate_latest_pct >= 4.25:
        score += 0.5
    elif cash_rate_latest_pct >= 3.5:
        score += 0.25

    if cash_rate_change_1y_pctpts >= 0.5:
        score += 0.5
    elif cash_rate_change_1y_pctpts > 0:
        score += 0.25
    elif cash_rate_change_1y_pctpts <= -0.25:
        score -= 0.5
    elif cash_rate_change_1y_pctpts < 0:
        score -= 0.25

    score = round(min(5.0, max(1.0, score)), 2)
    if score <= 2.25:
        label = "Proxy from cash-rate backdrop (supportive)"
    elif score <= 3.25:
        label = "Proxy from cash-rate backdrop (mixed)"
    else:
        label = "Proxy from cash-rate backdrop (restrictive)"
    return score, label


def _latest_date(*values: str) -> str:
    dates = pd.to_datetime([value for value in values if pd.notna(value)], errors="coerce")
    if len(dates) == 0 or dates.isna().all():
        return ""
    return dates.max().date().isoformat()


def _source_note(row: pd.Series) -> str:
    notes = [str(row.get("approvals_source_dataset", "ABS Building Approvals - Non-residential"))]
    if pd.notna(row.get("activity_source_dataset")):
        notes.append(str(row["activity_source_dataset"]))
    else:
        notes.append("building activity not staged; approvals trend used as proxy")
    if pd.notna(row.get("housing_finance_source_dataset")):
        notes.append(str(row["housing_finance_source_dataset"]))
    else:
        notes.append("housing finance not staged; cash-rate backdrop used as proxy")
    return "; ".join(notes)


def build_region_risk_table(
    approvals_summary: pd.DataFrame,
    building_activity_summary: pd.DataFrame,
    housing_finance_summary: pd.DataFrame,
    cash_rate_summary: pd.DataFrame,
) -> pd.DataFrame:
    cash_row = cash_rate_summary.iloc[0]
    rate_score, rate_label = _rate_backdrop_score(
        float(cash_row["cash_rate_latest_pct"]),
        float(cash_row["cash_rate_change_1y_pctpts"]),
    )

    base = approvals_summary.merge(
        building_activity_summary,
        on=["region", "state", "region_group", "property_segment"],
        how="left",
    ).merge(
        housing_finance_summary,
        on=["region", "state", "region_group", "property_segment"],
        how="left",
    )

    rows = []
    for row in base.itertuples(index=False):
        approvals_score, approvals_label = classify_directional_trend(
            row.approvals_change_pct,
            row.approvals_momentum_pct,
        )

        if pd.notna(getattr(row, "activity_source_dataset", pd.NA)):
            commencements_score, _ = classify_directional_trend(
                row.commencements_change_pct,
                row.commencements_momentum_pct,
            )
            completions_score, _ = classify_directional_trend(
                row.completions_change_pct,
                row.completions_momentum_pct,
            )
            activity_score = average_scores(commencements_score, completions_score)
            _, activity_label = classify_directional_trend(
                row.commencements_change_pct,
                row.completions_change_pct,
            )
        else:
            activity_score = approvals_score
            activity_label = "Proxy from approvals trend"

        if pd.notna(getattr(row, "housing_finance_source_dataset", pd.NA)):
            finance_score, finance_label = classify_directional_trend(
                row.housing_finance_change_pct,
                row.housing_finance_momentum_pct,
            )
        else:
            finance_score = rate_score
            finance_label = rate_label

        region_score = average_scores(
            row.structural_segment_score,
            approvals_score,
            activity_score,
            finance_score,
        )
        row_series = pd.Series(row._asdict())
        rows.append(
            {
                "region": row.region,
                "state": row.state,
                "region_group": row.region_group,
                "property_segment": row.property_segment,
                "building_approvals_trend": approvals_label,
                "building_activity_trend": activity_label,
                "housing_finance_trend": finance_label,
                "region_risk_score": region_score,
                "region_risk_band": risk_band(region_score),
                "as_of_date": _latest_date(
                    row.approvals_as_of_date,
                    getattr(row, "activity_as_of_date", pd.NA),
                    getattr(row, "housing_finance_as_of_date", pd.NA),
                    cash_row["as_of_date"],
                ),
                "source_note": _source_note(row_series),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["region_risk_score", "property_segment"], ascending=[False, True])
        .reset_index(drop=True)
    )
