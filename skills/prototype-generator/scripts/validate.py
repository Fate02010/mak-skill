#!/usr/bin/env python3
"""
validate.py — draw.io 文件自动化验收检查，输出问题报告。

用法:
    python3 validate.py <drawio_file> [--fix] [--json]

选项:
    --fix   自动修复可修复的问题（目前仅坐标 8 倍数对齐）
    --json  输出 JSON 格式报告（默认输出人类可读格式）

仅依赖 Python 标准库。
"""

import argparse
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _text_len(value: str) -> int:
    """计算 mxCell value 的纯文本字数（去掉 HTML 标签）。"""
    if not value:
        return 0
    plain = re.sub(r"<[^>]+>", "", value)
    plain = re.sub(r"&[a-zA-Z]+;|&#[0-9]+;|&#x[0-9a-fA-F]+;", " ", plain)
    return len(plain.strip())


_LABEL_KEYWORDS = {"价格", "状态", "时间", "编号", "姓名", "金额", "数量", "名称",
                    "电话", "地址", "日期", "备注", "类型", "规格", "单位"}
_PLACEHOLDER_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"字段[一二三四五六七八九十0-9]",
        r"列表项[0-9一二三四五六七八九十]",
        r"示例数据",
        r"真实字段",
        r"占位",
        r"待补充",
        r"功能待定",
        r"Lorem ipsum",
        r"数据项[0-9]",
        r"按钮[A-Z0-9]",
    )
]


def _is_pure_description(cell: ET.Element) -> bool:
    """判断一个 mxCell 是否为「纯说明元素」。"""
    style = cell.get("style", "")
    value = cell.get("value", "")
    if "text;" not in style:
        return False
    if _text_len(value) <= 30:
        return False
    for kw in _LABEL_KEYWORDS:
        if kw in value:
            return False
    return True


def _is_text_cell(cell: ET.Element) -> bool:
    """判断 mxCell 是否为 text 类型。"""
    return "text;" in cell.get("style", "")


def _get_geometry(cell: ET.Element):
    """获取 mxCell 下的 mxGeometry 子元素。"""
    return cell.find("mxGeometry")


def _annotation_x_threshold(swimlane_width: float) -> float:
    """根据 swimlane 宽度推断标注区起点。"""
    if swimlane_width <= 700:
        return 400.0  # 移动端 (标注区 x >= 400)
    return 1464.0  # Web (标注区 x >= 1464)


def _is_nav_group_swimlane(children: list[ET.Element]) -> bool:
    """判断 swimlane 是否属于导航图里的模块分组。"""
    if not children:
        return False
    node_like = 0
    for child in children:
        style = child.get("style", "")
        if "fillColor=#e3f2fd" in style and "strokeColor=#1e88e5" in style and "fontSize=12" in style:
            node_like += 1
    return node_like == len(children)


def _is_auth_like_page(name: str) -> bool:
    text = str(name or "")
    if "日志" in text:
        return False
    return any(token in text for token in ("登录", "注册", "找回密码", "重置密码", "验证码"))


def _is_overlay_like_page(name: str) -> bool:
    text = str(name or "")
    return any(token in text for token in ("弹窗", "抽屉", "确认", "提示"))


def _is_detail_like_page(name: str) -> bool:
    text = str(name or "")
    return "详情" in text and "列表" not in text


def _is_form_like_page(name: str) -> bool:
    text = str(name or "")
    return any(token in text for token in ("表单", "编辑页", "设置页", "配置页"))


def _is_in_ui_area(cell: ET.Element, threshold: float) -> bool:
    """判断 mxCell 是否位于 UI 区（x < 标注区起点）。"""
    geo = _get_geometry(cell)
    if geo is None:
        return True  # 无坐标时默认属于 UI 区
    x = float(geo.get("x", "0"))
    return x < threshold


def _round8(val: float) -> float:
    """四舍五入到最近的 8 倍数。"""
    return round(val / 8.0) * 8.0


# ---------------------------------------------------------------------------
# 解析 draw.io 结构
# ---------------------------------------------------------------------------

