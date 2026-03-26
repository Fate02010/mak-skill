#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from html_utils import parse_page_spec, to_markdown
from requirements_utils import (
    default_actions_for_page,
    default_states_for_page,
    infer_object_name,
    infer_page_shape,
    infer_terminal_type_from_module,
    parse_requirement_modules,
    safe_slug,
)


def repair_drawio_page_models(
    requirements_dir: str | Path,
    page_models_dir: str | Path,
    findings: list[dict],
) -> list[dict]:
    requirements = parse_requirement_modules(requirements_dir)
    page_models_root = Path(page_models_dir)
    changes: list[dict] = []
    target_pages = {
        value
        for finding in findings
        for value in [str(finding.get("page_or_sheet", "")).strip()]
        if value and "/" not in value and not value.endswith((".json", ".md", ".drawio", ".html", ".xml"))
    }
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
            if "loading" not in page["states"]:
                page["states"]["loading"] = "加载中显示骨架屏"
                changed = True
            elif "占位" in str(page["states"].get("loading", "")):
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
) -> list[dict]:
    requirements = parse_requirement_modules(requirements_dir)
    page_specs_root = Path(page_specs_dir)
    changes: list[dict] = []
    target_pages = {
        value
        for finding in findings
        for value in [str(finding.get("page_or_sheet", "")).strip()]
        if value and "/" not in value and not value.endswith((".json", ".md", ".drawio", ".html", ".xml"))
    }
    target_page_set = {item for item in target_pages if item}
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
            if target_page_set and page_name not in target_page_set:
                continue
            if page_name not in existing:
                spec.setdefault("pages", []).append(_build_html_page_stub(req))
                changed = True
                continue
            page = existing[page_name]
            field_names = [field.get("name", "") for field in page.get("fields", [])]
            for field in req.get("fields", []):
                if field not in field_names:
                    page.setdefault("fields", []).append(
                        {"name": field, "control": "input", "required": "否", "note": ""}
                    )
                    changed = True
            column_names = [column.get("name", "") for column in page.get("table_columns", [])]
            if str(page.get("page_type", "")).strip() in {"web_list", "mobile_list"}:
                for field in req.get("fields", []):
                    if field not in column_names and len(column_names) < 8:
                        page.setdefault("table_columns", []).append({"name": field, "note": ""})
                        changed = True
            for action in req.get("actions", []):
                if action not in page.get("actions", []):
                    page.setdefault("actions", []).append(action)
                    changed = True
            for state in req.get("states", []):
                if state not in page.get("states", []):
                    page.setdefault("states", []).append(state)
                    changed = True
        if changed:
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(to_markdown(spec), encoding="utf-8")
            changes.append({"path": str(spec_path), "module_name": module_name})
    return changes


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
    page_type, _ = infer_page_shape(page_name)
    return {
        "page_name": page_name,
        "page_type": page_type,
        "output_file": f"{safe_slug(page_name, 'page')}.html",
        "is_nav_page": False,
        "fields": [{"name": field, "control": "input", "required": "否", "note": ""} for field in req.get("fields", [])],
        "table_columns": [{"name": field, "note": ""} for field in req.get("fields", [])[:8]],
        "actions": req.get("actions", []) or default_actions_for_page(page_name, infer_object_name(page_name)),
        "jumps": [{"action": action, "target": page_name} for action in (req.get("actions", [])[:1] or ["查看详情"])],
        "states": req.get("states", []) or default_states_for_page(page_name),
    }
