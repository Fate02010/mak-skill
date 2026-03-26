#!/usr/bin/env python3
from __future__ import annotations

import html
import re
from pathlib import Path

from requirements_utils import infer_terminal_type_from_module, safe_slug


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
                spec["pages"].append(current)
            page_name = stripped.split("：", 1)[1].strip()
            current = {
                "page_name": page_name,
                "page_type": "web_detail",
                "output_file": f"{safe_slug(page_name, 'page')}.html",
                "is_nav_page": False,
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
        elif current and current_section == "页面元信息" and stripped.startswith("- 输出文件："):
            current["output_file"] = stripped.split("：", 1)[1].strip()
        elif current and current_section == "页面元信息" and stripped.startswith("- 是否导航页："):
            current["is_nav_page"] = "是" in stripped.split("：", 1)[1]
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
        elif current and current_section in {"操作", "状态"} and stripped.startswith("- "):
            value = stripped[2:].strip()
            if current_section == "操作" and value:
                current["actions"].append(value)
            if current_section == "状态" and value:
                current["states"].append(value)
        elif current and current_section == "跳转" and stripped.startswith("- "):
            value = stripped[2:].strip()
            parts = [item.strip() for item in value.split("->", 1)]
            if len(parts) == 2:
                current["jumps"].append({"action": parts[0], "target": parts[1]})
            elif value:
                current["jumps"].append({"action": value, "target": ""})
        idx += 1
    if current:
        spec["pages"].append(current)
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
        default_output_file = f"{safe_slug(page.get('page_name', ''), 'page')}.html"
        lines.extend(
            [
                f"## 页面规格：{page.get('page_name', '')}",
                "### 页面元信息",
                f"- 页面类型：{page.get('page_type', 'web_detail')}",
                f"- 输出文件：{page.get('output_file', default_output_file)}",
                f"- 是否导航页：{'是' if page.get('is_nav_page') else '否'}",
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


def render_page_html(spec: dict, page: dict, page_file_map: dict[str, str]) -> str:
    module_name = spec.get("module_name", "")
    page_name = page.get("page_name", "")
    page_type = page.get("page_type", "web_detail")
    terminal_class = terminal_css_class(module_name)
    states = page.get("states", []) or ["正常", "无数据", "异常"]
    actions = page.get("actions", []) or ["查看详情"]
    jumps = page.get("jumps", [])
    fields = page.get("fields", [])
    columns = page.get("table_columns", [])
    title = html.escape(page_name)
    nav_html = ""
    if page_type != "login":
        nav_html = f'<header class="page-header"><div class="page-title">{html.escape(module_name)}</div><div class="page-subtitle">{title}</div></header>'

    if page_type in {"web_list", "mobile_list"}:
        content_html = _render_list_page(page_name, fields, columns, actions, states, jumps, page_file_map)
    elif page_type in {"web_form", "mobile_form", "login"}:
        content_html = _render_form_page(page_name, fields, actions, states, jumps, page_file_map, is_login=page_type == "login")
    elif page_type in {"dashboard", "bigscreen_dashboard", "industrial_console", "portal_home", "portal_hub", "mobile_home", "profile"}:
        content_html = _render_dashboard_page(page_name, fields, actions, states, jumps, page_file_map)
    else:
        content_html = _render_detail_page(page_name, fields, actions, states, jumps, page_file_map)
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"zh-CN\">\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        f"  <title>{title}</title>\n"
        "  <link rel=\"stylesheet\" href=\"common.css\">\n"
        "</head>\n"
        f"<body class=\"prototype-page terminal-{terminal_class}\">\n"
        f"  <div class=\"page-shell\" data-prototype-shell=\"1\" data-page-name=\"{html.escape(page_name)}\" data-page-type=\"{html.escape(page_type)}\">\n"
        f"    {nav_html}\n"
        "    <main class=\"page-main\">\n"
        f"{content_html}\n"
        "    </main>\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    )


def render_index_html(product_name: str, pages: list[dict]) -> str:
    links = "\n".join(
        f'      <li><a href="{html.escape(page["output_file"])}">{html.escape(page["page_name"])}</a></li>'
        for page in pages
        if page.get("output_file") != "index.html"
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
        "  <div class=\"page-shell\" data-prototype-shell=\"1\" data-page-name=\"原型导航\" data-page-type=\"index\">\n"
        "    <header class=\"page-header\"><div class=\"page-title\">原型导航</div></header>\n"
        "    <main class=\"page-main\">\n"
        "      <section class=\"page-card\">\n"
        "        <ul class=\"prototype-index-links\">\n"
        f"{links}\n"
        "        </ul>\n"
        "      </section>\n"
        "    </main>\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    )


def _jump_href(action: str, jumps: list[dict], page_file_map: dict[str, str]) -> str:
    for jump in jumps:
        if jump.get("action") == action:
            target = jump.get("target", "")
            if target in page_file_map:
                return page_file_map[target]
    return "#"


def _render_list_page(page_name: str, fields: list[dict], columns: list[dict], actions: list[str], states: list[str], jumps: list[dict], page_file_map: dict[str, str]) -> str:
    filter_fields = "\n".join(
        f'      <label class="field-chip">{html.escape(field.get("name", ""))}</label>'
        for field in fields[:4]
    )
    action_html = "\n".join(
        f'      <a class="btn btn-primary page-action" href="{html.escape(_jump_href(action, jumps, page_file_map))}">{html.escape(action)}</a>'
        for action in actions[:3]
    )
    column_cells = "".join(f"<th>{html.escape(column.get('name', ''))}</th>" for column in (columns or [{"name": "名称"}, {"name": "状态"}]))
    row_cells = "".join(f"<td>{html.escape(column.get('name', ''))}示例</td>" for column in (columns or [{"name": "名称"}, {"name": "状态"}]))
    return (
        "      <section class=\"page-card page-filters\">"
        f"{filter_fields}"
        "      </section>\n"
        "      <section class=\"page-actions\">"
        f"{action_html}"
        "      </section>\n"
        "      <section class=\"page-card page-table-wrap\">\n"
        "        <table class=\"page-table\"><thead><tr>"
        f"{column_cells}<th>操作</th>"
        "</tr></thead><tbody><tr>"
        f"{row_cells}<td><button class=\"btn btn-secondary\">查看</button><button class=\"btn btn-secondary\">编辑</button></td>"
        "</tr></tbody></table>\n"
        "      </section>\n"
        "      <section class=\"page-states\">\n"
        f"        <div class=\"page-state\" data-state=\"empty\">无{html.escape(page_name)}数据，点击主操作开始创建。</div>\n"
        "        <div class=\"page-state\" data-state=\"error\">列表加载失败，请重试。</div>\n"
        f"        <div class=\"page-state\" data-state=\"status\">状态覆盖：{' / '.join(html.escape(item) for item in states[:3])}</div>\n"
        "      </section>\n"
        "      <footer class=\"page-pagination\">分页：上一页 / 下一页</footer>"
    )


def _render_form_page(page_name: str, fields: list[dict], actions: list[str], states: list[str], jumps: list[dict], page_file_map: dict[str, str], *, is_login: bool = False) -> str:
    field_html = "\n".join(
        f'      <label class="page-form-row"><span>{html.escape(field.get("name", ""))}</span><input type="text" placeholder="{html.escape(field.get("note", "") or field.get("name", ""))}"></label>'
        for field in fields
    )
    if not field_html:
        field_html = '      <label class="page-form-row"><span>内容</span><input type="text" placeholder="请输入"></label>'
    action_lines = []
    for index, action in enumerate(actions[:2] or ["提交", "取消"]):
        btn_class = "btn-primary" if index == 0 else "btn-secondary"
        action_lines.append(
            f'      <a class="btn {btn_class} page-action" href="{html.escape(_jump_href(action, jumps, page_file_map))}">{html.escape(action)}</a>'
        )
    action_html = "\n".join(action_lines)
    shell_class = " login-card" if is_login else ""
    return (
        f'      <section class="page-card page-form{shell_class}">\n'
        f"{field_html}\n"
        "      </section>\n"
        "      <section class=\"page-actions\">"
        f"{action_html}"
        "      </section>\n"
        "      <section class=\"page-states\">\n"
        f"        <div class=\"page-state\" data-state=\"processing\">{' / '.join(html.escape(item) for item in states[:1] or ['处理中'])}，主按钮置灰。</div>\n"
        "        <div class=\"page-state\" data-state=\"error\">提交失败，请检查输入后重试。</div>\n"
        "        <div class=\"page-state\" data-state=\"empty\">表单初始为空。</div>\n"
        "      </section>\n"
    )


def _render_detail_page(page_name: str, fields: list[dict], actions: list[str], states: list[str], jumps: list[dict], page_file_map: dict[str, str]) -> str:
    field_html = "\n".join(
        f'      <div class="kv-row"><span class="kv-key">{html.escape(field.get("name", ""))}</span><span class="kv-value">{html.escape(field.get("name", ""))}示例</span></div>'
        for field in fields[:10]
    )
    action_lines = []
    for index, action in enumerate(actions[:3] or ["返回"]):
        btn_class = "btn-primary" if index == 0 else "btn-secondary"
        action_lines.append(
            f'      <a class="btn {btn_class} page-action" href="{html.escape(_jump_href(action, jumps, page_file_map))}">{html.escape(action)}</a>'
        )
    action_html = "\n".join(action_lines)
    return (
        "      <section class=\"page-card detail-status\" data-state=\"status\">"
        f"状态：{' / '.join(html.escape(item) for item in states[:3])}"
        "      </section>\n"
        "      <section class=\"page-card detail-kv\">"
        f"{field_html}"
        "      </section>\n"
        "      <section class=\"page-card detail-records\">最近记录 / 操作日志 / 规则说明</section>\n"
        "      <section class=\"page-actions\">"
        f"{action_html}"
        "      </section>\n"
        "      <section class=\"page-states\">\n"
        "        <div class=\"page-state\" data-state=\"empty\">暂无扩展记录。</div>\n"
        "        <div class=\"page-state\" data-state=\"error\">详情加载失败，请重试。</div>\n"
        "      </section>\n"
    )


def _render_dashboard_page(page_name: str, fields: list[dict], actions: list[str], states: list[str], jumps: list[dict], page_file_map: dict[str, str]) -> str:
    metric_cards = "\n".join(
        f'      <div class="metric-card"><div class="metric-title">{html.escape(field.get("name", ""))}</div><div class="metric-value">128</div></div>'
        for field in fields[:4]
    ) or '      <div class="metric-card"><div class="metric-title">核心指标</div><div class="metric-value">128</div></div>'
    action_lines = []
    for index, action in enumerate(actions[:3] or ["查看详情"]):
        btn_class = "btn-primary" if index == 0 else "btn-secondary"
        action_lines.append(
            f'      <a class="btn {btn_class} page-action" href="{html.escape(_jump_href(action, jumps, page_file_map))}">{html.escape(action)}</a>'
        )
    action_html = "\n".join(action_lines)
    return (
        "      <section class=\"metric-grid\">"
        f"{metric_cards}"
        "      </section>\n"
        "      <section class=\"page-card dashboard-main\">图表区 / 地图区 / 设备区</section>\n"
        "      <section class=\"page-actions\">"
        f"{action_html}"
        "      </section>\n"
        "      <section class=\"page-states\">\n"
        "        <div class=\"page-state\" data-state=\"empty\">暂无数据，请先接入来源。</div>\n"
        "        <div class=\"page-state\" data-state=\"error\">数据刷新失败，请稍后重试。</div>\n"
        f"        <div class=\"page-state\" data-state=\"status\">{' / '.join(html.escape(item) for item in states[:3])}</div>\n"
        "      </section>\n"
    )
