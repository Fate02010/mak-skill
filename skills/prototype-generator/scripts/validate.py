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

        btn_colors = set()
        font_sizes = set()

        for c in children:
            if not _is_in_ui_area(c, threshold):
                continue
            style = c.get("style", "")

            # 按钮检测：style 含 "btn" 或者有非白非灰 fillColor + rounded
            is_btn = "btn" in style.lower()
            if not is_btn:
                has_fill = re.search(r"fillColor=([^;]+)", style)
                if has_fill and has_fill.group(1) not in _plain_colors and "rounded" in style:
                    is_btn = True
            if is_btn:
                m = re.search(r"fillColor=([^;]+)", style)
                color = m.group(1) if m else "none"
                btn_colors.add(color)

            # 字号检测
            m = re.search(r"fontSize=(\d+)", style)
            if m:
                font_sizes.add(m.group(1))

        has_btn_variety = len(btn_colors) >= 2
        has_font_variety = len(font_sizes) >= 2

        if not (has_btn_variety and has_font_variety):
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

        # 检查是否为含数据行的页面
        row_count = 0
        has_data_pattern = False
        for c in children:
            style = c.get("style", "")
            if "table_row" in style or "card" in style:
                has_data_pattern = True
                row_count += 1

        if has_data_pattern and row_count < 3:
            if worst != "FAIL":
                worst = "WARN"
            warn_count += 1
            details.append(f"{name}: 仅 {row_count} 条数据行 (建议 >= 3)")

    return RuleResult("C8", "数据行充分性", worst, warn_count, details)


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
