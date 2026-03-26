#!/usr/bin/env python3
"""
check_prototype_consistency.py - 检查 requirements 与 page_specs 的页面覆盖率和字段一致性。

用法:
    python3 check_prototype_consistency.py <requirements_path> <page_specs_dir> [--threshold 0.8] [--json]

约定:
    - requirements_path: requirements 目录，或单个需求文档文件
    - page_specs_dir: 固定为 WORK_DIR/.prototype-generator/page_specs
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rulepack as RULEPACK


ACTIVE_RULEPACK = RULEPACK.resolve_effective_rulepack(explicit_name="base")


def set_active_rulepack(rulepack: dict):
    global ACTIVE_RULEPACK
    ACTIVE_RULEPACK = rulepack or RULEPACK.resolve_effective_rulepack(explicit_name="base")


def normalize_name(value: str) -> str:
    return RULEPACK.normalize_token(value)


def canonical_page_name(value: str) -> str:
    return normalize_name(RULEPACK.canonical_page_name(value, ACTIVE_RULEPACK))


def canonical_action_name(value: str) -> str:
    return normalize_name(RULEPACK.canonical_action_name(value, ACTIVE_RULEPACK))


def split_page_names(raw: str) -> list[str]:
    text = raw.strip()
    if not text:
        return []
    parts = re.split(r"[、，,；;]\s*", text)
    return [part.strip() for part in parts if part.strip()]


def parse_md_table(lines: list[str], start_index: int) -> tuple[list[list[str]], int]:
    rows = []
    idx = start_index
    while idx < len(lines):
        line = lines[idx].strip()
        if not line.startswith("|"):
            break
        if re.match(r"^\|[\s\-:|]+\|$", line):
            idx += 1
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
        idx += 1
    return rows, idx


def add_token(container: set[str], value: str):
    token = re.sub(r"<[^>]+>", "", value or "").strip()
    token = token.split("（", 1)[0].split("(", 1)[0].strip()
    token = token.replace("：", " ").replace(":", " ")
    if token:
        container.add(token)


@dataclass
class RequirementPage:
    name: str
    scope: str
    fields: set[str] = field(default_factory=set)
    required_actions: set[str] = field(default_factory=set)
    expected_layout: str = ""


def collect_requirement_files(path: str) -> list[str]:
    if os.path.isfile(path):
        return [path]
    files = []
    for root, _, names in os.walk(path):
        for name in names:
            if name.endswith(".md"):
                files.append(os.path.join(root, name))
    return sorted(files)


def extract_fields_from_bullets(lines: list[str], start_index: int) -> tuple[list[str], int]:
    fields = []
    idx = start_index
    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped:
            idx += 1
            continue
        if stripped.startswith("#### ") or stripped.startswith("### ") or stripped.startswith("## "):
            break
        if stripped.startswith("- "):
            value = stripped[2:].strip()
            value = value.split("（", 1)[0].split("(", 1)[0].strip()
            if value and len(value) <= 30:
                fields.append(value)
            idx += 1
            continue
        break
    return fields, idx


def extract_actions(value: str) -> set[str]:
    actions = set()
    for item in re.split(r"[、，,/；;]\s*", str(value or "").strip()):
        cleaned = canonical_action_name(item)
        if cleaned:
            actions.add(cleaned)
    return actions


def infer_requirement_scope(path: str) -> str:
    name = os.path.basename(path)
    if "溯源展示" in name:
        return "trace"
    if "后台" in name:
        return "admin"
    lowered = name.lower()
    if "H5" in name or re.search(r"(^|[_-])h5([_-]|$)", lowered):
        return "h5"
    if "大屏" in name or any(token in lowered for token in ("bigscreen", "big_screen", "datav")):
        return "bigscreen"
    if "官网" in name or "门户" in name or "portal" in lowered:
        return "portal"
    if "工控机" in name or "HMI" in name or any(token in lowered for token in ("industrial", "ipc")):
        return "industrial"
    if "小程序" in name or "miniapp" in lowered or "wx" in lowered:
        return "miniapp"
    if "app" in lowered or "移动端" in name:
        return "app"
    return "all"


def infer_expected_layout(page_name: str) -> str:
    text = str(page_name or "")
    if "登录" in text:
        return "login"
    if any(token in text for token in ("分析", "报表", "看板")):
        return "dashboard"
    if "资源管理" in text or "品类管理" in text or "分类管理" in text or "部门管理" in text:
        return "tree_list"
    if "详情" in text:
        return "detail"
    if "发货弹窗" in text or "新增" in text or "编辑" in text:
        return "form_modal"
    if any(token in text for token in ("删除", "确认", "关闭")) and "弹窗" in text:
        return "confirm_modal"
    return "list"


def infer_generated_page_scope(page: dict) -> str:
    source = str(page.get("source", "")).lower()
    name = str(page.get("name", ""))
    module_name = str(page.get("module_name", ""))
    if "H5-" in module_name or re.search(r"(^|[_-])h5([_-]|$)", source):
        return "h5"
    if "大屏-" in module_name or any(token in source for token in ("bigscreen", "big_screen", "datav")):
        return "bigscreen"
    if "官网门户-" in module_name or "官网" in module_name or re.search(r"(^|[_-])portal([_-]|$)", source):
        return "portal"
    if "工控机-" in module_name or any(token in source for token in ("industrial", "ipc", "hmi")):
        return "industrial"
    if "后台" in module_name or "后台" in name or "admin_" in source:
        return "admin"
    if "小程序" in module_name or "小程序" in name or any(token in source for token in ("mini", "mobile", "wx")):
        return "miniapp"
    if "App-" in module_name or "APP-" in module_name or re.search(r"(^|[_-])app([_-]|$)", source):
        return "app"
    return "all"


def infer_generated_scope(generated_pages: dict[str, dict]) -> str:
    admin = 0
    miniapp = 0
    app = 0
    h5 = 0
    bigscreen = 0
    portal = 0
    industrial = 0
    for page in generated_pages.values():
        scope = infer_generated_page_scope(page)
        if scope == "admin":
            admin += 1
        elif scope == "miniapp":
            miniapp += 1
        elif scope == "app":
            app += 1
        elif scope == "h5":
            h5 += 1
        elif scope == "bigscreen":
            bigscreen += 1
        elif scope == "portal":
            portal += 1
        elif scope == "industrial":
            industrial += 1
    active_scopes = [
        scope
        for scope, count in (
            ("admin", admin),
            ("miniapp", miniapp),
            ("app", app),
            ("h5", h5),
            ("bigscreen", bigscreen),
            ("portal", portal),
            ("industrial", industrial),
        )
        if count
    ]
    if len(active_scopes) == 1:
        return active_scopes[0]
    if len(active_scopes) > 1:
        return "mixed"
    return "all"


def requirement_page_entry(mapping: list[RequirementPage], scope: str, name: str) -> RequirementPage:
    for page in mapping:
        if page.scope == scope and page.name == name:
            return page
    page = RequirementPage(name=name, scope=scope, expected_layout=infer_expected_layout(name))
    mapping.append(page)
    return page


def assign_fields_to_pages(
    pages: list[str],
    list_fields: set[str],
    form_fields: set[str],
    detail_fields: set[str],
    list_actions: set[str],
    detail_actions: set[str],
    mapping: list[RequirementPage],
    scope: str,
):
    list_like = [
        page for page in pages
        if any(token in page for token in ("列表", "管理")) and "详情" not in page and "弹窗" not in page and "抽屉" not in page
    ]
    form_like = [
        page for page in pages
        if any(token in page for token in ("新增", "编辑", "弹窗", "抽屉", "表单")) and "删除确认" not in page
    ]
    detail_like = [page for page in pages if "详情" in page]

    for page in pages:
        requirement_page_entry(mapping, scope, page)

    for page in list_like:
        entry = requirement_page_entry(mapping, scope, page)
        entry.fields.update(list_fields)
        entry.required_actions.update(list_actions)
    for page in form_like:
        requirement_page_entry(mapping, scope, page).fields.update(form_fields)
    for page in detail_like:
        entry = requirement_page_entry(mapping, scope, page)
        entry.fields.update(detail_fields)
        entry.required_actions.update(detail_actions)


def parse_requirement_file(path: str, mapping: list[RequirementPage]):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    scope = infer_requirement_scope(path)

    current_pages: list[str] = []
    list_fields: set[str] = set()
    form_fields: set[str] = set()
    detail_fields: set[str] = set()
    list_actions: set[str] = set()
    detail_actions: set[str] = set()

    def flush():
        if current_pages:
            assign_fields_to_pages(
                current_pages,
                list_fields,
                form_fields,
                detail_fields,
                list_actions,
                detail_actions,
                mapping,
                scope,
            )

    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()

        if line.startswith("#### "):
            flush()
            current_pages = []
            list_fields = set()
            form_fields = set()
            detail_fields = set()
            list_actions = set()
            detail_actions = set()
            idx += 1
            continue

        if line.startswith("- **页面/界面：**"):
            raw = line.split("**页面/界面：**", 1)[1].strip()
            current_pages = split_page_names(raw)
            for page in current_pages:
                requirement_page_entry(mapping, scope, page)
            idx += 1
            continue

        if "筛选条件：" in line:
            fields, idx = extract_fields_from_bullets(lines, idx + 1)
            list_fields.update(fields)
            continue

        if "列表展示列：" in line:
            table_rows, idx = parse_md_table(lines, idx + 1)
            if table_rows:
                for row in table_rows[1:]:
                    if row and row[0]:
                        list_fields.add(row[0])
                    if row and row[0] == "操作" and len(row) > 1:
                        list_actions.update(extract_actions(row[1]))
            continue

        if "新增/编辑表单字段规格" in line:
            table_rows, idx = parse_md_table(lines, idx + 1)
            if table_rows:
                for row in table_rows[1:]:
                    if row and row[0]:
                        form_fields.add(row[0])
            continue

        if "展示字段：" in line:
            raw = line.split("展示字段：", 1)[1].strip()
            detail_fields.update(split_page_names(raw))
            idx += 1
            continue

        if "操作按钮（按状态区分）" in line:
            idx += 1
            while idx < len(lines):
                stripped = lines[idx].strip()
                if not stripped.startswith("- "):
                    break
                if "可操作" in stripped:
                    detail_actions.update(extract_actions(stripped.split("：", 1)[1] if "：" in stripped else stripped))
                idx += 1
            continue

        idx += 1

    flush()


def parse_drawio_page_spec_file(path: str) -> dict[str, dict]:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    module_name = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            module_name = stripped[2:].strip()
            break

    swimlanes = {}
    elements = []
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line == "## swimlane 布局":
            rows, idx = parse_md_table(lines, idx + 1)
            if rows:
                for row in rows[1:]:
                    if len(row) >= 3:
                        swimlanes[row[0]] = {
                            "label": row[1],
                            "lane_type": row[2],
                            "values": set(),
                            "actions": set(),
                            "component_types": set(),
                        }
            continue
        if line == "## 元素列表":
            rows, idx = parse_md_table(lines, idx + 1)
            if rows:
                for row in rows[1:]:
                    if len(row) >= 5:
                        elements.append(row)
            continue
        idx += 1

    for row in elements:
        parent = row[1]
        component_type = row[2]
        value = row[3]
        if parent in swimlanes and value.strip():
            swimlanes[parent]["values"].add(value.strip())
            swimlanes[parent]["component_types"].add(component_type)
            if component_type.startswith("btn") or component_type == "text_link":
                swimlanes[parent]["actions"].add(canonical_action_name(value))

    def infer_generated_layout(label: str, lane_type: str, component_types: set[str], values: set[str]) -> str:
        label_text = str(label or "")
        text = " ".join([label_text, *sorted(values)])
        if lane_type == "modal":
            if any(token in text for token in ("发货备注", "关闭原因", "活动说明")) or any(
                token in component_types for token in ("input", "select", "textarea")
            ):
                return "form_modal"
            return "confirm_modal"
        if "登录" in label_text:
            return "login"
        if any(token in label_text for token in ("分析", "报表", "看板")):
            return "dashboard"
        if "资源管理" in label_text:
            if "pagination" in component_types or "list_row" not in component_types:
                return "list"
            return "tree_list"
        if "品类管理" in label_text or "分类管理" in label_text or "部门管理" in label_text:
            return "tree_list"
        if "详情" in label_text:
            return "detail"
        if "table_header" in component_types or "pagination" in component_types:
            return "list"
        return "list"

    result = {}
    for swimlane in swimlanes.values():
        corpus = " ".join(sorted(swimlane["values"]))
        result[swimlane["label"]] = {
            "name": swimlane["label"],
            "normalized": canonical_page_name(swimlane["label"]),
            "corpus": corpus,
            "source": os.path.basename(path),
            "module_name": module_name,
            "actions": sorted(action for action in swimlane["actions"] if action),
            "layout": infer_generated_layout(
                swimlane["label"],
                swimlane.get("lane_type", ""),
                swimlane.get("component_types", set()),
                swimlane["values"],
            ),
        }
    return result


def parse_generic_page_spec_file(path: str) -> dict[str, dict]:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    module_name = ""
    pages: dict[str, dict] = {}
    current: dict | None = None
    idx = 0

    while idx < len(lines):
        stripped = lines[idx].strip()

        if stripped.startswith("# ") and not module_name:
            module_name = stripped[2:].strip()
            idx += 1
            continue

        if stripped.startswith("## 页面规格：") or stripped.startswith("## 页面规格:"):
            name = stripped.split("：", 1)[1].strip() if "：" in stripped else stripped.split(":", 1)[1].strip()
            current = {
                "name": name,
                "normalized": canonical_page_name(name),
                "tokens": set(),
                "actions": set(),
            }
            pages[name] = current
            idx += 1
            continue

        if current is None:
            idx += 1
            continue

        if stripped.startswith("|"):
            rows, idx = parse_md_table(lines, idx)
            if rows:
                for row in rows[1:]:
                    for cell in row:
                        add_token(current["tokens"], cell)
            continue

        if stripped.startswith("- "):
            content = stripped[2:].strip()
            content = content.split("：", 1)[1].strip() if "：" in content else content.split(":", 1)[1].strip() if ":" in content else content
            for part in re.split(r"\s*(?:->|→)\s*", content):
                add_token(current["tokens"], part)
                current["actions"].update(extract_actions(part))
            idx += 1
            continue

        if stripped and not stripped.startswith("#"):
            add_token(current["tokens"], stripped)

        idx += 1

    result = {}
    for page in pages.values():
        result[page["name"]] = {
            "name": page["name"],
            "normalized": page["normalized"],
            "corpus": " ".join(sorted(page["tokens"])),
            "source": os.path.basename(path),
            "module_name": module_name,
            "actions": sorted(action for action in page.get("actions", set()) if action),
            "layout": infer_expected_layout(page["name"]),
        }
    return result


def load_page_specs(path: str) -> dict[str, dict]:
    result = {}
    for root, _, names in os.walk(path):
        for name in sorted(names):
            if not name.startswith("page_spec_") or not name.endswith(".md"):
                continue
            file_path = os.path.join(root, name)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "## swimlane 布局" in content and "## 元素列表" in content:
                file_result = parse_drawio_page_spec_file(file_path)
            else:
                file_result = parse_generic_page_spec_file(file_path)
            result.update(file_result)
    return result


def check_consistency(
    requirements_path: str,
    page_specs_dir: str,
    coverage_threshold: float,
    scope: str = "auto",
    rulepack_name: str | None = None,
) -> dict:
    requirements_abs = Path(requirements_path).resolve()
    requirements_dir = requirements_abs.parent if requirements_abs.is_file() else requirements_abs
    work_dir = requirements_dir.parent
    effective_rulepack = RULEPACK.resolve_effective_rulepack(explicit_name=rulepack_name, work_dir=str(work_dir))
    set_active_rulepack(effective_rulepack)
    requirement_pages: list[RequirementPage] = []
    for path in collect_requirement_files(requirements_path):
        parse_requirement_file(path, requirement_pages)

    generated_pages = load_page_specs(page_specs_dir)
    generated_by_normalized = {page["normalized"]: page for page in generated_pages.values()}
    normalized_scope = "admin" if scope == "backend" else scope
    resolved_scope = infer_generated_scope(generated_pages) if normalized_scope == "auto" else normalized_scope
    filtered_requirement_pages = [
        page for page in requirement_pages
        if resolved_scope in {"all", "mixed"} or page.scope in {resolved_scope, "all"}
    ]

    missing_pages = []
    missing_field_pages = []
    low_coverage = []
    action_mismatch_pages = []
    layout_mismatch_pages = []
    checked_pages = 0

    requirement_norm_map = {canonical_page_name(page.name): page.name for page in filtered_requirement_pages}

    for req_page in filtered_requirement_pages:
        normalized = canonical_page_name(req_page.name)
        generated = generated_by_normalized.get(normalized)
        if not generated:
            missing_pages.append(req_page.name)
            continue

        expected_fields = sorted({field for field in req_page.fields if field})
        checked_pages += 1
        if expected_fields:
            corpus = normalize_name(generated["corpus"])
            hit = [field for field in expected_fields if normalize_name(field) in corpus]
            missing_fields = [field for field in expected_fields if field not in hit]
            coverage = len(hit) / max(len(expected_fields), 1)

            if missing_fields:
                missing_field_pages.append({
                    "page": req_page.name,
                    "coverage": round(coverage, 2),
                    "missing_fields": missing_fields[:20],
                    "source": generated["source"],
                })

            if coverage < coverage_threshold:
                low_coverage.append({
                    "page": req_page.name,
                    "coverage": round(coverage, 2),
                    "missing_fields": missing_fields[:20],
                    "source": generated["source"],
                })

        expected_actions = {canonical_action_name(action) for action in req_page.required_actions if action}
        generated_actions = {canonical_action_name(action) for action in generated.get("actions", []) if action}
        missing_actions = sorted(action for action in expected_actions if action and action not in generated_actions)
        if missing_actions:
            action_mismatch_pages.append({
                "page": req_page.name,
                "missing_actions": missing_actions,
                "source": generated["source"],
            })

        expected_layout = req_page.expected_layout
        actual_layout = generated.get("layout", "")
        if expected_layout and actual_layout and expected_layout != actual_layout:
            layout_mismatch_pages.append({
                "page": req_page.name,
                "expected_layout": expected_layout,
                "actual_layout": actual_layout,
                "source": generated["source"],
            })

    extra_pages = sorted(
        page["name"]
        for page in generated_pages.values()
        if page["normalized"] not in requirement_norm_map
    )

    fail = bool(missing_pages or missing_field_pages or low_coverage or action_mismatch_pages or layout_mismatch_pages)
    warn = bool(extra_pages)
    return {
        "coverage_threshold": coverage_threshold,
        "scope": resolved_scope,
        "rulepack": RULEPACK.build_active_rulepack_metadata(effective_rulepack),
        "requirements_pages": len(filtered_requirement_pages),
        "generated_pages": len(generated_pages),
        "checked_pages": checked_pages,
        "missing_pages": missing_pages,
        "missing_field_pages": missing_field_pages,
        "low_coverage_pages": low_coverage,
        "action_mismatch_pages": action_mismatch_pages,
        "layout_mismatch_pages": layout_mismatch_pages,
        "extra_pages": extra_pages,
        "summary": {
            "fail": 1 if fail else 0,
            "warn": 1 if warn else 0,
            "pass": 0 if fail else 1,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="检查 requirements 与 page_specs 的覆盖率和一致性")
    parser.add_argument("requirements_path")
    parser.add_argument("page_specs_dir")
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument(
        "--scope",
        choices=["auto", "all", "admin", "miniapp", "app", "h5", "bigscreen", "portal", "industrial", "mixed", "backend"],
        default="auto",
    )
    parser.add_argument("--rulepack", default="")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if not os.path.exists(args.requirements_path):
        print(f"错误：requirements 路径不存在 — {args.requirements_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(args.page_specs_dir):
        print(f"错误：page_specs 目录不存在 — {args.page_specs_dir}", file=sys.stderr)
        sys.exit(1)

    report = check_consistency(
        args.requirements_path,
        args.page_specs_dir,
        args.threshold,
        "admin" if args.scope == "backend" else args.scope,
        args.rulepack or None,
    )
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== 覆盖率与一致性检查 ===")
        print(f"coverage threshold: {report['coverage_threshold']}")
        print(f"scope: {report['scope']}")
        print(f"requirements 页面数：{report['requirements_pages']}")
        print(f"page_specs 页面数：{report['generated_pages']}")
        print(f"已检查页面数：{report['checked_pages']}")
        if report["missing_pages"]:
            print("缺失页面：")
            for page in report["missing_pages"]:
                print(f"- {page}")
        if report["missing_field_pages"]:
            print("缺失字段页面：")
            for item in report["missing_field_pages"]:
                missing = ", ".join(item["missing_fields"])
                print(f"- {item['page']}: coverage={item['coverage']}, source={item['source']}, missing={missing}")
        if report["low_coverage_pages"]:
            print("低覆盖页面：")
            for item in report["low_coverage_pages"]:
                missing = ", ".join(item["missing_fields"])
                print(f"- {item['page']}: coverage={item['coverage']}, source={item['source']}, missing={missing}")
        if report["action_mismatch_pages"]:
            print("动作错配页面：")
            for item in report["action_mismatch_pages"]:
                missing = ", ".join(item["missing_actions"])
                print(f"- {item['page']}: source={item['source']}, missing_actions={missing}")
        if report["layout_mismatch_pages"]:
            print("布局错配页面：")
            for item in report["layout_mismatch_pages"]:
                print(
                    f"- {item['page']}: source={item['source']}, "
                    f"expected={item['expected_layout']}, actual={item['actual_layout']}"
                )
        if report["extra_pages"]:
            print("额外页面（未在 requirements 中声明）：")
            for page in report["extra_pages"]:
                print(f"- {page}")
        if report["summary"]["pass"] > 0 and not report["extra_pages"]:
            print("PASS")

    if report["summary"]["fail"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
