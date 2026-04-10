from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reference_layer import run_reference_layer_pipeline


if __name__ == "__main__":
    run_reference_layer_pipeline()
