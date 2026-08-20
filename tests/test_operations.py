from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
TASK_NAME = "Weekly Wisereads 深度解读"
TIMEZONE = "Asia/Shanghai"
DTSTART = "20260817T100000"
RRULE = "FREQ=WEEKLY;BYDAY=MO;BYHOUR=10;BYMINUTE=0"
REPOSITORY = "geekjourneyx/weekly-wisereads"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _correction_staging_script() -> str:
    runbook = _read("docs/operations/release-and-rollback.md")
    match = re.search(
        r"<!-- CORRECTION:STAGE:START -->\n\s*```bash\n(.*?)\n\s*```",
        runbook,
        re.DOTALL,
    )
    assert match, "correction staging script must be a marked bash block"
    return match.group(1)


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        text=True,
        capture_output=True,
    )


def _correction_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    report_dir = repo / "reports" / "2026"
    report_dir.mkdir(parents=True)
    (repo / "README.md").write_text("root\n", encoding="utf-8")
    (repo / "notes.txt").write_text("unrelated\n", encoding="utf-8")
    (repo / "reports" / "README.md").write_text("archive\n", encoding="utf-8")
    (report_dir / "2026-08-12-vol-155.md").write_text("original\n", encoding="utf-8")
    (report_dir / "2026-08-19-vol-156.md").write_text("original\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Operations Test")
    _git(repo, "config", "user.email", "operations@example.invalid")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "fixture")
    return repo


def _run_correction_staging(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", _correction_staging_script()],
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    )


def test_scheduled_task_runbook_records_live_configuration_and_prompt_checksum():
    runbook = _read("docs/operations/scheduled-task.md")
    prompt = _read("skills/weekly-wisereads/references/scheduled-prompt.md").replace("\r\n", "\n")
    checksum = sha256(prompt.encode("utf-8")).hexdigest()

    for value in (
        TASK_NAME,
        TIMEZONE,
        DTSTART,
        RRULE,
        REPOSITORY,
        checksum,
    ):
        assert value in runbook
    assert "Task identifier: private" in runbook
    assert "Configuration audited: `2026-08-20`" in runbook
    assert not re.search(r"\b[0-9a-f]{32}\b", runbook)
    assert re.search(r"Preflight dry run: `2026-[^`]+`", runbook)
    assert "Ownership: repository administrators and the private Scheduled task owner" in runbook
    assert "First live execution: `2026-08-17T10:00:00+08:00`" in runbook
    assert "stale cached homepage" in runbook
    assert "BLOCKED_DISCOVERY_STALE" in runbook
    assert "it is not represented as a run of the newly created task" in runbook
    for field in ("Changed files", "degraded sources", "Unresolved risk", "issue label and URL"):
        assert field in runbook
    for placeholder in ("TODO", "TBD", "<task-id>", "REPLACE_ME"):
        assert placeholder not in runbook


def test_release_runbook_documents_every_terminal_family_and_forward_fix():
    runbook = _read("docs/operations/release-and-rollback.md")
    normalized = runbook.lower()

    for state in (
        "PUBLISHED",
        "NOOP_ALREADY_PROCESSED",
        "NOOP_AFTER_RACE",
        "BLOCKED_*",
        "FAILED_*",
        "PUBLISHED_UNVERIFIED",
    ):
        assert state in runbook
    for rule in (
        "exactly one rebuild",
        "never force-push",
        "never delete a historical report",
        "GitHub permission loss",
        "forward-fix",
        "report plus both indexes as one correction consistency set",
    ):
        assert rule.lower() in normalized
    assert "NOOP_NO_NEW_ISSUE" not in runbook
    assert "new-report publication runtime is not a correction tool" in runbook
    assert "set -euo pipefail" in runbook
    assert 'test -z "$(git diff --cached --name-only)"' in runbook
    assert 'report_path="$(git diff --name-only --diff-filter=M' in runbook
    assert 'test -f "$report_path"' in runbook
    assert 'git add -- "$report_path" README.md reports/README.md' in runbook
    assert 'staged_paths="$(git diff --cached --name-only)"' in runbook


def test_plan_records_result_state_reconciliation_against_runtime_authority():
    plan = _read("docs/superpowers/plans/2026-08-12-weekly-wisereads.md")

    assert "Implementation reconciliation — 2026-08-12" in plan
    assert "no distinct observable condition" in plan
    assert "This note supersedes that state in Steps 3 and 4" in plan
    assert "public runbook records the audited configuration and date only" in plan
    assert "requirements in Steps 1, 3, 5 and 7" in plan


