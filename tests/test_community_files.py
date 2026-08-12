from __future__ import annotations

from pathlib import Path
import shlex
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = ROOT / "AGENTS.md"
CONTRIBUTING_PATH = ROOT / "CONTRIBUTING.md"
ISSUE_FORM_PATH = ROOT / ".github" / "ISSUE_TEMPLATE" / "correction.yml"
PR_TEMPLATE_PATH = ROOT / ".github" / "pull_request_template.md"
RELEASE_VALIDATION_COMMAND = (
    "python skills/weekly-wisereads/scripts/validate_repository.py --repo-root . --phase release"
)


def _read(path: Path) -> str:
    assert path.exists(), f"missing file: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def test_contributing_sets_evidence_first_policy():
    text = _read(CONTRIBUTING_PATH)

    accepted = (
        "fact corrections",
        "first-party sources",
        "method improvements",
        "Skill/template fixes",
        "counter-material",
    )
    rejected = (
        "copied source text",
        "promotion",
        "unsourced claims",
        "unread batch AI reports",
    )

    for phrase in accepted:
        assert phrase in text

    for phrase in rejected:
        assert phrase in text

    assert "python -m pytest -q" in text
    assert RELEASE_VALIDATION_COMMAND in text
    assert "disagreement alone is not grounds to remove a source" in text
    assert "evidence quality is reviewed independently from popularity" in text


def test_correction_issue_form_requires_evidence_fields():
    form = yaml.safe_load(_read(ISSUE_FORM_PATH))

    assert form["name"] == "Correction request"
    assert form["title"].startswith("[Correction]")
    assert form["body"]

    fields_by_id = {
        item["attributes"].get("label", ""): item
        for item in form["body"]
        if isinstance(item, dict) and item.get("type") != "markdown"
    }
    ids = {
        item["id"]: item
        for item in form["body"]
        if isinstance(item, dict) and item.get("type") != "markdown"
    }

    for required_id in (
        "report_path",
        "disputed_sentence",
        "proposed_correction",
        "first_party_source",
        "copyright_confirmation",
    ):
        assert required_id in ids
        assert ids[required_id]["validations"]["required"] is True

    assert ids["copyright_confirmation"]["type"] == "checkboxes"


def test_pull_request_template_repeats_validation_and_review_rules():
    text = _read(PR_TEMPLATE_PATH)

    assert "python -m pytest -q" in text
    assert RELEASE_VALIDATION_COMMAND in text
    assert "disagreement alone is not grounds to remove a source" in text
    assert "evidence quality is reviewed independently from popularity" in text


def test_repository_instructions_use_the_executable_release_validation_command():
    assert RELEASE_VALIDATION_COMMAND in _read(AGENTS_PATH)

    completed = subprocess.run(
        shlex.split(RELEASE_VALIDATION_COMMAND),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
