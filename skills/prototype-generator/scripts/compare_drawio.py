#!/usr/bin/env python3
"""
compare_drawio.py - 比较两个 draw.io 文件的结构差异，输出量化 diff_score。

用法:
    python3 compare_drawio.py <baseline.drawio> <candidate.drawio> [--json]

score 越低越接近，目标建议 <= 5。

说明：
    兼容两种常见结构：
    1. 一个 diagram 内包含多个 swimlane
    2. 一个页面就是一个 diagram（无 swimlane）
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET


def normalize_name(name: str) -> str:
    text = re.sub(r"<[^>]+>", "", name or "").strip().lower()
    text = text.replace("（后台）", "")
    text = text.replace("(后台)", "")
    text = text.replace("页（后台）", "")
    text = text.replace("页(后台)", "")
    text = text.replace("页", "")
    text = text.replace("弹窗", "")
    text = text.replace("新增/编辑", "添加编辑")
    text = text.replace("dashboard", "工作台")
    text = re.sub(r"\s+", "", text)
    return text


def category_for_style(style: str) -> str:
    value = (style or "").lower()
    if "swimlane" in value:
        return "swimlane"
    if "edge" in value:
        return "edge"
    if "bottom_bar" in value:
        return "bottom_bar"
    if "modal" in value:
        return "modal"
    if "nav" in value:
        return "nav"
    if "pagination" in value:
        return "pagination"
    if "table_header" in value:
        return "table_header"
    if "table_row" in value:
        return "table_row"
    if "tag_" in value:
        return "tag"
    if "btn" in value or "strokecolor=#1e88e5" in value or "strokecolor=#f44336" in value:
        return "button"
    if "input" in value or "select" in value or "textarea" in value:
        return "form_control"
    if "card" in value:
        return "card"
    if "annotation" in value:
        return "annotation"
    if "text;" in value:
        return "text"
    return "other"


def geometry(elem: ET.Element) -> tuple[float, float, float, float]:
    geo = elem.find("mxGeometry")
    if geo is None:
        return (0.0, 0.0, 0.0, 0.0)
    return tuple(float(geo.get(attr, "0")) for attr in ("x", "y", "width", "height"))


def summarize_cells(cells: list[ET.Element]) -> dict:
    relevant = [cell for cell in cells if cell.get("id") not in {"0", "1"}]
    categories = {}
    min_x = min_y = math.inf
    max_x = max_y = 0.0

    for cell in relevant:
        cat = category_for_style(cell.get("style", ""))
        categories[cat] = categories.get(cat, 0) + 1
        x, y, w, h = geometry(cell)
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x + w)
        max_y = max(max_y, y + h)

    if not relevant:
        bbox = (0.0, 0.0, 0.0, 0.0)
    else:
        bbox = (min_x, min_y, max(0.0, max_x - min_x), max(0.0, max_y - min_y))

    return {
        "cell_count": len(relevant),
        "categories": categories,
        "geometry": bbox,
    }


def parse_drawio(path: str) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()
    diagrams = []
    for diagram in root.findall(".//diagram"):
        graph_root = diagram.find("./mxGraphModel/root")
        if graph_root is None:
            continue
        cells = {cell.get("id"): cell for cell in graph_root.findall("mxCell") if cell.get("id")}
        cell_list = [cell for cell in graph_root.findall("mxCell") if cell.get("id")]
        swimlanes = []
        for cell in cells.values():
            style = cell.get("style", "")
            if "swimlane" in style:
                swimlane_id = cell.get("id")
                children = [c for c in cells.values() if c.get("parent") == swimlane_id]
                categories = {}
                for child in children:
                    cat = category_for_style(child.get("style", ""))
                    categories[cat] = categories.get(cat, 0) + 1
                swimlanes.append(
                    {
                        "name": normalize_name(cell.get("value", "")),
                        "raw_name": cell.get("value", ""),
                        "cell_count": len(children),
                        "categories": categories,
                        "geometry": geometry(cell),
                    }
                )
        diagrams.append(
            {
                "name": normalize_name(diagram.get("name", "")),
                "raw_name": diagram.get("name", ""),
                "swimlanes": swimlanes,
                "summary": summarize_cells(cell_list),
            }
        )
    return {"diagrams": diagrams}


def category_distance(base: dict[str, int], cand: dict[str, int]) -> float:
    keys = set(base) | set(cand)
    if not keys:
        return 0.0
    numerator = 0.0
    denominator = 0.0
    for key in keys:
        b = base.get(key, 0)
        c = cand.get(key, 0)
        numerator += abs(b - c)
        denominator += max(b, c)
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compare(baseline: dict, candidate: dict) -> dict:
    base_diagrams = {d["name"]: d for d in baseline["diagrams"]}
    cand_diagrams = {d["name"]: d for d in candidate["diagrams"]}
    diagram_keys = sorted(set(base_diagrams) | set(cand_diagrams))

    details = []
    total_score = 0.0

    for key in diagram_keys:
        base = base_diagrams.get(key)
        cand = cand_diagrams.get(key)
        if base is None or cand is None:
            total_score += 20.0
            details.append({"diagram": key, "score": 20.0, "reason": "diagram_missing"})
            continue

        base_sw = {s["name"]: s for s in base["swimlanes"]}
        cand_sw = {s["name"]: s for s in cand["swimlanes"]}
        use_swimlane_mode = bool(base_sw) and bool(cand_sw)

        diagram_score = 0.0
        missing_pages = 0
        if use_swimlane_mode:
            swimlane_keys = sorted(set(base_sw) | set(cand_sw))
            for swimlane_key in swimlane_keys:
                b = base_sw.get(swimlane_key)
                c = cand_sw.get(swimlane_key)
                if b is None or c is None:
                    diagram_score += 8.0
                    missing_pages += 1
                    continue

                base_count = max(b["cell_count"], 1)
                cell_gap = abs(b["cell_count"] - c["cell_count"]) / base_count
                category_gap = category_distance(b["categories"], c["categories"])

                bx, by, bw, bh = b["geometry"]
                cx, cy, cw, ch = c["geometry"]
                denom = max(bw + bh, 1.0)
                geo_gap = (abs(bx - cx) + abs(by - cy) + abs(bw - cw) + abs(bh - ch)) / denom

                diagram_score += min(8.0, cell_gap * 4.0 + category_gap * 6.0 + geo_gap * 2.0)

            page_denominator = max(len(swimlane_keys), 1)
            diagram_score /= page_denominator
            diagram_score += abs(len(base["swimlanes"]) - len(cand["swimlanes"])) / page_denominator * 5.0
        else:
            b = base["summary"]
            c = cand["summary"]
            base_count = max(b["cell_count"], 1)
            cell_gap = abs(b["cell_count"] - c["cell_count"]) / base_count
            category_gap = category_distance(b["categories"], c["categories"])

            bx, by, bw, bh = b["geometry"]
            cx, cy, cw, ch = c["geometry"]
            denom = max(bw + bh, 1.0)
            geo_gap = (abs(bx - cx) + abs(by - cy) + abs(bw - cw) + abs(bh - ch)) / denom
            diagram_score = min(8.0, cell_gap * 4.0 + category_gap * 6.0 + geo_gap * 2.0)
            swimlane_keys = []

        details.append(
            {
                "diagram": key,
                "score": round(diagram_score, 2),
                "baseline_pages": len(base["swimlanes"]),
                "candidate_pages": len(cand["swimlanes"]),
                "missing_pages": missing_pages,
                "mode": "swimlane" if use_swimlane_mode else "diagram",
            }
        )
        total_score += diagram_score

    total_score += abs(len(base_diagrams) - len(cand_diagrams)) * 3.0
    total_score = round(total_score / max(len(diagram_keys), 1), 2)
    return {
        "diff_score": total_score,
        "target_pass": total_score <= 5.0,
        "details": details,
    }


def main():
    parser = argparse.ArgumentParser(description="比较两个 draw.io 文件的结构差异")
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    result = compare(parse_drawio(args.baseline), parse_drawio(args.candidate))
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"diff_score: {result['diff_score']}")
        print(f"target_pass: {'YES' if result['target_pass'] else 'NO'}")
        for detail in result["details"]:
            print(
                f"- {detail['diagram']}: score={detail['score']} "
                f"(baseline_pages={detail.get('baseline_pages', 0)}, "
                f"candidate_pages={detail.get('candidate_pages', 0)}, "
                f"missing_pages={detail.get('missing_pages', 0)})"
            )

    if not result["target_pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
