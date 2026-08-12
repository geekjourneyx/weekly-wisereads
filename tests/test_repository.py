import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_foundation_files_exist():
    required = {
        ".gitignore",
        "AGENTS.md",
        "LICENSE",
        "pyproject.toml",
        "docs/design/2026-08-12-weekly-wisereads-design.md",
    }
    assert {path for path in required if not (ROOT / path).is_file()} == set()


def test_shared_repository_path_fixtures(repo_root: Path, design_path: Path):
    assert repo_root == ROOT
    assert design_path == repo_root / "docs" / "design" / "2026-08-12-weekly-wisereads-design.md"
    assert design_path.is_file()


def test_repository_supports_offline_editable_install(tmp_path: Path):
    repo_copy = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        repo_copy,
        ignore=shutil.ignore_patterns(
            ".git",
            ".pytest_cache",
            "__pycache__",
            "*.pyc",
            "*.egg-info",
            ".superpowers",
        ),
    )
    user_base = tmp_path / "userbase"
    env = os.environ.copy()
    env["PYTHONUSERBASE"] = str(user_base)
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-build-isolation",
            "--no-deps",
            "-e",
            str(repo_copy),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
