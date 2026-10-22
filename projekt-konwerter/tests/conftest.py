import sys
from pathlib import Path

# Pozwala uruchomić `pytest` z katalogu projektu bez instalowania pakietu.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
