import hashlib
import json
from pathlib import Path
import re
from datetime import timezone, timedelta

import pytest

from build_publication import build_publication_plan
from contracts import parse_inventory, validate_inventory, validate_report
from discovery import discover_latest_issue
from publication_runtime import RefSnapshot, run_atomic_publication


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
EVALS = ROOT / "tests" / "evals"
INVENTORIES = FIXTURES / "inventories"


def _inventory(name: str = "valid-all-types.json"):
    path = INVENTORIES / name
    return parse_inventory(path.read_text(encoding="utf-8"), str(path))


def _inventory_payload(name: str = "valid-all-types.json") -> dict:
    return json.loads((INVENTORIES / name).read_text(encoding="utf-8"))


def _report(name: str = "valid-report.md") -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _item_block(text: str, item_id: str) -> str:
    match = re.search(
        rf"(?ms)<!-- source-item:{re.escape(item_id)} -->(.*?)(?=<!-- source-item:item-\d{{2}} -->|^## 这份榜单没有告诉我们的)",
        text,
    )
    assert match is not None, f"missing report block for {item_id}"
    return match.group(1)


def _eval_payload(name: str) -> tuple[str, dict]:
    text = (EVALS / name).read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.DOTALL)
    assert len(blocks) == 1, f"{name} must contain exactly one machine-checkable transcript"
    return text, json.loads(blocks[0])


def _seed_publication_repo(repo: Path, readme: str | None = None) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "README.md").write_text(
        readme
        or (
            "stable\n"
            "<!-- AUTO:LATEST:START -->\nnone\n<!-- AUTO:LATEST:END -->\n"
            "<!-- AUTO:RECENT:START -->\nnone\n<!-- AUTO:RECENT:END -->\n"
        ),
        encoding="utf-8",
    )
    (repo / "reports").mkdir()
    (repo / "reports" / "README.md").write_text("# 报告归档\n", encoding="utf-8")


def _special_report() -> str:
    return """---
title: "Wisereads Special Edition Vol. 2 深度解读"
issue_key: "wisereads-special-vol-2"
issue_kind: "special"
issue_number: 2
issue_label: "Special Edition Vol. 2"
source_url: "https://wise.readwise.io/issues/wisereads-special-vol-2/"
discovered_at: "2026-08-12T11:00:00+08:00"
generated_at: "2026-08-12T12:00:00+08:00"
language: "zh-CN"
reading_time_minutes: 15
sources_total: 1
sources_full_read: 1
sources_partial: 0
sources_alternate: 0
sources_summary_only: 0
sources_unavailable: 0
sources_degraded: 0
---
Special Edition report fixture.
"""


def test_degraded_access_states_are_terminal_and_disclosed_in_the_report():
    inventory = _inventory()
    report = _report()
    by_id = {item.item_id: item for item in inventory.items}

    assert validate_inventory(inventory, "valid-all-types.json", require_terminal=True) == []
    assert by_id["item-03"].access_status == "PARTIAL"
    assert by_id["item-05"].access_status == "SUMMARY_ONLY"
    assert by_id["item-06"].access_status == "UNAVAILABLE"
    assert by_id["item-06"].failure_reason == "Removed before review."

    for item_id, status in (
        ("item-03", "PARTIAL"),
        ("item-05", "SUMMARY_ONLY"),
        ("item-06", "UNAVAILABLE"),
    ):
        block = _item_block(report, item_id)
        assert f"- access_status: {status}" in block
        degradation = re.search(r"(?m)^- degradation_note: (.+)$", block)
        assert degradation is not None
        assert len(degradation.group(1).strip()) >= 8

    assert "不能声称已理解其内容" in _item_block(report, "item-06")


def test_below_half_near_complete_coverage_is_a_hard_finding():
    payload = _inventory_payload()
    payload["items"][1]["access_status"] = "PARTIAL"
    inventory = parse_inventory(json.dumps(payload, ensure_ascii=False), "coverage-below.json")

    report = _report()
    report = report.replace("sources_full_read: 2", "sources_full_read: 1", 1)
    report = report.replace("sources_partial: 1", "sources_partial: 2", 1)
    report = report.replace("sources_degraded: 4", "sources_degraded: 5", 1)
    item_two = _item_block(report, "item-02")
    replacement = item_two.replace("- access_status: FULL", "- access_status: PARTIAL", 1).replace(
        "- degradation_note: 无；原视频可直接完整访问。",
        "- degradation_note: 只复核到公开视频片段，完整上下文不可得。",
        1,
    )
    report = report.replace(item_two, replacement, 1)

    findings = validate_report(report, "coverage-below.md", inventory)

    assert (1 + 1) / 6 < 0.50
    assert "REPORT_COVERAGE_BELOW_THRESHOLD" in {finding.code for finding in findings}


