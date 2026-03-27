#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from requirements_utils import infer_page_shape, parse_requirement_modules, safe_slug


def ensure_compressed_requirements(work_dir: str | Path, *, force: bool = False) -> dict:
    root = Path(work_dir).resolve()
    requirements_dir = root / "requirements"
    if not requirements_dir.is_dir():
        return {"status": "skipped", "reason": "requirements_dir_missing", "artifacts": {}}

    detail_modules = _load_detail_modules(requirements_dir)
    if not detail_modules:
        return {"status": "skipped", "reason": "no_detail_docs", "artifacts": {}}

    overview_path = requirements_dir / "详细需求文档_overview.md"
    briefs_dir = requirements_dir / "module_briefs"
    index_path = requirements_dir / "index.md"
    briefs_dir.mkdir(parents=True, exist_ok=True)

    changed_paths: list[str] = []
    if force or not overview_path.exists():
        overview_text = _build_overview_markdown(root.name, detail_modules)
        overview_path.write_text(overview_text, encoding="utf-8")
        changed_paths.append(str(overview_path))

    for module_name, module in detail_modules.items():
        brief_path = briefs_dir / f"模块摘要_{module_name}.md"
        brief_text = _build_module_brief_markdown(module_name, module)
        if force or not brief_path.exists() or brief_path.read_text(encoding="utf-8") != brief_text:
            brief_path.write_text(brief_text, encoding="utf-8")
            changed_paths.append(str(brief_path))

    index_text = _build_index_markdown(detail_modules)
    if force or not index_path.exists() or index_path.read_text(encoding="utf-8") != index_text:
        index_path.write_text(index_text, encoding="utf-8")
        changed_paths.append(str(index_path))

    return {
        "status": "rewritten" if changed_paths else "ok",
        "mode": "split",
        "artifacts": {
            "overview": str(overview_path),
            "module_briefs_dir": str(briefs_dir),
            "index": str(index_path),
            "detail_files": [module["doc_path"] for module in detail_modules.values()],
        },
        "changed_paths": changed_paths,
        "module_count": len(detail_modules),
    }


def _load_detail_modules(requirements_dir: Path) -> dict[str, dict]:
    modules = parse_requirement_modules(requirements_dir)
    if modules:
        return modules
    single_path = requirements_dir / "详细需求文档.md"
    if not single_path.exists():
        return {}
    return _split_single_requirements(single_path)


def _split_single_requirements(single_path: Path) -> dict[str, dict]:
    content = single_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    modules: dict[str, list[str]] = {}
    current_module = ""
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, current_module
        if not current_module or not any(line.strip() for line in buffer):
            buffer = []
            return
        modules[current_module] = list(buffer)
        buffer = []

    for line in lines:
        stripped = line.strip()
        module_match = re.match(r"^###\s+(.+)$", stripped)
        if module_match and not stripped.startswith("#### "):
            flush()
            current_module = module_match.group(1).strip()
            buffer = [f"# {single_path.stem} — {current_module}\n", "", f"## 3. 功能模块清单 — {current_module}", ""]
            continue
        if current_module:
            buffer.append(line)
    flush()

    if not modules:
        modules["默认模块"] = [content]

    split_dir = single_path.parent
    results: dict[str, dict] = {}
    for module_name, module_lines in modules.items():
        path = split_dir / f"详细需求文档_{module_name}.md"
        module_text = "\n".join(module_lines).strip() + "\n"
        if not path.exists():
            path.write_text(module_text, encoding="utf-8")
        results[module_name] = {
            "module_name": module_name,
            "doc_path": str(path),
            "pages": _parse_pages_fields_from_text(module_text, module_name),
        }
    return results


def _parse_pages_fields_from_text(content: str, module_name: str) -> dict:
    pages: dict[str, dict] = {}
    current_pages: list[str] = []
    field_bucket: list[str] = []
    lines = content.splitlines()
    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.startswith("- **页面/界面：**"):
            if current_pages:
                _assign_fields(pages, current_pages, field_bucket, module_name)
            current_pages = [item.strip() for item in re.split(r"[、，,；;]\s*", line.split("**页面/界面：**", 1)[1].strip()) if item.strip()]
            field_bucket = []
            for page_name in current_pages:
                page = pages.setdefault(page_name, _empty_page(page_name, module_name))
                page["doc_line"] = idx + 1
            continue
        if current_pages and line.startswith("- ") and not line.startswith("- **"):
            field = line[2:].strip().split("（", 1)[0].split("(", 1)[0].strip()
            if field and field not in field_bucket and len(field) <= 40:
                field_bucket.append(field)
            continue
        if current_pages and line.startswith("#### "):
            _assign_fields(pages, current_pages, field_bucket, module_name)
            current_pages = []
            field_bucket = []
    if current_pages:
        _assign_fields(pages, current_pages, field_bucket, module_name)
    return pages


def _empty_page(page_name: str, module_name: str) -> dict:
    page_type, archetype = infer_page_shape(page_name)
    return {
        "page_name": page_name,
        "page_type": page_type,
        "page_archetype": archetype,
        "fields": [],
        "actions": [],
        "states": [],
    }


def _assign_fields(pages: dict, current_pages: list[str], field_bucket: list[str], module_name: str) -> None:
    for page_name in current_pages:
        page = pages.setdefault(page_name, _empty_page(page_name, module_name))
        for field in field_bucket:
            if field not in page["fields"]:
                page["fields"].append(field)


