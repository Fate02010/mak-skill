#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from html_utils import parse_page_spec, to_markdown
from requirements_compression import ensure_compressed_requirements, _build_module_brief_markdown as build_compressed_module_brief_markdown
from reference_utils import ensure_reference_pack
from requirements_utils import (
    default_actions_for_page,
    default_states_for_page,
    infer_object_name,
    infer_page_semantics,
    infer_page_shape,
    infer_terminal_type_from_module,
    parse_requirement_modules,
    safe_slug,
)


RENDERER_BASELINE_FILES = {
    "scripts/html_utils.py": "templates/html_utils_renderer_baseline.py",
    "scripts/render_html.py": "templates/render_html_renderer_baseline.py",
    "templates/common.css": "templates/common_renderer_baseline.css",
}
HTML_RENDERER_REGRESSION_TESTS = [
    "tests.test_prototype_generator_drawio.PrototypeGeneratorDrawioTests.test_html_renderer_login_page_excludes_admin_navigation",
    "tests.test_prototype_generator_drawio.PrototypeGeneratorDrawioTests.test_html_renderer_list_page_contains_filter_table_and_pagination",
    "tests.test_prototype_generator_drawio.PrototypeGeneratorDrawioTests.test_html_renderer_detail_page_keeps_detail_skeleton_for_h8",
    "tests.test_prototype_generator_drawio.PrototypeGeneratorDrawioTests.test_html_renderer_confirm_page_distinguishes_primary_and_secondary_actions_for_h9",
    "tests.test_prototype_generator_drawio.PrototypeGeneratorDrawioTests.test_html_renderer_outputs_consistency_markers",
    "tests.test_prototype_generator_drawio.PrototypeGeneratorDrawioTests.test_render_html_writes_body_slot_artifacts",
]


def repair_drawio_page_models(
    requirements_dir: str | Path,
    page_models_dir: str | Path,
    findings: list[dict],
) -> list[dict]:
    requirements = parse_requirement_modules(requirements_dir)
    page_models_root = Path(page_models_dir)
    changes: list[dict] = []
    target_pages = _target_pages(findings)
    for model_path in sorted(page_models_root.glob("page_model_*.json")):
        model = json.loads(model_path.read_text(encoding="utf-8"))
        module_name = str(model.get("module_name", "")).strip()
        module_req = requirements.get(module_name)
        if not module_req:
            continue
        changed = False
        existing = {page.get("page_name", ""): page for page in model.get("pages", []) if isinstance(page, dict)}
        for page_name, req in module_req["pages"].items():
            if target_pages and page_name not in target_pages:
                continue
            if page_name not in existing:
                model.setdefault("pages", []).append(_build_page_model_stub(model, req))
                changed = True
                continue
            page = existing[page_name]
            page_fields = [str(item.get("name", "")).strip() for item in page.get("fields", []) if isinstance(item, dict)]
            for field_name in req.get("fields", []):
                if field_name not in page_fields:
                    page.setdefault("fields", []).append(
                        {"name": field_name, "control": "input", "required": False, "validation": ""}
                    )
                    page_fields.append(field_name)
                    changed = True
            if str(page.get("page_type", "")).strip() in {"web_list", "mobile_list"}:
                table_columns = list(page.get("table_columns", []))
                for field_name in req.get("fields", []):
                    if field_name not in table_columns and len(table_columns) < 8:
                        table_columns.append(field_name)
                        changed = True
                page["table_columns"] = table_columns
            action_names = [str(item.get("name", "")).strip() for item in page.get("actions", []) if isinstance(item, dict)]
            for action_name in req.get("actions", []):
                if action_name not in action_names:
                    page.setdefault("actions", []).append(
                        {"name": action_name, "target": req.get("page_name", ""), "kind": "primary" if not action_names else "secondary"}
                    )
                    action_names.append(action_name)
                    changed = True
            status_values = list(page.get("status_values", []))
            for status in req.get("states", []):
                if status not in status_values:
                    status_values.append(status)
                    changed = True
            if status_values:
                page["status_values"] = status_values
            page.setdefault("states", {})
            if "loading" not in page["states"] or "占位" in str(page["states"].get("loading", "")):
                page["states"]["loading"] = "加载中显示骨架屏"
                changed = True
            if "error" not in page["states"]:
                page["states"]["error"] = "失败后允许重试"
                changed = True
        if changed:
            model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changes.append({"path": str(model_path), "module_name": module_name})
    handled_modules = {item["module_name"] for item in changes}
    existing_modules = {json.loads(path.read_text(encoding="utf-8")).get("module_name", "") for path in page_models_root.glob("page_model_*.json")}
    for module_name, module_req in requirements.items():
        if module_name in existing_modules or module_name in handled_modules:
            continue
        if target_pages and not any(page_name in target_pages for page_name in module_req["pages"]):
            continue
        terminal_type, terminal_name = infer_terminal_type_from_module(module_name)
        payload = {
            "terminal_type": terminal_type,
            "terminal_name": terminal_name,
            "module_name": module_name,
            "module_key": safe_slug(module_name, "module"),
            "pages": [_build_page_model_stub({"module_name": module_name}, req) for req in module_req["pages"].values()],
        }
        path = page_models_root / f"page_model_{safe_slug(module_name, 'module')}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        changes.append({"path": str(path), "module_name": module_name})
    return changes