def test_special_edition_uses_special_filename_and_observed_identity_for_dedupe(tmp_path: Path):
    inventory = _inventory("valid-special-edition.json")
    discovered_in_beijing = inventory.discovered_at.astimezone(timezone(timedelta(hours=8)))
    identity_slug = f"special-vol-{inventory.issue_number}"
    report_path = f"reports/{discovered_in_beijing:%Y}/{discovered_in_beijing:%Y-%m-%d}-{identity_slug}.md"

    assert inventory.issue_kind == "special"
    assert inventory.issue_key == "wisereads-special-vol-2"
    assert inventory.source_url == "https://wise.readwise.io/issues/wisereads-special-vol-2/"
    assert report_path == "reports/2026/2026-08-12-special-vol-2.md"

    fresh_repo = tmp_path / "fresh"
    _seed_publication_repo(fresh_repo)
    plan = build_publication_plan(fresh_repo, report_path, _special_report())
    assert plan.issue_key == inventory.issue_key
    assert report_path in plan.files

    duplicate_repo = tmp_path / "duplicate"
    _seed_publication_repo(duplicate_repo)
    existing = duplicate_repo / "reports" / "2026" / "2026-08-11-special-vol-2.md"
    existing.parent.mkdir(parents=True)
    existing.write_text(_special_report(), encoding="utf-8")

    duplicate = build_publication_plan(duplicate_repo, report_path, _special_report())
    assert duplicate.issue_key == "wisereads-special-vol-2"
    assert duplicate.files == {}

    with pytest.raises(
        ValueError,
        match="canonical report_path is reports/2026/2026-08-12-special-vol-2.md",
    ):
        build_publication_plan(
            fresh_repo,
            "reports/2026/2026-08-12-vol-2.md",
            _special_report(),
        )


@pytest.mark.parametrize(
    "readme",
    [
        (
            "<!-- AUTO:LATEST:END -->\n"
            "<!-- AUTO:RECENT:START -->\nnone\n<!-- AUTO:RECENT:END -->\n"
        ),
        (
            "<!-- AUTO:LATEST:START -->\n"
            "<!-- AUTO:LATEST:START -->\nnone\n<!-- AUTO:LATEST:END -->\n"
            "<!-- AUTO:RECENT:START -->\nnone\n<!-- AUTO:RECENT:END -->\n"
        ),
    ],
    ids=("missing-marker", "duplicate-marker"),
)
def test_missing_or_duplicate_readme_markers_prevent_a_publication_plan(tmp_path: Path, readme: str):
    _seed_publication_repo(tmp_path, readme)

    with pytest.raises(ValueError, match="LATEST must have exactly one marker pair"):
        build_publication_plan(
            tmp_path,
            "reports/2026/2026-08-12-special-vol-2.md",
            _special_report(),
        )


def test_task7_no_ai_emergent_theme_and_popular_but_weak_green_outcomes_are_retained():
    inventory = _inventory()
    no_ai = _report("no-ai-report.md")
    emergent = _report("valid-report.md")
    popular_but_weak = _report("weak-popular-report.md")
    baseline = (EVALS / "baseline-results.md").read_text(encoding="utf-8")

    no_ai_codes = {finding.code for finding in validate_report(no_ai, "no-ai-report.md", inventory)}
    emergent_codes = {finding.code for finding in validate_report(emergent, "valid-report.md", inventory)}
    popular_codes = {
        finding.code for finding in validate_report(popular_but_weak, "weak-popular-report.md", inventory)
    }

    assert "本期无显著 AI / Agent / 工程信号" in no_ai
    assert "REPORT_AI_ABSENCE" not in no_ai_codes
    assert "### 主题：证据迁移成本" in emergent
    assert "- supporting_item_ids: [item-01, item-04]" in emergent
    assert "REPORT_THEME_WITHOUT_SUPPORT" not in emergent_codes
    assert "中等质量、证据不够扎实" in popular_but_weak
    assert "REPORT_POPULARITY_EQUALS_QUALITY" not in popular_codes
    assert baseline.count("## GREEN with the Skill") == 1
    assert "It kept the exact sentence `本期无显著 AI / Agent / 工程信号`" in baseline
    assert "rejected “#1 = best”" in baseline


