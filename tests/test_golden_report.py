from pathlib import Path

from contracts import parse_front_matter, parse_inventory, validate_report


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "2026" / "2026-08-12-vol-155.md"
INVENTORY = ROOT / "tests" / "fixtures" / "issues" / "vol-155" / "inventory.json"


def test_vol_155_is_the_validated_golden_report():
    inventory = parse_inventory(INVENTORY.read_text(encoding="utf-8"), str(INVENTORY))
    text = REPORT.read_text(encoding="utf-8")
    meta, _ = parse_front_matter(text, str(REPORT))

    assert meta.issue_key == inventory.issue_key == "wisereads-vol-155"
    assert meta.source_url == inventory.source_url
    assert meta.sources_total == inventory.detail_page_item_count == len(inventory.items)
    assert 15 <= meta.reading_time_minutes <= 20
    assert validate_report(text, str(REPORT), inventory) == []


def test_golden_report_covers_every_item_once():
    inventory = parse_inventory(INVENTORY.read_text(encoding="utf-8"), str(INVENTORY))
    text = REPORT.read_text(encoding="utf-8")

    for item in inventory.items:
        assert text.count(f"<!-- source-item:{item.item_id} -->") == 1


def test_golden_report_discloses_degraded_items_actual_evidence_urls():
    inventory = parse_inventory(INVENTORY.read_text(encoding="utf-8"), str(INVENTORY))
    text = REPORT.read_text(encoding="utf-8")
    item_07 = text.split("<!-- source-item:item-07 -->", 1)[1].split(
        "<!-- source-item:item-08 -->", 1
    )[0]
    item_08 = text.split("<!-- source-item:item-08 -->", 1)[1].split("</details>", 1)[0]

    item_07_evidence_urls = (
        "https://wise.readwise.io/issues/wisereads-vol-155/",
        "https://www.library.hbs.edu/working-knowledge/when-a-vacation-isnt-enough-a-sabbatical-can-recharge-your-life-and-your-career",
        "https://www.hbs.edu/managing-the-future-of-work/podcast/why-time-away-may-be-the-future-of-work",
        "https://www.library.hbs.edu/working-knowledge/feel-like-a-time-bomb-lately-consider-taking-a-career-break",
        "https://www.simonandschuster.com/books/Big-Time-Off/DJ-DiDonna/9781668060896",
    )
    for source_url in item_07_evidence_urls:
        assert source_url in item_07

    item_08_inventory = next(item for item in inventory.items if item.item_id == "item-08")
    assert item_08_inventory.alternate_url == "https://stevekamb.com/newsletter/"
    assert f"- alternate_url: {item_08_inventory.alternate_url}" in item_08
    for source_url in (
        "https://stevekamb.com/will-your-new-routine-succeed-or-fail-this-is-the-biggest-indicator/",
        "https://stevekamb.com/the-frustrating-importance-of-wasted-effort/",
        "https://stevekamb.com/start-ugly/",
        "https://stevekamb.com/why-we-should-surround-ourselves-with-failure/",
    ):
        assert source_url in item_08
