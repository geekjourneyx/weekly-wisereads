from __future__ import annotations

import argparse
from pathlib import Path
import sys

from contracts import Finding, parse_inventory, validate_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_report.py",
        usage="validate_report.py --inventory INVENTORY --report REPORT",
    )
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)

    inventory_path = Path(args.inventory)
    report_path = Path(args.report)

    try:
        inventory_text = inventory_path.read_text(encoding="utf-8")
        inventory = parse_inventory(inventory_text, str(inventory_path))
    except (OSError, ValueError) as exc:
        print(_format_parse_error(str(inventory_path), exc))
        return 1

    try:
        report_text = report_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(_format_parse_error(str(report_path), exc))
        return 1

    findings = validate_report(report_text, str(report_path), inventory)
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
