import json
from pathlib import Path
import re

from contracts import parse_inventory, validate_report
from validate_report import main
import pytest

ROOT = Path(__file__).parent
FIXTURES = ROOT / "fixtures"
INVENTORIES = FIXTURES / "inventories"


def inventory():
    path = INVENTORIES / "valid-all-types.json"
    return parse_inventory(path.read_text(encoding="utf-8"), str(path))


def inventory_payload():
    path = INVENTORIES / "valid-all-types.json"
    return json.loads(path.read_text(encoding="utf-8"))


def inventory_from_payload(payload: dict, path: str = "inventory.json"):
    return parse_inventory(json.dumps(payload, ensure_ascii=False), path)


def report(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def report_path(name: str) -> str:
    return str(FIXTURES / name)


def replace_once(text: str, before: str, after: str) -> str:
    assert before in text
    return text.replace(before, after, 1)


def set_item_field(text: str, item_id: str, field: str, value: str) -> str:
    pattern = re.compile(
        rf"(?ms)(<!-- source-item:{re.escape(item_id)} -->.*?^- {re.escape(field)}: )[^\n]+$"
    )
    text, count = pattern.subn(rf"\1{value}", text, count=1)
    assert count == 1
    return text


def set_bias_field(text: str, field: str, value: str) -> str:
    pattern = re.compile(
        rf"(?ms)(## 这份榜单没有告诉我们的.*?^- {re.escape(field)}: )[^\n]+$"
    )
    text, count = pattern.subn(rf"\1{value}", text, count=1)
    assert count == 1
    return text


def test_valid_report_passes_every_gate():
    assert validate_report(report("valid-report.md"), "valid-report.md", inventory()) == []


@pytest.mark.parametrize("minutes", [-5, 0, 14, 21, 999])
def test_report_reading_time_must_stay_within_layered_reading_target(minutes: int):
    text = replace_once(report("valid-report.md"), "reading_time_minutes: 18", f"reading_time_minutes: {minutes}")

    findings = validate_report(text, "invalid-reading-time.md", inventory())

    assert "REPORT_METADATA_INVALID" in {finding.code for finding in findings}


def test_no_ai_report_requires_exact_absence_statement():
    findings = validate_report(report("no-ai-report.md"), "no-ai-report.md", inventory())
    assert "REPORT_AI_ABSENCE" not in {finding.code for finding in findings}


def test_ranked_weak_item_can_receive_negative_quality_judgment():
    findings = validate_report(report("weak-popular-report.md"), "weak-popular-report.md", inventory())
    assert "REPORT_POPULARITY_EQUALS_QUALITY" not in {finding.code for finding in findings}


def test_ebook_ranking_claim_is_rejected():
    findings = validate_report(report("invalid-ebook-claim.md"), "invalid-ebook-claim.md", inventory())
    assert "POSITIONING_EBOOK_RANKING" in {finding.code for finding in findings}


def test_validate_report_cli_uses_inventory_contract_output(capsys):
    exit_code = main(
        [
            "--inventory",
            str(INVENTORIES / "valid-all-types.json"),
            "--report",
            report_path("invalid-ebook-claim.md"),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "POSITIONING_EBOOK_RANKING" in captured.out


def test_validate_report_cli_accepts_valid_report(capsys):
    exit_code = main(
        [
            "--inventory",
            str(INVENTORIES / "valid-all-types.json"),
            "--report",
            report_path("valid-report.md"),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""


def test_validate_report_cli_reports_inventory_parse_error(tmp_path, capsys):
    broken_inventory = tmp_path / "broken.json"
    broken_inventory.write_text("{not json", encoding="utf-8")

    exit_code = main(["--inventory", str(broken_inventory), "--report", report_path("valid-report.md")])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out.startswith(f"PARSE_ERROR {broken_inventory}: malformed JSON")


def test_validate_report_cli_reports_missing_report_file(capsys):
    exit_code = main(
        [
            "--inventory",
            str(INVENTORIES / "valid-all-types.json"),
            "--report",
            str(FIXTURES / "missing-report.md"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out.startswith(f"PARSE_ERROR {FIXTURES / 'missing-report.md'}:")


def test_report_rejects_metadata_identity_mismatch():
    text = replace_once(report("valid-report.md"), 'issue_key: "wisereads-vol-155"', 'issue_key: "wisereads-vol-999"')

    findings = validate_report(text, "metadata-mismatch.md", inventory())

    assert "REPORT_METADATA_INVALID" in {finding.code for finding in findings}


def test_report_rejects_status_count_sum_mismatch():
    text = replace_once(report("valid-report.md"), "sources_partial: 1", "sources_partial: 2")

    findings = validate_report(text, "count-mismatch.md", inventory())

    assert "REPORT_STATUS_COUNT_MISMATCH" in {finding.code for finding in findings}


@pytest.mark.parametrize(
    "alternate_line",
    [
        "",
        "- alternate_url: https://example.com/wrong-alternate\n",
    ],
    ids=("missing", "mismatch"),
)
def test_report_requires_inventory_matching_alternate_url(alternate_line: str):
    text = report("valid-report.md").replace(
        "- alternate_url: https://example.com/pdf-alternate\n",
        alternate_line,
        1,
    )

    findings = validate_report(text, "alternate-url.md", inventory())

    assert "REPORT_ITEM_COVERAGE" in {finding.code for finding in findings}


def test_report_rejects_below_fifty_percent_coverage():
    payload = inventory_payload()
    payload["items"][1]["access_status"] = "PARTIAL"
    downgraded_inventory = inventory_from_payload(payload, "downgraded.json")

    text = report("valid-report.md")
    text = replace_once(text, "sources_full_read: 2", "sources_full_read: 1")
    text = replace_once(text, "sources_partial: 1", "sources_partial: 2")
    text = replace_once(text, "sources_degraded: 4", "sources_degraded: 5")
    text = set_item_field(text, "item-02", "access_status", "PARTIAL")
    text = set_item_field(text, "item-02", "degradation_note", "仅访问到视频片段，缺少完整上下文。")

    findings = validate_report(text, "coverage-below.md", downgraded_inventory)

    assert "REPORT_COVERAGE_BELOW_THRESHOLD" in {finding.code for finding in findings}


def test_report_requires_exact_heading_lines_not_prose_mentions():
    text = report("valid-report.md")
    text = replace_once(text, "## 本期行动建议", "- 这里仅在正文里提到 ## 本期行动建议 这几个字")

    findings = validate_report(text, "fake-heading.md", inventory())

    assert "REPORT_METADATA_INVALID" in {finding.code for finding in findings}


def test_report_rejects_duplicate_required_heading():
    text = report("valid-report.md")
    text = replace_once(
        text,
        "## 来源与证据说明",
        "## 本期行动建议\n\n- 重复标题。\n\n## 来源与证据说明",
    )

    findings = validate_report(text, "duplicate-heading.md", inventory())

    assert "REPORT_METADATA_INVALID" in {finding.code for finding in findings}


def test_report_rejects_missing_anchor():
    text = replace_once(report("valid-report.md"), "<!-- source-item:item-06 -->\n", "")

    findings = validate_report(text, "missing-anchor.md", inventory())

    assert "REPORT_ITEM_COVERAGE" in {finding.code for finding in findings}


def test_report_rejects_duplicate_anchor():
    text = replace_once(report("valid-report.md"), "<!-- source-item:item-06 -->", "<!-- source-item:item-05 -->")

    findings = validate_report(text, "duplicate-anchor.md", inventory())

    assert "REPORT_DUPLICATE_SOURCE" in {finding.code for finding in findings}


def test_report_rejects_duplicate_source_url():
    text = set_item_field(report("valid-report.md"), "item-02", "original_url", "https://example.com/article")

    findings = validate_report(text, "duplicate-url.md", inventory())

    assert "REPORT_DUPLICATE_SOURCE" in {finding.code for finding in findings}


def test_report_rejects_degraded_access_overclaim():
    text = set_item_field(report("valid-report.md"), "item-05", "degradation_note", "已经完整阅读电子书全部内容。")

    findings = validate_report(text, "overclaim.md", inventory())

    assert "REPORT_SUMMARY_OVERCLAIM" in {finding.code for finding in findings}


def test_report_rejects_no_ai_without_exact_sentence():
    text = replace_once(report("no-ai-report.md"), f"- 本期无显著 AI / Agent / 工程信号\n", "")

    findings = validate_report(text, "no-ai-missing.md", inventory())

    assert "REPORT_AI_ABSENCE" in {finding.code for finding in findings}


def test_report_rejects_theme_missing_support_inside_theme_block():
    text = replace_once(
        report("valid-report.md"),
        "- supporting_item_ids: [item-01, item-04]",
        "- supporting_item_ids: []",
    )

    findings = validate_report(text, "theme-missing.md", inventory())

    assert "REPORT_THEME_WITHOUT_SUPPORT" in {finding.code for finding in findings}


def test_report_rejects_theme_with_unknown_support_item():
    text = replace_once(
        report("valid-report.md"),
        "- supporting_item_ids: [item-01, item-04]",
        "- supporting_item_ids: [item-01, item-99]",
    )

    findings = validate_report(text, "theme-unknown.md", inventory())

    assert "REPORT_THEME_WITHOUT_SUPPORT" in {finding.code for finding in findings}


def test_report_rejects_theme_support_outside_theme_block():
    text = report("valid-report.md")
    text = replace_once(text, "- supporting_item_ids: [item-01, item-04]\n", "")
    text = replace_once(
        text,
        "## 本期最值得理解的判断\n\n",
        "## 本期最值得理解的判断\n\n- supporting_item_ids: [item-01, item-04]\n",
    )

    findings = validate_report(text, "theme-outside.md", inventory())

    assert "REPORT_THEME_WITHOUT_SUPPORT" in {finding.code for finding in findings}


def test_report_rejects_generic_bias_structure():
    text = report("valid-report.md")
    before = """## 这份榜单没有告诉我们的

- Readwise 用户样本: 进入本期的样本来自 Readwise 高亮用户已经聚集的阅读集合，天然偏向更易被保存与回看的内容。
- 排序边界: 排名只覆盖文章、视频、线程与公开 PDF 的高亮表现，不覆盖策划纳入电子书，也不等于全网最佳。
- 观察维度: medium, geography, source sample
- supporting_item_ids: [item-03, item-06]
- 观察到的偏差: 可传播媒介与英语公开互联网材料更容易进入本期信号，低传播专业材料更难被看见。
- 缺席声音: 缺少来自非英语研究语境与低传播专业社群的一手补充声音。
- 可能后果: item-06 的缺失会放大“易传播表达”在本期判断中的权重，让结论更像传播结构观察而非全面质量盘点。
"""
    after = """## 这份榜单没有告诉我们的

存在样本偏差。
"""
    text = replace_once(text, before, after)

    findings = validate_report(text, "generic-bias.md", inventory())

    assert "REPORT_BIAS_SECTION_MISSING" in {finding.code for finding in findings}


def test_report_rejects_bias_with_short_generic_filler_values():
    text = set_bias_field(report("valid-report.md"), "观察到的偏差", "略。")

    findings = validate_report(text, "bias-filler.md", inventory())

    assert "REPORT_BIAS_SECTION_MISSING" in {finding.code for finding in findings}


def test_report_rejects_bias_when_all_prose_fields_repeat_same_value():
    text = report("valid-report.md")
    repeated = "同一段偏差说明已经足够具体。"
    for field in ["Readwise 用户样本", "排序边界", "观察到的偏差", "缺席声音", "可能后果"]:
        text = set_bias_field(text, field, repeated)

    findings = validate_report(text, "bias-repeated.md", inventory())

    assert "REPORT_BIAS_SECTION_MISSING" in {finding.code for finding in findings}


def test_report_rejects_bias_with_missing_supporting_ids():
    text = set_bias_field(report("valid-report.md"), "supporting_item_ids", "[]")

    findings = validate_report(text, "bias-missing-support.md", inventory())

    assert "REPORT_BIAS_SECTION_MISSING" in {finding.code for finding in findings}


def test_report_rejects_bias_with_unknown_supporting_ids():
    text = set_bias_field(report("valid-report.md"), "supporting_item_ids", "[item-03, item-99]")

    findings = validate_report(text, "bias-unknown-support.md", inventory())

    assert "REPORT_BIAS_SECTION_MISSING" in {finding.code for finding in findings}


def test_report_rejects_bias_without_concrete_dimension():
    text = set_bias_field(report("valid-report.md"), "观察维度", "综合判断")

    findings = validate_report(text, "bias-no-dimension.md", inventory())

    assert "REPORT_BIAS_SECTION_MISSING" in {finding.code for finding in findings}


def test_report_rejects_missing_independent_quality_judgment():
    text = replace_once(
        report("valid-report.md"),
        "- independent_quality_judgment: 证据充足、结构清晰，但仍只代表一个问题框架。\n",
        "",
    )

    findings = validate_report(text, "missing-quality-field.md", inventory())

    assert "REPORT_ITEM_COVERAGE" in {finding.code for finding in findings}


@pytest.mark.parametrize(
    "phrase",
    [
        "高亮排名越靠前，往往也说明内容质量越好。",
        "排名最靠前的条目通常也是最值得读的。",
        "高亮排名第一的材料往往最真实。",
        "排名越高的条目通常也越可靠。",
        "榜首意味着最值得读。",
        "排名越高并不总是虚假，但通常也越可靠。",
        "高亮靠前，不少人会觉得内容最真实。",
    ],
)
def test_report_rejects_popularity_quality_equivalence_paraphrases(phrase: str):
    text = replace_once(
        report("valid-report.md"),
        "- 高亮热度说明读者注意力，不自动等于事实强度、内容质量或你的适配度。",
        f"- {phrase}",
    )

    findings = validate_report(text, "popularity-paraphrase.md", inventory())

    assert "REPORT_POPULARITY_EQUALS_QUALITY" in {finding.code for finding in findings}


@pytest.mark.parametrize(
    "phrase",
    [
        "排名越高的条目未必越可靠。",
        "榜首并不意味着最值得读。",
        "高亮靠前不代表内容最真实。",
    ],
)
def test_report_allows_popularity_caveat_sentences(phrase: str):
    text = replace_once(
        report("valid-report.md"),
        "- 高亮热度说明读者注意力，不自动等于事实强度、内容质量或你的适配度。",
        f"- {phrase}",
    )

    findings = validate_report(text, "popularity-caveat.md", inventory())

    assert "REPORT_POPULARITY_EQUALS_QUALITY" not in {finding.code for finding in findings}
