import sys
from pathlib import Path

# The project is never installed into its own venv, so the compiler is imported from src/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