def repair_html_page_specs(
    requirements_dir: str | Path,
    page_specs_dir: str | Path,
    findings: list[dict],
    *,
    force_rebuild_layout: bool = False,
) -> list[dict]:
    requirements = parse_requirement_modules(requirements_dir)
    page_specs_root = Path(page_specs_dir)
    changes: list[dict] = []
    target_pages = _target_pages(findings)
    rebuild_pages = set()
    if force_rebuild_layout:
        rebuild_pages.update(target_pages)
    for finding in findings:
        if str(finding.get("repair_action", "")) in {"rewrite_module_brief", "rewrite_requirements"}:
            page = str(finding.get("page_or_sheet", "")).strip()
            if page and "/" not in page and not page.endswith((".md", ".html", ".json", ".xml")):
                rebuild_pages.add(page)
        if str(finding.get("rule", "")) == "LAYOUT_MISMATCH":
            page = str(finding.get("page_or_sheet", "")).strip()
            if page:
                rebuild_pages.add(page)

    module_specs: dict[str, tuple[Path, dict]] = {}
    for spec_path in sorted(page_specs_root.glob("page_spec_*.md")):
        spec = parse_page_spec(spec_path)
        module_specs[spec.get("module_name", "")] = (spec_path, spec)

    for module_name, module_req in requirements.items():
        if module_name in module_specs:
            spec_path, spec = module_specs[module_name]
        else:
            spec = {
                "module_name": module_name,
                "module_key": safe_slug(module_name, "module"),
                "output_format": "html",
                "pages": [],
            }
            spec_path = page_specs_root / f"page_spec_{safe_slug(module_name, 'module')}.md"
        changed = False
        existing = {page.get("page_name", ""): page for page in spec.get("pages", [])}
        for page_name, req in module_req["pages"].items():
            req = {**req, "module_name": module_name}
            if target_pages and page_name not in target_pages and page_name not in rebuild_pages:
                continue
            if page_name not in existing:
                spec.setdefault("pages", []).append(_build_html_page_stub(req))
                changed = True
                continue
            if page_name in rebuild_pages:
                replacement = _build_html_page_stub(req)
                original = existing[page_name]
                replacement["output_file"] = original.get("output_file") or replacement["output_file"]
                replacement["is_nav_page"] = bool(original.get("is_nav_page", replacement["is_nav_page"]))
                spec["pages"] = [replacement if page.get("page_name", "") == page_name else page for page in spec.get("pages", [])]
                existing[page_name] = replacement
                changed = True
                continue
            page = existing[page_name]
            field_names = [field.get("name", "") for field in page.get("fields", [])]
            for field in req.get("fields", []):
                if field not in field_names:
                    page.setdefault("fields", []).append({"name": field, "control": "input", "required": "否", "note": ""})
                    field_names.append(field)
                    changed = True
            column_names = [column.get("name", "") for column in page.get("table_columns", [])]
            if str(page.get("page_type", "")).strip() in {"web_list", "mobile_list"}:
                for field in req.get("fields", []):
                    if field not in column_names and len(column_names) < 8:
                        page.setdefault("table_columns", []).append({"name": field, "note": ""})
                        column_names.append(field)
                        changed = True
            for action in req.get("actions", []):
                if action not in page.get("actions", []):
                    page.setdefault("actions", []).append(action)
                    changed = True
            for state in req.get("states", []):
                if state not in page.get("states", []):
                    page.setdefault("states", []).append(state)
                    changed = True
            inferred_type, inferred_archetype = infer_page_shape(page_name)
            if not page.get("page_archetype"):
                page["page_archetype"] = inferred_archetype
                changed = True
            if not page.get("page_type"):
                page["page_type"] = inferred_type
                changed = True
        if changed:
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(to_markdown(spec), encoding="utf-8")
            changes.append({"path": str(spec_path), "module_name": module_name})
    return changes


