"""Loaders for the property reference-layer ABS inputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import RAW_ABS_DIR, RAW_MANUAL_DIR, RAW_PUBLIC_DIR_ABS
from src.load_public_data import parse_building_approvals
from src.utils import normalise_text


BUILDING_APPROVALS_FILENAME = "87310051_feb2026_building_approvals_nonres.xlsx"
OPTIONAL_BUILDING_ACTIVITY_FILES = (
    "building_activity_property_extract.csv",
    "building_activity_property_extract.xlsx",
)
OPTIONAL_LENDING_INDICATOR_FILES = (
    "lending_indicators_property_extract.csv",
    "lending_indicators_property_extract.xlsx",
)

REFERENCE_SEGMENTS = {
    "Total Non-residential": {
        "region_group": "National aggregate",
        "structural_segment_score": 3.2,
    },
    "Commercial Buildings - Total": {
        "region_group": "Commercial",
        "structural_segment_score": 3.6,
    },
    "Offices": {
        "region_group": "Commercial",
        "structural_segment_score": 4.1,
    },
    "Retail and wholesale trade buildings": {
        "region_group": "Commercial",
        "structural_segment_score": 3.8,
    },
    "Industrial Buildings - Total": {
        "region_group": "Industrial",
        "structural_segment_score": 2.8,
    },
    "Warehouses": {
        "region_group": "Industrial",
        "structural_segment_score": 2.4,
    },
    "Health buildings": {
        "region_group": "Social infrastructure",
        "structural_segment_score": 2.3,
    },
    "Education buildings": {
        "region_group": "Social infrastructure",
        "structural_segment_score": 2.5,
    },
    "Aged care facilities": {
        "region_group": "Social infrastructure",
        "structural_segment_score": 2.9,
    },
    "Short term accommodation buildings": {
        "region_group": "Accommodation",
        "structural_segment_score": 4.2,
    },
    "Agricultural and aquacultural buildings": {
        "region_group": "Agriculture",
        "structural_segment_score": 3.3,
    },
}

PROPERTY_ID_COLUMNS = ["region", "state", "region_group", "property_segment"]


def _resolve_existing_file(candidates: tuple[str, ...], search_dirs: list[Path]) -> Path | None:
    for directory in search_dirs:
        for candidate in candidates:
            path = directory / candidate
            if path.exists():
                return path
    return None


def _read_tabular_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)


def _column_lookup(df: pd.DataFrame) -> dict[str, str]:
    return {normalise_text(column): column for column in df.columns}


def _pick_column(column_map: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        column = column_map.get(normalise_text(candidate))
        if column is not None:
            return column
    return None


def _empty_time_series(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=PROPERTY_ID_COLUMNS + ["date", *columns, "source_dataset"])


def _empty_summary(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=PROPERTY_ID_COLUMNS + columns)


def _ensure_identifier_fields(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "region" not in out.columns:
        out["region"] = "Australia"
    if "state" not in out.columns:
        out["state"] = "Australia"
    if "region_group" not in out.columns:
        out["region_group"] = "National"
    return out


def _summarise_series(df: pd.DataFrame, value_column: str, prefix: str) -> pd.DataFrame:
    if df.empty:
        return _empty_summary(
            [f"{prefix}_as_of_date", f"{prefix}_change_pct", f"{prefix}_momentum_pct", f"{prefix}_source_dataset"]
        )

    rows = []
    for keys, group in df.groupby(PROPERTY_ID_COLUMNS, dropna=False):
        group = group.sort_values("date").dropna(subset=[value_column])
        if group.empty:
            continue

        latest = group.iloc[-1]
        one_year_ago = group[group["date"] <= latest["date"] - pd.DateOffset(years=1)]
        prev = one_year_ago.iloc[-1] if not one_year_ago.empty else None
        prior_window = group.iloc[-6:-3] if len(group) >= 6 else pd.DataFrame()
        recent_three = group.tail(3)[value_column].mean()
        prior_three = prior_window[value_column].mean() if not prior_window.empty else pd.NA

        rows.append(
            {
                PROPERTY_ID_COLUMNS[0]: keys[0],
                PROPERTY_ID_COLUMNS[1]: keys[1],
                PROPERTY_ID_COLUMNS[2]: keys[2],
                PROPERTY_ID_COLUMNS[3]: keys[3],
                f"{prefix}_as_of_date": latest["date"].date().isoformat(),
                f"{prefix}_change_pct": (
                    (float(latest[value_column]) / float(prev[value_column]) - 1) * 100
                    if prev is not None and prev[value_column]
                    else pd.NA
                ),
                f"{prefix}_momentum_pct": (
                    (float(recent_three) / float(prior_three) - 1) * 100
                    if pd.notna(prior_three) and prior_three
                    else pd.NA
                ),
                f"{prefix}_source_dataset": latest.get("source_dataset", ""),
            }
        )

    return pd.DataFrame(rows)


def load_building_approvals_reference() -> pd.DataFrame:
    path = _resolve_existing_file((BUILDING_APPROVALS_FILENAME,), [RAW_ABS_DIR, RAW_PUBLIC_DIR_ABS])
    if path is None:
        raise FileNotFoundError(
            f"Could not find {BUILDING_APPROVALS_FILENAME} in {RAW_ABS_DIR} or {RAW_PUBLIC_DIR_ABS}"
        )

    approvals = parse_building_approvals(path)
    approvals = approvals[approvals["sector_group"] == "Total Sectors"].copy()
    approvals = approvals[approvals["building_type"].isin(REFERENCE_SEGMENTS)].copy()
    approvals["region"] = "Australia"
    approvals["state"] = "Australia"
    approvals["region_group"] = approvals["building_type"].map(
        lambda value: REFERENCE_SEGMENTS[value]["region_group"]
    )
    approvals["property_segment"] = approvals["building_type"]
    approvals["structural_segment_score"] = approvals["building_type"].map(
        lambda value: REFERENCE_SEGMENTS[value]["structural_segment_score"]
    )
    approvals["source_dataset"] = "ABS Building Approvals - Non-residential"

    return approvals[
        PROPERTY_ID_COLUMNS + ["date", "value", "structural_segment_score", "source_dataset"]
    ].copy()


def build_building_approvals_summary(approvals: pd.DataFrame) -> pd.DataFrame:
    summary = _summarise_series(approvals, "value", "approvals")
    structural = approvals[
        PROPERTY_ID_COLUMNS + ["structural_segment_score"]
    ].drop_duplicates(subset=PROPERTY_ID_COLUMNS)
    summary = summary.merge(structural, on=PROPERTY_ID_COLUMNS, how="left")
    return summary


def load_optional_building_activity_extract() -> pd.DataFrame:
    path = _resolve_existing_file(OPTIONAL_BUILDING_ACTIVITY_FILES, [RAW_ABS_DIR, RAW_MANUAL_DIR])
    if path is None:
        return _empty_time_series(["commencements_value", "completions_value"])

    df = _read_tabular_file(path)
    column_map = _column_lookup(df)

    date_column = _pick_column(column_map, ("date", "month", "period"))
    property_column = _pick_column(column_map, ("property_segment", "segment", "building_type"))
    if date_column is None or property_column is None:
        raise ValueError(
            f"{path.name} must include date/month and property_segment/segment columns for the property reference layer."
        )

    commencement_column = _pick_column(
        column_map,
        ("commencements_value", "commencements", "commencement_value", "building_activity_value", "value"),
    )
    completion_column = _pick_column(
        column_map,
        ("completions_value", "completions", "completion_value", "building_activity_value", "value"),
    )
    if commencement_column is None and completion_column is None:
        raise ValueError(
            f"{path.name} must include commencements, completions, or building_activity value columns."
        )

    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df[date_column], errors="coerce"),
            "property_segment": df[property_column],
            "region": (
                df[_pick_column(column_map, ("region",))]
                if _pick_column(column_map, ("region",)) is not None
                else "Australia"
            ),
            "state": (
                df[_pick_column(column_map, ("state",))]
                if _pick_column(column_map, ("state",)) is not None
                else "Australia"
            ),
            "region_group": (
                df[_pick_column(column_map, ("region_group", "region cluster"))]
                if _pick_column(column_map, ("region_group", "region cluster")) is not None
                else "National"
            ),
            "commencements_value": (
                pd.to_numeric(df[commencement_column], errors="coerce")
                if commencement_column is not None
                else pd.NA
            ),
            "completions_value": (
                pd.to_numeric(df[completion_column], errors="coerce")
                if completion_column is not None
                else pd.NA
            ),
        }
    )
    out = _ensure_identifier_fields(out).dropna(subset=["date", "property_segment"])
    out["source_dataset"] = f"Staged ABS building activity extract ({path.name})"
    return out


def build_building_activity_summary(activity_df: pd.DataFrame) -> pd.DataFrame:
    if activity_df.empty:
        return _empty_summary(
            [
                "activity_as_of_date",
                "commencements_change_pct",
                "commencements_momentum_pct",
                "completions_change_pct",
                "completions_momentum_pct",
                "activity_source_dataset",
            ]
        )

    commencements = _summarise_series(activity_df, "commencements_value", "commencements")
    completions = _summarise_series(activity_df, "completions_value", "completions")
    summary = commencements.merge(completions, on=PROPERTY_ID_COLUMNS, how="outer")
    summary["activity_as_of_date"] = summary[
        ["commencements_as_of_date", "completions_as_of_date"]
    ].bfill(axis=1).iloc[:, 0]
    summary["activity_source_dataset"] = summary[
        ["commencements_source_dataset", "completions_source_dataset"]
    ].bfill(axis=1).iloc[:, 0]
    return summary.drop(
        columns=[
            "commencements_as_of_date",
            "completions_as_of_date",
            "commencements_source_dataset",
            "completions_source_dataset",
        ]
    )


def load_optional_lending_indicator_extract() -> pd.DataFrame:
    path = _resolve_existing_file(OPTIONAL_LENDING_INDICATOR_FILES, [RAW_ABS_DIR, RAW_MANUAL_DIR])
    if path is None:
        return _empty_time_series(["housing_finance_value"])

    df = _read_tabular_file(path)
    column_map = _column_lookup(df)

    date_column = _pick_column(column_map, ("date", "month", "period"))
    property_column = _pick_column(column_map, ("property_segment", "segment", "building_type"))
    finance_column = _pick_column(
        column_map,
        ("housing_finance_value", "housing_finance", "finance_value", "value"),
    )
    if date_column is None or property_column is None or finance_column is None:
        raise ValueError(
            f"{path.name} must include date/month, property_segment/segment, and housing_finance/value columns."
        )

    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df[date_column], errors="coerce"),
            "property_segment": df[property_column],
            "region": (
                df[_pick_column(column_map, ("region",))]
                if _pick_column(column_map, ("region",)) is not None
                else "Australia"
            ),
            "state": (
                df[_pick_column(column_map, ("state",))]
                if _pick_column(column_map, ("state",)) is not None
                else "Australia"
            ),
            "region_group": (
                df[_pick_column(column_map, ("region_group", "region cluster"))]
                if _pick_column(column_map, ("region_group", "region cluster")) is not None
                else "National"
            ),
            "housing_finance_value": pd.to_numeric(df[finance_column], errors="coerce"),
        }
    )
    out = _ensure_identifier_fields(out).dropna(subset=["date", "property_segment"])
    out["source_dataset"] = f"Staged ABS lending indicators extract ({path.name})"
    return out


def build_housing_finance_summary(finance_df: pd.DataFrame) -> pd.DataFrame:
    return _summarise_series(finance_df, "housing_finance_value", "housing_finance")
