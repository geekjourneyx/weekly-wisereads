from __future__ import annotations

import json
from pathlib import Path
import re
import shutil

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "skills" / "weekly-wisereads" / "references"

EXPECTED_CONTENT_TYPES = {
    "article",
    "youtube",
    "tweet-thread",
    "pdf",
    "ebook",
    "other",
}
EXPECTED_SELECTION_BASES = {
    "highlight-ranked",
    "curated-or-partnered-ebook",
    "page-stated-other",
}
EXPECTED_ACCESS_STATUSES = {
    "FULL",
    "PARTIAL",
    "ALTERNATE",
    "SUMMARY_ONLY",
    "UNAVAILABLE",
}
EXPECTED_JUDGMENT_LABELS = {"已证实", "作者观点", "项目推断", "待验证"}
EXPECTED_NO_AI_SENTENCE = "本期无显著 AI / Agent / 工程信号"
EXPECTED_ISSUE_KEYS = {
    "issue_key",
    "issue_kind",
    "issue_number",
    "issue_label",
    "source_url",
    "discovered_at",
    "detail_page_item_count",
}
EXPECTED_ITEM_KEYS = {
    "item_id",
    "position",
    "title",
    "creator",
    "original_url",
    "content_type",
    "selection_basis",
    "access_status",
    "alternate_url",
    "failure_reason",
}
EXPECTED_SOURCE_CARD_KEYS = {
    "item_id",
    "core_claim",
    "argument_chain",
    "evidence",
    "assumptions",
    "counter_explanations",
    "highlight_reason",
    "popularity_quality_alignment",
    "candidate_themes",
    "professional_lens",
    "long_term_lens",
    "editorial_level",
    "report_takeaways",
}
EXPECTED_SYNTHESIS_KEYS = {
    "themes",
    "attention_signal",
    "quality_vs_popularity_findings",
    "absent_perspectives",
    "ai_signal",
    "professional_opportunities",
    "long_term_views",
    "focus_item_ids",
}
EXPECTED_REPORT_SECTIONS = [
    "## 30 秒看懂本期",
    "## 本周集体阅读信号",
    "## 本期最值得理解的判断",
    "## 本期最值得反复思考的观点",
    "## 重点文章深拆",
    "## 专业与机会观察（如有）",
    "## 全部条目阅读笔记",
    "## 这份榜单没有告诉我们的",
    "## 本期行动建议",
    "## 来源与证据说明",
]
EXPECTED_BIAS_KEYS = {
    "Readwise 用户样本",
    "排序边界",
    "观察维度",
    "supporting_item_ids",
    "观察到的偏差",
    "缺席声音",
    "可能后果",
}


def read(name: str, refs_dir: Path = REFS) -> str:
    return (refs_dir / name).read_text(encoding="utf-8")


def extract_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"(?ms)^{re.escape(heading)}\n(.*?)(?=^#{{1,6}}\s|\Z)")
    match = pattern.search(text)
    assert match, f"missing section {heading}"
    return match.group(1).strip()


def extract_bullet_block(text: str, label: str) -> list[str]:
    pattern = re.compile(rf"(?m)^{re.escape(label)}\n\n((?:- [^\n]*(?:\n|$))+)")
    match = pattern.search(text)
    assert match, f"missing bullet block {label}"
    return [line[2:].strip() for line in match.group(1).splitlines() if line.startswith("- ")]


def extract_fenced_block(text: str, language: str) -> str:
    pattern = re.compile(rf"(?ms)```{re.escape(language)}\n(.*?)\n```")
    match = pattern.search(text)
    assert match, f"missing {language} code block"
    return match.group(1)


def bullet_lines(section_text: str) -> list[str]:
    return [line[2:].strip() for line in section_text.splitlines() if line.startswith("- ")]