def repair_html_module_briefs(
    requirements_dir: str | Path,
    findings: list[dict],
) -> list[dict]:
    requirements_root = Path(requirements_dir)
    briefs_dir = requirements_root / "module_briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)
    requirements = parse_requirement_modules(requirements_root)
    target_modules = _target_modules(requirements, findings)
    changes: list[dict] = []
    for module_name, module_req in requirements.items():
        if target_modules and module_name not in target_modules:
            continue
        brief_path = briefs_dir / f"模块摘要_{module_name}.md"
        brief_text = build_compressed_module_brief_markdown(module_name, module_req)
        if not brief_path.exists() or brief_path.read_text(encoding="utf-8") != brief_text:
            brief_path.write_text(brief_text, encoding="utf-8")
            changes.append({"path": str(brief_path), "module_name": module_name})
    return changes


def repair_html_requirements(
    requirements_dir: str | Path,
    findings: list[dict],
) -> list[dict]:
    requirements_root = Path(requirements_dir)
    report = ensure_compressed_requirements(requirements_root.parent, force=True)
    changes: list[dict] = []
    for path in report.get("changed_paths", []):
        module_name = "requirements"
        if "模块摘要_" in path:
            module_name = Path(path).stem.replace("模块摘要_", "", 1)
        elif path.endswith("详细需求文档_overview.md"):
            module_name = "overview"
        elif path.endswith("index.md"):
            module_name = "index"
        changes.append({"path": str(path), "module_name": module_name})
    return changes


def repair_html_reference_pack(
    work_dir: str | Path,
    findings: list[dict],
) -> list[dict]:
    manifest = ensure_reference_pack(work_dir)
    changes = [{"path": str(Path(manifest["reference_pack_dir"]) / "manifest.json"), "module_name": "reference_pack"}]
    for module in manifest.get("modules", []):
        summary_file = module.get("summary_file")
        if summary_file:
            changes.append({"path": str(summary_file), "module_name": module.get("module_name", "")})
    return changes


def repair_html_renderer(
    skill_dir: str | Path,
    findings: list[dict],
) -> list[dict]:
    root = Path(skill_dir)
    changes: list[dict] = []
    for target_rel, baseline_rel in RENDERER_BASELINE_FILES.items():
        target_path = root / target_rel
        baseline_path = root / baseline_rel
        if not baseline_path.exists():
            continue
        baseline_text = baseline_path.read_text(encoding="utf-8")
        current_text = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        if current_text != baseline_text:
            target_path.write_text(baseline_text, encoding="utf-8")
            changes.append({"path": str(target_path), "module_name": "html_renderer"})
    return changes


