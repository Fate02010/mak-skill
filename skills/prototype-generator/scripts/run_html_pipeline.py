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
from requirements_compression import ensure_compressed_requirements
from reference_utils import enrich_page_spec_file, ensure_reference_pack
from requirements_utils import infer_page_shape, parse_requirement_modules
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


def _load_generated_page_meta(prototypes_dir: Path) -> dict:
    generated = {}
    for path in sorted(prototypes_dir.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        page_name = _extract_attr(text, "data-page-name") or path.stem
        generated[page_name] = {
            "file": path.name,
            "page_type": _extract_attr(text, "data-page-type"),
            "page_archetype": _extract_attr(text, "data-page-archetype"),
            "reference_basis": _extract_attr(text, "data-reference-basis"),
            "has_body_slot": _extract_attr(text, "data-body-slot") == "1" or 'data-body-slot="1"' in text or "data-body-slot='1'" in text,
            "text": text,
        }
    return generated


def _extract_attr(text: str, attr: str) -> str:
    for quote in ('"', "'"):
        marker = f"{attr}={quote}"
        if marker in text:
            return text.split(marker, 1)[1].split(quote, 1)[0]
    return ""


def _parse_validation_detail(detail: str) -> str:
    text = str(detail or "").strip()
    if " -> " in text:
        return text.split(" -> ", 1)[0].strip()
    if ":" in text:
        return text.split(":", 1)[0].strip()
    return text


def _page_name_from_detail(detail: str, generated_meta: dict) -> str:
    token = _parse_validation_detail(detail)
    if token in generated_meta:
        return token
    for page_name, meta in generated_meta.items():
        if meta.get("file") == token:
            return page_name
    return token


def _requirement_page_lookup(requirements_dir: Path) -> dict[str, dict]:
    mapping = {}
    for module_name, module_req in parse_requirement_modules(requirements_dir).items():
        for page_name, page_req in module_req.get("pages", {}).items():
            mapping[page_name] = {
                "module_name": module_name,
                "page_archetype": page_req.get("page_archetype", infer_page_shape(page_name)[1]),
            }
    return mapping


def _is_split_requirements(requirements_dir: Path) -> bool:
    return (requirements_dir / "index.md").exists()


def _brief_exists(requirements_dir: Path, module_name: str) -> bool:
    return (requirements_dir / "module_briefs" / f"模块摘要_{module_name}.md").exists()


def _routing_item(finding: dict) -> dict:
    return {
        "layer": finding["repair_target"],
        "repair_action": finding.get("repair_action", ""),
        "root_cause_hint": finding.get("root_cause_hint", ""),
        "stop_category": finding.get("stop_category", ""),
        "pages": [finding["page_or_sheet"]],
    }


def _make_html_finding(
    *,
    scope: str,
    page_or_sheet: str,
    layer: str,
    rule: str,
    severity: str,
    message: str,
    repair_target: str,
    repair_action: str,
    root_cause_hint: str,
    expected_fix_scope: str,
    stop_category: str,
    auto_repairable: bool = True,
) -> dict:
    return make_finding(
        format="html",
        scope=scope,
        page_or_sheet=page_or_sheet,
        layer=layer,
        rule=rule,
        severity=severity,
        message=message,
        repair_target=repair_target,
        extra={
            "repair_action": repair_action,
            "root_cause_hint": root_cause_hint,
            "expected_fix_scope": expected_fix_scope,
            "stop_category": stop_category,
            "auto_repairable": auto_repairable,
        },
    )


def _route_html_validation_rule(
    *,
    rule: str,
    detail: str,
    scope: str,
    generated_meta: dict,
    page_requirements: dict,
) -> dict:
    page_name = _page_name_from_detail(detail, generated_meta)
    page_meta = generated_meta.get(page_name, {})
    req_meta = page_requirements.get(page_name, {})
    expected_archetype = req_meta.get("page_archetype", "")
    actual_archetype = page_meta.get("page_archetype", "")
    archetype_conflict = bool(expected_archetype and actual_archetype and expected_archetype != actual_archetype)
    if rule == "H7":
        return _make_html_finding(
            scope=scope,
            page_or_sheet=page_name,
            layer="reference_pack",
            rule=rule,
            severity="error",
            message="reference metadata 缺失",
            repair_target="reference_pack",
            repair_action="rebuild_reference_pack",
            root_cause_hint="页面缺少 reference metadata，需重建 reference_pack 并重新富化 page_spec",
            expected_fix_scope="reference_pack",
            stop_category="auto_repairable",
        )
    if rule in {"H1", "H2", "H4", "H10", "H11", "H12", "H13", "BODY_RENDER", "BODY_SLOT_MISSING", "BODY_CONTRACT", "RENDER"}:
        return _make_html_finding(
            scope=scope,
            page_or_sheet=page_name,
            layer="html_render",
            rule=rule,
            severity="error",
            message="HTML 渲染层输出异常",
            repair_target="html_render",
            repair_action="patch_renderer",
            root_cause_hint="HTML 文档壳、链接或稳定性样式输出异常，应修复 renderer 而不是补 page_spec",
            expected_fix_scope="html_render",
            stop_category="needs_skill_patch",
        )
    if rule in {"H8", "H9"} and not archetype_conflict:
        return _make_html_finding(
            scope=scope,
            page_or_sheet=page_name,
            layer="html_render",
            rule=rule,
            severity="error",
            message="页面骨架或视觉层级不足",
            repair_target="html_render",
            repair_action="patch_renderer",
            root_cause_hint="页面 archetype 已对齐但 renderer 输出骨架不达标，应修复 html_utils.py / 模板",
            expected_fix_scope="html_render",
            stop_category="needs_skill_patch",
        )
    return _make_html_finding(
        scope=scope,
        page_or_sheet=page_name,
        layer="page_spec",
        rule=rule,
        severity="error",
        message="页面 archetype 与校验期望不一致",
        repair_target="page_spec",
        repair_action="rewrite_page_spec",
        root_cause_hint="page_archetype 缺失或与 requirements 推断不一致，应先重冻规格",
        expected_fix_scope="page_spec",
        stop_category="auto_repairable",
    )


def _collect_review_findings(
    *,
    scope: str,
    consistency: dict,
    html_validation: dict,
    requirements_dir: Path,
    generated_meta: dict,
) -> list[dict]:
    findings: list[dict] = []
    page_requirements = _requirement_page_lookup(requirements_dir)
    split_mode = _is_split_requirements(requirements_dir)

    for page in consistency.get("missing_pages", []):
        findings.append(
            _make_html_finding(
                scope=scope,
                page_or_sheet=page,
                layer="page_spec",
                rule="MISSING_PAGE",
                severity="error",
                message="requirements 页面未生成 HTML",
                repair_target="page_spec",
                repair_action="rewrite_page_spec",
                root_cause_hint="页面未生成，多数是 page_spec 缺页或输出文件缺失",
                expected_fix_scope="page_spec",
                stop_category="auto_repairable",
            )
        )
    for item in consistency.get("missing_field_pages", []):
        findings.append(
            _make_html_finding(
                scope=scope,
                page_or_sheet=item.get("page", ""),
                layer="page_spec",
                rule="MISSING_FIELDS",
                severity="error",
                message=f"页面缺少字段: {', '.join(item.get('missing_fields', [])[:5])}",
                repair_target="page_spec",
                repair_action="rewrite_page_spec",
                root_cause_hint="字段覆盖不足，应补充冻结后的 page_spec 字段、列和状态",
                expected_fix_scope="page_spec",
                stop_category="auto_repairable",
            )
        )
    for item in consistency.get("low_coverage_pages", []):
        findings.append(
            _make_html_finding(
                scope=scope,
                page_or_sheet=item.get("page", ""),
                layer="page_spec",
                rule="LOW_COVERAGE",
                severity="error",
                message=f"字段覆盖率过低: {item.get('coverage', 0)}",
                repair_target="page_spec",
                repair_action="rewrite_page_spec",
                root_cause_hint="页面覆盖率不足，应补充冻结规格中的字段和列表列",
                expected_fix_scope="page_spec",
                stop_category="auto_repairable",
            )
        )
    for item in consistency.get("layout_mismatch_pages", []):
        page_name = item.get("page", "")
        module_name = page_requirements.get(page_name, {}).get("module_name", "")
        if split_mode and module_name and _brief_exists(requirements_dir, module_name):
            repair_target = "module_brief"
            repair_action = "rewrite_module_brief"
            expected_scope = "module_brief"
            hint = "页面原型偏离 requirements，优先重冻 module_brief 再同步 page_spec"
        else:
            repair_target = "requirements"
            repair_action = "rewrite_requirements"
            expected_scope = "requirements"
            hint = "页面原型偏离 requirements 且无可用 module_brief，应回到 requirements 层重冻规格"
        findings.append(
            _make_html_finding(
                scope=scope,
                page_or_sheet=page_name,
                layer=repair_target,
                rule="LAYOUT_MISMATCH",
                severity="error",
                message=f"页面原型不匹配: requirements={item.get('expected')} html={item.get('actual')}",
                repair_target=repair_target,
                repair_action=repair_action,
                root_cause_hint=hint,
                expected_fix_scope=expected_scope,
                stop_category="needs_refreeze",
            )
        )
    for result in html_validation.get("results", []):
        if result.get("status") == "PASS":
            continue
        severity = severity_from_status(result.get("status", ""))
        if severity != "error":
            continue
        for detail in result.get("details", []) or ["all"]:
            findings.append(
                _route_html_validation_rule(
                    rule=result.get("rule", ""),
                    detail=str(detail),
                    scope=scope,
                    generated_meta=generated_meta,
                    page_requirements=page_requirements,
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
    body_slots_dir = artifact_dir / "body_slots"
    prototypes_dir.mkdir(parents=True, exist_ok=True)
    body_slots_dir.mkdir(parents=True, exist_ok=True)
    if not page_specs_dir.is_dir():
        raise SystemExit(f"page_specs 目录不存在: {page_specs_dir}")
    if not requirements_dir.is_dir():
        raise SystemExit(f"requirements 目录不存在: {requirements_dir}")

    shutil.copyfile(skill_dir / "templates" / "common.css", prototypes_dir / "common.css")
    reference_manifest = ensure_reference_pack(work_dir)
    if reference_manifest.get("policy_violations"):
        findings = [
            _make_html_finding(
                scope="all",
                page_or_sheet=item.get("path", ""),
                layer="reference_pack",
                rule="REFERENCE_POLICY",
                severity="error",
                message=f"引用了禁用来源: {item.get('path', '')}",
                repair_target="reference_pack",
                repair_action="rebuild_reference_pack",
                root_cause_hint="reference_pack 命中了禁用来源，应重建参考包并排除污染输入",
                expected_fix_scope="reference_pack",
                stop_category="auto_repairable",
            )
            for item in reference_manifest.get("policy_violations", [])
        ]
        return {
            "work_dir": str(work_dir),
            "product_name": product_name,
            "summary": {"fail": 1, "warn": 0, "pass": 0},
            "reference_pack": reference_manifest,
            "failure_routing": [_routing_item(item) for item in findings],
            "review_findings": findings,
        }
    render_script = skill_dir / "scripts" / "render_html.py"
    consistency_script = skill_dir / "scripts" / "check_html_consistency.py"
    validate_script = skill_dir / "scripts" / "validate_html.py"
    context_budget_script = skill_dir / "scripts" / "check_context_budget.py"
    brief_consistency_script = skill_dir / "scripts" / "check_module_brief_consistency.py"

    context_budget_result = _run_command([sys.executable, str(context_budget_script), str(work_dir), "--json"])
    context_budget_report = _parse_json_stdout(context_budget_result)
    compression_report = {"status": "skipped", "artifacts": {}}
    if context_budget_result["returncode"] != 0:
        compression_report = ensure_compressed_requirements(work_dir, force=True)
        context_budget_result = _run_command([sys.executable, str(context_budget_script), str(work_dir), "--json"])
        context_budget_report = _parse_json_stdout(context_budget_result)
    if context_budget_result["returncode"] != 0:
        findings = [
            _make_html_finding(
                scope="all",
                page_or_sheet=item,
                layer="requirements",
                rule="CONTEXT_BUDGET",
                severity="error",
                message="上下文预算预检失败",
                repair_target="requirements",
                repair_action="rewrite_requirements",
                root_cause_hint="requirements 或 module_brief 超出预算，需要回到 requirements 层重整上下文",
                expected_fix_scope="requirements",
                stop_category="needs_refreeze",
            )
            for item in context_budget_report.get("failures", [])
        ]
        return {
            "work_dir": str(work_dir),
            "product_name": product_name,
            "summary": {"fail": 1, "warn": 0, "pass": 0},
            "context_budget": context_budget_report,
            "requirements_compression": compression_report,
            "failure_routing": [_routing_item(item) for item in findings],
            "review_findings": findings,
        }

    brief_consistency_report = {"summary": {"fail": 0, "warn": 0, "pass": 1}, "skipped": True}
    if (requirements_dir / "index.md").exists():
        brief_result = _run_command([sys.executable, str(brief_consistency_script), str(requirements_dir), "--json"])
        brief_consistency_report = _parse_json_stdout(brief_result)
        if brief_result["returncode"] != 0:
            compression_report = ensure_compressed_requirements(work_dir, force=True)
            brief_result = _run_command([sys.executable, str(brief_consistency_script), str(requirements_dir), "--json"])
            brief_consistency_report = _parse_json_stdout(brief_result)
        if brief_result["returncode"] != 0:
            fail_items = list(brief_consistency_report.get("missing_briefs", []))
            for item in brief_consistency_report.get("missing_pages", []):
                fail_items.extend(item.get("pages", []))
            for item in brief_consistency_report.get("low_coverage_modules", []):
                fail_items.append(item.get("module", ""))
            findings = [
                _make_html_finding(
                    scope="all",
                    page_or_sheet=item,
                    layer="module_brief",
                    rule="MODULE_BRIEF",
                    severity="error",
                    message="module_brief 覆盖率校验失败",
                    repair_target="module_brief",
                    repair_action="rewrite_module_brief",
                    root_cause_hint="module_brief 缺失或覆盖不足，需要重冻模块摘要",
                    expected_fix_scope="module_brief",
                    stop_category="needs_refreeze",
                )
                for item in fail_items
                if item
            ]
            return {
                "work_dir": str(work_dir),
                "product_name": product_name,
                "summary": {"fail": 1, "warn": 0, "pass": 0},
                "context_budget": context_budget_report,
                "requirements_compression": compression_report,
                "module_brief_consistency": brief_consistency_report,
                "failure_routing": [_routing_item(item) for item in findings],
                "review_findings": findings,
            }

    rendered_pages: list[dict] = []
    body_slot_artifacts: list[dict] = []
    page_specs = sorted(page_specs_dir.glob("page_spec_*.md"))
    render_failures = []
    for spec_path in page_specs:
        enrich_page_spec_file(spec_path, reference_manifest)
        result = _run_command(
            [
                sys.executable,
                str(render_script),
                str(spec_path),
                str(prototypes_dir),
                "--body-slots-dir",
                str(body_slots_dir),
                "--json",
            ]
        )
        if result["returncode"] != 0:
            render_failures.append({"page_spec": str(spec_path), **result})
            continue
        render_payload = _parse_json_stdout(result)
        rendered_pages.extend(render_payload.get("rendered_pages", []))
        body_slot_artifacts.extend(
            [
                {
                    "page_name": item.get("page_name", ""),
                    **item.get("body_slot_artifacts", {}),
                }
                for item in render_payload.get("rendered_pages", [])
                if item.get("body_slot_artifacts")
            ]
        )
    if render_failures:
        findings = [
            _make_html_finding(
                scope="all",
                page_or_sheet=item["page_spec"],
                layer="html_render",
                rule=_render_failure_rule(item),
                severity="error",
                message="HTML 渲染失败",
                repair_target="html_render",
                repair_action="patch_renderer",
                root_cause_hint="HTML 渲染脚本或模板输出失败，应进入 renderer 修复",
                expected_fix_scope="html_render",
                stop_category="needs_skill_patch",
            )
            for item in render_failures
        ]
        return {
            "work_dir": str(work_dir),
            "product_name": product_name,
            "summary": {"fail": 1, "warn": 0, "pass": 0},
            "render_failures": render_failures,
            "failure_routing": [_routing_item(item) for item in findings],
            "review_findings": findings,
        }

    all_pages = []
    for spec_path in page_specs:
        spec = parse_page_spec(spec_path)
        for page in spec.get("pages", []):
            all_pages.append({"module_name": spec.get("module_name", ""), **page})
    (prototypes_dir / "index.html").write_text(render_index_html(product_name, all_pages), encoding="utf-8")

    consistency_scope = _consistency_scope(product_name)
    consistency_result = _run_command([sys.executable, str(consistency_script), str(requirements_dir), str(prototypes_dir), "--json"])
    consistency_report = _parse_json_stdout(consistency_result)
    validation_result = _run_command([sys.executable, str(validate_script), str(prototypes_dir), "--json"])
    html_validation = _parse_json_stdout(validation_result)
    generated_meta = _load_generated_page_meta(prototypes_dir)
    review_findings = _collect_review_findings(
        scope=consistency_scope,
        consistency=consistency_report,
        html_validation=html_validation,
        requirements_dir=requirements_dir,
        generated_meta=generated_meta,
    )
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
            "reference_pack": str(artifact_dir / "reference_pack"),
            "body_slots_dir": str(body_slots_dir),
        },
        "body_generation": {
            "page_count": len(body_slot_artifacts),
            "artifacts": body_slot_artifacts,
        },
        "coverage": {
            "missing_pages": consistency_report.get("missing_pages", []),
            "low_coverage_pages": consistency_report.get("low_coverage_pages", []),
        },
        "validator_results": html_validation,
        "context_budget": context_budget_report,
        "requirements_compression": compression_report,
        "module_brief_consistency": brief_consistency_report,
        "consistency_scope": consistency_scope,
        "consistency": consistency_report,
        "final_validation": html_validation,
        "reference_pack": reference_manifest,
        "failure_routing": [_routing_item(item) for item in review_findings if item["severity"] == "error"],
        "review_findings": review_findings,
        "summary": {"fail": fail, "warn": 0, "pass": 1 if fail == 0 else 0},
    }


def _render_failure_rule(result: dict) -> str:
    text = f"{result.get('stderr', '')}\n{result.get('stdout', '')}"
    if "BODY_RENDER:" in text:
        return "BODY_RENDER"
    if "BODY_CONTRACT:" in text:
        return "BODY_CONTRACT"
    return "RENDER"


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
