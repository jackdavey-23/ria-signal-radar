from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_2026() -> Path:
    return FIX / "registered_2026.csv"


@pytest.fixture
def fixture_2025() -> Path:
    return FIX / "registered_2025.csv"