def validate_inventory_contract(text: str) -> None:
    purpose = extract_section(text, "## Purpose")
    assert "must not store" in purpose and "SourceCard" in purpose and "IssueSynthesis" in purpose, (
        "inventory must forbid persisted source text and analysis artifacts"
    )

    content_type_values = {
        value
        for line in bullet_lines(extract_section(text, "### `content_type`"))
        for value in re.findall(r"`([^`]+)`", line)
    }
    assert content_type_values == EXPECTED_CONTENT_TYPES, "inventory content types must match the stable contract"

    selection_basis_values = {
        value
        for line in bullet_lines(extract_section(text, "### `selection_basis`"))
        for value in re.findall(r"`([^`]+)`", line)
    }
    assert selection_basis_values == EXPECTED_SELECTION_BASES, "inventory selection bases must match the stable contract"
    assert "`ebook` items must use `curated-or-partnered-ebook`." in text, (
        "inventory must route ebooks to curated-or-partnered-ebook"
    )

    discovery_rules = set(extract_bullet_block(text, "During discovery:"))
    assert "`access_status` may be `null`" in discovery_rules, (
        "inventory discovery state must allow access_status null"
    )
    assert "`alternate_url` must be `null`" in discovery_rules, (
        "inventory discovery state must keep alternate_url null"
    )
    assert "`failure_reason` must be `null`" in discovery_rules, (
        "inventory discovery state must keep failure_reason null"
    )

    terminal_rules = extract_bullet_block(
        text,
        "During or after research completion, every item must be terminal:",
    )
    terminal_statuses = {
        value for value in re.findall(r"`([^`]+)`", terminal_rules[0]) if value in EXPECTED_ACCESS_STATUSES
    }
    assert terminal_statuses == EXPECTED_ACCESS_STATUSES, (
        "inventory terminal rules must enumerate every access status"
    )
    assert "`null` is forbidden once discovery is frozen and reading begins" in set(terminal_rules), (
        "inventory terminal rules must forbid null access_status after discovery"
    )

    state_invariants = set(extract_bullet_block(text, "State-specific invariants:"))
    assert "`ALTERNATE` requires a non-null `alternate_url`" in state_invariants, (
        "inventory ALTERNATE state must require alternate_url"
    )
    assert "`UNAVAILABLE` requires a non-null `failure_reason`" in state_invariants, (
        "inventory UNAVAILABLE state must require failure_reason"
    )

    fail_closed_rules = set(
        extract_bullet_block(
            text,
            "The inventory is invalid and cannot proceed to synthesis if any of the following occur:",
        )
    )
    assert "`ebook` paired with any selection basis other than `curated-or-partnered-ebook`" in fail_closed_rules, (
        "inventory must fail closed when an ebook uses the wrong selection basis"
    )
    assert "an item remains with `access_status: null` after research completion" in fail_closed_rules, (
        "inventory must fail closed when a terminal item keeps null access_status"
    )

    example = json.loads(extract_fenced_block(extract_section(text, "## Compact example"), "json"))
    assert example["schema_version"] == 1
    assert set(example["issue"]) == EXPECTED_ISSUE_KEYS, "inventory example issue keys must stay stable"
    assert len(example["items"]) == 1
    assert set(example["items"][0]) == EXPECTED_ITEM_KEYS, "inventory example item keys must stay metadata-only"
    assert example["items"][0]["content_type"] in EXPECTED_CONTENT_TYPES
    assert example["items"][0]["selection_basis"] in EXPECTED_SELECTION_BASES
    assert example["items"][0]["alternate_url"] is None
    assert example["items"][0]["failure_reason"] is None


def validate_analysis_method(text: str) -> None:
    assert text.index("## SourceCard") < text.index("## IssueSynthesis"), (
        "analysis must define SourceCard before IssueSynthesis"
    )
    assert "全部条目进入终态后" in text, "analysis must keep the terminal-card join barrier"

    source_card = yaml.safe_load(extract_fenced_block(extract_section(text, "## SourceCard"), "yaml"))
    assert set(source_card) == EXPECTED_SOURCE_CARD_KEYS, "SourceCard example keys must stay stable"
    assert source_card["item_id"] == "item-01"
    assert source_card["evidence"][0]["judgment_label"] == "confirmed|author-view|project-inference|to-verify"
    assert source_card["highlight_reason"]["judgment_label"] == "project-inference"

    issue_synthesis = yaml.safe_load(extract_fenced_block(extract_section(text, "## IssueSynthesis"), "yaml"))
    assert set(issue_synthesis) == EXPECTED_SYNTHESIS_KEYS, "IssueSynthesis example keys must stay stable"
    assert issue_synthesis["themes"][0]["supporting_item_ids"], (
        "issue synthesis example must keep supporting_item_ids non-empty"
    )
    assert issue_synthesis["themes"][0]["supporting_item_ids"] == ["item-01"]
    assert set(issue_synthesis["absent_perspectives"][0]) == {
        "dimension",
        "observed_skew",
        "missing_voice",
        "consequence",
    }, "issue synthesis example must define issue-specific missing perspective fields"
    assert issue_synthesis["focus_item_ids"] == ["item-01"]
    assert issue_synthesis["ai_signal"] == "significant|none"

    synthesis_rules = set(bullet_lines(extract_section(text, "### IssueSynthesis rules")))
    assert "every theme must include non-empty `supporting_item_ids`" in synthesis_rules, (
        "analysis must require non-empty supporting_item_ids"
    )
    assert (
        "`absent_perspectives` must capture issue-specific bias, missing voices, and the consequences of that skew for interpretation"
        in synthesis_rules
    ), "analysis must require issue-specific missing perspectives"

    ai_lens = extract_section(text, "## AI lens and absence handling")
    assert f"`{EXPECTED_NO_AI_SENTENCE}`" in ai_lens, "analysis must require the exact no-AI sentence"

    degradation_rules = set(bullet_lines(extract_section(text, "## Degradation and evidence discipline")))
    assert (
        "No source text cache, full transcript mirror, or quotation archive may be stored in the repository as part of this method"
        in degradation_rules
    ), "analysis must forbid persisted source text"


