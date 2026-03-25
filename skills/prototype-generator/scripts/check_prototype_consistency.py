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


def normalize_name(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value or "").strip().lower()
    text = text.replace("（后台）", "").replace("(后台)", "")
    text = text.replace("页面", "").replace("页", "")
    text = text.replace("新增/编辑", "编辑")
    text = text.replace("删除确认弹窗", "删除确认")
    text = text.replace("新增/编辑弹窗", "编辑弹窗")
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)
    return text


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
    fields: set[str] = field(default_factory=set)


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


def assign_fields_to_pages(
    pages: list[str],
    list_fields: set[str],
    form_fields: set[str],
    detail_fields: set[str],
    mapping: dict[str, RequirementPage],
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
        mapping.setdefault(page, RequirementPage(name=page))

    for page in list_like:
        mapping[page].fields.update(list_fields)
    for page in form_like:
        mapping[page].fields.update(form_fields)
    for page in detail_like:
        mapping[page].fields.update(detail_fields)


def parse_requirement_file(path: str, mapping: dict[str, RequirementPage]):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    current_pages: list[str] = []
    list_fields: set[str] = set()
    form_fields: set[str] = set()
    detail_fields: set[str] = set()

    def flush():
        if current_pages:
            assign_fields_to_pages(current_pages, list_fields, form_fields, detail_fields, mapping)

    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()

        if line.startswith("#### "):
            flush()
            current_pages = []
            list_fields = set()
            form_fields = set()
            detail_fields = set()
            idx += 1
            continue

        if line.startswith("- **页面/界面：**"):
            raw = line.split("**页面/界面：**", 1)[1].strip()
            current_pages = split_page_names(raw)
            for page in current_pages:
                mapping.setdefault(page, RequirementPage(name=page))
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

        idx += 1

    flush()


def parse_drawio_page_spec_file(path: str) -> dict[str, dict]:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    swimlanes = {}
    elements = []
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line == "## swimlane 布局":
            rows, idx = parse_md_table(lines, idx + 1)
            if rows:
                for row in rows[1:]:
                    if len(row) >= 2:
                        swimlanes[row[0]] = {
                            "label": row[1],
                            "values": set(),
                        }
            continue
        if line == "## 元素列表":
            rows, idx = parse_md_table(lines, idx + 1)
            if rows:
                for row in rows[1:]:
                    if len(row) >= 4:
                        elements.append(row)
            continue
        idx += 1

    for row in elements:
        parent = row[1]
        value = row[3]
        if parent in swimlanes and value.strip():
            swimlanes[parent]["values"].add(value.strip())

    result = {}
    for swimlane in swimlanes.values():
        corpus = " ".join(sorted(swimlane["values"]))
        result[swimlane["label"]] = {
            "name": swimlane["label"],
            "normalized": normalize_name(swimlane["label"]),
            "corpus": corpus,
            "source": os.path.basename(path),
        }
    return result


def parse_generic_page_spec_file(path: str) -> dict[str, dict]:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    pages: dict[str, dict] = {}
    current: dict | None = None
    idx = 0

    while idx < len(lines):
        stripped = lines[idx].strip()

        if stripped.startswith("## 页面规格：") or stripped.startswith("## 页面规格:"):
            name = stripped.split("：", 1)[1].strip() if "：" in stripped else stripped.split(":", 1)[1].strip()
            current = {
                "name": name,
                "normalized": normalize_name(name),
                "tokens": set(),
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


def check_consistency(requirements_path: str, page_specs_dir: str, coverage_threshold: float) -> dict:
    requirement_pages: dict[str, RequirementPage] = {}
    for path in collect_requirement_files(requirements_path):
        parse_requirement_file(path, requirement_pages)

    generated_pages = load_page_specs(page_specs_dir)
    generated_by_normalized = {page["normalized"]: page for page in generated_pages.values()}

    missing_pages = []
    missing_field_pages = []
    low_coverage = []
    checked_pages = 0

    requirement_norm_map = {normalize_name(page.name): page.name for page in requirement_pages.values()}

    for req_page in requirement_pages.values():
        normalized = normalize_name(req_page.name)
        generated = generated_by_normalized.get(normalized)
        if not generated:
            missing_pages.append(req_page.name)
            continue

        expected_fields = sorted({field for field in req_page.fields if field})
        if not expected_fields:
            checked_pages += 1
            continue

        corpus = normalize_name(generated["corpus"])
        hit = [field for field in expected_fields if normalize_name(field) in corpus]
        missing_fields = [field for field in expected_fields if field not in hit]
        coverage = len(hit) / max(len(expected_fields), 1)
        checked_pages += 1

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

    extra_pages = sorted(
        page["name"]
        for page in generated_pages.values()
        if page["normalized"] not in requirement_norm_map
    )

    fail = bool(missing_pages or missing_field_pages or low_coverage)
    warn = bool(extra_pages)
    return {
        "coverage_threshold": coverage_threshold,
        "requirements_pages": len(requirement_pages),
        "generated_pages": len(generated_pages),
        "checked_pages": checked_pages,
        "missing_pages": missing_pages,
        "missing_field_pages": missing_field_pages,
        "low_coverage_pages": low_coverage,
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
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if not os.path.exists(args.requirements_path):
        print(f"错误：requirements 路径不存在 — {args.requirements_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(args.page_specs_dir):
        print(f"错误：page_specs 目录不存在 — {args.page_specs_dir}", file=sys.stderr)
        sys.exit(1)

    report = check_consistency(args.requirements_path, args.page_specs_dir, args.threshold)
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== 覆盖率与一致性检查 ===")
        print(f"coverage threshold: {report['coverage_threshold']}")
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