def _build_overview_markdown(product_name: str, detail_modules: dict[str, dict]) -> str:
    module_lines = []
    enum_values = set()
    total_pages = 0
    for module_name, module in detail_modules.items():
        pages = list(module.get("pages", {}).values())
        total_pages += len(pages)
        page_names = "、".join(page["page_name"] for page in pages[:6]) or "无页面"
        module_lines.append(f"- {module_name}：包含 {len(pages)} 个页面，主要页面有 {page_names}")
        for page in pages:
            for state in page.get("states", []):
                enum_values.add(state)
    prototype_rows = [
        "| 模块 | 页面 | 页面类型 | 页面原型 | 主要字段数 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for module_name, module in detail_modules.items():
        for page in module.get("pages", {}).values():
            prototype_rows.append(
                f"| {module_name} | {page['page_name']} | {page.get('page_type', '')} | {page.get('page_archetype', '')} | {len(page.get('fields', []))} |"
            )
    if len(prototype_rows) == 2:
        prototype_rows.append("| 默认模块 | 无页面 | web_detail | detail_kv | 0 |")
    enum_lines = "\n".join(f"- {value}" for value in sorted(enum_values)) or "- 正常\n- 异常\n- 处理中"
    return (
        f"# {product_name or '产品'} 详细需求文档 — Overview\n\n"
        "## 1. 产品概述\n"
        f"- 自动压缩重写生成，共 {len(detail_modules)} 个模块，{total_pages} 个页面。\n\n"
        "## 2. 用户角色\n- 待从详细需求文档补充的角色摘要\n\n"
        "## 2.5 系统边界与外部依赖\n- 待从详细需求文档补充的系统边界摘要\n\n"
        "## 2.8 模块职责与协作关系\n"
        f"{chr(10).join(module_lines) if module_lines else '- 无模块'}\n\n"
        "## 3.5 移动端导航结构\n- 如存在移动端页面，按页面类型补充 Tab/入口映射\n\n"
        "## 3.6 后台导航结构\n- 如存在后台页面，按模块名称补充后台导航归属\n\n"
        "## 4. 核心业务流程\n- 自动压缩重写未推导完整流程，后续按模块详细文档补全\n\n"
        "## 4.5 关键业务事件\n- 待从详细需求文档补充关键业务事件\n\n"
        "## 5. 数据模型与状态\n- 页面字段与状态已由模块详细文档抽取\n\n"
        "## 5.5 枚举值字典\n"
        f"{enum_lines}\n\n"
        "## 5.8 权限与数据口径总则\n- 待从详细需求文档补充权限与数据口径\n\n"
        "## 6. 非功能需求\n- 待从详细需求文档补充非功能需求\n\n"
        "## 7. 原型图清单\n"
        f"{chr(10).join(prototype_rows)}\n"
    )


def _build_module_brief_markdown(module_name: str, module: dict) -> str:
    pages = module.get("pages", {})
    page_lines = []
    field_bucket = []
    for page_name, page in pages.items():
        page_lines.append(f"- {page_name}（{page.get('page_archetype', '')}）")
        for field in page.get("fields", []):
            if field not in field_bucket:
                field_bucket.append(field)
    return (
        f"# {module_name} 模块摘要\n\n"
        "## 1. 模块目标与边界\n"
        f"- 模块：{module_name}\n\n"
        "## 2. 终端与导航归属\n"
        f"- 默认根据模块名 `{module_name}` 与页面类型推导终端\n\n"
        "## 3. 页面清单与页面 archetype\n"
        f"{chr(10).join(page_lines) if page_lines else '- 无页面'}\n\n"
        "## 4. 核心实体与 CRUD 闭环\n"
        "- 待按模块详细文档补全核心实体与 CRUD 闭环\n\n"
        "## 5. 关键字段索引\n"
        f"{chr(10).join(f'- {field}' for field in field_bucket[:12]) if field_bucket else '- 无字段'}\n\n"
        "## 6. 状态 / 枚举摘要\n- 待按模块详细文档补全状态与枚举\n\n"
        "## 7. 权限与数据口径摘要\n- 待按模块详细文档补全权限与口径\n\n"
        "## 8. 跨模块跳转与外部依赖\n- 待按模块详细文档补全跨模块跳转与依赖\n\n"
        "## 9. 详细文档章节映射\n"
        f"- 详细文档：requirements/{Path(module.get('doc_path', '')).name}\n"
    )


def _build_index_markdown(detail_modules: dict[str, dict]) -> str:
    lines = [
        "# 需求文档索引",
        "",
        "## 共用文件",
        "- requirements/详细需求文档_overview.md",
        "",
        "## 模块文件",
    ]
    for module_name, module in sorted(detail_modules.items()):
        detail_name = Path(module.get("doc_path", f"详细需求文档_{module_name}.md")).name
        brief_name = f"模块摘要_{module_name}.md"
        page_count = len(module.get("pages", {}))
        lines.append(
            f"- {module_name}: requirements/{detail_name} | requirements/module_briefs/{brief_name} | pages={page_count}"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="自动生成压缩后的 requirements artifacts（overview/module_briefs/index）")
    parser.add_argument("work_dir")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    report = ensure_compressed_requirements(args.work_dir, force=args.force)
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