def validate_evidence_policy(text: str) -> None:
    assert "访问状态不等于判断类型" in text, "evidence policy must keep access and judgment orthogonal"

    access_statuses = {
        value
        for line in extract_bullet_block(extract_section(text, "## Access statuses"), "Allowed terminal access statuses:")
        for value in re.findall(r"`([^`]+)`", line)
    }
    assert access_statuses == EXPECTED_ACCESS_STATUSES, (
        "evidence policy must enumerate every terminal access status"
    )

    judgment_labels = {
        value
        for line in extract_bullet_block(
            extract_section(text, "## Judgment labels"),
            "Every evidence statement uses one of four judgment labels:",
        )
        for value in re.findall(r"\*\*([^*]+)\*\*", line)
    }
    assert judgment_labels == EXPECTED_JUDGMENT_LABELS, (
        "evidence policy must enumerate every judgment label"
    )


def validate_report_template(text: str) -> None:
    fixed_match = re.search(r"## Fixed section order\n\n```markdown\n(.*?)\n```", text, flags=re.DOTALL)
    assert fixed_match, "report template must include a markdown code block for fixed section order"
    fixed_order = fixed_match.group(1).splitlines()
    assert fixed_order == EXPECTED_REPORT_SECTIONS, "report template must keep the fixed level-2 section order stable"

    assert "## Theme entry shape" in text, "missing section ## Theme entry shape"
    theme_match = re.search(r"## Theme entry shape\n\n.*?```markdown\n(.*?)\n```", text, flags=re.DOTALL)
    assert theme_match, "report template must define a markdown code block for theme entry shape"
    theme_shape = theme_match.group(1)
    assert "### 主题：" in theme_shape, "report template must define a deterministic level-3 theme heading shape"
    assert "- supporting_item_ids: [item-01]" in theme_shape, (
        "report template must require a bracketed supporting_item_ids field per theme"
    )
    assert theme_shape.count("supporting_item_ids") == 1, (
        "report template must keep exactly one supporting_item_ids field in the theme example"
    )

    assert "## Bias section shape" in text, "missing section ## Bias section shape"
    bias_match = re.search(r"## Bias section shape\n\n.*?```markdown\n(.*?)\n```", text, flags=re.DOTALL)
    assert bias_match, "report template must define a markdown code block for bias section shape"
    bias_shape = bias_match.group(1)
    assert "- supporting_item_ids: [item-02]" in bias_shape, (
        "report template bias section must require bracketed supporting_item_ids"
    )
    assert "- 观察维度: medium, creator, geography" in bias_shape, (
        "report template must document concrete bias dimensions"
    )
    bias_keys = {key for key, _ in re.findall(r"^- ([^:\n]+):\s*(.+)$", bias_shape, flags=re.MULTILINE)}
    assert bias_keys == EXPECTED_BIAS_KEYS, "report template bias section must define the exact structural fields"
    assert "至少 6 个非标点字符" in text, "report template must document the conservative minimum for bias prose"
    assert "略/未知/待补充/无/存在偏差" in text, "report template must document rejected generic bias fillers"
    assert "medium/creator/geography/language/profession/source sample" in text, (
        "report template must document concrete bias dimensions"
    )
    assert "存在样本偏差。" not in bias_shape, "report template bias example must not degrade to a generic sentence"

    assert "## Source item block" in text, "missing section ## Source item block"
    source_match = re.search(r"## Source item block\n\n.*?```markdown\n(.*?)\n```", text, flags=re.DOTALL)
    assert source_match, "report template must define a markdown code block for the source item block"
    source_item = source_match.group(1)
    assert "- independent_quality_judgment: ..." in source_item, (
        "report template must require independent_quality_judgment per source item"
    )


def validate_reference_set(refs_dir: Path) -> None:
    validate_inventory_contract(read("inventory-contract.md", refs_dir))
    validate_analysis_method(read("analysis-method.md", refs_dir))
    validate_evidence_policy(read("evidence-policy.md", refs_dir))
    validate_report_template(read("report-template.md", refs_dir))


def mutate_reference(tmp_path: Path, filename: str, before: str, after: str) -> Path:
    refs_dir = tmp_path / "references"
    shutil.copytree(REFS, refs_dir)
    path = refs_dir / filename
    original = path.read_text(encoding="utf-8")
    assert before in original, f"mutation precondition missing in {filename}: {before!r}"
    path.write_text(original.replace(before, after, 1), encoding="utf-8")
    return refs_dir


