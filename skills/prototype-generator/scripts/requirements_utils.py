#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path


def infer_terminal_type_from_module(module_name: str) -> tuple[str, str]:
    text = str(module_name or "").strip()
    if text.startswith("后台-"):
        return "admin", "后台"
    if text.startswith("小程序-"):
        return "miniapp", "小程序"
    if text.startswith("App-") or text.startswith("APP-"):
        return "app", "App"
    if text.startswith("H5-"):
        return "h5", "H5"
    if text.startswith("大屏-"):
        return "bigscreen", "大屏"
    if text.startswith("官网门户-"):
        return "portal", "官网门户"
    if text.startswith("工控机-"):
        return "industrial", "工控机"
    return "admin", "后台"


def safe_slug(value: str, fallback: str = "module") -> str:
    lowered = str(value or "").strip().lower()
    lowered = re.sub(r"[^0-9a-z]+", "_", lowered).strip("_")
    return lowered or fallback


def infer_page_shape(page_name: str) -> tuple[str, str]:
    text = str(page_name or "")
    if "登录" in text:
        return "login", "login"
    if any(token in text for token in ("看板", "分析", "报表", "Dashboard")):
        return "dashboard", "dashboard"
    if any(token in text for token in ("大屏", "态势", "监控台")):
        return "bigscreen_dashboard", "bigscreen_board"
    if any(token in text for token in ("工控", "HMI", "工位", "控制台")):
        return "industrial_console", "industrial_hmi"
    if "官网" in text and any(token in text for token in ("首页", "主页")):
        return "portal_home", "portal_landing"
    if "门户" in text:
        return "portal_hub", "portal_hub"
    if any(token in text for token in ("详情", "授权", "档案")):
        return "web_detail", "detail_kv"
    if any(token in text for token in ("新增", "编辑", "表单", "配置", "设置", "弹窗", "确认")):
        return "web_form", "modal_form" if any(token in text for token in ("弹窗", "确认")) else "form_page"
    if any(token in text for token in ("首页", "我的")):
        return "mobile_home", "mobile_home"
    if any(token in text for token in ("列表", "管理", "中心")):
        return "web_list", "list_table"
    return "web_detail", "detail_kv"


def infer_object_name(page_name: str, module_name: str = "") -> str:
    text = str(page_name or "").strip()
    for token in ("列表页", "管理页", "详情页", "表单页", "弹窗", "页面", "页", "首页", "中心"):
        text = text.replace(token, "")
    text = text.replace("确认", "").replace("新增", "").replace("编辑", "").strip(" -")
    if text:
        return text
    module = str(module_name or "")
    if "-" in module:
        module = module.split("-", 1)[1]
    return module or "对象"


def default_actions_for_page(page_name: str, object_name: str) -> list[str]:
    text = str(page_name or "")
    if "登录" in text:
        return ["登录"]
    if any(token in text for token in ("详情", "授权", "档案")):
        return ["返回", "编辑"]
    if any(token in text for token in ("弹窗", "确认")):
        return ["确认", "取消"]
    if any(token in text for token in ("表单", "新增", "编辑", "配置", "设置")):
        return ["提交", "取消"]
    if any(token in text for token in ("看板", "分析", "报表", "首页")):
        return ["查看详情"]
    if any(token in text for token in ("列表", "管理", "中心")):
        return [f"新增{object_name}", "编辑", "删除", "查看详情"]
    return ["查看详情"]


def default_states_for_page(page_name: str) -> list[str]:
    text = str(page_name or "")
    if "登录" in text:
        return ["默认", "验证码错误", "账号锁定"]
    if any(token in text for token in ("看板", "分析", "报表")):
        return ["正常", "无数据", "刷新失败"]
    if any(token in text for token in ("列表", "管理", "中心")):
        return ["启用", "停用", "草稿"]
    return ["正常", "处理中", "异常"]


def parse_requirement_modules(requirements_path: str | os.PathLike[str]) -> dict[str, dict]:
    root = Path(requirements_path)
    if root.is_file():
        files = [root]
    else:
        files = sorted(
            path
            for path in root.glob("*.md")
            if path.name.startswith("详细需求文档_") and path.name != "详细需求文档_overview.md"
        )
    modules: dict[str, dict] = {}
    for path in files:
        module_name = path.stem.replace("详细需求文档_", "", 1)
        content = path.read_text(encoding="utf-8")
        entry = modules.setdefault(module_name, {"module_name": module_name, "doc_path": str(path), "pages": {}})
        entry["pages"].update(_parse_requirement_pages(content, module_name))
    return modules


def _parse_requirement_pages(content: str, module_name: str) -> dict[str, dict]:
    pages: dict[str, dict] = {}
    lines = content.splitlines()
    current_pages: list[str] = []
    field_bucket: list[str] = []
    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.startswith("- **页面/界面：**"):
            if current_pages:
                _assign_fields(pages, current_pages, field_bucket, module_name)
            raw_pages = line.split("**页面/界面：**", 1)[1].strip()
            current_pages = [item.strip() for item in re.split(r"[、，,；;]\s*", raw_pages) if item.strip()]
            field_bucket = []
            for page_name in current_pages:
                page = pages.setdefault(page_name, _empty_page(page_name, module_name))
                page["doc_line"] = idx + 1
            continue
        if current_pages and line.startswith("- ") and not line.startswith("- **"):
            value = line[2:].strip()
            value = value.split("（", 1)[0].split("(", 1)[0].strip()
            if value and value not in field_bucket and len(value) <= 40:
                field_bucket.append(value)
            continue
        if current_pages and line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if cells and cells[0] not in {"字段名", "字段", "列名", "--------", "------", "---"}:
                field = cells[0].strip()
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
    object_name = infer_object_name(page_name, module_name)
    return {
        "page_name": page_name,
        "page_type": page_type,
        "page_archetype": archetype,
        "object_name": object_name,
        "fields": [],
        "actions": default_actions_for_page(page_name, object_name),
        "states": default_states_for_page(page_name),
    }


def _assign_fields(pages: dict[str, dict], current_pages: list[str], field_bucket: list[str], module_name: str):
    for page_name in current_pages:
        page = pages.setdefault(page_name, _empty_page(page_name, module_name))
        for field in field_bucket:
            if field not in page["fields"]:
                page["fields"].append(field)
