from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
from types import MappingProxyType
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from contracts import PublicationPlan, ReportEntry, parse_front_matter


MANAGED_BLOCKS = ("LATEST", "RECENT")
ARCHIVE_HEADER = "# 报告归档\n\n按发布时间倒序排列所有已发布报告。\n"


def replace_managed_block(document: str, block: str, replacement: str) -> str:
    markers = _collect_markers(document, (block,))
    if block not in markers:
        raise ValueError(f"unknown managed block: {block}")

    start_marker, end_marker, start_index, end_index = markers[block]
    body = _render_block(start_marker, end_marker, replacement)
    return f"{document[:start_index]}{body}{document[end_index:]}"


def discover_reports(repo_root: Path) -> list[ReportEntry]:
    repo_root = Path(repo_root)
    reports_root = repo_root / "reports"
    if not reports_root.exists():
        return []

    entries: list[ReportEntry] = []
    for file_path in sorted(reports_root.rglob("*.md")):
        relative_path = file_path.relative_to(repo_root).as_posix()
        if relative_path == "reports/README.md":
            continue
        meta, _ = parse_front_matter(file_path.read_text(encoding="utf-8"), relative_path)
        entries.append(ReportEntry(path=relative_path, meta=meta))

    return sorted(
        entries,
        key=lambda entry: (-entry.meta.discovered_at.timestamp(), -entry.meta.issue_number, entry.path),
    )


