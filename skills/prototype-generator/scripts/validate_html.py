#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from html_utils import forbidden_body_markers_for, required_body_markers_for


PLACEHOLDER_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"Lorem ipsum",
        r"待补充",
        r"功能待定",
        r"示例文字",
        r"按钮N",
        r"字段[0-9一二三四五六七八九十]",
        r"数据项\d",
        r"列表项\d",
        r"InputA",
    )
]

UNSTABLE_RENDER_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"font-family\s*:",
        r"transform\s*:\s*scale\(",
        r"\bzoom\s*:",
    )
]


class RuleResult:
    __slots__ = ("rule", "title", "status", "count", "details")

    def __init__(self, rule: str, title: str, status: str, count: int, details: list[str]):
        self.rule = rule
        self.title = title
        self.status = status
        self.count = count
        self.details = details

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "title": self.title,
            "status": self.status,
            "count": self.count,
            "details": self.details,
        }


def run_checks(path: str | Path) -> dict:
    target = Path(path)
    files = [target] if target.is_file() else sorted(target.glob("*.html"))
    if not files:
        return {
            "summary": {"fail": 1, "warn": 0, "pass": 0},
            "results": [RuleResult("H0", "html_exists", "FAIL", 1, [str(target)]).to_dict()],
        }

    missing_structure: list[str] = []
    missing_css: list[str] = []
    placeholders: list[str] = []
    broken_links: list[str] = []
    missing_shell: list[str] = []
    missing_states: list[str] = []
    missing_archetype: list[str] = []
    weak_skeleton: list[str] = []
    weak_hierarchy: list[str] = []
    unstable_rendering: list[str] = []
    body_slot_issues: list[str] = []
    missing_admin_shell: list[str] = []
    index_nav_issues: list[str] = []
    file_names = {file.name for file in files}
    for file in files:
        text = file.read_text(encoding="utf-8")
        lowered = text.lower()
        page_type = _extract_attr(text, "data-page-type")
        page_archetype = _extract_attr(text, "data-page-archetype")
        reference_basis = _extract_attr(text, "data-reference-basis")
        shell_variant = _extract_attr(text, "data-shell-variant")
        if "<html" not in lowered or "<head" not in lowered or "<body" not in lowered or "</html>" not in lowered or "<title>" not in lowered:
            missing_structure.append(file.name)
        if 'href="common.css"' not in text and "href='common.css'" not in text:
            missing_css.append(file.name)
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern.search(text):
                placeholders.append(file.name)
                break
        if 'data-prototype-shell="1"' not in text or 'data-page-name="' not in text:
            missing_shell.append(file.name)
        if not page_archetype or not reference_basis:
            missing_archetype.append(file.name)
        if page_type != "index":
            has_empty = 'data-state="empty"' in text
            has_error = 'data-state="error"' in text or "empty-state" in text
            has_processing = 'data-state="processing"' in text or "sticky-action-card" in text
            if not (has_empty and has_error):
                missing_states.append(file.name)
            if page_type in {"web_form", "mobile_form", "login"} and not has_processing:
                missing_states.append(file.name)
        hrefs = re.findall(r'href="([^"]+)"', text) + re.findall(r"href='([^']+)'", text)
        for href in hrefs:
            if href.startswith(("http://", "https://", "#", "javascript:")):
                continue
            if href.endswith(".html") and href not in file_names:
                broken_links.append(f"{file.name} -> {href}")
        for href in re.findall(r"location\.href\s*=\s*'([^']+)'", text):
            if href.endswith(".html") and href not in file_names:
                broken_links.append(f"{file.name} -> {href}")
        skeleton_issue = _check_archetype_skeleton(file.name, text, page_type, page_archetype)
        if skeleton_issue:
            weak_skeleton.append(skeleton_issue)
        hierarchy_issue = _check_visual_hierarchy(file.name, text, page_type)
        if hierarchy_issue:
            weak_hierarchy.append(hierarchy_issue)
        body_slot_issue = _check_body_slot_contract(file.name, text, page_type, page_archetype)
        if body_slot_issue:
            body_slot_issues.append(body_slot_issue)
        admin_shell_issue = _check_admin_shell(file.name, text, page_type, page_archetype, shell_variant)
        if admin_shell_issue:
            missing_admin_shell.append(admin_shell_issue)
        index_nav_issue = _check_index_navigation(file.name, text, page_type, shell_variant)
        if index_nav_issue:
            index_nav_issues.append(index_nav_issue)
        for pattern in UNSTABLE_RENDER_PATTERNS:
            if pattern.search(text):
                unstable_rendering.append(f"{file.name}: 命中不稳定样式 `{pattern.pattern}`")
                break

    results = [
        RuleResult("H1", "html_document_structure", "FAIL" if missing_structure else "PASS", len(missing_structure), missing_structure),
        RuleResult("H2", "common_css_link", "FAIL" if missing_css else "PASS", len(missing_css), missing_css),
        RuleResult("H3", "placeholder_text", "FAIL" if placeholders else "PASS", len(placeholders), placeholders),
        RuleResult("H4", "broken_local_links", "FAIL" if broken_links else "PASS", len(broken_links), broken_links),
        RuleResult("H5", "page_shell_markers", "FAIL" if missing_shell else "PASS", len(missing_shell), missing_shell),
        RuleResult("H6", "state_coverage", "FAIL" if missing_states else "PASS", len(sorted(set(missing_states))), sorted(set(missing_states))),
        RuleResult("H7", "reference_metadata", "FAIL" if missing_archetype else "PASS", len(missing_archetype), missing_archetype),
        RuleResult("H8", "archetype_skeleton", "FAIL" if weak_skeleton else "PASS", len(weak_skeleton), weak_skeleton),
        RuleResult("H9", "visual_hierarchy", "FAIL" if weak_hierarchy else "PASS", len(weak_hierarchy), weak_hierarchy),
        RuleResult("H10", "render_stability", "FAIL" if unstable_rendering else "PASS", len(unstable_rendering), unstable_rendering),
        RuleResult("H11", "body_slot_contract", "FAIL" if body_slot_issues else "PASS", len(body_slot_issues), body_slot_issues),
        RuleResult("H12", "admin_console_shell", "FAIL" if missing_admin_shell else "PASS", len(missing_admin_shell), missing_admin_shell),
        RuleResult("H13", "grouped_index_navigation", "FAIL" if index_nav_issues else "PASS", len(index_nav_issues), index_nav_issues),
    ]
    fail = sum(1 for item in results if item.status == "FAIL")
    return {
        "summary": {"fail": fail, "warn": 0, "pass": 1 if fail == 0 else 0},
        "results": [item.to_dict() for item in results],
    }


