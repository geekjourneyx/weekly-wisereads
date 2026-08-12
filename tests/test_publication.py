import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from build_publication import build_publication_plan, discover_reports, replace_managed_block


def test_replace_managed_block_changes_only_block_body():
    document = "before\n<!-- AUTO:LATEST:START -->\nold\n<!-- AUTO:LATEST:END -->\nafter\n"

    updated = replace_managed_block(document, "LATEST", "new")

    assert updated == "before\n<!-- AUTO:LATEST:START -->\nnew\n<!-- AUTO:LATEST:END -->\nafter\n"


def test_duplicate_marker_is_rejected():
    document = "<!-- AUTO:LATEST:START -->\na\n<!-- AUTO:LATEST:START -->\nb\n<!-- AUTO:LATEST:END -->"

    with pytest.raises(ValueError, match="exactly one marker pair"):
        replace_managed_block(document, "LATEST", "new")


def test_nested_markers_are_rejected():
    document = (
        "<!-- AUTO:LATEST:START -->\n"
        "a\n"
        "<!-- AUTO:RECENT:START -->\n"
        "b\n"
        "<!-- AUTO:RECENT:END -->\n"
        "<!-- AUTO:LATEST:END -->\n"
    )

    with pytest.raises(ValueError, match="nested markers are not allowed"):
        replace_managed_block(document, "LATEST", "new")


def test_publication_plan_contains_atomic_three_file_set(tmp_path: Path):
    (tmp_path / "README.md").write_text(
        "stable\n"
        "<!-- AUTO:LATEST:START -->\nnone\n<!-- AUTO:LATEST:END -->\n"
        "<!-- AUTO:RECENT:START -->\nnone\n<!-- AUTO:RECENT:END -->\n",
        encoding="utf-8",
    )
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "README.md").write_text("# 报告归档\n", encoding="utf-8")

    plan = build_publication_plan(
        tmp_path,
        "reports/2026/2026-08-12-vol-155.md",
        _valid_report(),
    )

    assert set(plan.files) == {
        "reports/2026/2026-08-12-vol-155.md",
        "reports/README.md",
        "README.md",
    }


@pytest.mark.parametrize(
    ("report_path", "message"),
    [
        ("../outside.md", r"report_path must be a normalized POSIX relative path under reports/<year>/.*\.md"),
        ("/tmp/outside.md", r"report_path must be a normalized POSIX relative path under reports/<year>/.*\.md"),
        ("README.md", r"report_path must be a normalized POSIX relative path under reports/<year>/.*\.md"),
        ("reports/README.md", r"report_path must be a normalized POSIX relative path under reports/<year>/.*\.md"),
        ("reports/2026/nested/issue.md", r"report_path must be a normalized POSIX relative path under reports/<year>/.*\.md"),
        ("reports/2026/a/b.md", r"report_path must be a normalized POSIX relative path under reports/<year>/.*\.md"),
        ("reports/2026/not-markdown.txt", r"report_path must be a normalized POSIX relative path under reports/<year>/.*\.md"),
        (r"reports\\2026\\escape.md", r"report_path must use forward slashes"),
        ("reports/2026/./issue.md", r"report_path must be a normalized POSIX relative path under reports/<year>/.*\.md"),
        ("reports/2026/../issue.md", r"report_path must be a normalized POSIX relative path under reports/<year>/.*\.md"),
        (".", r"report_path must be a normalized POSIX relative path under reports/<year>/.*\.md"),
        ("..", r"report_path must be a normalized POSIX relative path under reports/<year>/.*\.md"),
    ],
)
def test_publication_plan_rejects_invalid_report_targets_before_repo_reads(
    tmp_path: Path,
    report_path: str,
    message: str,
):
    with pytest.raises(ValueError, match=message):
        build_publication_plan(tmp_path, report_path, _valid_report())


def test_discover_reports_returns_newest_first_entries(tmp_path: Path):
    reports_dir = tmp_path / "reports" / "2026"
    reports_dir.mkdir(parents=True)
    (tmp_path / "reports" / "README.md").write_text("# 报告归档\n", encoding="utf-8")
    older_path = "reports/2026/2026-08-05-vol-154.md"
    newer_path = "reports/2026/2026-08-12-vol-155.md"
    _write_report_file(tmp_path, older_path, _valid_report(issue_number=154, date="2026-08-05"))
    _write_report_file(tmp_path, newer_path, _valid_report(issue_number=155, date="2026-08-12"))

    entries = discover_reports(tmp_path)

    assert [entry.path for entry in entries] == [newer_path, older_path]


