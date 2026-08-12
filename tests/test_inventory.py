import json
from pathlib import Path

from contracts import parse_inventory, validate_inventory

FIXTURES = Path(__file__).parent / "fixtures" / "inventories"


def load(name: str):
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return parse_inventory(text, name)


def test_valid_inventory_covers_every_supported_type():
    inventory = load("valid-all-types.json")
    assert validate_inventory(inventory, "valid-all-types.json", True) == []
    assert len(inventory.items) == inventory.detail_page_item_count == 6


def test_duplicate_source_url_is_rejected():
    findings = validate_inventory(load("invalid-duplicate-url.json"), "duplicate.json", True)
    assert "INVENTORY_DUPLICATE_URL" in {finding.code for finding in findings}


def test_ranked_ebook_is_rejected():
    findings = validate_inventory(load("invalid-ebook-selection.json"), "ebook.json", True)
    assert "INVENTORY_EBOOK_SELECTION" in {finding.code for finding in findings}


def test_special_edition_preserves_page_identity():
    inventory = load("valid-special-edition.json")
    assert validate_inventory(inventory, "special.json", True) == []
    assert inventory.issue_key == "wisereads-special-vol-2"
    assert inventory.issue_kind == "special"
    assert inventory.issue_number == 2
    assert inventory.issue_label == "Special Edition Vol. 2"


def test_discovery_state_allows_null_access_status_only_when_requested():
    payload = json.loads((FIXTURES / "valid-all-types.json").read_text(encoding="utf-8"))
    payload["items"][0]["access_status"] = None
    inventory = parse_inventory(json.dumps(payload), "discovery.json")

    assert validate_inventory(inventory, "discovery.json", False) == []
    assert "INVENTORY_NON_TERMINAL_STATUS" in {
        finding.code for finding in validate_inventory(inventory, "discovery.json", True)
    }
