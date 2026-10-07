"""Route the importer promotion through its distinct action directory/branch."""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parents[1] / "promote-image.py"), run_name="__main__")
