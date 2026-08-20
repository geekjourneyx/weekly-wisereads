from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from build_publication import discover_reports
from validate_repository import _validate_duplicate_reports, validate_repository


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def make_repo(tmp_path: Path, phase: str) -> Path:
    repo = tmp_path / phase
    repo.mkdir()

    _copy_tree(ROOT / "skills", repo / "skills")
    _copy_tree(ROOT / "assets", repo / "assets")

    (repo / "README.md").write_text(
        "# Weekly Wisereads\n\n"
        "深读 Readwise 用户上周高亮最多的内容，从集体阅读信号中，提炼值得理解、质疑与长期保留的观点。\n\n"
        "<!-- AUTO:LATEST:START -->\n"
        "- [Vol. 155｜Wisereads Vol. 155 深度解读](reports/2026/2026-08-12-vol-155.md)\n"
        "<!-- AUTO:LATEST:END -->\n\n"
        "<!-- AUTO:RECENT:START -->\n"
        "- [Vol. 155｜Wisereads Vol. 155 深度解读](reports/2026/2026-08-12-vol-155.md)\n\n"
        "- [完整归档](reports/README.md)\n"
        "<!-- AUTO:RECENT:END -->\n",
        encoding="utf-8",
    )

    reports_dir = repo / "reports"
    reports_dir.mkdir()
    (reports_dir / "README.md").write_text(
        "# 报告归档\n\n"
        "按发布时间倒序排列所有已发布报告。\n\n"
        "- [Vol. 155｜Wisereads Vol. 155 深度解读](2026/2026-08-12-vol-155.md)\n",
        encoding="utf-8",
    )

    if phase == "release":
        report_dir = reports_dir / "2026"
        report_dir.mkdir()
        shutil.copy2(FIXTURES / "valid-report.md", report_dir / "2026-08-12-vol-155.md")
        issue_dir = repo / "tests" / "fixtures" / "issues" / "vol-155"
        issue_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURES / "inventories" / "valid-all-types.json", issue_dir / "inventory.json")

    return repo


def _copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc"),
    )


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _assert_findings_are_sorted(findings) -> None:
    ordered = sorted(findings, key=lambda finding: (finding.path, finding.code, finding.message))
    assert [(f.path, f.code, f.message) for f in findings] == [
        (f.path, f.code, f.message) for f in ordered
    ]


def _codes(findings) -> list[str]:
    return [finding.code for finding in findings]


def test_release_phase_rejects_missing_readme(tmp_path: Path):
    repo = make_repo(tmp_path, "release")
    (repo / "README.md").unlink()
    before = _tree_digest(repo)

    findings = validate_repository(repo, phase="release")

    after = _tree_digest(repo)
    assert "REPOSITORY_README_MISSING" in _codes(findings)
    _assert_findings_are_sorted(findings)
    assert after == before


def test_release_phase_accepts_valid_fixture(tmp_path: Path):
    repo = make_repo(tmp_path, "release")
    before = _tree_digest(repo)

    findings = validate_repository(repo, phase="release")

    after = _tree_digest(repo)
    assert findings == []
    assert after == before


def test_release_phase_rejects_report_path_that_bypasses_canonical_naming(tmp_path: Path):
    repo = make_repo(tmp_path, "release")
    source = repo / "reports" / "2026" / "2026-08-12-vol-155.md"
    bypass = repo / "reports" / "9999" / "arbitrary-name.md"
    bypass.parent.mkdir()
    source.replace(bypass)
    readme = repo / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "reports/2026/2026-08-12-vol-155.md", "reports/9999/arbitrary-name.md"
        ),
        encoding="utf-8",
    )
    archive = repo / "reports" / "README.md"
    archive.write_text(
        archive.read_text(encoding="utf-8").replace(
            "2026/2026-08-12-vol-155.md", "9999/arbitrary-name.md"
        ),
        encoding="utf-8",
    )

    findings = validate_repository(repo, phase="release")

    assert "REPOSITORY_REPORT_PATH_NONCANONICAL" in _codes(findings)


def test_release_phase_rejects_duplicate_issue_identity(tmp_path: Path):
    repo = make_repo(tmp_path, "release")
    duplicate = repo / "reports" / "2026" / "2026-08-13-vol-155-duplicate.md"
    duplicate.write_text((FIXTURES / "valid-report.md").read_text(encoding="utf-8"), encoding="utf-8")
    before = _tree_digest(repo)

    findings = validate_repository(repo, phase="release")

    after = _tree_digest(repo)
    assert "REPOSITORY_DUPLICATE_ISSUE" in _codes(findings)
    _assert_findings_are_sorted(findings)
    assert after == before


def test_release_phase_rejects_positioning_drift(tmp_path: Path):
    repo = make_repo(tmp_path, "release")
    readme = repo / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "深读 Readwise 用户上周高亮最多的内容，从集体阅读信号中，提炼值得理解、质疑与长期保留的观点。",
            "Weekly Wisereads 是一个面向中文 AI Builder 与创业者的 AI 周报独立开源项目。",
        ),
        encoding="utf-8",
    )
    before = _tree_digest(repo)

    findings = validate_repository(repo, phase="release")

    after = _tree_digest(repo)
    assert "POSITIONING_AI_IDENTITY" in _codes(findings)
    _assert_findings_are_sorted(findings)
    assert after == before


