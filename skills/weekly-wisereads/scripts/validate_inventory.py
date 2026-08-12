from __future__ import annotations

import argparse
from pathlib import Path
import sys

from contracts import Finding, parse_inventory, validate_inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_inventory.py",
        usage="validate_inventory.py [--allow-discovery-state] INVENTORY",
    )
    parser.add_argument("--allow-discovery-state", action="store_true")
    parser.add_argument("inventory")
    args = parser.parse_args(argv)

    inventory_path = Path(args.inventory)

    try:
        text = inventory_path.read_text(encoding="utf-8")
        inventory = parse_inventory(text, str(inventory_path))
    except (OSError, ValueError) as exc:
        print(_format_parse_error(str(inventory_path), exc))
        return 1

    findings = validate_inventory(
        inventory,
        str(inventory_path),
        require_terminal=not args.allow_discovery_state,
    )
    if findings:
        for finding in findings:
            print(_format_finding(finding))
        return 1
    return 0


def _format_finding(finding: Finding) -> str:
    return f"{finding.code} {finding.path}: {finding.message}"


def _format_parse_error(path: str, exc: Exception) -> str:
    message = str(exc)
    prefix = f"{path}: "
    if message.startswith(prefix):
        message = message[len(prefix) :]
    return f"PARSE_ERROR {path}: {message}"


if __name__ == "__main__":
    sys.exit(main())