def test_publication_plan_renders_archive_and_readme_blocks(tmp_path: Path):
    _write_seed_files(tmp_path)
    existing_specs = [
        (154, "2026-08-05"),
        (153, "2026-07-29"),
        (152, "2026-07-22"),
        (151, "2026-07-15"),
        (150, "2026-07-08"),
        (149, "2026-07-01"),
    ]
    for issue_number, date in existing_specs:
        _write_report_file(
            tmp_path,
            f"reports/2026/{date}-vol-{issue_number}.md",
            _valid_report(issue_number=issue_number, date=date),
        )

    report_path = "reports/2026/2026-08-12-vol-155.md"
    report_text = _valid_report(issue_number=155, date="2026-08-12")
    plan = build_publication_plan(tmp_path, report_path, report_text)

    assert plan.files[report_path] == report_text
    assert plan.files["README.md"] == (
        "intro\n"
        "<!-- AUTO:LATEST:START -->\n"
        "- [Vol. 155｜Wisereads Vol. 155 深度解读](reports/2026/2026-08-12-vol-155.md)\n"
        "<!-- AUTO:LATEST:END -->\n"
        "mid\n"
        "<!-- AUTO:RECENT:START -->\n"
        "- [Vol. 155｜Wisereads Vol. 155 深度解读](reports/2026/2026-08-12-vol-155.md)\n"
        "- [Vol. 154｜Wisereads Vol. 154 深度解读](reports/2026/2026-08-05-vol-154.md)\n"
        "- [Vol. 153｜Wisereads Vol. 153 深度解读](reports/2026/2026-07-29-vol-153.md)\n"
        "- [Vol. 152｜Wisereads Vol. 152 深度解读](reports/2026/2026-07-22-vol-152.md)\n"
        "- [Vol. 151｜Wisereads Vol. 151 深度解读](reports/2026/2026-07-15-vol-151.md)\n"
        "- [Vol. 150｜Wisereads Vol. 150 深度解读](reports/2026/2026-07-08-vol-150.md)\n"
        "\n"
        "- [完整归档](reports/README.md)\n"
        "<!-- AUTO:RECENT:END -->\n"
        "outro\n"
    )
    assert plan.files["reports/README.md"] == (
        "# 报告归档\n"
        "\n"
        "按发布时间倒序排列所有已发布报告。\n"
        "\n"
        "- [Vol. 155｜Wisereads Vol. 155 深度解读](2026/2026-08-12-vol-155.md)\n"
        "- [Vol. 154｜Wisereads Vol. 154 深度解读](2026/2026-08-05-vol-154.md)\n"
        "- [Vol. 153｜Wisereads Vol. 153 深度解读](2026/2026-07-29-vol-153.md)\n"
        "- [Vol. 152｜Wisereads Vol. 152 深度解读](2026/2026-07-22-vol-152.md)\n"
        "- [Vol. 151｜Wisereads Vol. 151 深度解读](2026/2026-07-15-vol-151.md)\n"
        "- [Vol. 150｜Wisereads Vol. 150 深度解读](2026/2026-07-08-vol-150.md)\n"
        "- [Vol. 149｜Wisereads Vol. 149 深度解读](2026/2026-07-01-vol-149.md)\n"
    )


def test_duplicate_issue_key_returns_noop_plan(tmp_path: Path):
    _write_seed_files(tmp_path)
    _write_report_file(
        tmp_path,
        "reports/2026/2026-08-05-vol-154.md",
        _valid_report(issue_number=155, date="2026-08-05"),
    )

    plan = build_publication_plan(
        tmp_path,
        "reports/2026/2026-08-12-vol-155.md",
        _valid_report(issue_number=155, date="2026-08-12"),
    )

    assert plan.issue_key == "wisereads-vol-155"
    assert plan.files == {}


def test_duplicate_source_url_returns_noop_plan_after_canonicalization(tmp_path: Path):
    _write_seed_files(tmp_path)
    _write_report_file(
        tmp_path,
        "reports/2026/2026-08-05-vol-154.md",
        _valid_report(
            issue_number=154,
            date="2026-08-05",
            source_url="https://wise.readwise.io/issues/wisereads-vol-155",
        ),
    )

    plan = build_publication_plan(
        tmp_path,
        "reports/2026/2026-08-12-vol-155.md",
        _valid_report(issue_number=155, date="2026-08-12"),
    )

    assert plan.files == {}


@pytest.mark.parametrize("source_url", ["https://wise.readwise.io/issues/wisereads-vol-155/?utm=x", "https://wise.readwise.io/issues/wisereads-vol-155#fragment"])
def test_duplicate_source_url_noops_query_and_fragment_variants(tmp_path: Path, source_url: str):
    _write_seed_files(tmp_path)
    _write_report_file(
        tmp_path,
        "reports/2026/2026-08-05-vol-154.md",
        _valid_report(
            issue_number=154,
            date="2026-08-05",
            source_url=source_url,
        ),
    )

    plan = build_publication_plan(
        tmp_path,
        "reports/2026/2026-08-12-vol-155.md",
        _valid_report(issue_number=155, date="2026-08-12"),
    )

    assert plan.files == {}