class DrawioFile:
    """解析 draw.io XML 并提供 swimlane -> children 映射。"""

    def __init__(self, path: str):
        self.path = path
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()
        self.all_cells: dict[str, ET.Element] = {}
        self.swimlanes: list = []
        self.swimlane_children: dict[str, list] = {}

        self._parse()

    def _parse(self):
        # 收集所有 mxCell
        for cell in self.root.iter("mxCell"):
            cid = cell.get("id", "")
            if cid:
                self.all_cells[cid] = cell

        # 识别 swimlane（style 含 swimlane 或 shape=mxgraph.mockup）
        for cid, cell in self.all_cells.items():
            style = cell.get("style", "")
            if "swimlane" in style:
                self.swimlanes.append(cell)
                self.swimlane_children[cid] = []

        # 将子元素归入各 swimlane
        for cid, cell in self.all_cells.items():
            parent = cell.get("parent", "")
            if parent in self.swimlane_children:
                self.swimlane_children[parent].append(cell)

    def swimlane_name(self, sl: ET.Element) -> str:
        return sl.get("value", sl.get("id", "?"))

    def swimlane_width(self, sl: ET.Element) -> float:
        geo = _get_geometry(sl)
        if geo is not None:
            return float(geo.get("width", "400"))
        return 400.0

    def all_mxcells(self) -> list:
        return list(self.all_cells.values())

    def write_back(self):
        self.tree.write(self.path, encoding="utf-8", xml_declaration=True)


# ---------------------------------------------------------------------------
# 检查规则
# ---------------------------------------------------------------------------

class RuleResult:
    __slots__ = ("rule", "title", "status", "count", "details")

    def __init__(self, rule: str, title: str, status: str,
                 count: int = 0, details: object = None):
        self.rule = rule
        self.title = title
        self.status = status  # PASS / WARN / FAIL
        self.count = count
        self.details = details or []

    def to_dict(self) -> dict:
        d = {"rule": self.rule, "status": self.status, "count": self.count}
        if self.details:
            d["details"] = self.details
        return d


# ---- C1 说明框过多 ---------------------------------------------------------

def check_c1(doc: DrawioFile) -> RuleResult:
    worst = "PASS"
    details: list = []
    total_excess = 0

    for sl in doc.swimlanes:
        sid = sl.get("id", "?")
        name = doc.swimlane_name(sl)
        threshold = _annotation_x_threshold(doc.swimlane_width(sl))
        children = doc.swimlane_children.get(sid, [])

        desc_count = 0
        for c in children:
            if _is_in_ui_area(c, threshold) and _is_pure_description(c):
                desc_count += 1

        if desc_count >= 5:
            worst = "FAIL"
            total_excess += desc_count
            details.append(f"{name}: {desc_count} 个纯说明元素")
        elif desc_count >= 3:
            if worst != "FAIL":
                worst = "WARN"
            total_excess += desc_count
            details.append(f"{name}: {desc_count} 个纯说明元素")

    return RuleResult("C1", "说明框", worst, total_excess, details)


# ---- C2 大段文字占主体 -----------------------------------------------------

def check_c2(doc: DrawioFile) -> RuleResult:
    worst = "PASS"
    details: list = []
    total = 0

    for sl in doc.swimlanes:
        sid = sl.get("id", "?")
        name = doc.swimlane_name(sl)
        threshold = _annotation_x_threshold(doc.swimlane_width(sl))
        children = doc.swimlane_children.get(sid, [])

        long_count = 0
        for c in children:
            if not _is_in_ui_area(c, threshold):
                continue
            style = c.get("style", "")
            if "text;" not in style:
                continue
            if _text_len(c.get("value", "")) > 50:
                long_count += 1

        if long_count >= 3:
            worst = "FAIL"
            total += long_count
            details.append(f"{name}: {long_count} 个超 50 字文本元素")

    return RuleResult("C2", "大段文字", worst, total, details)


# ---- C3 页面像文档 ---------------------------------------------------------

def check_c3(doc: DrawioFile) -> RuleResult:
    worst = "PASS"
    details: list = []
    total = 0

    for sl in doc.swimlanes:
        sid = sl.get("id", "?")
        name = doc.swimlane_name(sl)
        threshold = _annotation_x_threshold(doc.swimlane_width(sl))
        children = doc.swimlane_children.get(sid, [])

        ui_cells = [c for c in children if _is_in_ui_area(c, threshold)]
        if not ui_cells:
            continue

        text_count = sum(1 for c in ui_cells if _is_text_cell(c))
        ratio = text_count / len(ui_cells)

        if ratio > 0.70:
            worst = "FAIL"
            total += 1
            details.append(f"{name}: text 元素占比 {ratio:.0%} ({text_count}/{len(ui_cells)})")

    return RuleResult("C3", "页面像文档", worst, total, details)


