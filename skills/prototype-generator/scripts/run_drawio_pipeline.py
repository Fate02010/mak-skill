#!/usr/bin/env python3
"""
run_drawio_pipeline.py - 在真实 WORK_DIR 上编排 draw.io 生成与交付门禁。

用法:
    python3 run_drawio_pipeline.py <work_dir> <product_name> [--max-parallel 3] [--keep-tmp] [--json]

职责:
    - 从 WORK_DIR/.prototype-generator/page_models/*.json 构建 page_specs
    - 渲染模块级 tmp xml
    - 运行 requirements/page_specs 一致性检查
    - 校验模块 tmp xml
    - 合并最终 prototypes/[product_name].drawio
    - 校验最终 .drawio
    - 输出失败路由建议，供主进程决定回退到 page_model / page_spec / render-merge

说明:
    本脚本负责真实产物级门禁，不直接改写 page_model/page_spec 业务语义。
    若校验失败，应由主进程或上层 agent 根据 failure routing 回到上游修复后重跑本脚本。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import shutil
import subprocess
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rulepack as RULEPACK


RULE_TO_LAYER = {
    "C10": "page_model",
    "C11": "page_model",
    "C13": "page_model",
    "C15": "page_spec",
    "C16": "page_model",
    "C17": "render_merge",
    "C18": "page_model",
}


def _consistency_scope(product_name: str) -> str:
    text = str(product_name or "")
    scopes = []
    if "后台" in text:
        scopes.append("admin")
    if "小程序" in text:
        scopes.append("miniapp")
    if "H5" in text:
        scopes.append("h5")
    if "大屏" in text:
        scopes.append("bigscreen")
    if "官网" in text or "门户" in text:
        scopes.append("portal")
    if "工控机" in text or "HMI" in text:
        scopes.append("industrial")
    if any(token in text for token in ("APP", "App", "移动端")):
        scopes.append("app")
    scopes = list(dict.fromkeys(scopes))
    if len(scopes) == 1:
        return scopes[0]
    if len(scopes) > 1:
        return "mixed"
    return "auto"


def _run_command(cmd: list[str]) -> dict:
    completed = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _parse_json_stdout(result: dict) -> dict:
    stdout = (result.get("stdout") or "").strip()
    if not stdout:
        return {}
    return json.loads(stdout)


def _module_suffix(model_path: Path) -> str:
    name = model_path.stem
    if name.startswith("page_model_"):
        return name[len("page_model_"):]
    return name


def _parallel_map(items: list, max_parallel: int, fn):
    results = []
    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        future_map = {executor.submit(fn, item): item for item in items}
        for future in as_completed(future_map):
            item = future_map[future]
            try:
                results.append((item, future.result()))
            except Exception as exc:  # pragma: no cover - defensive
                results.append((item, {"returncode": 1, "stdout": "", "stderr": str(exc), "cmd": []}))
    return results


def _collect_failure_routing(consistency_report: dict, tmp_reports: list[tuple[Path, dict]], final_report: dict) -> list[dict]:
    routing = []
    if consistency_report.get("missing_pages"):
        routing.append({
            "layer": "page_model",
            "reason": "requirements 与 page_specs 缺页",
            "pages": consistency_report["missing_pages"],
        })
    if consistency_report.get("missing_field_pages"):
        routing.append({
            "layer": "page_spec",
            "reason": "page_specs 字段覆盖不足",
            "pages": [item["page"] for item in consistency_report["missing_field_pages"]],
        })
    if consistency_report.get("low_coverage_pages"):
        routing.append({
            "layer": "page_model",
            "reason": "字段覆盖率过低",
            "pages": [item["page"] for item in consistency_report["low_coverage_pages"]],
        })
    if consistency_report.get("action_mismatch_pages"):
        routing.append({
            "layer": "page_model",
            "reason": "页面动作与需求不一致",
            "pages": [item["page"] for item in consistency_report["action_mismatch_pages"]],
        })
    if consistency_report.get("layout_mismatch_pages"):
        routing.append({
            "layer": "page_spec",
            "reason": "页面骨架与需求不一致",
            "pages": [item["page"] for item in consistency_report["layout_mismatch_pages"]],
        })

    for tmp_xml, report in tmp_reports:
        for item in report.get("results", []):
            if item.get("status") != "FAIL":
                continue
            routing.append({
                "layer": RULE_TO_LAYER.get(item["rule"], "page_spec"),
                "reason": f"{tmp_xml.name}: {item['rule']}",
                "pages": item.get("details", []),
            })

    for item in final_report.get("results", []):
        if item.get("status") != "FAIL":
            continue
        routing.append({
            "layer": RULE_TO_LAYER.get(item["rule"], "page_spec"),
            "reason": f"final: {item['rule']}",
            "pages": item.get("details", []),
        })
    return routing


def _print_human_summary(report: dict):
    print("=== draw.io pipeline ===")
    print(f"work_dir: {report['work_dir']}")
    print(f"product: {report['product_name']}")
    print(f"page_models: {report['page_model_count']}")
    print(f"final_drawio: {report['final_drawio']}")
    print(
        f"summary: fail={report['summary']['fail']} "
        f"warn={report['summary']['warn']} pass={report['summary']['pass']}"
    )
    if report["failure_routing"]:
        print("failure_routing:")
        for item in report["failure_routing"]:
            pages = ", ".join(item["pages"][:5]) if item["pages"] else "-"
            print(f"- {item['layer']}: {item['reason']} | {pages}")


def main():
    parser = argparse.ArgumentParser(description="运行真实 WORK_DIR 上的 draw.io 交付门禁")
    parser.add_argument("work_dir")
    parser.add_argument("product_name")
    parser.add_argument("--max-parallel", type=int, default=3)
    parser.add_argument("--keep-tmp", action="store_true")
    parser.add_argument("--rulepack", default="")
    parser.add_argument("--rulepack-override", default="")
    parser.add_argument("--dump-rulepack", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    max_parallel = max(1, min(int(args.max_parallel), 3))
    skill_dir = Path(__file__).resolve().parents[1]
    work_dir = Path(args.work_dir).resolve()
    artifact_dir = work_dir / ".prototype-generator"
    page_models_dir = artifact_dir / "page_models"
    page_specs_dir = artifact_dir / "page_specs"
    tmp_dir = artifact_dir / "tmp"
    review_tmp_dir = artifact_dir / "review_tmp"
    requirements_dir = work_dir / "requirements"
    prototypes_dir = work_dir / "prototypes"
    final_drawio = prototypes_dir / f"{args.product_name}.drawio"
    active_rulepack_path = artifact_dir / "active_rulepack.json"

    page_specs_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    prototypes_dir.mkdir(parents=True, exist_ok=True)

    if not page_models_dir.is_dir():
        raise SystemExit(f"page_models 目录不存在: {page_models_dir}")
    if not requirements_dir.is_dir():
        raise SystemExit(f"requirements 目录不存在: {requirements_dir}")

    for stale in tmp_dir.glob("drawio_*_tmp.xml"):
        stale.unlink()

    build_script = skill_dir / "scripts" / "build_page_spec.py"
    render_script = skill_dir / "scripts" / "render.py"
    validate_script = skill_dir / "scripts" / "validate.py"
    merge_script = skill_dir / "scripts" / "merge.py"
    consistency_script = skill_dir / "scripts" / "check_prototype_consistency.py"
    brief_consistency_script = skill_dir / "scripts" / "check_module_brief_consistency.py"
    context_budget_script = skill_dir / "scripts" / "check_context_budget.py"
    styles_md = skill_dir / "steps" / "step5-component-styles.md"

    page_models = sorted(page_models_dir.glob("page_model_*.json"))
    if not page_models:
        raise SystemExit(f"未找到 page_model_*.json: {page_models_dir}")

    effective_rulepack = RULEPACK.resolve_effective_rulepack(
        explicit_name=args.rulepack or None,
        work_dir=str(work_dir),
        override_path=args.rulepack_override or None,
    )
    active_rulepack_payload = RULEPACK.build_active_rulepack_metadata(effective_rulepack)
    active_rulepack_path.write_text(
        json.dumps(active_rulepack_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    context_budget_result = _run_command([sys.executable, str(context_budget_script), str(work_dir), "--json"])
    context_budget_report = _parse_json_stdout(context_budget_result)
    if context_budget_result["returncode"] != 0:
        report = {
            "work_dir": str(work_dir),
            "product_name": args.product_name,
            "page_model_count": len(page_models),
            "final_drawio": str(final_drawio),
            "context_budget": context_budget_report,
            "summary": {"fail": 1, "warn": context_budget_report.get("summary", {}).get("warn", 0), "pass": 0},
            "failure_routing": [{"layer": "requirements", "reason": "上下文预算预检失败", "pages": context_budget_report.get("failures", [])}],
        }
        if args.json_output:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            _print_human_summary(report)
        raise SystemExit(1)

    brief_consistency_report = {
        "summary": {"fail": 0, "warn": 0, "pass": 1},
        "skipped": True,
    }
    if (requirements_dir / "index.md").exists():
        brief_consistency_result = _run_command([sys.executable, str(brief_consistency_script), str(requirements_dir), "--json"])
        brief_consistency_report = _parse_json_stdout(brief_consistency_result)
        if brief_consistency_result["returncode"] != 0:
            brief_fail_items = list(brief_consistency_report.get("missing_briefs", []))
            for item in brief_consistency_report.get("missing_pages", []):
                brief_fail_items.extend(item.get("pages", []))
            for item in brief_consistency_report.get("low_coverage_modules", []):
                brief_fail_items.append(item.get("module", ""))
            report = {
                "work_dir": str(work_dir),
                "product_name": args.product_name,
                "page_model_count": len(page_models),
                "final_drawio": str(final_drawio),
                "context_budget": context_budget_report,
                "module_brief_consistency": brief_consistency_report,
                "summary": {"fail": 1, "warn": context_budget_report.get("summary", {}).get("warn", 0), "pass": 0},
                "failure_routing": [{"layer": "requirements", "reason": "module_brief 覆盖率校验失败", "pages": [item for item in brief_fail_items if item]}],
            }
            if args.json_output:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                _print_human_summary(report)
            raise SystemExit(1)

    def build_task(model_path: Path) -> dict:
        suffix = _module_suffix(model_path)
        output_spec = page_specs_dir / f"page_spec_{suffix}.md"
        cmd = [sys.executable, str(build_script), str(model_path), str(output_spec)]
        if effective_rulepack.get("detected_pack") and effective_rulepack.get("detected_pack") != "base":
            cmd.extend(["--rulepack", effective_rulepack["detected_pack"]])
        return _run_command(cmd)

    build_results = _parallel_map(page_models, max_parallel, build_task)
    build_failures = [
        {"model": str(item), **result}
        for item, result in build_results
        if result["returncode"] != 0
    ]
    if build_failures:
        report = {
            "work_dir": str(work_dir),
            "product_name": args.product_name,
            "page_model_count": len(page_models),
            "final_drawio": str(final_drawio),
            "build_failures": build_failures,
            "summary": {"fail": 1, "warn": 0, "pass": 0},
            "failure_routing": [{"layer": "page_model", "reason": "page_spec 构建失败", "pages": [item["model"] for item in build_failures]}],
        }
        if args.json_output:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            _print_human_summary(report)
        raise SystemExit(1)

    page_specs = sorted(page_specs_dir.glob("page_spec_*.md"))

    def render_task(spec_path: Path) -> dict:
        suffix = spec_path.stem.replace("page_spec_", "", 1)
        tmp_xml = tmp_dir / f"drawio_{suffix}_tmp.xml"
        return _run_command([sys.executable, str(render_script), str(styles_md), str(spec_path), str(tmp_xml)])

    render_results = _parallel_map(page_specs, max_parallel, render_task)
    render_failures = [
        {"page_spec": str(item), **result}
        for item, result in render_results
        if result["returncode"] != 0
    ]
    if render_failures:
        report = {
            "work_dir": str(work_dir),
            "product_name": args.product_name,
            "page_model_count": len(page_models),
            "final_drawio": str(final_drawio),
            "render_failures": render_failures,
            "summary": {"fail": 1, "warn": 0, "pass": 0},
            "failure_routing": [{"layer": "render_merge", "reason": "模块渲染失败", "pages": [item["page_spec"] for item in render_failures]}],
        }
        if args.json_output:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            _print_human_summary(report)
        raise SystemExit(1)

    consistency_scope = _consistency_scope(args.product_name)
    consistency_result = _run_command(
        [
            sys.executable,
            str(consistency_script),
            str(requirements_dir),
            str(page_specs_dir),
            "--scope",
            consistency_scope,
            "--rulepack",
            effective_rulepack.get("detected_pack", "base"),
            "--json",
        ]
    )
    consistency_report = _parse_json_stdout(consistency_result)

    tmp_xmls = sorted(tmp_dir.glob("drawio_*_tmp.xml"))

    def validate_tmp_task(tmp_xml: Path) -> dict:
        return _run_command([
            sys.executable,
            str(validate_script),
            str(tmp_xml),
            "--rulepack",
            effective_rulepack.get("detected_pack", "base"),
            "--json",
        ])

    tmp_validate_results = _parallel_map(tmp_xmls, max_parallel, validate_tmp_task)
    tmp_reports: list[tuple[Path, dict]] = []
    for tmp_xml, result in tmp_validate_results:
        tmp_reports.append((tmp_xml, _parse_json_stdout(result)))

    merge_cmd = [sys.executable, str(merge_script), str(final_drawio), args.product_name]
    if args.keep_tmp:
        merge_cmd.append("--keep-tmp")
    merge_cmd.extend(["--rulepack", effective_rulepack.get("detected_pack", "base")])
    merge_cmd.extend(["--glob", str(tmp_dir / "drawio_*_tmp.xml")])
    merge_result = _run_command(merge_cmd)

    final_report = {}
    if merge_result["returncode"] == 0 and final_drawio.exists():
        final_result = _run_command([
            sys.executable,
            str(validate_script),
            str(final_drawio),
            "--rulepack",
            effective_rulepack.get("detected_pack", "base"),
            "--json",
        ])
        final_report = _parse_json_stdout(final_result)
    else:
        final_report = {
            "summary": {"fail": 1, "warn": 0, "pass": 0},
            "results": [
                {
                    "rule": "MERGE",
                    "name": "merge",
                    "status": "FAIL",
                    "count": 1,
                    "details": [merge_result.get("stderr", "").strip() or "merge 失败"],
                }
            ],
        }

    failure_routing = _collect_failure_routing(consistency_report, tmp_reports, final_report)

    fail = 0
    warn = 0
    if consistency_report.get("summary", {}).get("fail"):
        fail += 1
    if consistency_report.get("summary", {}).get("warn"):
        warn += 1
    for _, report in tmp_reports:
        fail += report.get("summary", {}).get("fail", 0)
        warn += report.get("summary", {}).get("warn", 0)
    fail += final_report.get("summary", {}).get("fail", 0)
    warn += final_report.get("summary", {}).get("warn", 0)

    report = {
        "work_dir": str(work_dir),
        "product_name": args.product_name,
        "page_model_count": len(page_models),
        "page_spec_count": len(page_specs),
        "tmp_xml_count": len(tmp_xmls),
        "max_parallel": max_parallel,
        "final_drawio": str(final_drawio),
        "active_rulepack": active_rulepack_payload,
        "active_rulepack_path": str(active_rulepack_path),
        "context_budget": context_budget_report,
        "module_brief_consistency": brief_consistency_report,
        "consistency": consistency_report,
        "consistency_scope": consistency_scope,
        "tmp_validations": {tmp_xml.name: payload for tmp_xml, payload in tmp_reports},
        "final_validation": final_report,
        "failure_routing": failure_routing,
        "summary": {
            "fail": fail,
            "warn": warn,
            "pass": 1 if fail == 0 else 0,
        },
    }

    if fail == 0 and not args.keep_tmp:
        shutil.rmtree(review_tmp_dir, ignore_errors=True)

    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human_summary(report)
        if args.dump_rulepack:
            print(json.dumps(active_rulepack_payload, ensure_ascii=False, indent=2))

    raise SystemExit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
