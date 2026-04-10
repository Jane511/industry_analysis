import pandas as pd

from src.arrears_environment import build_base_arrears_environment
from src.downturn_overlay import build_property_downturn_overlays
from src.property_cycle import build_property_cycle_table
from src.region_risk import build_region_risk_table


def _sample_approvals_summary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "region": "Australia",
                "state": "Australia",
                "region_group": "Commercial",
                "property_segment": "Offices",
                "approvals_as_of_date": "2026-02-01",
                "approvals_change_pct": -35.7,
                "approvals_momentum_pct": -64.0,
                "approvals_source_dataset": "ABS Building Approvals - Non-residential",
                "structural_segment_score": 4.1,
            },
            {
                "region": "Australia",
                "state": "Australia",
                "region_group": "Industrial",
                "property_segment": "Warehouses",
                "approvals_as_of_date": "2026-02-01",
                "approvals_change_pct": 69.3,
                "approvals_momentum_pct": -9.1,
                "approvals_source_dataset": "ABS Building Approvals - Non-residential",
                "structural_segment_score": 2.4,
            },
        ]
    )


def _empty_activity_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "region",
            "state",
            "region_group",
            "property_segment",
            "activity_as_of_date",
            "commencements_change_pct",
            "commencements_momentum_pct",
            "completions_change_pct",
            "completions_momentum_pct",
            "activity_source_dataset",
        ]
    )


def _empty_finance_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "region",
            "state",
            "region_group",
            "property_segment",
            "housing_finance_as_of_date",
            "housing_finance_change_pct",
            "housing_finance_momentum_pct",
            "housing_finance_source_dataset",
        ]
    )


def _cash_rate_summary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "as_of_date": "2026-03-16",
                "cash_rate_latest_pct": 3.85,
                "cash_rate_change_1y_pctpts": -0.25,
                "cash_rate_trend": "Falling",
                "source_dataset": "RBA F1 cash-rate table",
            }
        ]
    )


def test_region_risk_table_uses_proxy_inputs_when_optional_sources_missing() -> None:
    region_risk = build_region_risk_table(
        _sample_approvals_summary(),
        _empty_activity_summary(),
        _empty_finance_summary(),
        _cash_rate_summary(),
    )

    offices_score = float(region_risk.loc[region_risk["property_segment"] == "Offices", "region_risk_score"].iloc[0])
    warehouses_score = float(region_risk.loc[region_risk["property_segment"] == "Warehouses", "region_risk_score"].iloc[0])

    assert offices_score > warehouses_score
    assert (region_risk["building_activity_trend"] == "Proxy from approvals trend").all()
    assert region_risk["housing_finance_trend"].str.contains("cash-rate backdrop").all()


def test_property_cycle_table_flags_negative_segment_as_downturn() -> None:
    property_cycle = build_property_cycle_table(
        _sample_approvals_summary(),
        _empty_activity_summary(),
    )

    offices_stage = property_cycle.loc[property_cycle["property_segment"] == "Offices", "cycle_stage"].iloc[0]
    warehouses_stage = property_cycle.loc[property_cycle["property_segment"] == "Warehouses", "cycle_stage"].iloc[0]

    assert offices_stage == "downturn"
    assert warehouses_stage in {"growth", "neutral", "slowing"}


def test_arrears_environment_defaults_to_low_improving_when_context_missing() -> None:
    arrears_environment = build_base_arrears_environment(
        _cash_rate_summary(),
        pd.DataFrame(columns=["as_of_date", "arrears_environment_level", "arrears_trend", "notes", "source_note"]),
        pd.DataFrame(columns=["as_of_date", "notes", "source_note"]),
    )

    row = arrears_environment.iloc[0]
    assert row["arrears_environment_level"] == "Low"
    assert row["arrears_trend"] == "Improving"
    assert float(row["macro_housing_risk_score"]) < 2.5
    assert "local transformation instructions" in row["notes"]


def test_property_downturn_overlays_are_monotonic() -> None:
    property_cycle = build_property_cycle_table(
        _sample_approvals_summary(),
        _empty_activity_summary(),
    )
    arrears_environment = build_base_arrears_environment(
        _cash_rate_summary(),
        pd.DataFrame(columns=["as_of_date", "arrears_environment_level", "arrears_trend", "notes", "source_note"]),
        pd.DataFrame(columns=["as_of_date", "notes", "source_note"]),
    )

    overlays = build_property_downturn_overlays(arrears_environment, property_cycle)
    pd_multipliers = overlays["pd_multiplier"].tolist()
    haircuts = overlays["property_value_haircut"].tolist()

    assert overlays["scenario"].tolist() == ["base", "mild", "moderate", "severe"]
    assert pd_multipliers == sorted(pd_multipliers)
    assert haircuts == sorted(haircuts)
    assert haircuts[0] == 0.0