# ---- C4 内容同权 -----------------------------------------------------------

def check_c4(doc: DrawioFile) -> RuleResult:
    worst = "PASS"
    details: list = []
    warn_count = 0

    _plain_colors = {"", "none", "#ffffff", "#FFFFFF", "#f5f5f5", "#F5F5F5",
                     "#e0e0e0", "#E0E0E0", "#cccccc", "#CCCCCC",
                     "white", "#fafafa", "#FAFAFA"}

    for sl in doc.swimlanes:
        sid = sl.get("id", "?")
        name = doc.swimlane_name(sl)
        threshold = _annotation_x_threshold(doc.swimlane_width(sl))
        children = doc.swimlane_children.get(sid, [])
        if _is_nav_group_swimlane(children):
            continue

        btn_colors = set()
        font_sizes = set()
        btn_count = 0

        for c in children:
            if not _is_in_ui_area(c, threshold):
                continue
            style = c.get("style", "")

            # 按钮检测：style 含 "btn"，或蓝/红描边按钮，或有非灰 fillColor + rounded
            is_btn = "btn" in style.lower()
            if not is_btn:
                has_stroke = re.search(r"strokeColor=([^;]+)", style)
                has_fill = re.search(r"fillColor=([^;]+)", style)
                if has_stroke and has_stroke.group(1) in {"#1e88e5", "#1565c0", "#f44336", "#e53935"} and "rounded" in style:
                    is_btn = True
                elif has_fill and has_fill.group(1) not in _plain_colors and "rounded" in style:
                    is_btn = True
            if is_btn:
                btn_count += 1
                m = re.search(r"fillColor=([^;]+)", style)
                stroke = re.search(r"strokeColor=([^;]+)", style)
                fill = m.group(1) if m else "none"
                border = stroke.group(1) if stroke else "none"
                color = f"{fill}|{border}"
                btn_colors.add(color)

            # 字号检测
            m = re.search(r"fontSize=(\d+)", style)
            if m:
                font_sizes.add(m.group(1))

        has_btn_variety = len(btn_colors) >= 2
        has_font_variety = len(font_sizes) >= 2

        if btn_count < 2 and has_font_variety:
            continue

        if btn_count >= 2 and not (has_btn_variety and has_font_variety):
            if worst != "FAIL":
                worst = "WARN"
            warn_count += 1
            reasons = []
            if not has_btn_variety:
                reasons.append(f"按钮仅 {len(btn_colors)} 种样式")
            if not has_font_variety:
                reasons.append(f"字号仅 {len(font_sizes)} 种")
            details.append(f"{name}: {', '.join(reasons)}")

    return RuleResult("C4", "视觉层级", worst, warn_count, details)


# ---- C5 坐标 8 倍数对齐 ---------------------------------------------------

def check_c5(doc: DrawioFile, fix: bool = False) -> RuleResult:
    violations: list = []
    fixed_count = 0

    for cell in doc.all_mxcells():
        geo = _get_geometry(cell)
        if geo is None:
            continue

        cid = cell.get("id", "?")

        for attr in ("x", "y", "width", "height"):
            raw = geo.get(attr)
            if raw is None:
                continue
            val = float(raw)

            # height=1 分隔线豁免
            if attr == "height" and val == 1:
                continue

            if val % 8 != 0:
                corrected = _round8(val)
                violations.append(f"{cid}: {attr}={int(val)} -> 应为 {int(corrected)}")
                if fix:
                    geo.set(attr, str(int(corrected)))
                    fixed_count += 1

    if fix and fixed_count > 0:
        doc.write_back()

    count = len(violations)
    if count == 0:
        status = "PASS"
    elif count <= 5:
        status = "WARN"
    else:
        status = "FAIL"

    return RuleResult("C5", "坐标对齐", status, count,
                      violations[:20] if violations else [])  # 最多展示 20 条


# ---- C6 登录页无导航 -------------------------------------------------------

def check_c6(doc: DrawioFile) -> RuleResult:
    details: list = []
    worst = "PASS"

    for sl in doc.swimlanes:
        name = doc.swimlane_name(sl)
        if "登录" not in name:
            continue

        sid = sl.get("id", "?")
        children = doc.swimlane_children.get(sid, [])

        for c in children:
            style = c.get("style", "")
            if "nav" in style or "bottom_bar" in style:
                worst = "WARN"
                details.append(f"{name}: 包含导航/底部栏元素 (style 含 nav/bottom_bar)")
                break

    return RuleResult("C6", "登录页无导航", worst, len(details), details)