def run_html_renderer_regression_suite(skill_dir: str | Path) -> dict:
    repo_root = Path(skill_dir).resolve().parents[2]
    cmd = [sys.executable, "-m", "unittest", *HTML_RENDERER_REGRESSION_TESTS]
    completed = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root, check=False)
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "cmd": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def apply_html_repairs(
    work_dir: str | Path,
    findings: list[dict],
    *,
    skill_dir: str | Path | None = None,
) -> dict:
    root = Path(work_dir)
    requirements_dir = root / "requirements"
    artifact_dir = root / ".prototype-generator"
    page_specs_dir = artifact_dir / "page_specs"
    grouped = _group_findings_by_action(findings)
    changes: list[dict] = []
    executed_actions: list[str] = []
    attempted_fix_scopes: list[str] = []
    skill_dir = Path(skill_dir) if skill_dir else Path(__file__).resolve().parents[1]
    regression = {"status": "skipped", "cmd": [], "returncode": 0, "stdout": "", "stderr": ""}

    if grouped.get("rebuild_reference_pack"):
        changes.extend(repair_html_reference_pack(root, grouped["rebuild_reference_pack"]))
        executed_actions.append("rebuild_reference_pack")
        attempted_fix_scopes.append("reference_pack")

    if grouped.get("rewrite_requirements"):
        changes.extend(repair_html_requirements(requirements_dir, grouped["rewrite_requirements"]))
        executed_actions.append("rewrite_requirements")
        attempted_fix_scopes.append("requirements")

    if grouped.get("rewrite_module_brief"):
        changes.extend(repair_html_module_briefs(requirements_dir, grouped["rewrite_module_brief"]))
        executed_actions.append("rewrite_module_brief")
        attempted_fix_scopes.append("module_brief")

    page_spec_findings = list(grouped.get("rewrite_page_spec", []))
    force_rebuild_layout = bool(grouped.get("rewrite_module_brief") or grouped.get("rewrite_requirements"))
    if force_rebuild_layout:
        page_spec_findings.extend(grouped.get("rewrite_module_brief", []))
        page_spec_findings.extend(grouped.get("rewrite_requirements", []))
    if page_spec_findings:
        changes.extend(
            repair_html_page_specs(
                requirements_dir,
                page_specs_dir,
                page_spec_findings,
                force_rebuild_layout=force_rebuild_layout,
            )
        )
        executed_actions.append("rewrite_page_spec")
        attempted_fix_scopes.append("page_spec")

    if grouped.get("patch_renderer"):
        changes.extend(repair_html_renderer(skill_dir, grouped["patch_renderer"]))
        executed_actions.append("patch_renderer")
        attempted_fix_scopes.append("html_render")
        regression = run_html_renderer_regression_suite(skill_dir)

    blocked_findings = []
    status = "ok"
    if regression.get("status") == "failed":
        status = "blocked"
        blocked_findings = list(grouped.get("patch_renderer", []))
    return {
        "status": status,
        "changes": changes,
        "executed_actions": executed_actions,
        "attempted_fix_scopes": attempted_fix_scopes,
        "regression": regression,
        "blocked_findings": blocked_findings,
    }


