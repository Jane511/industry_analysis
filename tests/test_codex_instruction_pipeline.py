from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.codex_config import EXPECTED_OUTPUTS
from src.codex_run_pipeline import run_pipeline
def test_codex_instruction_pipeline_outputs(tmp_path: Path):
    result=run_pipeline(project_root=tmp_path,persist=True)
    for name in EXPECTED_OUTPUTS:
        assert name in result["outputs"]
        assert not result["outputs"][name].empty
        assert (tmp_path/"outputs"/"tables"/name).exists()
    assert result["validation"]["status"].all()