# ---- C7 XML 合法性 ---------------------------------------------------------

def check_c7(doc: DrawioFile) -> RuleResult:
    details: list = []

    # mxCell 数量 vs mxGeometry 数量一致性
    cell_count = 0
    geo_count = 0
    for cell in doc.root.iter("mxCell"):
        cell_count += 1
        if cell.find("mxGeometry") is not None:
            geo_count += 1

    # 检查 parent 引用
    all_ids = set()
    for cell in doc.root.iter("mxCell"):
        cid = cell.get("id", "")
        if cid:
            all_ids.add(cid)

    orphan_count = 0
    for cell in doc.root.iter("mxCell"):
        parent = cell.get("parent", "")
        if parent and parent not in all_ids:
            orphan_count += 1
            cid = cell.get("id", "?")
            details.append(f"{cid}: parent={parent} 不存在")

    if orphan_count > 0:
        status = "FAIL"
    else:
        status = "PASS"

    return RuleResult("C7", "XML合法性", status, orphan_count, details)


# ---- C8 数据行充分性 -------------------------------------------------------

def check_c8(doc: DrawioFile) -> RuleResult:
    details: list = []
    worst = "PASS"
    warn_count = 0

    for sl in doc.swimlanes:
        sid = sl.get("id", "?")
        name = doc.swimlane_name(sl)
        children = doc.swimlane_children.get(sid, [])

        if _is_auth_like_page(name) or _is_overlay_like_page(name) or _is_detail_like_page(name):
            continue

        table_row_count = 0
        list_row_count = 0
        card_count = 0
        has_table_header = False
        has_pagination = False
        for c in children:
            style = c.get("style", "")
            if "table_row" in style:
                table_row_count += 1
            if "list_row" in style:
                list_row_count += 1
            if "card" in style:
                card_count += 1
            if "table_header" in style:
                has_table_header = True
            if "pagination" in style:
                has_pagination = True

        row_count = 0
        if has_table_header or has_pagination or table_row_count > 0:
            row_count = table_row_count
        elif list_row_count > 0:
            row_count = list_row_count
        elif card_count >= 2:
            # 卡片流页面至少应有多张卡片，单卡页不视为“数据行不足”。
            row_count = card_count

        if row_count and row_count < 3:
            if worst != "FAIL":
                worst = "WARN"
            warn_count += 1
            details.append(f"{name}: 仅 {row_count} 条数据行 (建议 >= 3)")

    return RuleResult("C8", "数据行充分性", worst, warn_count, details)


# ---- C9 骨架完整性 -------------------------------------------------------

def check_c9(doc: DrawioFile) -> RuleResult:
    worst = "PASS"
    details: list = []
    issue_count = 0

    for sl in doc.swimlanes:
        sid = sl.get("id", "?")
        name = doc.swimlane_name(sl)
        children = doc.swimlane_children.get(sid, [])
        if _is_nav_group_swimlane(children):
            continue
        has_nav = False
        has_bg = False
        has_annotation = False
        has_list = False
        has_form = False
        has_modal = False

        for c in children:
            style = c.get("style", "")
            value = c.get("value", "")
            if "fillColor=#1e88e5" in style or "fillColor=#1565c0" in style:
                has_nav = True
            if "fillColor=#f5f5f5" in style or "fillColor=#263238" in style:
                has_bg = True
            if "fillColor=#fffde7" in style or ("fontSize=10" in style and "#5d4037" in style):
                has_annotation = True
            if "table_row" in style or "card" in style or "list_row" in style or ("fontSize=12" in style and "spacingLeft=8" in style):
                has_list = True
            if any(token in style for token in ("strokeColor=#bdbdbd", "spacingLeft=8", "verticalAlign=top;fontSize=13")):
                has_form = True
            if "shadow=1;arcSize=8" in style and "fillColor=#ffffff" in style and "rounded=1" in style:
                has_modal = has_modal or ("弹窗" in name)
            if "annotation_card" in value:
                has_annotation = True

        reasons = []
        if "登录" not in name and "删除确认" not in name and not has_modal and not has_nav and "首页" not in name:
            reasons.append("缺少导航骨架")
        if "登录" not in name and not has_bg and not has_modal:
            reasons.append("缺少背景层")
        if "弹窗" not in name and not has_annotation:
            reasons.append("缺少标注卡")
        if "列表" in name and not has_list:
            reasons.append("缺少列表骨架")
        if ("新增" in name or "编辑" in name or "表单" in name) and not has_form and not has_modal:
            reasons.append("缺少表单控件")

        if reasons:
            worst = "WARN"
            issue_count += 1
            details.append(f"{name}: {', '.join(reasons)}")

    return RuleResult("C9", "骨架完整性", worst, issue_count, details)


