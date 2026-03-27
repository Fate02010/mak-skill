#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

from requirements_utils import infer_page_shape, infer_terminal_type_from_module, safe_slug


BODY_RENDER_ENV = "PROTOTYPE_GENERATOR_BODY_RENDER_CMD"


def parse_markdown_table(lines: list[str], start_index: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    idx = start_index
    while idx < len(lines):
        line = lines[idx].rstrip()
        if not line.strip().startswith("|"):
            break
        if re.match(r"^\|[\s\-:|]+\|$", line.strip()):
            idx += 1
            continue
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        idx += 1
    return rows, idx


def parse_page_spec(path: str | Path) -> dict:
    content = Path(path).read_text(encoding="utf-8")
    return parse_page_spec_text(content)


def parse_page_spec_text(content: str) -> dict:
    lines = content.splitlines()
    spec = {"module_name": "", "module_key": "", "output_format": "html", "pages": []}
    current = None
    idx = 0
    current_section = ""
    list_sections = {"操作", "状态", "布局指令", "视觉线索", "交互模式", "参考来源"}
    while idx < len(lines):
        line = lines[idx].rstrip()
        stripped = line.strip()
        if stripped.startswith("- 模块名称："):
            spec["module_name"] = stripped.split("：", 1)[1].strip()
        elif stripped.startswith("- 模块英文名："):
            spec["module_key"] = stripped.split("：", 1)[1].strip()
        elif stripped.startswith("- 输出格式："):
            spec["output_format"] = stripped.split("：", 1)[1].strip() or "html"
        elif stripped.startswith("## 页面规格："):
            if current:
                spec["pages"].append(_normalize_page(current))
            page_name = stripped.split("：", 1)[1].strip()
            inferred_type, inferred_archetype = infer_page_shape(page_name)
            current = {
                "page_name": page_name,
                "page_type": inferred_type,
                "page_archetype": inferred_archetype,
                "output_file": f"{safe_slug(page_name, 'page')}.html",
                "is_nav_page": False,
                "reference_basis": "fallback",
                "reference_pack_file": "",
                "reference_summary": "",
                "reference_sources": [],
                "layout_directives": [],
                "visual_cues": [],
                "interaction_patterns": [],
                "fields": [],
                "table_columns": [],
                "actions": [],
                "jumps": [],
                "states": [],
            }
            current_section = ""
        elif stripped.startswith("### "):
            current_section = stripped[4:].strip()
        elif current and current_section == "页面元信息" and stripped.startswith("- 页面类型："):
            current["page_type"] = stripped.split("：", 1)[1].strip()
        elif current and current_section == "页面元信息" and stripped.startswith("- 页面原型："):
            current["page_archetype"] = stripped.split("：", 1)[1].strip()
        elif current and current_section == "页面元信息" and stripped.startswith("- 输出文件："):
            current["output_file"] = stripped.split("：", 1)[1].strip()
        elif current and current_section == "页面元信息" and stripped.startswith("- 是否导航页："):
            current["is_nav_page"] = "是" in stripped.split("：", 1)[1]
        elif current and current_section == "参考依据" and stripped.startswith("- 参考来源："):
            current["reference_basis"] = stripped.split("：", 1)[1].strip()
        elif current and current_section == "参考依据" and stripped.startswith("- 参考包文件："):
            current["reference_pack_file"] = stripped.split("：", 1)[1].strip()
        elif current and current_section == "参考依据" and stripped.startswith("- 参考摘要："):
            current["reference_summary"] = stripped.split("：", 1)[1].strip()
        elif current and current_section in {"字段", "列表列"} and stripped.startswith("|"):
            rows, next_idx = parse_markdown_table(lines, idx)
            if current_section == "字段":
                for row in rows[1:]:
                    if not row:
                        continue
                    current["fields"].append(
                        {
                            "name": row[0],
                            "control": row[1] if len(row) > 1 else "input",
                            "required": row[2] if len(row) > 2 else "否",
                            "note": row[3] if len(row) > 3 else "",
                        }
                    )
            else:
                for row in rows[1:]:
                    if row:
                        current["table_columns"].append({"name": row[0], "note": row[1] if len(row) > 1 else ""})
            idx = next_idx - 1
        elif current and current_section in list_sections and stripped.startswith("- "):
            value = stripped[2:].strip()
            if value:
                current[_section_key(current_section)].append(value)
        elif current and current_section == "跳转" and stripped.startswith("- "):
            value = stripped[2:].strip()
            parts = [item.strip() for item in value.split("->", 1)]
            if len(parts) == 2:
                current["jumps"].append({"action": parts[0], "target": parts[1]})
            elif value:
                current["jumps"].append({"action": value, "target": ""})
        idx += 1
    if current:
        spec["pages"].append(_normalize_page(current))
    return spec


def to_markdown(spec: dict) -> str:
    lines = [
        "# 页面规格冻结",
        "",
        "## 模块信息",
        f"- 模块名称：{spec.get('module_name', '')}",
        f"- 模块英文名：{spec.get('module_key', '')}",
        f"- 输出格式：{spec.get('output_format', 'html')}",
        "",
    ]
    for page in spec.get("pages", []):
        page = _normalize_page(page)
        default_output_file = f"{safe_slug(page.get('page_name', ''), 'page')}.html"
        lines.extend(
            [
                f"## 页面规格：{page.get('page_name', '')}",
                "### 页面元信息",
                f"- 页面类型：{page.get('page_type', 'web_detail')}",
                f"- 页面原型：{page.get('page_archetype', infer_page_shape(page.get('page_name', ''))[1])}",
                f"- 输出文件：{page.get('output_file', default_output_file)}",
                f"- 是否导航页：{'是' if page.get('is_nav_page') else '否'}",
                "",
                "### 参考依据",
                f"- 参考来源：{page.get('reference_basis', 'fallback')}",
                f"- 参考包文件：{page.get('reference_pack_file', '')}",
                f"- 参考摘要：{page.get('reference_summary', '')}",
                "",
                "### 参考来源",
            ]
        )
        for item in page.get("reference_sources", []):
            lines.append(f"- {item}")
        if not page.get("reference_sources"):
            lines.append("- 无")
        lines.extend(["", "### 布局指令"])
        for item in page.get("layout_directives", []):
            lines.append(f"- {item}")
        if not page.get("layout_directives"):
            lines.append("- 无")
        lines.extend(["", "### 视觉线索"])
        for item in page.get("visual_cues", []):
            lines.append(f"- {item}")
        if not page.get("visual_cues"):
            lines.append("- 无")
        lines.extend(["", "### 交互模式"])
        for item in page.get("interaction_patterns", []):
            lines.append(f"- {item}")
        if not page.get("interaction_patterns"):
            lines.append("- 无")
        lines.extend(
            [
                "",
                "### 字段",
                "| 字段名 | 控件/展示 | 必填 | 说明 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for field in page.get("fields", []):
            lines.append(
                f"| {field.get('name', '')} | {field.get('control', 'input')} | {field.get('required', '否')} | {field.get('note', '')} |"
            )
        if not page.get("fields"):
            lines.append("| - | text | 否 | 无 |")
        lines.extend(["", "### 列表列", "| 列名 | 说明 |", "| --- | --- |"])
        for column in page.get("table_columns", []):
            lines.append(f"| {column.get('name', '')} | {column.get('note', '')} |")
        if not page.get("table_columns"):
            lines.append("| - | 无 |")
        lines.extend(["", "### 操作"])
        for action in page.get("actions", []):
            lines.append(f"- {action}")
        if not page.get("actions"):
            lines.append("- 查看详情")
        lines.extend(["", "### 跳转"])
        for jump in page.get("jumps", []):
            lines.append(f"- {jump.get('action', '')} -> {jump.get('target', '')}")
        if not page.get("jumps"):
            lines.append("- 查看详情 -> 详情页")
        lines.extend(["", "### 状态"])
        for state in page.get("states", []):
            lines.append(f"- {state}")
        if not page.get("states"):
            lines.append("- 正常")
        lines.append("")
    return "\n".join(lines)


def terminal_css_class(module_name: str) -> str:
    terminal_type, _ = infer_terminal_type_from_module(module_name)
    return terminal_type


def required_body_markers_for(page_type: str, page_archetype: str) -> list[str]:
    if page_type == "index" or page_archetype == "index":
        return ["prototype-index-links"]
    if page_type in {"web_list", "mobile_list"}:
        return ["filter-grid", "prototype-table", "prototype-pagination"]
    if page_type in {"web_form", "mobile_form"}:
        return ["prototype-form-card", "sticky-action-card"]
    if page_type == "login":
        return ["prototype-login-card", "login-helper-row"]
    if page_archetype == "detail_kv":
        return ["kv-grid", "timeline-list"]
    if page_archetype in {"dashboard", "mobile_home", "portal_landing"} or page_type in {
        "dashboard",
        "bigscreen_dashboard",
        "industrial_console",
        "portal_home",
        "portal_hub",
        "mobile_home",
        "profile",
    }:
        return ["metric-grid", "dashboard-focus-panel"]
    return ["kv-grid"]


def forbidden_body_markers_for(page_type: str) -> list[str]:
    base = ["<html", "<head", "<body", "prototype-sidebar", "nav-bar", "data-prototype-shell"]
    if page_type == "login":
        return base + ["breadcrumb", "prototype-side-nav"]
    return base


def build_body_spec(spec: dict, page: dict, page_file_map: dict[str, str]) -> dict:
    normalized = _normalize_page(page)
    page_type = normalized.get("page_type", "web_detail")
    page_archetype = normalized.get("page_archetype", infer_page_shape(normalized.get("page_name", ""))[1])
    return {
        "page_name": normalized.get("page_name", ""),
        "page_type": page_type,
        "page_archetype": page_archetype,
        "slot_mode": "controlled_body",
        "required_markers": required_body_markers_for(page_type, page_archetype),
        "forbidden_markers": forbidden_body_markers_for(page_type),
        "sections": _body_sections_for(spec, normalized, page_file_map),
    }


def build_body_prompt(spec: dict, page: dict, body_spec: dict) -> str:
    normalized = _normalize_page(page)
    section_lines = []
    for section in body_spec.get("sections", []):
        section_lines.extend(
            [
                f"## 区块：{section.get('section_key', '')}",
                f"- 角色：{section.get('section_role', '')}",
                f"- 布局提示：{section.get('layout_hint', '')}",
                f"- 内容要求：{section.get('content_requirements', '')}",
                f"- 必含字段：{', '.join(section.get('required_fields', [])) or '无'}",
                f"- 必含操作：{', '.join(section.get('required_actions', [])) or '无'}",
                "",
            ]
        )
    return "\n".join(
        [
            "# HTML Body Slot Prompt",
            "",
            f"- 模块：{spec.get('module_name', '')}",
            f"- 页面：{normalized.get('page_name', '')}",
            f"- 页面类型：{normalized.get('page_type', '')}",
            f"- 页面原型：{normalized.get('page_archetype', '')}",
            "- 只输出 body slot 片段，禁止输出完整 HTML 文档、head、body、sidebar、nav。",
            "- 禁止自定义 font-family、zoom、transform: scale(...)。",
            "- 禁止重写 common.css 已有组件类。",
            f"- 必须命中标记：{', '.join(body_spec.get('required_markers', [])) or '无'}",
            f"- 禁止命中标记：{', '.join(body_spec.get('forbidden_markers', [])) or '无'}",
            "",
            "## 页面参考",
            f"- 参考摘要：{normalized.get('reference_summary', '') or '无'}",
            f"- 布局指令：{'; '.join(normalized.get('layout_directives', [])) or '无'}",
            f"- 视觉线索：{'; '.join(normalized.get('visual_cues', [])) or '无'}",
            f"- 交互模式：{'; '.join(normalized.get('interaction_patterns', [])) or '无'}",
            "",
            *section_lines,
        ]
    ).strip() + "\n"


def generate_body_html(spec: dict, page: dict, page_file_map: dict[str, str], body_spec: dict, body_prompt: str) -> str:
    normalized = _normalize_page(page)
    body_html = _render_body_with_backend(spec, normalized, page_file_map, body_spec, body_prompt)
    if not body_html:
        body_html = _render_page_content(spec, normalized, page_file_map)
    _validate_body_contract(body_html, body_spec)
    return body_html


def compose_page_html(spec: dict, page: dict, page_file_map: dict[str, str], body_html: str) -> str:
    module_name = spec.get("module_name", "")
    normalized = _normalize_page(page)
    page_name = normalized.get("page_name", "")
    page_type = normalized.get("page_type", "web_detail")
    page_archetype = normalized.get("page_archetype", infer_page_shape(page_name)[1])
    terminal_class = terminal_css_class(module_name)
    title = html.escape(page_name)
    body_class = _body_class(terminal_class, page_type)
    shell_class = _shell_class(terminal_class, page_type)
    content_html = _wrap_body_slot(body_html)
    shell = _wrap_terminal_shell(spec, normalized, terminal_class, content_html, page_file_map)
    reference_comment = "\n".join(
        [
            "<!-- REFERENCE_PACK",
            f"basis: {normalized.get('reference_basis', 'fallback')}",
            f"archetype: {page_archetype}",
            f"summary: {normalized.get('reference_summary', '')}",
            "sources:",
            *[f"- {item}" for item in normalized.get("reference_sources", [])],
            "-->",
        ]
    )
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"zh-CN\">\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        f"  <title>{title}</title>\n"
        "  <link rel=\"stylesheet\" href=\"common.css\">\n"
        "</head>\n"
        f"<body class=\"{html.escape(body_class)}\">\n"
        f"{reference_comment}\n"
        f"  <div class=\"{html.escape(shell_class)}\" data-prototype-shell=\"1\" data-page-name=\"{html.escape(page_name)}\" "
        f"data-page-type=\"{html.escape(page_type)}\" data-page-archetype=\"{html.escape(page_archetype)}\" "
        f"data-reference-basis=\"{html.escape(normalized.get('reference_basis', 'fallback'))}\">\n"
        f"{shell}\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    )


def render_page_html(spec: dict, page: dict, page_file_map: dict[str, str]) -> str:
    normalized = _normalize_page(page)
    body_spec = build_body_spec(spec, normalized, page_file_map)
    body_prompt = build_body_prompt(spec, normalized, body_spec)
    body_html = generate_body_html(spec, normalized, page_file_map, body_spec, body_prompt)
    return compose_page_html(spec, normalized, page_file_map, body_html)


def render_index_html(product_name: str, pages: list[dict]) -> str:
    links = "\n".join(
        (
            "          <li class=\"prototype-index-item\">"
            f"<a href=\"{html.escape(page['output_file'])}\"><span>{html.escape(page['page_name'])}</span>"
            f"<small>{html.escape(page['output_file'])}</small></a></li>"
        )
        for page in pages
        if page.get("output_file") != "index.html"
    )
    slot_html = (
        "    <!-- BODY_SLOT_START -->\n"
        "    <section class=\"prototype-body-slot\" data-body-slot=\"1\">\n"
        "    <section class=\"hero-card hero-card-wide\">\n"
        "      <div>\n"
        "        <p class=\"hero-eyebrow\">Prototype Generator</p>\n"
        "        <h1 class=\"hero-title\">原型导航</h1>\n"
        f"        <p class=\"hero-subtitle\">{html.escape(product_name)} 的 HTML 高保真输出入口。</p>\n"
        "      </div>\n"
        "      <div class=\"hero-metrics\">\n"
        f"        <div class=\"metric-card\"><span class=\"metric-label\">页面数</span><strong class=\"metric-value\">{len([p for p in pages if p.get('output_file') != 'index.html'])}</strong></div>\n"
        "      </div>\n"
        "    </section>\n"
        "    <section class=\"prototype-card\">\n"
        "      <ul class=\"prototype-index-links\">\n"
        f"{links}\n"
        "      </ul>\n"
        "    </section>\n"
        "    </section>\n"
        "    <!-- BODY_SLOT_END -->\n"
    )
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"zh-CN\">\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        f"  <title>{html.escape(product_name)}</title>\n"
        "  <link rel=\"stylesheet\" href=\"common.css\">\n"
        "</head>\n"
        "<body class=\"prototype-page terminal-admin\">\n"
        "  <div class=\"prototype-shell prototype-index-shell\" data-prototype-shell=\"1\" data-page-name=\"原型导航\" data-page-type=\"index\" data-page-archetype=\"index\" data-reference-basis=\"generated\">\n"
        f"{slot_html}"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    )


def _body_sections_for(spec: dict, page: dict, page_file_map: dict[str, str]) -> list[dict]:
    page_type = page.get("page_type", "web_detail")
    page_archetype = page.get("page_archetype", infer_page_shape(page.get("page_name", ""))[1])
    fields = [field.get("name", "") for field in page.get("fields", []) if field.get("name")]
    actions = list(page.get("actions", []) or [])
    if page_type in {"web_list", "mobile_list"}:
        return [
            {"section_key": "summary_metrics", "section_role": "顶部摘要", "layout_hint": "紧凑指标卡", "content_requirements": "展示 2-3 个业务摘要", "required_fields": fields[:3], "required_actions": []},
            {"section_key": "filters", "section_role": "筛选区", "layout_hint": "筛选表单 + 查询/重置", "content_requirements": "保留输入控件和操作按钮", "required_fields": fields[:4], "required_actions": actions[:2]},
            {"section_key": "table", "section_role": "列表区", "layout_hint": "表格 + 操作列 + 分页", "content_requirements": "至少 3 行数据和操作列", "required_fields": [column.get("name", "") for column in page.get("table_columns", [])[:6]], "required_actions": actions[:3]},
        ]
    if page_type in {"web_form", "mobile_form"}:
        midpoint = max(2, len(fields) // 2 or len(fields))
        return [
            {"section_key": "primary_form", "section_role": "主表单", "layout_hint": "两列字段分组", "content_requirements": "先展示核心字段", "required_fields": fields[:midpoint], "required_actions": []},
            {"section_key": "secondary_form", "section_role": "补充配置", "layout_hint": "承载说明和附加字段", "content_requirements": "展示次级字段和说明", "required_fields": fields[midpoint:], "required_actions": []},
            {"section_key": "actions", "section_role": "底部操作区", "layout_hint": "吸底操作卡", "content_requirements": "清晰区分主次按钮", "required_fields": [], "required_actions": actions[:2]},
        ]
    if page_type == "login":
        return [
            {"section_key": "login_form", "section_role": "登录表单", "layout_hint": "单卡片堆叠输入", "content_requirements": "账号、密码、验证码按需展示", "required_fields": fields[:3], "required_actions": actions[:2]},
            {"section_key": "helper_links", "section_role": "辅助区", "layout_hint": "底部两端辅助链接", "content_requirements": "保留忘记密码/联系管理员", "required_fields": [], "required_actions": []},
        ]
    if page_archetype in {"dashboard", "mobile_home", "portal_landing"} or page_type in {
        "dashboard",
        "bigscreen_dashboard",
        "industrial_console",
        "portal_home",
        "portal_hub",
        "mobile_home",
        "profile",
    }:
        return [
            {"section_key": "metrics", "section_role": "指标区", "layout_hint": "指标卡栅格", "content_requirements": "展示 3-4 个核心指标", "required_fields": fields[:4], "required_actions": []},
            {"section_key": "focus_panel", "section_role": "主分析区", "layout_hint": "主面板 + 侧栏", "content_requirements": "保留图表或重点面板", "required_fields": fields[:2], "required_actions": actions[:2]},
        ]
    return [
        {"section_key": "summary", "section_role": "摘要区", "layout_hint": "摘要头信息", "content_requirements": "展示主状态和摘要字段", "required_fields": fields[:3], "required_actions": []},
        {"section_key": "kv", "section_role": "键值信息", "layout_hint": "双列 kv-grid", "content_requirements": "字段按业务顺序展示", "required_fields": fields[:8], "required_actions": []},
        {"section_key": "records", "section_role": "记录区", "layout_hint": "时间线记录", "content_requirements": "展示处理记录和关键操作", "required_fields": [], "required_actions": actions[:3]},
    ]


def _render_body_with_backend(spec: dict, page: dict, page_file_map: dict[str, str], body_spec: dict, body_prompt: str) -> str:
    command = os.environ.get(BODY_RENDER_ENV)
    if not command:
        return ""
    payload = {
        "module_name": spec.get("module_name", ""),
        "module_key": spec.get("module_key", ""),
        "page": page,
        "page_file_map": page_file_map,
        "body_spec": body_spec,
        "body_prompt": body_prompt,
    }
    completed = subprocess.run(
        shlex.split(command),
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError(f"BODY_RENDER: backend_failed: {completed.stderr.strip() or completed.stdout.strip() or completed.returncode}")
    stdout = completed.stdout.strip()
    if not stdout:
        raise ValueError("BODY_RENDER: backend returned empty body html")
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout
    if isinstance(parsed, dict):
        body_html = str(parsed.get("html", "")).strip()
        if not body_html:
            raise ValueError("BODY_RENDER: backend response missing html")
        return body_html
    raise ValueError("BODY_RENDER: backend response must be json object or raw html")


def _validate_body_contract(body_html: str, body_spec: dict) -> None:
    lowered = body_html.lower()
    for token in body_spec.get("forbidden_markers", []):
        if token.lower() in lowered:
            raise ValueError(f"BODY_CONTRACT: forbidden marker {token}")
    for token in body_spec.get("required_markers", []):
        if token and token not in body_html:
            raise ValueError(f"BODY_CONTRACT: missing required marker {token}")


def _wrap_body_slot(body_html: str) -> str:
    return (
        "    <!-- BODY_SLOT_START -->\n"
        "    <section class=\"prototype-body-slot\" data-body-slot=\"1\">\n"
        f"{body_html}\n"
        "    </section>\n"
        "    <!-- BODY_SLOT_END -->"
    )


def _normalize_page(page: dict) -> dict:
    normalized = dict(page)
    page_name = normalized.get("page_name", "")
    inferred_type, inferred_archetype = infer_page_shape(page_name)
    normalized["page_type"] = normalized.get("page_type") or inferred_type
    normalized["page_archetype"] = normalized.get("page_archetype") or inferred_archetype
    normalized["output_file"] = normalized.get("output_file") or f"{safe_slug(page_name, 'page')}.html"
    normalized["reference_basis"] = normalized.get("reference_basis") or "fallback"
    normalized["reference_pack_file"] = normalized.get("reference_pack_file") or ""
    normalized["reference_summary"] = normalized.get("reference_summary") or ""
    for key in (
        "reference_sources",
        "layout_directives",
        "visual_cues",
        "interaction_patterns",
        "fields",
        "table_columns",
        "actions",
        "jumps",
        "states",
    ):
        normalized[key] = list(normalized.get(key, []) or [])
    return normalized


def _section_key(section_name: str) -> str:
    mapping = {
        "操作": "actions",
        "状态": "states",
        "布局指令": "layout_directives",
        "视觉线索": "visual_cues",
        "交互模式": "interaction_patterns",
        "参考来源": "reference_sources",
    }
    return mapping[section_name]


def _body_class(terminal_class: str, page_type: str) -> str:
    if page_type == "login":
        return "login-page"
    if terminal_class in {"miniapp", "app"}:
        return "mobile"
    if terminal_class == "h5":
        return "h5"
    if terminal_class == "portal":
        return "portal-shell"
    if terminal_class == "bigscreen":
        return "bigscreen-shell"
    if terminal_class == "industrial":
        return "industrial-shell"
    return f"prototype-page terminal-{terminal_class}"


def _shell_class(terminal_class: str, page_type: str) -> str:
    if page_type == "login":
        return "prototype-shell prototype-login-shell"
    return "prototype-shell"


def _wrap_terminal_shell(spec: dict, page: dict, terminal_class: str, content_html: str, page_file_map: dict[str, str]) -> str:
    module_name = spec.get("module_name", "")
    page_name = page.get("page_name", "")
    page_type = page.get("page_type", "")
    title_block = _page_title_block(page)
    nav_items = _nav_items(module_name, page_name, page_file_map)

    if page_type == "login":
        return (
            "    <section class=\"login-hero-panel\">\n"
            f"      <p class=\"hero-eyebrow\">{html.escape(module_name)}</p>\n"
            f"      <h1 class=\"hero-title\">{html.escape(page_name)}</h1>\n"
            f"      <p class=\"hero-subtitle\">{html.escape(page.get('reference_summary', '使用高保真登录骨架生成。'))}</p>\n"
            "    </section>\n"
            f"    {content_html}\n"
        )

    if terminal_class == "portal":
        return (
            "    <section class=\"portal-hero prototype-portal-hero\">\n"
            f"{title_block}\n"
            f"{content_html}\n"
            "    </section>\n"
        )

    if terminal_class == "bigscreen":
        return (
            f"    <header class=\"prototype-bigscreen-header\">{title_block}</header>\n"
            f"{content_html}\n"
        )

    if terminal_class == "industrial":
        return (
            f"    <header class=\"prototype-industrial-header\">{title_block}</header>\n"
            f"{content_html}\n"
        )

    if terminal_class in {"miniapp", "app", "h5"}:
        browser_bar = "    <div class=\"h5-browser-bar\"><span>◀ 返回</span><span>搜索 / 地址</span><span>⋯</span></div>\n" if terminal_class == "h5" else ""
        tab_bar = _mobile_tab_bar(page_name)
        return (
            f"{browser_bar}"
            f"    <section class=\"prototype-mobile-shell\">\n{title_block}\n{content_html}\n    </section>\n"
            f"{tab_bar}"
        )

    return (
        "    <div class=\"layout prototype-admin-layout\">\n"
        "      <aside class=\"sidebar prototype-sidebar\">\n"
        f"        <div class=\"sidebar-brand\">{html.escape(module_name)}</div>\n"
        f"{nav_items}\n"
        "      </aside>\n"
        "      <main class=\"main-content prototype-main-content\">\n"
        f"{title_block}\n"
        f"{content_html}\n"
        "      </main>\n"
        "    </div>\n"
    )


def _page_title_block(page: dict) -> str:
    return (
        "      <section class=\"hero-card\">\n"
        "        <div>\n"
        "          <p class=\"hero-eyebrow\">高保真 HTML 原型</p>\n"
        f"          <h1 class=\"hero-title\">{html.escape(page.get('page_name', ''))}</h1>\n"
        f"          <p class=\"hero-subtitle\">{html.escape(page.get('reference_summary', ''))}</p>\n"
        "        </div>\n"
        f"        <div class=\"hero-chip-group\">{_state_tags(page.get('states', [])[:3])}</div>\n"
        "      </section>\n"
    )


def _nav_items(module_name: str, page_name: str, page_file_map: dict[str, str]) -> str:
    items = []
    for name, output_file in list(page_file_map.items())[:5]:
        active = " active" if name == page_name else ""
        items.append(f'        <a class="nav-item{active}" href="{html.escape(output_file)}">{html.escape(name)}</a>')
    if not items:
        items.append(f'        <a class="nav-item active" href="#">{html.escape(module_name)}</a>')
    return "      <nav class=\"prototype-side-nav\">\n" + "\n".join(items) + "\n      </nav>"


def _mobile_tab_bar(page_name: str) -> str:
    return (
        "    <nav class=\"tab-bar\">\n"
        f"      <a class=\"tab-bar-item active\" href=\"#\"><span>{html.escape(page_name[:4] or '首页')}</span></a>\n"
        "      <a class=\"tab-bar-item\" href=\"#\"><span>工作台</span></a>\n"
        "      <a class=\"tab-bar-item\" href=\"#\"><span>我的</span></a>\n"
        "    </nav>\n"
    )


def _render_page_content(spec: dict, page: dict, page_file_map: dict[str, str]) -> str:
    page_type = page.get("page_type", "web_detail")
    if page_type in {"web_list", "mobile_list"}:
        return _render_list_page(spec, page, page_file_map)
    if page_type in {"web_form", "mobile_form", "login"}:
        return _render_form_page(spec, page, page_file_map, is_login=page_type == "login")
    if page_type in {"dashboard", "bigscreen_dashboard", "industrial_console", "portal_home", "portal_hub", "mobile_home", "profile"}:
        return _render_dashboard_page(spec, page, page_file_map)
    return _render_detail_page(spec, page, page_file_map)


def _render_list_page(spec: dict, page: dict, page_file_map: dict[str, str]) -> str:
    page_name = page.get("page_name", "")
    fields = page.get("fields", [])
    columns = page.get("table_columns", []) or [{"name": field.get("name", "")} for field in fields[:4]]
    actions = page.get("actions", [])
    jumps = page.get("jumps", [])
    summary_cards = "\n".join(
        (
            "        <div class=\"metric-card\">"
            f"<span class=\"metric-label\">{html.escape(column.get('name', '指标'))}</span>"
            f"<strong class=\"metric-value\">{html.escape(_sample_value(column.get('name', ''), 0, page_name))}</strong>"
            "</div>"
        )
        for column in columns[:3]
    )
    filter_groups = "\n".join(
        (
            "        <div class=\"form-group compact\">"
            f"<label>{html.escape(field.get('name', '关键词'))}</label>"
            f"{_field_control(field, page_name, compact=True)}"
            "</div>"
        )
        for field in fields[:4]
    ) or (
        "        <div class=\"form-group compact\"><label>关键词</label><input class=\"input\" placeholder=\"请输入关键词\"></div>"
    )
    action_buttons = _action_buttons(actions[:3] or ["新增记录", "导出"], jumps, page_file_map)
    header_cells = "".join(f"<th>{html.escape(column.get('name', ''))}</th>" for column in columns)
    rows = []
    for index in range(3):
        cells = "".join(
            f"<td>{_cell_html(column.get('name', ''), _sample_value(column.get('name', ''), index, page_name))}</td>"
            for column in columns
        )
        rows.append(
            "            <tr>"
            f"{cells}"
            "<td class=\"table-actions-cell\">"
            f"{_row_action_buttons(actions, jumps, page_file_map)}"
            "</td></tr>"
        )
    return (
        "        <section class=\"metric-grid metric-grid-compact\">\n"
        f"{summary_cards}\n"
        "        </section>\n"
        "        <section class=\"content-two-column\">\n"
        "          <div class=\"content-main-stack\">\n"
        "            <section class=\"prototype-card prototype-toolbar-card\">\n"
        "              <div class=\"filter-grid\">\n"
        f"{filter_groups}\n"
        "              </div>\n"
        "              <div class=\"toolbar-actions\">\n"
        "                <button class=\"btn-secondary btn-sm\">重置</button>\n"
        "                <button class=\"btn-primary btn-sm\">查询</button>\n"
        f"{action_buttons}\n"
        "              </div>\n"
        "            </section>\n"
        "            <section class=\"prototype-card prototype-table-card\">\n"
        f"              <div class=\"section-heading\"><h2>{html.escape(page_name)}</h2><p>筛选后的业务列表与核心状态</p></div>\n"
        "              <table class=\"table prototype-table\"><thead><tr>"
        f"{header_cells}<th>操作</th></tr></thead><tbody>\n"
        f"{''.join(rows)}\n"
        "              </tbody></table>\n"
        "              <div class=\"pagination prototype-pagination\">\n"
        "                <button class=\"pagination-btn\">上一页</button>\n"
        "                <button class=\"pagination-btn active\">1</button>\n"
        "                <button class=\"pagination-btn\">2</button>\n"
        "                <button class=\"pagination-btn\">下一页</button>\n"
        "              </div>\n"
        "            </section>\n"
        "          </div>\n"
        "          <aside class=\"prototype-side-panel\">\n"
        "            <section class=\"prototype-card side-highlight-card\">\n"
        "              <h3>页面说明</h3>\n"
        f"              <p>{html.escape(page.get('reference_summary', '保持列表页信息密度与操作层级。'))}</p>\n"
        "            </section>\n"
        "            <section class=\"prototype-card\">\n"
        "              <h3>交互模式</h3>\n"
        f"              {_bullet_list(page.get('interaction_patterns', []))}\n"
        "            </section>\n"
        "            <section class=\"prototype-card empty-state\" data-state=\"empty\">\n"
        f"              <p>暂无{html.escape(page_name)}数据</p>\n"
        "              <button class=\"btn-primary\">创建首条记录</button>\n"
        "            </section>\n"
        "            <section class=\"prototype-card\" data-state=\"error\">\n"
        "              <h3>异常态</h3>\n"
        "              <p>列表加载失败时，保留筛选条件并提供重试入口。</p>\n"
        "            </section>\n"
        "          </aside>\n"
        "        </section>\n"
    )


def _render_form_page(spec: dict, page: dict, page_file_map: dict[str, str], *, is_login: bool = False) -> str:
    page_name = page.get("page_name", "")
    fields = page.get("fields", [])
    actions = page.get("actions", [])
    jumps = page.get("jumps", [])
    if is_login:
        form_rows = "\n".join(
            (
                "      <div class=\"form-group\">"
                f"<label>{html.escape(field.get('name', ''))}</label>"
                f"{_field_control(field, page_name)}"
                "</div>"
            )
            for field in (fields[:3] or [{"name": "账号"}, {"name": "密码"}])
        )
        action_buttons = _action_buttons(actions[:2] or ["登录", "找回密码"], jumps, page_file_map, stacked=True)
        return (
            "    <section class=\"login-card prototype-login-card\">\n"
            f"      <p class=\"hero-eyebrow\">{html.escape(spec.get('module_name', ''))}</p>\n"
            f"      <h2 class=\"section-title\">{html.escape(page_name)}</h2>\n"
            f"      <p class=\"section-subtitle\">{html.escape(page.get('reference_summary', ''))}</p>\n"
            f"{form_rows}\n"
            f"{action_buttons}\n"
            "      <div class=\"login-helper-row\"><a href=\"#\">忘记密码</a><a href=\"#\">联系管理员</a></div>\n"
            "      <div class=\"prototype-login-states\">\n"
            "        <div class=\"prototype-card\" data-state=\"processing\"><p>登录处理中，主按钮置灰并显示进度。</p></div>\n"
            "        <div class=\"prototype-card\" data-state=\"error\"><p>账号或密码错误时展示顶部错误提示。</p></div>\n"
            "        <div class=\"prototype-card\" data-state=\"empty\"><p>初次进入展示默认登录表单和辅助说明。</p></div>\n"
            "      </div>\n"
            "    </section>\n"
        )

    midpoint = max(2, len(fields) // 2 or len(fields))
    primary_fields = fields[:midpoint] or [{"name": "名称", "control": "input", "required": "是", "note": "请输入"}]
    secondary_fields = fields[midpoint:] or [{"name": "备注", "control": "textarea", "required": "否", "note": "补充说明"}]
    action_buttons = _action_buttons(actions[:2] or ["提交", "取消"], jumps, page_file_map)
    return (
        "        <section class=\"content-two-column\">\n"
        "          <div class=\"content-main-stack\">\n"
        "            <section class=\"prototype-card prototype-form-card\">\n"
        "              <div class=\"section-heading\"><h2>基础信息</h2><p>先完成影响主流程的字段。</p></div>\n"
        f"              <div class=\"form-grid\">{_field_group_html(primary_fields, page_name)}</div>\n"
        "            </section>\n"
        "            <section class=\"prototype-card prototype-form-card\">\n"
        "              <div class=\"section-heading\"><h2>补充配置</h2><p>承载说明、规则与附加能力。</p></div>\n"
        f"              <div class=\"form-grid\">{_field_group_html(secondary_fields, page_name)}</div>\n"
        "            </section>\n"
        "            <section class=\"prototype-card sticky-action-card\">\n"
        "              <div class=\"toolbar-actions toolbar-actions-right\">\n"
        f"{action_buttons}\n"
        "              </div>\n"
        "            </section>\n"
        "          </div>\n"
        "          <aside class=\"prototype-side-panel\">\n"
        "            <section class=\"prototype-card side-highlight-card\">\n"
        "              <h3>布局指令</h3>\n"
        f"              {_bullet_list(page.get('layout_directives', []))}\n"
        "            </section>\n"
        "            <section class=\"prototype-card\">\n"
        "              <h3>视觉线索</h3>\n"
        f"              {_bullet_list(page.get('visual_cues', []))}\n"
        "            </section>\n"
        "            <section class=\"prototype-card\" data-state=\"empty\">\n"
        "              <h3>空态</h3>\n"
        "              <p>首次进入时提示先完善关键字段。</p>\n"
        "            </section>\n"
        "            <section class=\"prototype-card\" data-state=\"error\">\n"
        "              <h3>异常态</h3>\n"
        "              <p>提交失败时保留输入内容并提示校验原因。</p>\n"
        "            </section>\n"
        "          </aside>\n"
        "        </section>\n"
        "        <section class=\"prototype-state-strip\">\n"
        f"{_state_tags(page.get('states', []))}\n"
        "        </section>\n"
    )


def _render_detail_page(spec: dict, page: dict, page_file_map: dict[str, str]) -> str:
    page_name = page.get("page_name", "")
    fields = page.get("fields", [])[:10]
    actions = page.get("actions", [])
    jumps = page.get("jumps", [])
    action_buttons = _action_buttons(actions[:3] or ["返回", "编辑"], jumps, page_file_map)
    kv_rows = "\n".join(
        (
            "              <div class=\"kv-row\">"
            f"<span class=\"kv-key\">{html.escape(field.get('name', ''))}</span>"
            f"<span class=\"kv-value\">{html.escape(_sample_value(field.get('name', ''), 0, page_name))}</span>"
            "</div>"
        )
        for field in fields
    )
    timeline_rows = "\n".join(
        (
            "              <div class=\"timeline-item\">"
            f"<strong>{html.escape(state)}</strong><span>{html.escape(_sample_time(index))}</span>"
            "</div>"
        )
        for index, state in enumerate(page.get("states", [])[:3] or ["已创建", "处理中", "已完成"])
    )
    return (
        "        <section class=\"hero-card hero-card-inline\">\n"
        "          <div>\n"
        f"            <h2 class=\"hero-title-small\">{html.escape(page_name)}摘要</h2>\n"
        "            <p class=\"hero-subtitle\">聚合关键字段、状态摘要和后续处理动作。</p>\n"
        "          </div>\n"
        f"          <div class=\"hero-chip-group\">{_state_tags(page.get('states', [])[:3])}</div>\n"
        "        </section>\n"
        "        <section class=\"content-two-column\">\n"
        "          <div class=\"content-main-stack\">\n"
        "            <section class=\"prototype-card\">\n"
        "              <div class=\"section-heading\"><h2>关键信息</h2><p>字段按业务阅读顺序展开。</p></div>\n"
        "              <div class=\"kv-grid\">\n"
        f"{kv_rows}\n"
        "              </div>\n"
        "            </section>\n"
        "            <section class=\"prototype-card\">\n"
        "              <div class=\"section-heading\"><h2>最近记录</h2><p>保留处理轨迹和备注说明。</p></div>\n"
        "              <div class=\"timeline-list\">\n"
        f"{timeline_rows}\n"
        "              </div>\n"
        "            </section>\n"
        "          </div>\n"
        "          <aside class=\"prototype-side-panel\">\n"
        "            <section class=\"prototype-card side-highlight-card\">\n"
        "              <h3>关键操作</h3>\n"
        f"{action_buttons}\n"
        "            </section>\n"
        "            <section class=\"prototype-card\">\n"
        "              <h3>交互模式</h3>\n"
        f"              {_bullet_list(page.get('interaction_patterns', []))}\n"
        "            </section>\n"
        "            <section class=\"prototype-card\" data-state=\"empty\">\n"
        "              <h3>空态</h3>\n"
        "              <p>暂无扩展记录时，仅展示摘要和主操作。</p>\n"
        "            </section>\n"
        "            <section class=\"prototype-card\" data-state=\"error\">\n"
        "              <h3>异常态</h3>\n"
        "              <p>详情加载失败时保留返回和重试操作。</p>\n"
        "            </section>\n"
        "          </aside>\n"
        "        </section>\n"
    )


def _render_dashboard_page(spec: dict, page: dict, page_file_map: dict[str, str]) -> str:
    page_name = page.get("page_name", "")
    fields = page.get("fields", [])
    actions = page.get("actions", [])
    jumps = page.get("jumps", [])
    metrics = "\n".join(
        (
            "          <div class=\"metric-card\">"
            f"<span class=\"metric-label\">{html.escape(field.get('name', '核心指标'))}</span>"
            f"<strong class=\"metric-value\">{html.escape(_sample_metric(field.get('name', ''), index))}</strong>"
            "</div>"
        )
        for index, field in enumerate(fields[:4] or [{"name": "订单金额"}, {"name": "待处理"}, {"name": "成交率"}])
    )
    action_buttons = _action_buttons(actions[:3] or ["查看详情"], jumps, page_file_map)
    return (
        "        <section class=\"metric-grid\">\n"
        f"{metrics}\n"
        "        </section>\n"
        "        <section class=\"content-two-column dashboard-layout\">\n"
        "          <section class=\"prototype-card dashboard-focus-panel\">\n"
        "            <div class=\"section-heading\"><h2>主分析区</h2><p>承载图表、趋势或场景主内容。</p></div>\n"
        "            <div class=\"chart-placeholder\">趋势图 / 地图 / 热点分布</div>\n"
        "          </section>\n"
        "          <aside class=\"prototype-side-panel\">\n"
        "            <section class=\"prototype-card side-highlight-card\">\n"
        "              <h3>关键动作</h3>\n"
        f"{action_buttons}\n"
        "            </section>\n"
        "            <section class=\"prototype-card\">\n"
        "              <h3>今日提醒</h3>\n"
        "              <div class=\"timeline-list\">\n"
        "                <div class=\"timeline-item\"><strong>告警</strong><span>设备离线 2 台</span></div>\n"
        "                <div class=\"timeline-item\"><strong>待办</strong><span>审批 6 单</span></div>\n"
        "                <div class=\"timeline-item\"><strong>异常</strong><span>支付失败率 2.1%</span></div>\n"
        "              </div>\n"
        "            </section>\n"
        "            <section class=\"prototype-card\" data-state=\"empty\">\n"
        "              <h3>空态</h3>\n"
        "              <p>未接入数据源时展示接入引导和占位图。</p>\n"
        "            </section>\n"
        "            <section class=\"prototype-card\" data-state=\"error\">\n"
        "              <h3>异常态</h3>\n"
        "              <p>刷新失败时保留上次成功数据并提示重试。</p>\n"
        "            </section>\n"
        "          </aside>\n"
        "        </section>\n"
        "        <section class=\"prototype-state-strip\">\n"
        f"{_state_tags(page.get('states', []))}\n"
        "        </section>\n"
    )


def _field_group_html(fields: list[dict], page_name: str) -> str:
    rendered = []
    for field in fields:
        required_mark = ' <span class="required">*</span>' if str(field.get("required", "否")) == "是" else ""
        rendered.append(
            "<div class=\"form-group\">"
            f"<label>{html.escape(field.get('name', ''))}{required_mark}</label>"
            f"{_field_control(field, page_name)}"
            "</div>"
        )
    return "".join(rendered)


def _field_control(field: dict, page_name: str, *, compact: bool = False) -> str:
    control = str(field.get("control", "input")).lower()
    name = field.get("name", "")
    note = field.get("note", "") or name or page_name
    if "select" in control:
        return (
            "<select class=\"input\">"
            f"<option>{html.escape(note)}</option>"
            "<option>默认选项</option><option>备选项</option></select>"
        )
    if "textarea" in control or "text_area" in control:
        return f"<textarea class=\"input prototype-textarea\" placeholder=\"{html.escape(note)}\"></textarea>"
    input_type = "password" if "密码" in name else "text"
    return f"<input class=\"input\" type=\"{input_type}\" placeholder=\"{html.escape(note)}\">"


def _action_buttons(actions: list[str], jumps: list[dict], page_file_map: dict[str, str], *, stacked: bool = False) -> str:
    rendered = []
    for index, action in enumerate(actions):
        classes = "btn-primary" if index == 0 else "btn-secondary"
        if "删除" in action:
            classes = "btn-danger"
        rendered.append(
            f'<a class="{classes}{" action-block" if stacked else ""}" href="{html.escape(_jump_href(action, jumps, page_file_map))}">{html.escape(action)}</a>'
        )
    return "\n".join(rendered)


def _row_action_buttons(actions: list[str], jumps: list[dict], page_file_map: dict[str, str]) -> str:
    row_actions = [action for action in actions if any(token in action for token in ("查看", "编辑", "删除"))] or ["查看", "编辑", "删除"]
    buttons = []
    for action in row_actions[:3]:
        classes = "btn-secondary btn-xs"
        if "删除" in action:
            classes = "btn-danger btn-xs"
        buttons.append(
            f'<a class="{classes}" href="{html.escape(_jump_href(action, jumps, page_file_map))}">{html.escape(action)}</a>'
        )
    return "".join(buttons)


def _jump_href(action: str, jumps: list[dict], page_file_map: dict[str, str]) -> str:
    for jump in jumps:
        if jump.get("action") == action:
            target = jump.get("target", "")
            if target in page_file_map:
                return page_file_map[target]
    return "#"


def _state_tags(states: list[str]) -> str:
    if not states:
        states = ["正常", "处理中", "异常"]
    return "".join(
        f'<span class="tag {_state_class(state)}">{html.escape(state)}</span>'
        for state in states[:3]
    )


def _state_class(state: str) -> str:
    text = str(state)
    if any(token in text for token in ("启用", "成功", "完成", "正常", "已生效")):
        return "tag-success"
    if any(token in text for token in ("失败", "停用", "异常", "拒绝")):
        return "tag-danger"
    if any(token in text for token in ("待", "审核", "处理中", "锁定")):
        return "tag-warning"
    return "tag-default"


def _sample_value(field_name: str, index: int, page_name: str) -> str:
    text = str(field_name)
    if any(token in text for token in ("编号", "编码", "ID")):
        return f"NO-{202603 + index}"
    if any(token in text for token in ("时间", "日期")):
        return _sample_time(index)
    if any(token in text for token in ("状态", "结果")):
        return ["已启用", "待审核", "已停用"][index % 3]
    if any(token in text for token in ("金额", "价格", "费用", "余额", "收入")):
        return f"¥{1280 + index * 240}"
    if any(token in text for token in ("数量", "库存", "次数")):
        return str(12 + index * 3)
    if any(token in text for token in ("比例", "率", "占比")):
        return f"{62 + index * 4}%"
    if any(token in text for token in ("手机", "电话")):
        return f"1380000{120 + index}"
    if any(token in text for token in ("邮箱",)):
        return f"user{index + 1}@example.com"
    if any(token in text for token in ("人", "用户", "客户", "负责人", "联系人", "姓名")):
        return ["张晓宇", "王婧", "陈立"][index % 3]
    if any(token in text for token in ("标题", "名称", "主题", "商品")):
        return f"{page_name}{index + 1}"
    return ["重点信息", "处理中", "待确认"][index % 3]


def _sample_metric(field_name: str, index: int) -> str:
    text = str(field_name)
    if any(token in text for token in ("率", "占比")):
        return f"{68 + index * 5}%"
    if any(token in text for token in ("金额", "收入", "GMV")):
        return f"¥{12000 + index * 3600}"
    return str(128 + index * 24)


def _sample_time(index: int) -> str:
    return ["2026-03-26 09:30", "2026-03-26 10:10", "2026-03-26 11:40"][index % 3]


def _cell_html(column_name: str, value: str) -> str:
    if any(token in column_name for token in ("状态", "结果")):
        return _state_tags([value])
    return html.escape(value)


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "<ul class=\"inline-bullets\"><li>无</li></ul>"
    return "<ul class=\"inline-bullets\">" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"
