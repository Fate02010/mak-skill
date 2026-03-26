#!/usr/bin/env python3
"""
check_module_brief_consistency.py - 检查 split 模式下 module_brief 是否覆盖模块详细文档的核心信息。

用法:
    python3 check_module_brief_consistency.py <requirements_dir> [--threshold 0.6] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys


def normalize_name(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", value or "").strip().lower()
    text = text.replace("（后台）", "").replace("(后台)", "")
    text = text.replace("新增/编辑", "编辑")
    text = text.replace("页面", "").replace("页", "")
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
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
        idx += 1
    return rows, idx


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
            if value and len(value) <= 40:
                fields.append(value)
            idx += 1
            continue
        break
    return fields, idx


def add_token(container: set[str], value: str):
    token = re.sub(r"<[^>]+>", "", value or "").strip()
    token = token.split("（", 1)[0].split("(", 1)[0].strip()
    token = token.replace("：", " ").replace(":", " ")
    if token:
        container.add(token)


def module_key_from_detail(name: str) -> str:
    return name.replace("详细需求文档_", "", 1).replace(".md", "")


def module_key_from_brief(name: str) -> str:
    return name.replace("模块摘要_", "", 1).replace(".md", "")


def parse_detail_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    pages: list[str] = []
    fields: set[str] = set()
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line.startswith("- **页面/界面：**"):
            raw = line.split("**页面/界面：**", 1)[1].strip()
            for page in split_page_names(raw):
                if page not in pages:
                    pages.append(page)
            idx += 1
            continue
        if "筛选条件：" in line:
            values, idx = extract_fields_from_bullets(lines, idx + 1)
            fields.update(values)
            continue
        if "列表展示列：" in line or "新增/编辑表单字段规格" in line:
            rows, idx = parse_md_table(lines, idx + 1)
            if rows:
                for row in rows[1:]:
                    if row and row[0]:
                        fields.add(row[0])
            continue
        if "展示字段：" in line:
            raw = line.split("展示字段：", 1)[1].strip()
            fields.update(split_page_names(raw))
            idx += 1
            continue
        idx += 1

    return {
        "pages": pages,
        "fields": sorted(fields),
    }


def parse_brief_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    tokens: set[str] = set()
    idx = 0
    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped:
            idx += 1
            continue
        if stripped.startswith("|"):
            rows, idx = parse_md_table(lines, idx)
            if rows:
                for row in rows[1:]:
                    for cell in row:
                        add_token(tokens, cell)
            continue
        if stripped.startswith("- "):
            add_token(tokens, stripped[2:].strip())
            idx += 1
            continue
        if not stripped.startswith("#"):
            add_token(tokens, stripped)
        idx += 1

    corpus = " ".join(sorted(tokens))
    return {
        "tokens": tokens,
        "corpus": corpus,
    }


def check_requirements(requirements_dir: str, threshold: float) -> dict:
    briefs_dir = os.path.join(requirements_dir, "module_briefs")
    detail_files = {}
    brief_files = {}
    for root, _, names in os.walk(requirements_dir):
        for name in names:
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            if name.startswith("详细需求文档_") and name not in {"详细需求文档_overview.md"}:
                detail_files[module_key_from_detail(name)] = path
            elif root == briefs_dir and name.startswith("模块摘要_"):
                brief_files[module_key_from_brief(name)] = path

    missing_briefs = []
    missing_pages = []
    low_coverage_modules = []
    checked_modules = 0

    for module_key, detail_path in sorted(detail_files.items()):
        brief_path = brief_files.get(module_key)
        if not brief_path:
            missing_briefs.append(module_key)
            continue
        detail = parse_detail_file(detail_path)
        brief = parse_brief_file(brief_path)
        corpus = normalize_name(brief["corpus"])
        checked_modules += 1

        module_missing_pages = [
            page for page in detail["pages"]
            if normalize_name(page) not in corpus
        ]
        if module_missing_pages:
            missing_pages.append({
                "module": module_key,
                "pages": module_missing_pages,
                "source": os.path.basename(brief_path),
            })

        expected_fields = [field for field in detail["fields"] if field]
        if expected_fields:
            hits = [field for field in expected_fields if normalize_name(field) in corpus]
            coverage = len(hits) / max(len(expected_fields), 1)
            if coverage < threshold:
                low_coverage_modules.append({
                    "module": module_key,
                    "coverage": round(coverage, 2),
                    "missing_fields": [field for field in expected_fields if field not in hits][:20],
                    "source": os.path.basename(brief_path),
                })

    fail = bool(missing_briefs or missing_pages or low_coverage_modules)
    return {
        "modules": len(detail_files),
        "checked_modules": checked_modules,
        "missing_briefs": missing_briefs,
        "missing_pages": missing_pages,
        "low_coverage_modules": low_coverage_modules,
        "summary": {
            "fail": 1 if fail else 0,
            "warn": 0,
            "pass": 0 if fail else 1,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="检查 module_brief 是否覆盖模块详细文档的核心信息")
    parser.add_argument("requirements_dir")
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if not os.path.isdir(args.requirements_dir):
        print(f"错误：requirements 目录不存在 — {args.requirements_dir}", file=sys.stderr)
        raise SystemExit(1)

    report = check_requirements(args.requirements_dir, args.threshold)
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== module_brief consistency ===")
        print(f"modules: {report['modules']}")
        print(f"checked: {report['checked_modules']}")
        if report["missing_briefs"]:
            print("missing_briefs:")
            for module in report["missing_briefs"]:
                print(f"- {module}")
        if report["missing_pages"]:
            print("missing_pages:")
            for item in report["missing_pages"]:
                print(f"- {item['module']}: {', '.join(item['pages'])}")
        if report["low_coverage_modules"]:
            print("low_coverage_modules:")
            for item in report["low_coverage_modules"]:
                print(f"- {item['module']}: {item['coverage']}")

    raise SystemExit(1 if report["summary"]["fail"] else 0)


if __name__ == "__main__":
    main()