# ---- C10 CRUD 闭环 -------------------------------------------------------

def check_c10(doc: DrawioFile) -> RuleResult:
    details: list = []
    worst = "PASS"
    modal_names = {doc.swimlane_name(sl) for sl in doc.swimlanes if "弹窗" in doc.swimlane_name(sl)}
    issue_count = 0

    for sl in doc.swimlanes:
        sid = sl.get("id", "?")
        name = doc.swimlane_name(sl)
        children = doc.swimlane_children.get(sid, [])
        if _is_nav_group_swimlane(children):
            continue
        is_list_like = "列表" in name or any("fontSize=12" in c.get("style", "") and "spacingLeft=8" in c.get("style", "") for c in children)
        has_edit = any("编辑" in c.get("value", "") and "fontSize=12" in c.get("style", "") for c in children)
        has_delete = any("删除" in c.get("value", "") and "fontSize=12" in c.get("style", "") for c in children)
        has_add = any("新增" in c.get("value", "") and "fontStyle=1" in c.get("style", "") for c in children)
        if not is_list_like:
            continue
        if not (has_edit or has_delete or has_add):
            continue
        if not any("新增/编辑" in modal for modal in modal_names):
            worst = "FAIL"
            issue_count += 1
            details.append(f"{name}: 有新增/编辑操作但缺少新增/编辑弹窗")
        if (has_edit or has_delete) and not any("删除" in modal and "确认" in modal for modal in modal_names):
            worst = "FAIL"
            issue_count += 1
            details.append(f"{name}: 有删除操作但缺少删除确认弹窗")

    return RuleResult("C10", "CRUD闭环", worst, issue_count, details)


# ---- C11 占位词残留 -----------------------------------------------------

def check_c11(doc: DrawioFile) -> RuleResult:
    details: list = []
    count = 0

    for cell in doc.all_mxcells():
        value = cell.get("value", "")
        plain = re.sub(r"<[^>]+>", "", value)
        for pattern in _PLACEHOLDER_PATTERNS:
            if pattern.search(plain):
                count += 1
                details.append(f"{cell.get('id', '?')}: {plain[:40]}")
                break

    status = "FAIL" if count > 0 else "PASS"
    return RuleResult("C11", "占位词残留", status, count, details[:20])


# ---- C12 视觉层级 -------------------------------------------------------

def check_c12(doc: DrawioFile) -> RuleResult:
    worst = "PASS"
    details: list = []
    count = 0

    for sl in doc.swimlanes:
        sid = sl.get("id", "?")
        name = doc.swimlane_name(sl)
        threshold = _annotation_x_threshold(doc.swimlane_width(sl))
        children = doc.swimlane_children.get(sid, [])
        if _is_nav_group_swimlane(children):
            continue
        categories = set()
        for c in children:
            if not _is_in_ui_area(c, threshold):
                continue
            style = c.get("style", "")
            if "btn" in style or "strokeColor=#1e88e5" in style or "strokeColor=#f44336" in style:
                categories.add("button")
            elif "tag_" in style or "fillColor=#e8f5e9" in style or "fillColor=#fff3e0" in style:
                categories.add("tag")
            elif "fontSize=16" in style or "fontStyle=1" in style:
                categories.add("title")
            elif "input" in style or "select" in style or "textarea" in style:
                categories.add("form")
            elif "card" in style or "modal_bg" in style:
                categories.add("container")
            elif "list_row" in style or "fillColor=#f5f5f5" in style or "fillColor=#263238" in style:
                categories.add("layout")
            elif "ellipse" in style or "#90caf9" in style or "spacingLeft=32" in style:
                categories.add("media")
            elif "text;" in style:
                categories.add("text")
        if len(categories) < 3:
            worst = "WARN"
            count += 1
            details.append(f"{name}: 视觉层级仅 {len(categories)} 类")

    return RuleResult("C12", "视觉层级多样性", worst, count, details)


