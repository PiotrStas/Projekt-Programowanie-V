import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # import studio bez instalowania pakietu

DANE = ROOT / "dane_testowe"


@pytest.fixture
def dane() -> Path:
    return DANE


@pytest.fixture
def small_df() -> pd.DataFrame:
    """Mały, ręcznie kontrolowany zbiór: 1 para duplikatów, braki liczbowe i tekstowe,
    wartość ujemna (poza zakresem) i jedna oczywista wartość odstająca."""
    return pd.DataFrame({
        "id":    [1, 2, 2, 3, 4, 5, 6, 7],
        "wiek":  [10.0, -5.0, -5.0, 20.0, None, 30.0, 35.0, 40.0],
        "pokoje": [4.0, 5.0, 5.0, 6.0, 5.0, 1000.0, 6.0, 5.0],
        "region": ["A", "B", "B", None, "A", "C", "A", "B"],
    })