def test_paywall_and_dead_link_eval_preserves_narrow_claims_and_terminal_states():
    text, payload = _eval_payload("paywall-and-dead-link.md")

    assert payload["network_calls"] == 0
    assert [card["access_status"] for card in payload["source_cards"]] == [
        "PARTIAL",
        "SUMMARY_ONLY",
        "UNAVAILABLE",
    ]
    assert all(card["degradation_note"] for card in payload["source_cards"])
    assert payload["source_cards"][2]["allowed_claim"] == "只能确认原始链接在本次评估中不可用。"
    assert payload["source_cards"][2]["forbidden_claim"] == "该文完整论证了某个观点。"
    assert payload["tree_digest_before"] == payload["tree_digest_after"]
    assert payload["tree_digest_before"] == hashlib.sha256(payload["synthetic_tree"].encode()).hexdigest()
    assert "None may be upgraded to `FULL`" in text


def test_unrecognized_homepage_eval_blocks_before_inventory_without_tree_change():
    _, payload = _eval_payload("homepage-structure-change.md")

    result = discover_latest_issue(payload["synthetic_homepage"])

    assert result.state == payload["state"] == "BLOCKED_DISCOVERY_STRUCTURE"
    assert result.issue is None
    assert payload["inventory_created"] is False
    assert payload["events"] == ["homepage_opened", "structure_unrecognized", "stop_without_write"]
    assert payload["tree_digest_before"] == payload["tree_digest_after"]
    assert payload["tree_digest_before"] == hashlib.sha256(payload["synthetic_tree"].encode()).hexdigest()
    assert payload["network_calls"] == 0


def test_main_race_eval_rebuilds_once_then_blocks_without_ref_move():
    _, payload = _eval_payload("main-race.md")

    class FakeConnector:
        def __init__(self):
            self._snapshots = iter(
                RefSnapshot(commit_sha=sha, tree_sha=f"tree-{index}")
                for index, sha in enumerate(payload["observed_main_shas"], start=1)
            )
            self.calls = []

        def read_main(self):
            snapshot = next(self._snapshots)
            self.calls.append(("read_main", snapshot.commit_sha))
            return snapshot

        def identity_exists(self, snapshot, issue_key, source_url):
            self.calls.append(("identity_exists", snapshot.commit_sha))
            return False

        def create_blob(self, path, content):
            self.calls.append(("create_blob", path))
            return f"blob-{path}"

        def create_tree(self, base_tree_sha, blobs):
            self.calls.append(("create_tree", base_tree_sha, tuple(sorted(blobs))))
            return f"new-{base_tree_sha}"

        def create_commit(self, parent_sha, tree_sha):
            self.calls.append(("create_commit", parent_sha, tree_sha))
            return f"commit-{parent_sha}"

        def update_main(self, commit_sha, *, force):
            self.calls.append(("update_main", commit_sha, force))

        def verify(self, commit_sha, plan):
            self.calls.append(("verify", commit_sha))
            return True

    connector = FakeConnector()
    rebuild_bases = []

    def build(base):
        rebuild_bases.append(base.commit_sha)
        return type("Plan", (), {
            "issue_key": "wisereads-vol-156",
            "source_url": "https://wise.readwise.io/issues/wisereads-vol-156/",
            "files": {"README.md": "r", "reports/README.md": "a", "reports/2026/x.md": "x"},
        })()

    result = run_atomic_publication(connector, build)

    assert payload["observed_main_shas"] == [
        "1111111111111111111111111111111111111111",
        "2222222222222222222222222222222222222222",
        "3333333333333333333333333333333333333333",
    ]
    assert payload["actions"] == ["build", "rebuild_once", "block"]
    assert rebuild_bases == payload["observed_main_shas"][:2]
    assert result.rebuild_count == payload["rebuild_count"] == 1
    assert result.state == payload["state"] == "BLOCKED_CONCURRENT_UPDATE"
    assert sum(call[0] == "update_main" for call in connector.calls) == payload["ref_move_calls"] == 0
    assert sum(call[0] == "create_blob" for call in connector.calls) == 6
    assert sum(call[0] == "create_tree" for call in connector.calls) == 2
    assert sum(call[0] == "create_commit" for call in connector.calls) == 2
    assert payload["tree_digest_before"] == payload["tree_digest_after"]
    assert payload["network_calls"] == 0