# ---- C13 页面类型降级 ---------------------------------------------------

def _classify_page_name(name: str) -> str:
    if "删除确认" in name or ("确认" in name and "弹窗" in name and "发货" not in name):
        return "confirm_dialog"
    if _is_auth_like_page(name):
        return "login"
    if "工作台" in name or "dashboard" in name.lower() or "后台首页" in name:
        return "dashboard"
    if "详情" in name or (("设置" in name or "处理" in name) and "列表" not in name and "弹窗" not in name):
        return "detail_kv"
    if "授权" in name or "权限" in name and ("抽屉" in name or "角色" in name):
        return "drawer_permission"
    if "发货" in name or "调度" in name or "路线" in name:
        return "dispatch_board"
    if "分类" in name or "部门岗位" in name or "组织" in name:
        return "tree_manage"
    if "新增" in name or "编辑" in name or "弹窗" in name or _is_form_like_page(name):
        return "modal_form"
    return "list_table"


def _count_features(cells: list[ET.Element], threshold: float) -> dict:
    features = {
        "cards": 0,
        "rows": 0,
        "buttons": 0,
        "inputs": 0,
        "tags": 0,
        "titles": 0,
        "timeline": 0,
        "tree": 0,
    }
    row_y_positions = {}
    input_y_positions = set()
    for cell in cells:
        if not _is_in_ui_area(cell, threshold):
            continue
        style = cell.get("style", "")
        value = cell.get("value", "")
        geo = _get_geometry(cell)
        y = float(geo.get("y", "0")) if geo is not None else 0.0

        is_card_like = (
            "shadow=1" in style and "arcSize=8" in style and "fillColor=#ffffff" in style
        ) or (
            "rounded=1" in style and "strokeColor=#e0e0e0" in style and "fillColor=#ffffff" in style
        )
        if is_card_like and "annotation" not in style:
            features["cards"] += 1

        is_table_text = (
            "text;" in style
            and "fontSize=12" in style
            and any(token in style for token in ("fillColor=#ffffff", "fillColor=#fafafa", "fillColor=#f5f5f5"))
        )
        if is_table_text:
            row_y_positions[y] = row_y_positions.get(y, 0) + 1

        if ("btn" in style or "strokeColor=#1e88e5" in style or
                "strokeColor=#f44336" in style or "fillColor=#1e88e5" in style or
                "fillColor=#f44336" in style):
            features["buttons"] += 1

        is_input_like = (
            "rounded=1" in style and
            "fillColor=#ffffff" in style and
            "strokeColor=#bdbdbd" in style
        )
        if is_input_like:
            input_y_positions.add(y)

        if "tag_" in style or "fillColor=#e8f5e9" in style or "fillColor=#fff3e0" in style:
            features["tags"] += 1
        if "fontStyle=1" in style or "fontSize=16" in style:
            features["titles"] += 1
        if "fontSize=16" in style and re.fullmatch(r"[0-9]+", value.strip()):
            features["cards"] += 1
        if "timeline" in style or "处理记录" in value or "时间轴" in value:
            features["timeline"] += 1
        if (
            "树" in value
            or ("权限" in value and ("分组" in value or "节点" in value))
            or "菜单权限" in value
            or "数据权限" in value
        ):
            features["tree"] += 1

    data_rows = 0
    for y, count in row_y_positions.items():
        if count >= 3:
            data_rows += 1
    if data_rows:
        # 第一组通常是表头，其余为数据行
        features["rows"] = max(0, data_rows - 1)

    features["inputs"] = max(features["inputs"], len(input_y_positions))
    return features