def test_inventory_contract_binds_terminal_state_and_storage_rules(tmp_path: Path):
    validate_inventory_contract(read("inventory-contract.md"))

    cases = [
        (
            "- `access_status` may be `null`\n",
            "",
            "inventory discovery state must allow access_status null",
        ),
        (
            "- `null` is forbidden once discovery is frozen and reading begins\n",
            "",
            "inventory terminal rules must forbid null access_status after discovery",
        ),
        (
            "- `ALTERNATE` requires a non-null `alternate_url`\n",
            "",
            "inventory ALTERNATE state must require alternate_url",
        ),
        (
            "- `UNAVAILABLE` requires a non-null `failure_reason`\n",
            "",
            "inventory UNAVAILABLE state must require failure_reason",
        ),
        (
            "`ebook` items must use `curated-or-partnered-ebook`. They must never be labeled `highlight-ranked`.",
            "`ebook` items may use any listed selection basis.",
            "inventory must route ebooks to curated-or-partnered-ebook",
        ),
    ]

    for before, after, message in cases:
        refs_dir = mutate_reference(tmp_path, "inventory-contract.md", before, after)
        with pytest.raises(AssertionError, match=re.escape(message)):
            validate_inventory_contract(read("inventory-contract.md", refs_dir))
        shutil.rmtree(refs_dir)


def test_analysis_method_binds_synthesis_ai_and_storage_rules(tmp_path: Path):
    validate_analysis_method(read("analysis-method.md"))

    cases = [
        (
            "supporting_item_ids: [item-01]",
            "supporting_item_ids: []",
            "issue synthesis example must keep supporting_item_ids non-empty",
        ),
        (
            f"`{EXPECTED_NO_AI_SENTENCE}`",
            "`本期未发现明显 AI 信号`",
            "analysis must require the exact no-AI sentence",
        ),
        (
            "`absent_perspectives` must capture issue-specific bias, missing voices, and the consequences of that skew for interpretation",
            "`absent_perspectives` may describe missing voices",
            "analysis must require issue-specific missing perspectives",
        ),
        (
            "- No source text cache, full transcript mirror, or quotation archive may be stored in the repository as part of this method\n",
            "",
            "analysis must forbid persisted source text",
        ),
    ]

    for before, after, message in cases:
        refs_dir = mutate_reference(tmp_path, "analysis-method.md", before, after)
        with pytest.raises(AssertionError, match=re.escape(message)):
            validate_analysis_method(read("analysis-method.md", refs_dir))
        shutil.rmtree(refs_dir)


def test_evidence_policy_keeps_access_and_judgment_orthogonal(tmp_path: Path):
    validate_evidence_policy(read("evidence-policy.md"))

    cases = [
        (
            "访问状态不等于判断类型。",
            "访问状态决定判断类型。",
            "evidence policy must keep access and judgment orthogonal",
        ),
        (
            "- **待验证**: the statement is plausible or contextually important, but could not yet be confirmed\n",
            "",
            "evidence policy must enumerate every judgment label",
        ),
    ]

    for before, after, message in cases:
        refs_dir = mutate_reference(tmp_path, "evidence-policy.md", before, after)
        with pytest.raises(AssertionError, match=re.escape(message)):
            validate_evidence_policy(read("evidence-policy.md", refs_dir))
        shutil.rmtree(refs_dir)


def test_report_template_binds_theme_bias_and_item_shapes(tmp_path: Path):
    validate_report_template(read("report-template.md"))

    cases = [
        (
            "## Theme entry shape",
            "## Theme shape",
            "missing section ## Theme entry shape",
        ),
        (
            "- supporting_item_ids: [item-01]",
            "- supporting_item_ids: item-01",
            "report template must require a bracketed supporting_item_ids field per theme",
        ),
        (
            "- 观察维度: medium, creator, geography\n",
            "- 观察维度: 综合判断\n",
            "report template must document concrete bias dimensions",
        ),
        (
            "至少 6 个非标点字符",
            "至少 2 个字符",
            "report template must document the conservative minimum for bias prose",
        ),
        (
            "- supporting_item_ids: [item-02]\n",
            "",
            "report template bias section must require bracketed supporting_item_ids",
        ),
        (
            "- 可能后果: ...\n",
            "",
            "report template bias section must define the exact structural fields",
        ),
        (
            "- independent_quality_judgment: ...\n",
            "",
            "report template must require independent_quality_judgment per source item",
        ),
    ]

    for before, after, message in cases:
        refs_dir = mutate_reference(tmp_path, "report-template.md", before, after)
        with pytest.raises(AssertionError, match=re.escape(message)):
            validate_report_template(read("report-template.md", refs_dir))
        shutil.rmtree(refs_dir)
