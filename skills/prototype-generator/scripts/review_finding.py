#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def severity_from_status(status: str) -> str:
    text = str(status or "").upper()
    if text == "FAIL":
        return "error"
    if text == "WARN":
        return "warn"
    return "info"


def make_finding(
    *,
    format: str,
    scope: str,
    page_or_sheet: str,
    layer: str,
    rule: str,
    severity: str,
    message: str,
    repair_target: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    finding = {
        "id": f"{format}:{layer}:{rule}:{page_or_sheet or 'all'}",
        "format": str(format or ""),
        "scope": str(scope or ""),
        "page_or_sheet": str(page_or_sheet or ""),
        "layer": str(layer or ""),
        "rule": str(rule or ""),
        "severity": str(severity or "error"),
        "message": str(message or ""),
        "repair_target": str(repair_target or layer or ""),
    }
    finding["stagnation_key"] = f"{finding['repair_target']}::{finding['rule']}::{finding['page_or_sheet'] or 'all'}"
    if extra:
        finding.update(extra)
    return finding


def summarize_findings(findings: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"error": 0, "warn": 0, "info": 0}
    for finding in findings:
        severity = str(finding.get("severity", "info"))
        summary[severity] = summary.get(severity, 0) + 1
    return summary