def check_c13(doc: DrawioFile) -> RuleResult:
    worst = "PASS"
    details: list = []
    count = 0

    for sl in doc.swimlanes:
        sid = sl.get("id", "?")
        name = doc.swimlane_name(sl)
        children = doc.swimlane_children.get(sid, [])
        if _is_nav_group_swimlane(children):
            continue

        archetype = _classify_page_name(name)
        threshold = _annotation_x_threshold(doc.swimlane_width(sl))
        features = _count_features(children, threshold)

        if archetype == "confirm_dialog" and features["inputs"] >= 2:
            archetype = "modal_form"
        reasons = []

        if archetype == "login":
            if features["inputs"] < 2:
                reasons.append("登录字段不足")
            if features["buttons"] < 1:
                reasons.append("缺少登录按钮")
        elif archetype == "dashboard":
            if features["cards"] < 4:
                reasons.append("指标卡不足 4 个")
            if features["rows"] < 2 and features["buttons"] < 2:
                reasons.append("缺少待办区或快捷入口区")
        elif archetype == "detail_kv":
            if features["tags"] < 1:
                reasons.append("缺少状态区")
            if features["timeline"] < 1:
                reasons.append("缺少处理记录/时间轴")
            if features["buttons"] < 2:
                reasons.append("缺少详情操作区")
        elif archetype == "drawer_permission":
            if features["tree"] < 1 and features["rows"] < 2:
                reasons.append("缺少权限树/权限分组结构")
            if features["buttons"] < 2:
                reasons.append("缺少保存/取消操作")
        elif archetype == "dispatch_board":
            if "弹窗" in name:
                if features["inputs"] < 2:
                    reasons.append("发货/调度弹窗字段不足")
                if features["buttons"] < 2:
                    reasons.append("缺少确认/取消操作")
                dispatch_tokens = ("司机", "路线", "发货", "配送", "车牌")
                hit = 0
                for cell in children:
                    value = re.sub(r"<[^>]+>", "", cell.get("value", ""))
                    if any(token in value for token in dispatch_tokens):
                        hit += 1
                if hit < 2:
                    reasons.append("缺少发货/路线/司机等调度字段")
            else:
                if features["rows"] < 3:
                    reasons.append("调度列表数据不足")
                dispatch_tokens = ("司机", "路线", "发货", "配送", "车牌")
                hit = 0
                for cell in children:
                    value = re.sub(r"<[^>]+>", "", cell.get("value", ""))
                    if any(token in value for token in dispatch_tokens):
                        hit += 1
                if hit < 4:
                    reasons.append("缺少发货/路线/司机等调度字段")
        elif archetype == "confirm_dialog":
            if features["buttons"] < 2:
                reasons.append("缺少确认/取消按钮")
            text_like = 0
            for cell in children:
                value = re.sub(r"<[^>]+>", "", cell.get("value", ""))
                if len(value.strip()) >= 8:
                    text_like += 1
            if text_like < 2:
                reasons.append("缺少确认说明文案")
        elif archetype == "modal_form":
            min_inputs = 2 if "退款" in name or "审核" in name else 3 if any(token in name for token in ("配置", "拒绝")) else 4
            if features["inputs"] < min_inputs:
                reasons.append(f"表单字段少于 {min_inputs} 个")
            if features["buttons"] < 2:
                reasons.append("缺少底部确认/取消按钮")
        elif archetype == "tree_manage":
            hit = 0
            for cell in children:
                value = re.sub(r"<[^>]+>", "", cell.get("value", ""))
                if any(token in value for token in ("父级", "上级", "部门", "分类", "岗位")):
                    hit += 1
            if hit < 3:
                reasons.append("缺少层级/树结构字段")
        else:  # list_table
            min_rows = 1 if "记录" in name else 3
            if features["rows"] < min_rows:
                reasons.append("列表数据行不足")
            if features["buttons"] < 2:
                reasons.append("主操作或行操作不足")

        if reasons:
            worst = "FAIL"
            count += 1
            details.append(f"{name}: {', '.join(reasons)}")

    return RuleResult("C13", "页面类型降级", worst, count, details)


# ---- C14 标注信息密度 ---------------------------------------------------

