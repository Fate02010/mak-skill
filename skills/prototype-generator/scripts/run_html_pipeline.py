#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from html_utils import parse_page_spec, render_index_html
from review_finding import make_finding, severity_from_status


def _run_command(cmd: list[str]) -> dict:
    completed = subprocess.run(cmd, capture_output=True, text=True)
    return {"cmd": cmd, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _parse_json_stdout(result: dict) -> dict:
    stdout = (result.get("stdout") or "").strip()
    return json.loads(stdout) if stdout else {}


def _consistency_scope(product_name: str) -> str:
    text = str(product_name or "")
    if "后台" in text:
        return "admin"
    if "小程序" in text:
        return "miniapp"
    if "H5" in text:
        return "h5"
    if "大屏" in text:
        return "bigscreen"
    if "官网" in text or "门户" in text:
        return "portal"
    if "工控机" in text or "HMI" in text:
        return "industrial"
    if any(token in text for token in ("APP", "App", "移动端")):
        return "app"
    return "auto"


def _collect_review_findings(scope: str, consistency: dict, html_validation: dict) -> list[dict]:
    findings: list[dict] = []
    for page in consistency.get("missing_pages", []):
        findings.append(make_finding(format="html", scope=scope, page_or_sheet=page, layer="page_spec", rule="MISSING_PAGE", severity="error", message="requirements 页面未生成 HTML", repair_target="page_spec"))
    for item in consistency.get("missing_field_pages", []):
        findings.append(
            make_finding(
                format="html",
                scope=scope,
                page_or_sheet=item.get("page", ""),
                layer="page_spec",
                rule="MISSING_FIELDS",
                severity="error",
                message=f"页面缺少字段: {', '.join(item.get('missing_fields', [])[:5])}",
                repair_target="page_spec",
            )
        )
    for item in consistency.get("low_coverage_pages", []):
        findings.append(
            make_finding(
                format="html",
                scope=scope,
                page_or_sheet=item.get("page", ""),
                layer="page_spec",
                rule="LOW_COVERAGE",
                severity="error",
                message=f"字段覆盖率过低: {item.get('coverage', 0)}",
                repair_target="page_spec",
            )
        )
    for result in html_validation.get("results", []):
        if result.get("status") == "PASS":
            continue
        for detail in result.get("details", []) or ["all"]:
            findings.append(
                make_finding(
                    format="html",
                    scope=scope,
                    page_or_sheet=str(detail),
                    layer="html_render",
                    rule=result.get("rule", ""),
                    severity=severity_from_status(result.get("status", "")),
                    message=result.get("title", ""),
                    repair_target="html_render" if result.get("rule") in {"H1", "H2", "H4"} else "page_spec",
                )
            )
    return findings


def run_pipeline(work_dir: str | Path, product_name: str, max_parallel: int = 3) -> dict:
    work_dir = Path(work_dir).resolve()
    skill_dir = Path(__file__).resolve().parents[1]
    artifact_dir = work_dir / ".prototype-generator"
    page_specs_dir = artifact_dir / "page_specs"
    requirements_dir = work_dir / "requirements"
    prototypes_dir = work_dir / "prototypes"
    prototypes_dir.mkdir(parents=True, exist_ok=True)
    if not page_specs_dir.is_dir():
        raise SystemExit(f"page_specs 目录不存在: {page_specs_dir}")
    if not requirements_dir.is_dir():
        raise SystemExit(f"requirements 目录不存在: {requirements_dir}")

    shutil.copyfile(skill_dir / "templates" / "common.css", prototypes_dir / "common.css")
    render_script = skill_dir / "scripts" / "render_html.py"
    consistency_script = skill_dir / "scripts" / "check_html_consistency.py"
    validate_script = skill_dir / "scripts" / "validate_html.py"
    context_budget_script = skill_dir / "scripts" / "check_context_budget.py"
    brief_consistency_script = skill_dir / "scripts" / "check_module_brief_consistency.py"

    context_budget_result = _run_command([sys.executable, str(context_budget_script), str(work_dir), "--json"])
    context_budget_report = _parse_json_stdout(context_budget_result)
    if context_budget_result["returncode"] != 0:
        return {
            "work_dir": str(work_dir),
            "product_name": product_name,
            "summary": {"fail": 1, "warn": 0, "pass": 0},
            "context_budget": context_budget_report,
            "failure_routing": [{"layer": "requirements", "reason": "上下文预算预检失败", "pages": context_budget_report.get("failures", [])}],
            "review_findings": [
                make_finding(format="html", scope="all", page_or_sheet=item, layer="requirements", rule="CONTEXT_BUDGET", severity="error", message="上下文预算预检失败", repair_target="requirements")
                for item in context_budget_report.get("failures", [])
            ],
        }

    brief_consistency_report = {"summary": {"fail": 0, "warn": 0, "pass": 1}, "skipped": True}
    if (requirements_dir / "index.md").exists():
        brief_result = _run_command([sys.executable, str(brief_consistency_script), str(requirements_dir), "--json"])
        brief_consistency_report = _parse_json_stdout(brief_result)
        if brief_result["returncode"] != 0:
            fail_items = list(brief_consistency_report.get("missing_briefs", []))
            for item in brief_consistency_report.get("missing_pages", []):
                fail_items.extend(item.get("pages", []))
            return {
                "work_dir": str(work_dir),
                "product_name": product_name,
                "summary": {"fail": 1, "warn": 0, "pass": 0},
                "context_budget": context_budget_report,
                "module_brief_consistency": brief_consistency_report,
                "failure_routing": [{"layer": "requirements", "reason": "module_brief 覆盖率校验失败", "pages": fail_items}],
                "review_findings": [
                    make_finding(format="html", scope="all", page_or_sheet=item, layer="requirements", rule="MODULE_BRIEF", severity="error", message="module_brief 覆盖率校验失败", repair_target="requirements")
                    for item in fail_items
                ],
            }

    rendered_pages: list[dict] = []
    page_specs = sorted(page_specs_dir.glob("page_spec_*.md"))
    render_failures = []
    for spec_path in page_specs:
        result = _run_command([sys.executable, str(render_script), str(spec_path), str(prototypes_dir), "--json"])
        if result["returncode"] != 0:
            render_failures.append({"page_spec": str(spec_path), **result})
            continue
        rendered_pages.extend(_parse_json_stdout(result).get("rendered_pages", []))
    if render_failures:
        findings = [
            make_finding(format="html", scope="all", page_or_sheet=item["page_spec"], layer="html_render", rule="RENDER", severity="error", message="HTML 渲染失败", repair_target="html_render")
            for item in render_failures
        ]
        return {
            "work_dir": str(work_dir),
            "product_name": product_name,
            "summary": {"fail": 1, "warn": 0, "pass": 0},
            "render_failures": render_failures,
            "failure_routing": [{"layer": "html_render", "reason": "HTML 渲染失败", "pages": [item["page_spec"] for item in render_failures]}],
            "review_findings": findings,
        }

    all_pages = []
    for spec_path in page_specs:
        spec = parse_page_spec(spec_path)
        for page in spec.get("pages", []):
            all_pages.append({"page_name": page.get("page_name", ""), "output_file": page.get("output_file", "")})
    (prototypes_dir / "index.html").write_text(render_index_html(product_name, all_pages), encoding="utf-8")

    consistency_scope = _consistency_scope(product_name)
    consistency_result = _run_command([sys.executable, str(consistency_script), str(requirements_dir), str(prototypes_dir), "--json"])
    consistency_report = _parse_json_stdout(consistency_result)
    validation_result = _run_command([sys.executable, str(validate_script), str(prototypes_dir), "--json"])
    html_validation = _parse_json_stdout(validation_result)
    review_findings = _collect_review_findings(consistency_scope, consistency_report, html_validation)
    fail = 0
    if consistency_report.get("summary", {}).get("fail"):
        fail += 1
    fail += html_validation.get("summary", {}).get("fail", 0)
    return {
        "work_dir": str(work_dir),
        "product_name": product_name,
        "page_spec_count": len(page_specs),
        "html_file_count": len(list(prototypes_dir.glob("*.html"))),
        "prototypes_dir": str(prototypes_dir),
        "artifacts": {
            "common_css": str(prototypes_dir / "common.css"),
            "index_html": str(prototypes_dir / "index.html"),
            "html_files": [str(path) for path in sorted(prototypes_dir.glob("*.html"))],
        },
        "coverage": {
            "missing_pages": consistency_report.get("missing_pages", []),
            "low_coverage_pages": consistency_report.get("low_coverage_pages", []),
        },
        "validator_results": html_validation,
        "context_budget": context_budget_report,
        "module_brief_consistency": brief_consistency_report,
        "consistency_scope": consistency_scope,
        "consistency": consistency_report,
        "final_validation": html_validation,
        "failure_routing": [
            {"layer": finding["repair_target"], "reason": finding["rule"], "pages": [finding["page_or_sheet"]]}
            for finding in review_findings
            if finding["severity"] == "error"
        ],
        "review_findings": review_findings,
        "summary": {"fail": fail, "warn": 0, "pass": 1 if fail == 0 else 0},
    }


def main():
    parser = argparse.ArgumentParser(description="运行真实 WORK_DIR 上的 HTML 原型交付门禁")
    parser.add_argument("work_dir")
    parser.add_argument("product_name")
    parser.add_argument("--max-parallel", type=int, default=3)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    report = run_pipeline(args.work_dir, args.product_name, max_parallel=max(1, min(args.max_parallel, 3)))
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["summary"]["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
