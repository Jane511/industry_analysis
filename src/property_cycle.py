"""Reference-layer market softness and property-cycle banding."""

from __future__ import annotations

import pandas as pd

from src.utils import average_scores, classify_directional_trend, cycle_stage_from_score, risk_band


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
        notes.append("building activity not staged; commencements and completions proxied from approvals trend")
    return "; ".join(notes)


def build_property_cycle_table(
    approvals_summary: pd.DataFrame,
    building_activity_summary: pd.DataFrame,
) -> pd.DataFrame:
    base = approvals_summary.merge(
        building_activity_summary,
        on=["region", "state", "region_group", "property_segment"],
        how="left",
    )

    rows = []
    for row in base.itertuples(index=False):
        approvals_score, _ = classify_directional_trend(
            row.approvals_change_pct,
            row.approvals_momentum_pct,
        )

        if pd.notna(getattr(row, "activity_source_dataset", pd.NA)):
            commencements_score, commencements_label = classify_directional_trend(
                row.commencements_change_pct,
                row.commencements_momentum_pct,
            )
            completions_score, completions_label = classify_directional_trend(
                row.completions_change_pct,
                row.completions_momentum_pct,
            )
        else:
            commencements_score = approvals_score
            completions_score = approvals_score
            commencements_label = "Proxy from approvals trend"
            completions_label = "Proxy from approvals trend"

        cycle_score = average_scores(approvals_score, commencements_score, completions_score)
        softness_score = average_scores(cycle_score, row.structural_segment_score)
        row_series = pd.Series(row._asdict())
        rows.append(
            {
                "region": row.region,
                "property_segment": row.property_segment,
                "approvals_change_pct": round(float(row.approvals_change_pct), 2)
                if pd.notna(row.approvals_change_pct)
                else pd.NA,
                "commencements_signal": commencements_label,
                "completions_signal": completions_label,
                "cycle_stage": cycle_stage_from_score(cycle_score),
                "market_softness_score": softness_score,
                "market_softness_band": risk_band(softness_score),
                "as_of_date": _latest_date(row.approvals_as_of_date, getattr(row, "activity_as_of_date", pd.NA)),
                "source_note": _source_note(row_series),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["market_softness_score", "property_segment"], ascending=[False, True])
        .reset_index(drop=True)
    )
