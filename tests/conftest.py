import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pomoc_api  # noqa: E402,F401  – dodaje katalog api/ do sys.path