def check_c14(doc: DrawioFile) -> RuleResult:
    worst = "PASS"
    details: list = []
    count = 0

    rule_tokens = (
        "规则", "校验", "排序", "分页", "导出", "状态", "空态", "加载态", "错误态",
        "数据范围", "前置", "仅", "必须", "范围", "可选值",
    )

    for sl in doc.swimlanes:
        sid = sl.get("id", "?")
        name = doc.swimlane_name(sl)
        children = doc.swimlane_children.get(sid, [])
        if _is_nav_group_swimlane(children):
            continue
        if "删除确认" in name:
            continue

        threshold = _annotation_x_threshold(doc.swimlane_width(sl))
        annotation_texts = []
        for cell in children:
            if _is_in_ui_area(cell, threshold):
                continue
            value = re.sub(r"<[^>]+>", "", cell.get("value", "")).strip()
            if value:
                annotation_texts.append(value)

        if not annotation_texts:
            continue

        combined = "\n".join(annotation_texts)
        has_summary = "页面：" in combined and "用途：" in combined
        has_jump = "跳转" in combined or "→" in combined
        rule_hit_count = sum(1 for token in rule_tokens if token in combined)

        if has_summary and has_jump and rule_hit_count < 2:
            worst = "WARN"
            count += 1
            details.append(f"{name}: 标注区缺少业务规则/状态边界，当前更像页面摘要")

    return RuleResult("C14", "标注信息密度", worst, count, details)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_checks(path: str, fix: bool = False) -> dict:
    """执行所有检查并返回结构化结果。"""
    # C7 先做 XML 合法性预检 — 解析失败直接报错
    try:
        doc = DrawioFile(path)
    except ET.ParseError as e:
        return {
            "file": os.path.basename(path),
            "stats": {"swimlanes": 0, "mxcells": 0},
            "results": [
                RuleResult("C7", "XML合法性", "FAIL", 1,
                           [f"XML 解析失败: {e}"]).to_dict()
            ],
            "summary": {"fail": 1, "warn": 0, "pass": 0},
        }

    results = [
        check_c7(doc),
        check_c5(doc, fix=fix),
        check_c1(doc),
        check_c2(doc),
        check_c3(doc),
        check_c4(doc),
        check_c6(doc),
        check_c8(doc),
        check_c9(doc),
        check_c10(doc),
        check_c11(doc),
        check_c12(doc),
        check_c13(doc),
        check_c14(doc),
    ]

    summary = {"fail": 0, "warn": 0, "pass": 0}
    for r in results:
        summary[r.status.lower()] += 1

    fixed_count = 0
    if fix:
        # C5 的 count 即为修复数
        for r in results:
            if r.rule == "C5" and r.count > 0:
                fixed_count = r.count

    return {
        "file": os.path.basename(path),
        "stats": {
            "swimlanes": len(doc.swimlanes),
            "mxcells": len(doc.all_cells),
        },
        "results": [r.to_dict() for r in results],
        "summary": summary,
        "_results_obj": results,
        "_fixed_count": fixed_count,
    }


def format_human(report: dict) -> str:
    """将报告格式化为人类可读文本。"""
    lines: list = []
    lines.append(f"\U0001f50d 验收报告：{report['file']}")
    lines.append("")

    stats = report["stats"]
    lines.append(f"\U0001f4ca 统计：{stats['swimlanes']} 个 swimlane，"
                 f"{stats['mxcells']} 个 mxCell")
    lines.append("")

    icon_map = {"PASS": "\u2705", "WARN": "\u26a0\ufe0f", "FAIL": "\u274c"}

    for r in report.get("_results_obj", []):
        icon = icon_map.get(r.status, "?")
        suffix = ""
        if r.count > 0:
            suffix = f" ({r.count} 个违规)"
        lines.append(f"{icon} {r.rule} {r.title}: {r.status}{suffix}")
        for d in r.details:
            lines.append(f"  - {d}")

    lines.append("")
    s = report["summary"]
    lines.append(f"总结：{s['fail']} FAIL / {s['warn']} WARN / {s['pass']} PASS")

    if report.get("_fixed_count", 0) > 0:
        lines.append(f"\n\U0001f527 已自动修复 {report['_fixed_count']} 处坐标对齐问题")

    return "\n".join(lines)


def format_json(report: dict) -> str:
    """将报告格式化为 JSON。"""
    out = {
        "file": report["file"],
        "stats": report["stats"],
        "results": report["results"],
        "summary": report["summary"],
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="draw.io 文件自动化验收检查")
    parser.add_argument("drawio_file", help="要检查的 .drawio 文件路径")
    parser.add_argument("--fix", action="store_true",
                        help="自动修复可修复的问题（坐标对齐）")
    parser.add_argument("--json", action="store_true", dest="json_output",
                        help="输出 JSON 格式报告")
    args = parser.parse_args()

    if not os.path.isfile(args.drawio_file):
        print(f"错误：文件不存在 — {args.drawio_file}", file=sys.stderr)
        sys.exit(1)

    report = run_checks(args.drawio_file, fix=args.fix)

    if args.json_output:
        print(format_json(report))
    else:
        print(format_human(report))

    # 如果有 FAIL 则 exit code 1
    if report["summary"]["fail"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
