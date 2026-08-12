from contracts import REPORT_CODES, parse_front_matter, validate_positioning
import pytest


VALID = """---
title: "Wisereads Vol. 155 深度解读"
issue_key: "wisereads-vol-155"
issue_kind: "standard"
issue_number: 155
issue_label: "Vol. 155"
source_url: "https://wise.readwise.io/issues/wisereads-vol-155/"
discovered_at: "2026-08-12T10:00:00+08:00"
generated_at: "2026-08-12T10:42:00+08:00"
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


def test_parse_front_matter_returns_typed_metadata():
    meta, body = parse_front_matter(VALID, "report.md")
    assert meta.issue_key == "wisereads-vol-155"
    assert meta.issue_number == 155
    assert meta.discovered_at.utcoffset().total_seconds() == 28800
    assert body == "body\n"


@pytest.mark.parametrize(
    "source_url",
    [
        "https://wise.readwise.io/",
        "https://wise.readwise.io/about",
        "https://wise.readwise.io/issues//",
    ],
)
def test_parse_front_matter_rejects_non_issue_source_urls(source_url: str):
    text = VALID.replace(
        'source_url: "https://wise.readwise.io/issues/wisereads-vol-155/"',
        f'source_url: "{source_url}"',
    )

    with pytest.raises(ValueError, match=r"^report\.md: source_url "):
        parse_front_matter(text, "report.md")


def test_parse_front_matter_rejects_nested_issue_source_paths():
    text = VALID.replace(
        'source_url: "https://wise.readwise.io/issues/wisereads-vol-155/"',
        'source_url: "https://wise.readwise.io/issues/foo/bar/"',
    )

    with pytest.raises(ValueError, match=r"^report\.md: source_url "):
        parse_front_matter(text, "report.md")


def test_positioning_rejects_ai_newsletter_identity():
    findings = validate_positioning(
        "Weekly Wisereads 是一个面向中文 AI Builder 与创业者的 AI 周报。",
        "README.md",
    )
    assert {finding.code for finding in findings} == {"POSITIONING_AI_IDENTITY"}


def test_positioning_allows_explicit_non_ai_identity_statement():
    findings = validate_positioning(
        "Weekly Wisereads is not an AI newsletter. Themes emerge from each issue.",
        "SKILL.md",
    )
    assert findings == []


def test_positioning_rejects_ranked_ebook_claim():
    findings = validate_positioning(
        "所有文章、视频、PDF 和电子书都按独立高亮用户数排名。",
        "README.md",
    )
    assert {finding.code for finding in findings} == {"POSITIONING_EBOOK_RANKING"}


def test_report_codes_match_public_contract():
    assert REPORT_CODES == {
        "REPORT_METADATA_INVALID",
        "REPORT_ITEM_COVERAGE",
        "REPORT_DUPLICATE_SOURCE",
        "REPORT_STATUS_COUNT_MISMATCH",
        "REPORT_COVERAGE_BELOW_THRESHOLD",
        "REPORT_AI_ABSENCE",
        "REPORT_BIAS_SECTION_MISSING",
        "REPORT_SUMMARY_OVERCLAIM",
        "REPORT_THEME_WITHOUT_SUPPORT",
        "REPORT_POPULARITY_EQUALS_QUALITY",
    }
