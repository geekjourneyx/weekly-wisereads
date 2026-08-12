from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal

from build_publication import (
    MANAGED_BLOCKS,
    _collect_markers,
    _render_archive,
    _render_readme_lines,
    _render_recent_block,
    canonical_report_path,
    canonicalize_source_identity,
    discover_reports,
    replace_managed_block,
)
from contracts import Finding, parse_inventory, validate_inventory, validate_positioning, validate_report


ROOT_README_BLOCKS = ("LATEST", "RECENT")
INVENTORY_FIXTURES_ROOT = Path("tests/fixtures/issues")
SKILL_REQUIRED_FILES = (
    "skills/weekly-wisereads/SKILL.md",
    "skills/weekly-wisereads/agents/openai.yaml",
    "skills/weekly-wisereads/references/positioning-contract.md",
    "skills/weekly-wisereads/references/inventory-contract.md",
    "skills/weekly-wisereads/references/analysis-method.md",
    "skills/weekly-wisereads/references/evidence-policy.md",
    "skills/weekly-wisereads/references/report-template.md",
    "skills/weekly-wisereads/references/quality-gates.md",
    "skills/weekly-wisereads/references/readme-update-contract.md",
    "skills/weekly-wisereads/references/atomic-publish-protocol.md",
    "skills/weekly-wisereads/references/scheduled-prompt.md",
)
ATOMIC_PROTOCOL_TOKENS = (
    "PUBLISHED",
    "NOOP_ALREADY_PROCESSED",
    "NOOP_AFTER_RACE",
    "BLOCKED_CONCURRENT_UPDATE",
    "PUBLISHED_UNVERIFIED",
    "force=false",
    "Create exactly three blobs",
    "Create one tree",
    "Create one commit",
    "rebuild once",
    "Re-read `main`",
    "Re-read all three published files",
)
UNSAFE_SVG_PATTERN = re.compile(
    r"""<(?:image|use|script)\b[^>]*(?:href|xlink:href)\s*=\s*["']https?://""",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class RepositoryPhase:
    value: Literal["bootstrap", "release"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_repository.py",
        usage="validate_repository.py --repo-root ROOT --phase bootstrap|release",
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--phase", required=True, choices=("bootstrap", "release"))
    args = parser.parse_args(argv)

    findings = validate_repository(Path(args.repo_root), phase=args.phase)
    for finding in findings:
        print(f"{finding.code} {finding.path}: {finding.message}")
    return 1 if findings else 0


def validate_repository(repo_root: Path, phase: Literal["bootstrap", "release"]) -> list[Finding]:
    repo_root = Path(repo_root)
    findings: list[Finding] = []

    findings.extend(_validate_skill_package(repo_root))
    findings.extend(_validate_atomic_protocol(repo_root))
    findings.extend(_validate_svg_assets(repo_root))

    if phase == "bootstrap":
        return _sort_findings(findings)

    findings.extend(_validate_release_surface(repo_root))
    return _sort_findings(findings)


def _validate_skill_package(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for relative in SKILL_REQUIRED_FILES:
        path = repo_root / relative
        if not path.is_file():
            findings.append(
                Finding(
                    code="REPOSITORY_SKILL_MISSING",
                    path=relative,
                    message="Required Weekly Wisereads Skill file is missing.",
                )
            )

    readme_path = repo_root / "README.md"
    if readme_path.is_file():
        findings.extend(validate_positioning(readme_path.read_text(encoding="utf-8"), "README.md"))

    skill_path = repo_root / "skills" / "weekly-wisereads" / "SKILL.md"
    if skill_path.is_file():
        findings.extend(validate_positioning(skill_path.read_text(encoding="utf-8"), skill_path.relative_to(repo_root).as_posix()))

    return findings


def _validate_atomic_protocol(repo_root: Path) -> list[Finding]:
    relative = "skills/weekly-wisereads/references/atomic-publish-protocol.md"
    path = repo_root / relative
    if not path.is_file():
        return []

    text = path.read_text(encoding="utf-8")
    missing = [token for token in ATOMIC_PROTOCOL_TOKENS if token not in text]
    if not missing:
        return []

    return [
        Finding(
            code="REPOSITORY_ATOMIC_PROTOCOL_INVALID",
            path=relative,
            message="Atomic publication protocol is missing required invariants: " + ", ".join(missing),
        )
    ]


def _validate_svg_assets(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    assets_root = repo_root / "assets"
    if not assets_root.exists():
        return findings

    for svg_path in sorted(assets_root.rglob("*.svg")):
        text = svg_path.read_text(encoding="utf-8")
        if UNSAFE_SVG_PATTERN.search(text):
            findings.append(
                Finding(
                    code="REPOSITORY_UNSAFE_SVG",
                    path=svg_path.relative_to(repo_root).as_posix(),
                    message="SVG assets must not reference external resources over http(s).",
                )
            )
    return findings


def _validate_release_surface(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    readme_path = repo_root / "README.md"
    archive_path = repo_root / "reports" / "README.md"

    if not readme_path.is_file():
        findings.append(
            Finding(
                code="REPOSITORY_README_MISSING",
                path="README.md",
                message="Release phase requires a root README.md.",
            )
        )
        return findings

    if not archive_path.is_file():
        findings.append(
            Finding(
                code="REPOSITORY_ARCHIVE_MISSING",
                path="reports/README.md",
                message="Release phase requires reports/README.md.",
            )
        )
        return findings

    try:
        report_entries = discover_reports(repo_root)
    except Exception as exc:  # pragma: no cover - defensive conversion
        findings.append(
            Finding(
                code="REPOSITORY_REPORT_INVALID",
                path="reports",
                message=str(exc),
            )
        )
        return findings

    if not report_entries:
        findings.append(
            Finding(
                code="REPOSITORY_REPORTS_MISSING",
                path="reports",
                message="Release phase requires at least one published report.",
            )
        )
        return findings

    findings.extend(_validate_duplicate_reports(report_entries))
    findings.extend(_validate_report_paths(report_entries))
    findings.extend(_validate_release_metadata(repo_root, report_entries))
    findings.extend(_validate_readme_blocks(repo_root, report_entries))
    findings.extend(_validate_archive_file(repo_root, report_entries))
    for entry in report_entries:
        report_text = (repo_root / entry.path).read_text(encoding="utf-8")
        findings.extend(validate_positioning(report_text, entry.path))
    return findings


def _validate_report_paths(report_entries) -> list[Finding]:
    return [
        Finding(
            code="REPOSITORY_REPORT_PATH_NONCANONICAL",
            path=entry.path,
            message=f"Published report path must be {canonical_report_path(entry.meta)}.",
        )
        for entry in report_entries
        if entry.path != canonical_report_path(entry.meta)
    ]


def _validate_duplicate_reports(report_entries) -> list[Finding]:
    findings: list[Finding] = []
    seen_issue_keys: dict[str, str] = {}
    seen_source_urls: dict[str, str] = {}

    for entry in report_entries:
        if entry.meta.issue_key in seen_issue_keys:
            findings.append(
                Finding(
                    code="REPOSITORY_DUPLICATE_ISSUE",
                    path=entry.path,
                    message=(
                        f"Duplicate issue_key {entry.meta.issue_key} also appears in "
                        f"{seen_issue_keys[entry.meta.issue_key]}."
                    ),
                )
            )
        else:
            seen_issue_keys[entry.meta.issue_key] = entry.path

        source_url = canonicalize_source_identity(entry.meta.source_url)
        if source_url in seen_source_urls:
            findings.append(
                Finding(
                    code="REPOSITORY_DUPLICATE_ISSUE",
                    path=entry.path,
                    message=(
                        f"Duplicate source_url {source_url} also appears in "
                        f"{seen_source_urls[source_url]}."
                    ),
                )
            )
        else:
            seen_source_urls[source_url] = entry.path
    return findings


def _validate_release_metadata(repo_root: Path, report_entries) -> list[Finding]:
    findings: list[Finding] = []
    parsed_inventories, inventory_findings = _load_metadata_inventories(repo_root)
    findings.extend(inventory_findings)
    if inventory_findings:
        return findings

    inventories_by_issue: dict[str, list[tuple[str, object]]] = {}
    for inventory_path, inventory in parsed_inventories:
        inventories_by_issue.setdefault(inventory.issue_key, []).append((inventory_path, inventory))

    for entry in report_entries:
        report_source = canonicalize_source_identity(entry.meta.source_url)
        candidate_inventories = inventories_by_issue.get(entry.meta.issue_key, [])
        matches = [
            (inventory_path, inventory)
            for inventory_path, inventory in candidate_inventories
            if canonicalize_source_identity(inventory.source_url) == report_source
        ]

        if not matches:
            findings.append(
                Finding(
                    code="REPOSITORY_INVENTORY_MISSING",
                    path=entry.path,
                    message=(
                        "Release reports must have exactly one matching metadata inventory under "
                        "tests/fixtures/issues/**/inventory.json keyed by issue_key and canonical source_url."
                    ),
                )
            )
            continue

        if len(matches) > 1:
            findings.append(
                Finding(
                    code="REPOSITORY_INVENTORY_AMBIGUOUS",
                    path=entry.path,
                    message=(
                        "Multiple metadata inventories match this release report: "
                        + ", ".join(inventory_path for inventory_path, _ in matches)
                    ),
                )
            )
            continue

        inventory_path, inventory = matches[0]
        findings.extend(validate_inventory(inventory, inventory_path, require_terminal=True))
        report_text = (repo_root / entry.path).read_text(encoding="utf-8")
        findings.extend(validate_report(report_text, entry.path, inventory))

    return findings


def _load_metadata_inventories(repo_root: Path) -> tuple[list[tuple[str, object]], list[Finding]]:
    inventories_root = repo_root / INVENTORY_FIXTURES_ROOT
    if not inventories_root.exists():
        return [], []

    parsed_inventories: list[tuple[str, object]] = []
    findings: list[Finding] = []
    for inventory_path in sorted(inventories_root.rglob("inventory.json")):
        relative_path = inventory_path.relative_to(repo_root).as_posix()
        try:
            inventory = parse_inventory(inventory_path.read_text(encoding="utf-8"), relative_path)
        except ValueError as exc:
            findings.append(
                Finding(
                    code="REPOSITORY_INVENTORY_INVALID",
                    path=relative_path,
                    message=str(exc),
                )
            )
            continue
        parsed_inventories.append((relative_path, inventory))

    return parsed_inventories, findings


def _validate_readme_blocks(repo_root: Path, report_entries) -> list[Finding]:
    readme_relative = "README.md"
    readme_text = (repo_root / readme_relative).read_text(encoding="utf-8")
    findings: list[Finding] = []

    try:
        _collect_markers(readme_text, ROOT_README_BLOCKS)
        expected = replace_managed_block(readme_text, "LATEST", _render_readme_lines(report_entries[:1]))
        expected = replace_managed_block(expected, "RECENT", _render_recent_block(report_entries[:6]))
    except ValueError as exc:
        return [
            Finding(
                code="REPOSITORY_README_MARKERS_INVALID",
                path=readme_relative,
                message=str(exc),
            )
        ]

    if expected != readme_text:
        findings.append(
            Finding(
                code="REPOSITORY_README_OUT_OF_SYNC",
                path=readme_relative,
                message="Managed README blocks do not match the published report set.",
            )
        )
    return findings


def _validate_archive_file(repo_root: Path, report_entries) -> list[Finding]:
    archive_relative = "reports/README.md"
    archive_text = (repo_root / archive_relative).read_text(encoding="utf-8")
    expected = _render_archive(report_entries)
    if archive_text == expected:
        return []
    return [
        Finding(
            code="REPOSITORY_ARCHIVE_OUT_OF_SYNC",
            path=archive_relative,
            message="reports/README.md does not match the published report set.",
        )
    ]


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    unique: dict[tuple[str, str, str], Finding] = {}
    for finding in findings:
        unique[(finding.path, finding.code, finding.message)] = finding
    return sorted(unique.values(), key=lambda finding: (finding.path, finding.code, finding.message))


if __name__ == "__main__":
    raise SystemExit(main())
