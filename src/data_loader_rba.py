"""Loaders for RBA property-reference inputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import RAW_MANUAL_DIR, RAW_PUBLIC_DIR, RAW_RBA_DIR
from src.load_public_data import load_rba_cash_rate


RBA_CASH_RATE_FILENAME = "rba_f1_data.csv"
OPTIONAL_RBA_CONTEXT_FILES = (
    "rba_housing_arrears_context.csv",
    "rba_housing_arrears_context.xlsx",
)


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


def load_cash_rate_summary() -> pd.DataFrame:
    path = _resolve_existing_file((RBA_CASH_RATE_FILENAME,), [RAW_RBA_DIR, RAW_PUBLIC_DIR])
    if path is None:
        raise FileNotFoundError(f"Could not find {RBA_CASH_RATE_FILENAME} in {RAW_RBA_DIR} or {RAW_PUBLIC_DIR}")

    cash_rate = load_rba_cash_rate(path).sort_values("date")
    latest = cash_rate.iloc[-1]
    one_year_ago = cash_rate[cash_rate["date"] <= latest["date"] - pd.DateOffset(years=1)]
    prev = one_year_ago.iloc[-1] if not one_year_ago.empty else latest
    change = float(latest["Cash Rate Target"] - prev["Cash Rate Target"])

    return pd.DataFrame(
        [
            {
                "as_of_date": latest["date"].date().isoformat(),
                "cash_rate_latest_pct": float(latest["Cash Rate Target"]),
                "cash_rate_change_1y_pctpts": change,
                "cash_rate_trend": "Falling" if change < 0 else "Rising" if change > 0 else "Stable",
                "source_dataset": "RBA F1 cash-rate table",
            }
        ]
    )


def load_optional_rba_housing_context() -> pd.DataFrame:
    path = _resolve_existing_file(OPTIONAL_RBA_CONTEXT_FILES, [RAW_RBA_DIR, RAW_MANUAL_DIR])
    if path is None:
        return pd.DataFrame(columns=["as_of_date", "arrears_environment_level", "arrears_trend", "notes", "source_note"])

    df = _read_tabular_file(path)
    expected = {"as_of_date", "arrears_environment_level", "arrears_trend", "notes"}
    missing = expected.difference(df.columns)
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {sorted(missing)}")

    out = df.copy()
    out["as_of_date"] = pd.to_datetime(out["as_of_date"], errors="coerce").dt.date.astype("string")
    out["source_note"] = out.get("source_note", f"Staged RBA housing arrears context ({path.name})")
    return out[["as_of_date", "arrears_environment_level", "arrears_trend", "notes", "source_note"]]
