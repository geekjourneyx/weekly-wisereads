from pathlib import Path
import re

from build_publication import discover_reports


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
EXPECTED_DESCRIPTION = (
    "A Chinese deep-reading archive of Weekly Wisereads, covering Readwise users' "
    "most-highlighted weekly documents and each issue's curated ebook selection."
)
EXPECTED_TOPICS = (
    "wisereads",
    "readwise",
    "weekly-wisereads",
    "deep-reading",
    "reading",
    "highlights",
    "knowledge-management",
    "newsletter",
    "chinese",
    "research",
    "critical-thinking",
    "reading-notes",
    "digital-reading",
)
SECTION_HEADINGS = (
    "# Weekly Wisereads",
    "## Latest Issue",
    "## What Is Weekly Wisereads",
    "## Why",
    "## What You Get",
    "## How It Works",
    "## Featured Insights",
    "## Archive",
    "## Use the Skill",
    "## Methodology",
    "## Contributing",
    "## About",
)


def _readme() -> str:
    assert README.is_file(), "README.md must exist"
    return README.read_text(encoding="utf-8")


def _managed_body(text: str, block: str) -> str:
    start = f"<!-- AUTO:{block}:START -->"
    end = f"<!-- AUTO:{block}:END -->"
    assert text.count(start) == text.count(end) == 1
    return text.split(start, 1)[1].split(end, 1)[0].strip()


def test_readme_has_the_approved_editorial_section_order():
    text = _readme()
    headings = re.findall(r"(?m)^#{1,2} .+$", text)
    assert headings == list(SECTION_HEADINGS)

    first_section = text[: text.index("## Latest Issue")]
    assert "独立、非官方" in first_section
    assert "Readwise" in first_section
    assert "深读 Readwise 用户上周高亮最多的内容，从集体阅读信号中，提炼值得理解、质疑与长期保留的观点。" in first_section


def test_readme_explains_selection_and_optional_ai_lens_without_old_identity():
    text = _readme()
    assert "文章、视频、tweets / threads 与公开 PDF" in text
    assert "独立高亮用户数" in text
    assert "电子书由 Readwise 单独策划或合作纳入" in text
    assert "不属于同一排名机制" in text
    assert "AI / Agent / 工程只是可选分析镜头" in text

    assert "不是 AI 周报" in text
    forbidden = (
        "面向中文 AI Builder",
        "是一个 AI 周报",
        "is an AI newsletter",
        "AI 内容配额",
    )
    assert all(phrase not in text for phrase in forbidden)


def test_readme_managed_blocks_publish_one_latest_and_bounded_recent_archive():
    text = _readme()
    latest = _managed_body(text, "LATEST")
    recent = _managed_body(text, "RECENT")
    newest = discover_reports(ROOT)[0]

    assert latest.count("\n") == 0
    assert newest.meta.issue_label in latest
    assert newest.path in latest

    issue_lines = [
        line for line in recent.splitlines()
        if line.startswith("- [") and "完整归档" not in line
    ]
    assert 1 <= len(issue_lines) <= 6
    assert newest.meta.issue_label in issue_lines[0]
    assert newest.path in issue_lines[0]
    assert "- [完整归档](reports/README.md)" in recent


def test_readme_uses_all_editorial_assets_with_meaningful_alt_text():
    text = _readme()
    expected = {
        "assets/readme/hero.svg": "Weekly Wisereads 编辑杂志封面",
        "assets/readme/signal-map.svg": "Weekly Wisereads 内容选择信号图",
        "assets/readme/workflow.svg": "Weekly Wisereads 从发现到发布的工作流",
        "assets/readme/evidence-levels.svg": "Weekly Wisereads 访问状态与判断类型证据图",
    }
    for path, alt in expected.items():
        assert f"![{alt}]({path})" in text


def test_readme_exposes_installable_skill_and_accurate_metadata_contract():
    text = _readme()
    assert "$weekly-wisereads" in text
    assert "[skills/weekly-wisereads/SKILL.md](skills/weekly-wisereads/SKILL.md)" in text

    forbidden_metadata_tokens = {"ai", "agent", "builder", "startup"}
    metadata = f"{EXPECTED_DESCRIPTION} {' '.join(EXPECTED_TOPICS)}".lower()
    metadata_words = set(re.findall(r"[a-z]+", metadata))
    assert forbidden_metadata_tokens.isdisjoint(metadata_words)
