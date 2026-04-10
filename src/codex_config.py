from pathlib import Path
PROJECT_ROOT=Path(__file__).resolve().parents[1]
REPO_NAME='industry_analysis'
PIPELINE_KIND='industry'
EXPECTED_OUTPUTS=['industry_risk_score_table.csv', 'benchmark_ratio_reference_table.csv', 'downturn_overlay_table.csv', 'market_softness_overlay.csv', 'concentration_support_table.csv']
