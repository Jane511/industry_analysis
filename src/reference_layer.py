"""Property and industry reference-layer pipeline."""

from __future__ import annotations

import pandas as pd

from src.arrears_environment import build_base_arrears_environment
from src.config import (
    PROCESSED_PROPERTY_REFERENCE_DIR,
    RAW_ABS_DIR,
    RAW_APRA_DIR,
    RAW_MANUAL_DIR,
    RAW_RBA_DIR,
    REFERENCE_OUTPUT_ARREARS_ENV_DIR,
    REFERENCE_OUTPUT_DOWNTURN_DIR,
    REFERENCE_OUTPUT_PROPERTY_CYCLE_DIR,
    REFERENCE_OUTPUT_REGION_RISK_DIR,
)
from src.data_loader_abs import (
    build_building_activity_summary,
    build_building_approvals_summary,
    build_housing_finance_summary,
    load_building_approvals_reference,
    load_optional_building_activity_extract,
    load_optional_lending_indicator_extract,
)
from src.data_loader_apra import load_optional_apra_property_context
from src.data_loader_rba import load_cash_rate_summary, load_optional_rba_housing_context
from src.downturn_overlay import build_property_downturn_overlays
from src.output import save_csv
from src.property_cycle import build_property_cycle_table
from src.region_risk import build_region_risk_table


def _prepare_directories() -> None:
    for directory in [
        RAW_ABS_DIR,
        RAW_APRA_DIR,
        RAW_RBA_DIR,
        RAW_MANUAL_DIR,
        PROCESSED_PROPERTY_REFERENCE_DIR,
        REFERENCE_OUTPUT_REGION_RISK_DIR,
        REFERENCE_OUTPUT_PROPERTY_CYCLE_DIR,
        REFERENCE_OUTPUT_ARREARS_ENV_DIR,
        REFERENCE_OUTPUT_DOWNTURN_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def _build_input_availability(
    activity_extract: pd.DataFrame,
    finance_extract: pd.DataFrame,
    rba_context: pd.DataFrame,
    apra_context: pd.DataFrame,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dataset": "ABS Building Approvals - Non-residential",
                "staged": True,
                "note": "Primary staged raw file used for the current reference-layer build.",
            },
            {
                "dataset": "ABS Building Activity extract",
                "staged": not activity_extract.empty,
                "note": (
                    "Used for commencements and completions signals."
                    if not activity_extract.empty
                    else "Not staged. Approvals trend used as the temporary cycle proxy."
                ),
            },
            {
                "dataset": "ABS Lending Indicators extract",
                "staged": not finance_extract.empty,
                "note": (
                    "Used for housing-finance trend signals."
                    if not finance_extract.empty
                    else "Not staged. Cash-rate backdrop used as the temporary finance proxy."
                ),
            },
            {
                "dataset": "RBA F1 cash-rate table",
                "staged": True,
                "note": "Used for the arrears-environment macro backdrop and finance proxy.",
            },
            {
                "dataset": "RBA housing arrears context extract",
                "staged": not rba_context.empty,
                "note": (
                    "Overrides the default qualitative arrears environment."
                    if not rba_context.empty
                    else "Not staged. Default qualitative arrears baseline is used."
                ),
            },
            {
                "dataset": "APRA property context extract",
                "staged": not apra_context.empty,
                "note": (
                    "Adds system-level banking/property context to the arrears note."
                    if not apra_context.empty
                    else "Not staged. APRA commentary is currently absent from the local build."
                ),
            },
        ]
    )


def run_reference_layer_pipeline() -> dict[str, pd.DataFrame]:
    _prepare_directories()

    approvals = load_building_approvals_reference()
    approvals_summary = build_building_approvals_summary(approvals)

    activity_extract = load_optional_building_activity_extract()
    activity_summary = build_building_activity_summary(activity_extract)

    finance_extract = load_optional_lending_indicator_extract()
    finance_summary = build_housing_finance_summary(finance_extract)

    cash_rate_summary = load_cash_rate_summary()
    rba_context = load_optional_rba_housing_context()
    apra_context = load_optional_apra_property_context()

    input_availability = _build_input_availability(activity_extract, finance_extract, rba_context, apra_context)
    save_csv(approvals_summary, PROCESSED_PROPERTY_REFERENCE_DIR / "building_approvals_segment_metrics.csv")
    save_csv(activity_summary, PROCESSED_PROPERTY_REFERENCE_DIR / "building_activity_segment_metrics.csv")
    save_csv(finance_summary, PROCESSED_PROPERTY_REFERENCE_DIR / "housing_finance_segment_metrics.csv")
    save_csv(cash_rate_summary, PROCESSED_PROPERTY_REFERENCE_DIR / "cash_rate_reference_summary.csv")
    save_csv(input_availability, PROCESSED_PROPERTY_REFERENCE_DIR / "reference_input_availability.csv")

    region_risk = build_region_risk_table(
        approvals_summary,
        activity_summary,
        finance_summary,
        cash_rate_summary,
    )
    property_cycle = build_property_cycle_table(approvals_summary, activity_summary)
    arrears_environment = build_base_arrears_environment(cash_rate_summary, rba_context, apra_context)
    downturn_overlays = build_property_downturn_overlays(arrears_environment, property_cycle)

    save_csv(region_risk, REFERENCE_OUTPUT_REGION_RISK_DIR / "region_risk_table.csv")
    save_csv(property_cycle, REFERENCE_OUTPUT_PROPERTY_CYCLE_DIR / "property_cycle_table.csv")
    save_csv(
        arrears_environment,
        REFERENCE_OUTPUT_ARREARS_ENV_DIR / "base_arrears_environment.csv",
    )
    save_csv(
        downturn_overlays,
        REFERENCE_OUTPUT_DOWNTURN_DIR / "property_downturn_overlays.csv",
    )

    return {
        "region_risk": region_risk,
        "property_cycle": property_cycle,
        "arrears_environment": arrears_environment,
        "downturn_overlays": downturn_overlays,
        "input_availability": input_availability,
    }