def build_publication_plan(repo_root: Path, report_path: str, report_text: str) -> PublicationPlan:
    return _build_publication_plan(repo_root, report_path, report_text, reject_existing_target=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="build_publication.py",
        usage="build_publication.py --repo-root ROOT --report REPORT [--json]",
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    report_path = _validate_report_path(args.report, repo_root, reject_existing_target=False)
    report_text = (repo_root / report_path).read_text(encoding="utf-8")
    plan = _build_publication_plan(repo_root, report_path, report_text, reject_existing_target=False)
    already_materialized = all(
        (repo_root / file_path).is_file()
        and (repo_root / file_path).read_text(encoding="utf-8") == content
        for file_path, content in plan.files.items()
    )

    payload = {
        "files": [] if already_materialized else sorted(plan.files),
        "issue_key": plan.issue_key,
        "state": "NOOP_ALREADY_PROCESSED" if already_materialized else "PLAN_READY",
        "source_url": plan.source_url,
    }
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    print(f"state: {payload['state']}")
    print(f"issue_key: {plan.issue_key}")
    print(f"source_url: {plan.source_url}")
    for file_path in payload["files"]:
        print(file_path)
    return 0


def _build_publication_plan(
    repo_root: Path,
    report_path: str,
    report_text: str,
    *,
    reject_existing_target: bool,
) -> PublicationPlan:
    repo_root = Path(repo_root)
    normalized_report_path = _validate_report_path(
        report_path,
        repo_root,
        reject_existing_target=reject_existing_target,
    )
    meta, _ = parse_front_matter(report_text, normalized_report_path)
    expected_report_path = canonical_report_path(meta)
    if normalized_report_path != expected_report_path:
        raise ValueError(f"canonical report_path is {expected_report_path}")

    existing_entries = [
        entry for entry in discover_reports(repo_root) if entry.path != normalized_report_path
    ]
    canonical_source_url = canonicalize_source_identity(meta.source_url)
    if any(
        entry.meta.issue_key == meta.issue_key
        or canonicalize_source_identity(entry.meta.source_url) == canonical_source_url
        for entry in existing_entries
    ):
        return PublicationPlan(
            issue_key=meta.issue_key,
            source_url=canonical_source_url,
            files=MappingProxyType({}),
        )

    readme_path = repo_root / "README.md"
    archive_path = repo_root / "reports" / "README.md"

    if not readme_path.is_file():
        raise ValueError("README.md is required")
    if not archive_path.is_file():
        raise ValueError("reports/README.md is required")

    new_entry = ReportEntry(path=normalized_report_path, meta=meta)
    _validate_unique_entries([*existing_entries, new_entry])

    published_entries = sorted(
        [*existing_entries, new_entry],
        key=lambda entry: (-entry.meta.discovered_at.timestamp(), -entry.meta.issue_number, entry.path),
    )

    latest_body = _render_readme_lines(published_entries[:1])
    recent_body = _render_recent_block(published_entries[:6])
    archive_body = _render_archive(published_entries)

    updated_readme = replace_managed_block(readme_path.read_text(encoding="utf-8"), "LATEST", latest_body)
    updated_readme = replace_managed_block(updated_readme, "RECENT", recent_body)
    _collect_markers(updated_readme, MANAGED_BLOCKS)

    files = MappingProxyType(
        {
            "README.md": updated_readme,
            "reports/README.md": archive_body,
            normalized_report_path: report_text,
        }
    )
    if set(files) != {"README.md", "reports/README.md", normalized_report_path}:
        raise ValueError("publication plan must contain exactly three file outputs")

    return PublicationPlan(
        issue_key=meta.issue_key,
        source_url=canonicalize_source_identity(meta.source_url),
        files=files,
    )


def canonical_report_path(meta) -> str:
    beijing_date = meta.discovered_at.astimezone(ZoneInfo("Asia/Shanghai"))
    identity = f"special-vol-{meta.issue_number}" if meta.issue_kind == "special" else f"vol-{meta.issue_number}"
    return f"reports/{beijing_date:%Y}/{beijing_date:%Y-%m-%d}-{identity}.md"


def _collect_markers(document: str, required_blocks: tuple[str, ...]) -> dict[str, tuple[str, str, int, int]]:
    token_map = {}
    tokens: list[tuple[int, int, str, str, str]] = []
    for block in MANAGED_BLOCKS:
        start_marker = f"<!-- AUTO:{block}:START -->"
        end_marker = f"<!-- AUTO:{block}:END -->"
        start_count = document.count(start_marker)
        end_count = document.count(end_marker)
        if block in required_blocks and (start_count != 1 or end_count != 1):
            raise ValueError(f"{block} must have exactly one marker pair")
        if start_count == 0 and end_count == 0:
            continue
        if start_count != 1 or end_count != 1:
            raise ValueError(f"{block} must have exactly one marker pair")

        start_index = document.index(start_marker)
        end_index = document.index(end_marker)
        token_map[block] = (start_marker, end_marker, start_index, end_index + len(end_marker))
        tokens.append((start_index, start_index + len(start_marker), block, "START", start_marker))
        tokens.append((end_index, end_index + len(end_marker), block, "END", end_marker))

    active_block: str | None = None
    for _, _, block, kind, _ in sorted(tokens):
        if kind == "START":
            if active_block is not None:
                raise ValueError("nested markers are not allowed")
            active_block = block
        else:
            if active_block != block:
                raise ValueError(f"{block} must have exactly one marker pair")
            active_block = None

    if active_block is not None:
        raise ValueError("managed markers must be balanced")

    return token_map


def _render_block(start_marker: str, end_marker: str, replacement: str) -> str:
    normalized = replacement.rstrip("\n")
    if normalized:
        return f"{start_marker}\n{normalized}\n{end_marker}"
    return f"{start_marker}\n{end_marker}"


def _validate_unique_entries(entries: list[ReportEntry]) -> None:
    seen_issue_keys: set[str] = set()
    seen_source_urls: set[str] = set()

    for entry in entries:
        if entry.meta.issue_key in seen_issue_keys:
            raise ValueError(f"duplicate issue_key: {entry.meta.issue_key}")
        seen_issue_keys.add(entry.meta.issue_key)

        canonical_source_url = canonicalize_source_identity(entry.meta.source_url)
        if canonical_source_url in seen_source_urls:
            raise ValueError(f"duplicate source_url: {canonical_source_url}")
        seen_source_urls.add(canonical_source_url)


def _validate_report_path(report_path: str, repo_root: Path, *, reject_existing_target: bool) -> str:
    if "\\" in report_path:
        raise ValueError("report_path must use forward slashes")

    candidate = PurePosixPath(report_path)
    normalized_report_path = candidate.as_posix()
    parts = candidate.parts
    is_under_reports_year = (
        not candidate.is_absolute()
        and normalized_report_path == report_path
        and len(parts) == 3
        and parts[0] == "reports"
        and bool(re.fullmatch(r"\d{4}", parts[1]))
        and candidate.suffix == ".md"
        and all(part not in {"", ".", ".."} for part in parts)
        and parts[2] != "README.md"
    )
    if not is_under_reports_year:
        raise ValueError("report_path must be a normalized POSIX relative path under reports/<year>/...md")

    if reject_existing_target and (repo_root / normalized_report_path).exists():
        raise ValueError(f"report_path already exists: {normalized_report_path}")

    return normalized_report_path


def canonicalize_source_identity(source_url: str) -> str:
    parsed = urlparse(source_url)
    issue_path = parsed.path.removeprefix("/issues/")
    issue_segments = issue_path.split("/")
    if (
        parsed.scheme != "https"
        or parsed.netloc != "wise.readwise.io"
        or not parsed.path.startswith("/issues/")
        or not issue_segments[0]
        or len(issue_segments) not in {1, 2}
        or any(segment for segment in issue_segments[1:] if segment)
    ):
        raise ValueError(f"invalid Wisereads source_url for publication identity: {source_url}")

    canonical_path = f"/issues/{issue_segments[0]}/"
    return parsed._replace(path=canonical_path, params="", query="", fragment="").geturl()


def _render_readme_lines(entries: list[ReportEntry]) -> str:
    return "\n".join(_render_link(entry, include_reports_prefix=True) for entry in entries)


def _render_recent_block(entries: list[ReportEntry]) -> str:
    recent_lines = [_render_link(entry, include_reports_prefix=True) for entry in entries]
    recent_lines.extend(("", "- [完整归档](reports/README.md)"))
    return "\n".join(recent_lines)


def _render_archive(entries: list[ReportEntry]) -> str:
    listing = "\n".join(_render_link(entry, include_reports_prefix=False) for entry in entries)
    if listing:
        return f"{ARCHIVE_HEADER}\n{listing}\n"
    return f"{ARCHIVE_HEADER}\n"


def _render_link(entry: ReportEntry, include_reports_prefix: bool) -> str:
    target = entry.path if include_reports_prefix else entry.path.removeprefix("reports/")
    return f"- [{entry.meta.issue_label}｜{entry.meta.title}]({target})"


if __name__ == "__main__":
    raise SystemExit(main())