def _check_archetype_skeleton(filename: str, text: str, page_type: str, page_archetype: str) -> str:
    row_count = text.count("<tr>")
    metric_count = text.count("metric-card")
    form_group_count = text.count("form-group")
    kv_count = text.count("kv-row")
    if page_archetype == "tree_manage":
        required = ("data-tree-manage=\"1\"", "prototype-resource-tree", "prototype-tree-node", "prototype-resource-detail-card")
        missing = [token for token in required if token not in text]
        if missing:
            return f"{filename}: 资源管理页缺少树管理骨架 {', '.join(missing)}"
    if page_type in {"web_list", "mobile_list"}:
        if "<table" not in text or row_count < 4:
            return f"{filename}: 列表页缺少真实表格或数据行不足"
    if page_type in {"web_form", "mobile_form"}:
        if form_group_count < 2 or "sticky-action-card" not in text:
            return f"{filename}: 表单页缺少分组字段或底部操作区"
    if page_type == "login":
        if "nav-bar" in text or "sidebar" in text:
            return f"{filename}: 登录页出现业务导航"
        if form_group_count < 2:
            return f"{filename}: 登录页字段不足"
    if page_archetype == "detail_kv" and kv_count < 2:
        return f"{filename}: 详情页缺少键值对区"
    if page_archetype in {"dashboard", "mobile_home", "portal_landing"} and metric_count < 2:
        return f"{filename}: 首页/看板缺少指标卡"
    return ""


