#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


DEFAULT_REPAIR_ACTIONS = {
    "page_spec": "rewrite_page_spec",
    "module_brief": "rewrite_module_brief",
    "requirements": "rewrite_requirements",
    "reference_pack": "rebuild_reference_pack",
    "html_render": "patch_renderer",
    "page_model": "rewrite_page_model",
    "render_merge": "rerender_output",
    "review": "review_manual",
}


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
    repair_target = str(repair_target or layer or "")
    repair_action = DEFAULT_REPAIR_ACTIONS.get(repair_target, f"repair_{repair_target}" if repair_target else "repair")
    stop_category = "auto_repairable"
    auto_repairable = True
    if repair_action in {"patch_renderer", "review_manual"}:
        stop_category = "needs_skill_patch" if repair_action == "patch_renderer" else "needs_refreeze"
    if repair_target in {"module_brief", "requirements"}:
        stop_category = "needs_refreeze"
    finding = {
        "id": f"{format}:{layer}:{rule}:{page_or_sheet or 'all'}",
        "format": str(format or ""),
        "scope": str(scope or ""),
        "page_or_sheet": str(page_or_sheet or ""),
        "layer": str(layer or ""),
        "rule": str(rule or ""),
        "severity": str(severity or "error"),
        "message": str(message or ""),
        "repair_target": repair_target,
        "repair_action": repair_action,
        "root_cause_hint": "",
        "expected_fix_scope": repair_target,
        "auto_repairable": auto_repairable,
        "stop_category": stop_category,
    }
    finding["stagnation_key"] = (
        f"{finding['repair_target']}::{finding['repair_action']}::{finding['rule']}::{finding['page_or_sheet'] or 'all'}"
    )
    if extra:
        finding.update(extra)
    finding["repair_action"] = str(finding.get("repair_action") or repair_action)
    finding["root_cause_hint"] = str(finding.get("root_cause_hint") or "")
    finding["expected_fix_scope"] = str(finding.get("expected_fix_scope") or finding["repair_target"])
    finding["auto_repairable"] = bool(finding.get("auto_repairable", auto_repairable))
    finding["stop_category"] = str(finding.get("stop_category") or stop_category)
    finding["stagnation_key"] = (
        f"{finding['repair_target']}::{finding['repair_action']}::{finding['rule']}::{finding['page_or_sheet'] or 'all'}"
    )
    return finding


def summarize_findings(findings: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"error": 0, "warn": 0, "info": 0}
    for finding in findings:
        severity = str(finding.get("severity", "info"))
        summary[severity] = summary.get(severity, 0) + 1
    return summary