def test_canonical_prompt_has_all_scheduled_safety_boundaries():
    prompt = _read("skills/weekly-wisereads/references/scheduled-prompt.md")

    for rule in (
        "$weekly-wisereads",
        "python skills/weekly-wisereads/scripts/discovery.py",
        "BLOCKED_DISCOVERY_STALE",
        "不得将网页工具、搜索结果或中间缓存",
        "只有实时发现成功后才能去重",
        "实时首页第一期",
        "不得发明独立高亮人数",
        "私人 Readwise 数据",
        "不得写入 `geekjourneyx/weekly-wisereads` 之外的仓库",
        "不得创建 Issue、Pull Request、Release、Discussion",
        "不得 force update",
        "不得修改根 README 的 `AUTO:LATEST` 与 `AUTO:RECENT` 区块之外内容",
    ):
        assert rule in prompt


def test_skill_requires_fresh_origin_discovery_before_deduplication():
    skill = _read("skills/weekly-wisereads/SKILL.md")

    for rule in (
        "python skills/weekly-wisereads/scripts/discovery.py",
        "BLOCKED_DISCOVERY_STALE",
        "Do not deduplicate until live discovery returns `DISCOVERED`",
        "Cached browser, web-search, or intermediary results are auxiliary only",
    ):
        assert rule in skill


def test_agent_rules_allow_reviewed_forward_fixes_without_history_rewrites():
    instructions = _read("AGENTS.md")

    assert "delete or rename a historical report" in instructions
    assert "rewrite Git history" in instructions
    assert "reviewed forward-fix" in instructions
    assert "rewrite a historical report" not in instructions


def test_correction_staging_accepts_exactly_one_modified_existing_report(tmp_path):
    repo = _correction_repo(tmp_path)
    report = repo / "reports" / "2026" / "2026-08-12-vol-155.md"
    report.write_text("corrected\n", encoding="utf-8")

    result = _run_correction_staging(repo)

    assert result.returncode == 0, result.stderr
    assert _git(repo, "diff", "--cached", "--name-only").stdout.splitlines() == [
        "reports/2026/2026-08-12-vol-155.md"
    ]


def test_correction_staging_rejects_zero_or_multiple_reports_without_staging(tmp_path):
    zero = _correction_repo(tmp_path / "zero")
    zero_result = _run_correction_staging(zero)
    assert zero_result.returncode != 0
    assert _git(zero, "diff", "--cached", "--name-only").stdout == ""

    multiple = _correction_repo(tmp_path / "multiple")
    for name in ("2026-08-12-vol-155.md", "2026-08-19-vol-156.md"):
        (multiple / "reports" / "2026" / name).write_text("corrected\n", encoding="utf-8")
    multiple_result = _run_correction_staging(multiple)
    assert multiple_result.returncode != 0
    assert _git(multiple, "diff", "--cached", "--name-only").stdout == ""


def test_correction_staging_rejects_deleted_or_renamed_report_without_staging(tmp_path):
    deleted = _correction_repo(tmp_path / "deleted")
    (deleted / "reports" / "2026" / "2026-08-12-vol-155.md").unlink()
    deleted_result = _run_correction_staging(deleted)
    assert deleted_result.returncode != 0
    assert _git(deleted, "diff", "--cached", "--name-only").stdout == ""

    renamed = _correction_repo(tmp_path / "renamed")
    old = renamed / "reports" / "2026" / "2026-08-12-vol-155.md"
    old.rename(renamed / "reports" / "2026" / "renamed.md")
    renamed_result = _run_correction_staging(renamed)
    assert renamed_result.returncode != 0
    assert _git(renamed, "diff", "--cached", "--name-only").stdout == ""


def test_correction_staging_rejects_pre_staged_unrelated_change_without_mutating_index(tmp_path):
    repo = _correction_repo(tmp_path)
    (repo / "notes.txt").write_text("already staged\n", encoding="utf-8")
    _git(repo, "add", "notes.txt")
    (repo / "reports" / "2026" / "2026-08-12-vol-155.md").write_text(
        "corrected\n", encoding="utf-8"
    )
    staged_before = _git(repo, "diff", "--cached", "--name-only").stdout

    result = _run_correction_staging(repo)

    assert result.returncode != 0
    assert _git(repo, "diff", "--cached", "--name-only").stdout == staged_before
    assert staged_before.splitlines() == ["notes.txt"]


def test_correction_staging_rejects_pre_staged_report_deletion_without_mutating_index(tmp_path):
    repo = _correction_repo(tmp_path)
    deleted = repo / "reports" / "2026" / "2026-08-12-vol-155.md"
    deleted.unlink()
    _git(repo, "add", "--", deleted.relative_to(repo).as_posix())
    (repo / "reports" / "2026" / "2026-08-19-vol-156.md").write_text(
        "corrected\n", encoding="utf-8"
    )
    staged_before = _git(repo, "diff", "--cached", "--name-only").stdout

    result = _run_correction_staging(repo)

    assert result.returncode != 0
    assert _git(repo, "diff", "--cached", "--name-only").stdout == staged_before
    assert staged_before.splitlines() == ["reports/2026/2026-08-12-vol-155.md"]
