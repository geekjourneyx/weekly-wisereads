from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "weekly-wisereads" / "SKILL.md"


def test_skill_frontmatter_and_size():
    text = SKILL.read_text(encoding="utf-8")
    _, raw, _body = text.split("---", 2)
    frontmatter = yaml.safe_load(raw)
    assert frontmatter["name"] == "weekly-wisereads"
    assert frontmatter["description"].startswith("Use when ")
    assert set(frontmatter) == {"name", "description"}
    assert len(text.splitlines()) < 500


def test_skill_directly_routes_every_reference():
    text = SKILL.read_text(encoding="utf-8")
    required = {
        "positioning-contract.md",
        "inventory-contract.md",
        "analysis-method.md",
        "evidence-policy.md",
        "report-template.md",
        "quality-gates.md",
        "readme-update-contract.md",
        "atomic-publish-protocol.md",
        "scheduled-prompt.md",
    }
    linked = set(re.findall(r"references/([a-z-]+\.md)", text))
    assert linked == required


def test_skill_does_not_hardcode_current_volume():
    assert "Vol.155" not in SKILL.read_text(encoding="utf-8")