@pytest.mark.parametrize(
    ("report_path", "issue_kind", "canonical_path"),
    [
        (
            "reports/2026/2026-08-12-special-vol-2.md",
            "standard",
            "reports/2026/2026-08-12-vol-2.md",
        ),
        (
            "reports/2026/2026-08-12-vol-2.md",
            "special",
            "reports/2026/2026-08-12-special-vol-2.md",
        ),
    ],
)
def test_publication_plan_rejects_noncanonical_standard_or_special_filename(
    tmp_path: Path,
    report_path: str,
    issue_kind: str,
    canonical_path: str,
):
    _write_seed_files(tmp_path)
    report_text = _valid_report(issue_number=2, date="2026-08-12")
    if issue_kind == "special":
        report_text = report_text.replace('issue_kind: "standard"', 'issue_kind: "special"').replace(
            'issue_label: "Vol. 2"', 'issue_label: "Special Edition Vol. 2"'
        )

    with pytest.raises(ValueError, match=f"canonical report_path is {re.escape(canonical_path)}"):
        build_publication_plan(tmp_path, report_path, report_text)


def test_publication_plan_rejects_target_equal_to_existing_report(tmp_path: Path):
    _write_seed_files(tmp_path)
    existing_path = "reports/2026/2026-08-12-vol-155.md"
    _write_report_file(tmp_path, existing_path, _valid_report())

    with pytest.raises(ValueError, match=r"report_path already exists: reports/2026/2026-08-12-vol-155\.md"):
        build_publication_plan(tmp_path, existing_path, _valid_report())


def test_plan_metadata_uses_canonical_source_url_without_rewriting_report_body(tmp_path: Path):
    _write_seed_files(tmp_path)
    report_path = "reports/2026/2026-08-12-vol-155.md"
    report_text = _valid_report(source_url="https://wise.readwise.io/issues/wisereads-vol-155/?utm=x")

    plan = build_publication_plan(tmp_path, report_path, report_text)

    assert plan.source_url == "https://wise.readwise.io/issues/wisereads-vol-155/"
    assert 'source_url: "https://wise.readwise.io/issues/wisereads-vol-155/?utm=x"' in plan.files[report_path]


def test_cli_json_dry_run_emits_only_metadata(tmp_path: Path):
    _write_seed_files(tmp_path)
    report_path = "reports/2026/2026-08-12-vol-155.md"
    report_file = tmp_path / report_path
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(
        _valid_report(source_url="https://wise.readwise.io/issues/wisereads-vol-155#fragment"),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "skills" / "weekly-wisereads" / "scripts" / "build_publication.py"),
            "--repo-root",
            str(tmp_path),
            "--report",
            report_path,
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload == {
        "files": [
            "README.md",
            "reports/2026/2026-08-12-vol-155.md",
            "reports/README.md",
        ],
        "issue_key": "wisereads-vol-155",
        "state": "PLAN_READY",
        "source_url": "https://wise.readwise.io/issues/wisereads-vol-155/",
    }
    assert 'source_url: "https://wise.readwise.io/issues/wisereads-vol-155#fragment"' in report_file.read_text(encoding="utf-8")
    assert "body" not in result.stdout
    assert "Wisereads Vol. 155 深度解读" not in result.stdout


def test_cli_json_dry_run_returns_explicit_noop_when_all_planned_files_match(tmp_path: Path):
    _write_seed_files(tmp_path)
    report_path = "reports/2026/2026-08-12-vol-155.md"
    report_text = _valid_report()
    plan = build_publication_plan(tmp_path, report_path, report_text)
    for path, content in plan.files.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "skills" / "weekly-wisereads" / "scripts" / "build_publication.py"),
            "--repo-root",
            str(tmp_path),
            "--report",
            report_path,
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload == {
        "files": [],
        "issue_key": "wisereads-vol-155",
        "state": "NOOP_ALREADY_PROCESSED",
        "source_url": "https://wise.readwise.io/issues/wisereads-vol-155/",
    }


def _write_seed_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "intro\n"
        "<!-- AUTO:LATEST:START -->\nold latest\n<!-- AUTO:LATEST:END -->\n"
        "mid\n"
        "<!-- AUTO:RECENT:START -->\nold recent\n<!-- AUTO:RECENT:END -->\n"
        "outro\n",
        encoding="utf-8",
    )
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "README.md").write_text(
        "# 报告归档\n\n按发布时间倒序排列所有已发布报告。\n",
        encoding="utf-8",
    )


def _write_report_file(tmp_path: Path, report_path: str, report_text: str) -> None:
    file_path = tmp_path / report_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(report_text, encoding="utf-8")


def _valid_report(
    issue_number: int = 155,
    date: str = "2026-08-12",
    source_url: str | None = None,
) -> str:
    canonical_source_url = source_url or f"https://wise.readwise.io/issues/wisereads-vol-{issue_number}/"
    return f"""---
title: "Wisereads Vol. {issue_number} 深度解读"
issue_key: "wisereads-vol-{issue_number}"
issue_kind: "standard"
issue_number: {issue_number}
issue_label: "Vol. {issue_number}"
source_url: "{canonical_source_url}"
discovered_at: "{date}T10:00:00+08:00"
generated_at: "{date}T10:42:00+08:00"
language: "zh-CN"
reading_time_minutes: 18
sources_total: 10
sources_full_read: 8
sources_partial: 0
sources_alternate: 1
sources_summary_only: 1
sources_unavailable: 0
sources_degraded: 2
---
body
"""