def _build_page_model_stub(model: dict, req: dict) -> dict:
    module_name = str(model.get("module_name", ""))
    page_name = req.get("page_name", "")
    page_type, archetype = infer_page_shape(page_name)
    object_name = req.get("object_name") or infer_object_name(page_name, module_name)
    fields = [
        {"name": field, "control": "input", "required": False, "validation": ""}
        for field in (req.get("fields", []) or [object_name, "状态"])
    ]
    actions = [
        {"name": action, "target": page_name, "kind": "primary" if idx == 0 else "secondary"}
        for idx, action in enumerate(req.get("actions", []) or default_actions_for_page(page_name, object_name))
    ]
    page = {
        "page_id": safe_slug(page_name, "page"),
        "page_name": page_name,
        "page_type": page_type,
        "page_archetype": archetype,
        "object_name": object_name,
        "role": "系统用户",
        "purpose": f"承载{page_name}核心操作",
        "nav_context": module_name,
        "fields": fields,
        "actions": actions,
        "status_values": req.get("states", []) or default_states_for_page(page_name),
        "states": {
            "loading": "加载中显示骨架屏",
            "error": "失败后允许重试",
        },
    }
    if page_type in {"web_list", "mobile_list"}:
        page["table_columns"] = list(req.get("fields", [])[:8] or ["名称", "状态", "更新时间"])
    if any(action["name"].startswith("新增") for action in actions):
        page["needs_crud"] = True
    return page


def _build_html_page_stub(req: dict) -> dict:
    page_name = req.get("page_name", "")
    page_type, page_archetype = infer_page_shape(page_name)
    module_name = req.get("module_name", "")
    semantics = infer_page_semantics(module_name, page_name, page_type, page_archetype)
    return {
        "page_name": page_name,
        "page_type": semantics.get("page_type", page_type),
        "page_archetype": semantics.get("page_archetype", page_archetype),
        "output_file": f"{safe_slug(page_name, 'page')}.html",
        "is_nav_page": semantics.get("is_nav_page", False),
        "is_entry_page": semantics.get("is_entry_page", False),
        "nav_group": semantics.get("nav_group", ""),
        "nav_parent": semantics.get("nav_parent", ""),
        "nav_label": semantics.get("nav_label", page_name),
        "nav_context": semantics.get("nav_context", ""),
        "shell_variant": semantics.get("shell_variant", ""),
        "design_system": semantics.get("design_system", ""),
        "reference_basis": "fallback",
        "reference_pack_file": "",
        "reference_summary": "",
        "reference_sources": [],
        "layout_directives": [],
        "visual_cues": [],
        "interaction_patterns": [],
        "fields": [{"name": field, "control": "input", "required": "否", "note": ""} for field in req.get("fields", [])],
        "table_columns": [{"name": field, "note": ""} for field in req.get("fields", [])[:8]],
        "actions": req.get("actions", []) or default_actions_for_page(page_name, infer_object_name(page_name)),
        "jumps": [{"action": action, "target": page_name} for action in (req.get("actions", [])[:1] or ["查看详情"])],
        "states": req.get("states", []) or default_states_for_page(page_name),
    }


def _target_pages(findings: list[dict]) -> set[str]:
    return {
        value
        for finding in findings
        for value in [str(finding.get("page_or_sheet", "")).strip()]
        if value and "/" not in value and not value.endswith((".json", ".md", ".drawio", ".html", ".xml"))
    }


def _target_modules(requirements: dict[str, dict], findings: list[dict]) -> set[str]:
    target_pages = _target_pages(findings)
    explicit_modules = {
        value
        for finding in findings
        for value in [str(finding.get("module_name", "")).strip(), str(finding.get("page_or_sheet", "")).strip()]
        if value in requirements
    }
    if explicit_modules:
        return explicit_modules
    modules = set()
    for module_name, module_req in requirements.items():
        if any(page_name in target_pages for page_name in module_req["pages"]):
            modules.add(module_name)
    return modules


def _index_requires_refresh(index_path: Path, requirements: dict[str, dict]) -> bool:
    if not index_path.exists():
        return True
    text = index_path.read_text(encoding="utf-8")
    return any(module_name not in text for module_name in requirements)


def _group_findings_by_action(findings: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for finding in findings:
        if str(finding.get("severity", "error")) != "error":
            continue
        action = str(finding.get("repair_action", "")).strip() or "rewrite_page_spec"
        grouped.setdefault(action, []).append(finding)
    return grouped