def test_release_phase_runs_report_validator_against_matching_inventory(tmp_path: Path):
    repo = make_repo(tmp_path, "release")
    report_path = repo / "reports" / "2026" / "2026-08-12-vol-155.md"
    report_path.write_text(
        report_path.read_text(encoding="utf-8").replace(
            "## 本期行动建议",
            "## 行动建议",
        ),
        encoding="utf-8",
    )
    before = _tree_digest(repo)

    findings = validate_repository(repo, phase="release")

    after = _tree_digest(repo)
    assert "REPORT_METADATA_INVALID" in _codes(findings)
    _assert_findings_are_sorted(findings)
    assert after == before


def test_release_phase_runs_inventory_validator_against_matching_inventory(tmp_path: Path):
    repo = make_repo(tmp_path, "release")
    inventory_path = repo / "tests" / "fixtures" / "issues" / "vol-155" / "inventory.json"
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    payload["items"][0]["access_status"] = None
    inventory_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    before = _tree_digest(repo)

    findings = validate_repository(repo, phase="release")

    after = _tree_digest(repo)
    assert "INVENTORY_NON_TERMINAL_STATUS" in _codes(findings)
    _assert_findings_are_sorted(findings)
    assert after == before


def test_release_phase_rejects_unsafe_svg(tmp_path: Path):
    repo = make_repo(tmp_path, "release")
    unsafe_svg = repo / "assets" / "unsafe.svg"
    unsafe_svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/x.png" /></svg>',
        encoding="utf-8",
    )
    before = _tree_digest(repo)

    findings = validate_repository(repo, phase="release")

    after = _tree_digest(repo)
    assert "REPOSITORY_UNSAFE_SVG" in _codes(findings)
    _assert_findings_are_sorted(findings)
    assert after == before


def test_release_phase_rejects_atomic_protocol_drift(tmp_path: Path):
    repo = make_repo(tmp_path, "release")
    protocol = repo / "skills" / "weekly-wisereads" / "references" / "atomic-publish-protocol.md"
    protocol.write_text(protocol.read_text(encoding="utf-8").replace("force=false", "force=true"), encoding="utf-8")
    before = _tree_digest(repo)

    findings = validate_repository(repo, phase="release")

    after = _tree_digest(repo)
    assert "REPOSITORY_ATOMIC_PROTOCOL_INVALID" in _codes(findings)
    _assert_findings_are_sorted(findings)
    assert after == before


def test_release_phase_allows_ephemeral_inventory_after_report_validation(tmp_path: Path):
    repo = make_repo(tmp_path, "release")
    (repo / "tests" / "fixtures" / "issues" / "vol-155" / "inventory.json").unlink()
    before = _tree_digest(repo)

    findings = validate_repository(repo, phase="release")

    after = _tree_digest(repo)
    assert findings == []
    assert after == before


def test_duplicate_issue_identity_uses_canonical_source_identity(tmp_path: Path):
    repo = make_repo(tmp_path, "release")
    duplicate = repo / "reports" / "2026" / "2026-08-13-vol-999.md"
    duplicate.write_text(
        _rewrite_report(
            (FIXTURES / "valid-report.md").read_text(encoding="utf-8"),
            {
                'title: "Wisereads Vol. 155 深度解读"': 'title: "Wisereads Vol. 999 深度解读"',
                'issue_key: "wisereads-vol-155"': 'issue_key: "wisereads-vol-999"',
                'issue_number: 155': "issue_number: 999",
                'issue_label: "Vol. 155"': 'issue_label: "Vol. 999"',
                'source_url: "https://wise.readwise.io/issues/wisereads-vol-155/"': 'source_url: "https://wise.readwise.io/issues/wisereads-vol-155?utm_source=dup"',
            },
        ),
        encoding="utf-8",
    )

    findings = _validate_duplicate_reports(discover_reports(repo))

    assert [finding.code for finding in findings] == ["REPOSITORY_DUPLICATE_ISSUE"]
    assert "https://wise.readwise.io/issues/wisereads-vol-155/" in findings[0].message


def test_bootstrap_phase_allows_report_to_be_absent(tmp_path: Path):
    repo = make_repo(tmp_path, "bootstrap")
    before = _tree_digest(repo)

    findings = validate_repository(repo, phase="bootstrap")

    after = _tree_digest(repo)
    assert findings == []
    assert after == before


def test_atomic_protocol_reference_contains_required_invariants():
    protocol = (
        ROOT / "skills" / "weekly-wisereads" / "references" / "atomic-publish-protocol.md"
    ).read_text(encoding="utf-8")

    for token in (
        "PUBLISHED",
        "NOOP_ALREADY_PROCESSED",
        "NOOP_AFTER_RACE",
        "BLOCKED_CONCURRENT_UPDATE",
        "PUBLISHED_UNVERIFIED",
        "force=false",
        "Create exactly three blobs",
        "rebuild once",
        "Re-read `main`",
        "Re-read all three published files",
    ):
        assert token in protocol

    inventory_contract = (
        ROOT / "skills" / "weekly-wisereads" / "references" / "inventory-contract.md"
    ).read_text(encoding="utf-8")
    assert "The frozen inventory is run-local validation state" in inventory_contract
    assert "must not become a fourth publication file" in inventory_contract


def _rewrite_report(report_text: str, replacements: dict[str, str]) -> str:
    updated = report_text
    for source, replacement in replacements.items():
        updated = updated.replace(source, replacement, 1)
    return updated
