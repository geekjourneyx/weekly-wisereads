from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "weekly-wisereads" / "scripts"
sys.path.insert(0, str(SCRIPTS))
DESIGN_PATH = ROOT / "docs" / "design" / "2026-08-12-weekly-wisereads-design.md"


@pytest.fixture
def repo_root() -> Path:
    return ROOT


@pytest.fixture
def design_path(repo_root: Path) -> Path:
    assert DESIGN_PATH == repo_root / "docs" / "design" / "2026-08-12-weekly-wisereads-design.md"
    return DESIGN_PATH
