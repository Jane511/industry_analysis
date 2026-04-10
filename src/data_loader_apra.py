"""Loaders for optional APRA property-reference context."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import RAW_APRA_DIR, RAW_MANUAL_DIR


OPTIONAL_APRA_CONTEXT_FILES = (
    "apra_property_context.csv",
    "apra_property_context.xlsx",
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


def load_optional_apra_property_context() -> pd.DataFrame:
    path = _resolve_existing_file(OPTIONAL_APRA_CONTEXT_FILES, [RAW_APRA_DIR, RAW_MANUAL_DIR])
    if path is None:
        return pd.DataFrame(columns=["as_of_date", "notes", "source_note"])

    df = _read_tabular_file(path)
    expected = {"as_of_date", "notes"}
    missing = expected.difference(df.columns)
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {sorted(missing)}")

    out = df.copy()
    out["as_of_date"] = pd.to_datetime(out["as_of_date"], errors="coerce").dt.date.astype("string")
    out["source_note"] = out.get("source_note", f"Staged APRA property context ({path.name})")
    return out[["as_of_date", "notes", "source_note"]]