def _check_visual_hierarchy(filename: str, text: str, page_type: str) -> str:
    primary_count = text.count("btn-primary") + text.count("btn-danger")
    secondary_count = text.count("btn-secondary")
    card_count = text.count("prototype-card") + text.count("hero-card")
    if page_type in {"web_list", "mobile_list"}:
        toolbar_match = re.search(r"<div class=['\"]toolbar-actions['\"]>(.*?)</div>", text, re.S)
        if toolbar_match:
            toolbar = toolbar_match.group(1)
            if any(label in toolbar for label in (">编辑<", ">删除<", ">查看详情<", ">授权<")):
                return f"{filename}: 列表页查询区混入行级操作"
    if page_type != "index" and primary_count == 0:
        return f"{filename}: 缺少主按钮"
    if page_type in {"web_list", "web_form", "web_detail", "dashboard"} and card_count < 2:
        return f"{filename}: 视觉层级不足，卡片区块过少"
    if primary_count > 0 and secondary_count == 0 and page_type in {"web_list", "web_form", "web_detail"}:
        return f"{filename}: 主次操作未区分"
    return ""


def _check_body_slot_contract(filename: str, text: str, page_type: str, page_archetype: str) -> str:
    if 'data-body-slot="1"' not in text and "data-body-slot='1'" not in text:
        return f"{filename}: 缺少 body slot 标记"
    if "<!-- BODY_SLOT_START -->" not in text or "<!-- BODY_SLOT_END -->" not in text:
        return f"{filename}: 缺少 body slot 边界注释"
    body_slot = text.split("<!-- BODY_SLOT_START -->", 1)[1].split("<!-- BODY_SLOT_END -->", 1)[0]
    lowered = body_slot.lower()
    for token in forbidden_body_markers_for(page_type):
        if token.lower() in lowered:
            return f"{filename}: body slot 命中禁用标记 {token}"
    for token in required_body_markers_for(page_type, page_archetype):
        if token and token not in body_slot:
            return f"{filename}: body slot 缺少必需标记 {token}"
    return ""


def _check_admin_shell(filename: str, text: str, page_type: str, page_archetype: str, shell_variant: str) -> str:
    page_name = _extract_attr(text, "data-page-name")
    if shell_variant != "admin_console" or page_type in {"index", "login"} or page_archetype == "modal_form" or "抽屉" in page_name:
        return ""
    required = ("prototype-admin-header", "prototype-sidebar", "prototype-nav-parent", "prototype-subnav-item", "prototype-workspace-intro")
    missing = [token for token in required if token not in text]
    if missing:
        return f"{filename}: 后台壳层缺少 {', '.join(missing)}"
    return ""


def _check_index_navigation(filename: str, text: str, page_type: str, shell_variant: str) -> str:
    if page_type != "index" or shell_variant != "admin_console":
        return ""
    required = ("prototype-index-admin-layout", "prototype-nav-group", "prototype-nav-parent", "prototype-subnav-item")
    if any(token not in text for token in required):
        return f"{filename}: 导航首页未按后台菜单树分组"
    return ""


def _extract_attr(text: str, attr: str) -> str:
    for quote in ('"', "'"):
        marker = f"{attr}={quote}"
        if marker in text:
            return text.split(marker, 1)[1].split(quote, 1)[0]
    return ""


def main():
    parser = argparse.ArgumentParser(description="校验 HTML 原型结构、参考元数据和高保真骨架")
    parser.add_argument("path")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    report = run_checks(args.path)
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["summary"]["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
