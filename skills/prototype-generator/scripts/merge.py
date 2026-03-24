#!/usr/bin/env python3
"""
merge.py - 合并多个模块的 draw.io XML 片段为一个完整的 .drawio 文件。

用法:
    python3 merge.py <output_drawio> <product_name> <tmp_xml_1> [tmp_xml_2] ...
    python3 merge.py <output_drawio> <product_name> --glob <work_dir>/drawio_*_tmp.xml

选项:
    --keep-tmp            合并完成后保留临时 XML 文件（默认删除）
    --glob PATTERN        使用通配符匹配输入文件
    --split-swimlanes     将每个 swimlane 拆成独立 diagram
    --include-pages LIST  仅保留指定页面，多个页面用英文逗号分隔
    --no-nav              不生成导航 diagram
"""

import sys
import os
import re
import glob as glob_mod
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional
import xml.etree.ElementTree as ET


def normalize_diagram_name(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^(page[_-]?spec|spec|tmp)\s*[:：_-]?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", "", text)
    replacements = {
        "后台-通用与看板": "后台-工作台",
        "后台-人员与权限": "后台-组织权限",
        "后台-商品与内容": "后台-商品管理",
        "后台-会员与营销": "后台-会员运营",
        "后台-订单与履约": "后台-订单管理",
        "后台-物联与溯源基础数据": "后台-溯源基础数据",
        "小程序-账号与首页": "小程序-首页",
        "小程序-商品与交易": "小程序-商品交易",
        "小程序-订单与会员": "小程序-订单中心",
    }
    return replacements.get(text, text)


def normalize_page_name(module_name: str, page_name: str) -> str:
    text = str(page_name or "").strip()
    module = normalize_diagram_name(module_name)
    replacements = {
        "商品列表页（后台）": "商品管理-商品列表",
        "新增/编辑商品弹窗": "商品管理-添加编辑商品",
        "删除商品确认弹窗": "商品管理-删除商品确认",
        "分类管理页": "商品管理-分类管理",
        "新增/编辑分类弹窗": "商品管理-添加编辑分类",
        "轮播图管理页": "商品管理-轮播图管理",
        "公告管理页": "商品管理-公告管理",
        "评论管理页": "商品管理-评论管理",
        "新增/编辑通用弹窗": "商品管理-通用编辑弹窗",
        "删除确认弹窗": "商品管理-删除确认",
        "订单管理页（后台）": "订单管理-订单列表",
        "订单详情页（后台）": "订单管理-订单详情",
        "发货单列表页": "发货单管理",
        "发货单详情页": "发货单详情",
        "确认发货弹窗": "订单管理-确认发货",
        "退款处理弹窗": "订单管理-退款处理",
        "工作台Dashboard": "工作台-Dashboard",
        "工作台（后台）": "工作台-Dashboard",
        "后台首页": "工作台-Dashboard",
        "会员管理页": "会员管理",
        "鱼塘管理页": "鱼塘管理",
        "运输桶管理页": "运输桶管理",
        "员工管理页": "员工管理",
        "角色管理页": "权限管理-角色列表",
        "登录页（后台）": "登录页",
    }
    if text in replacements:
        return replacements[text]
    text = re.sub(r"页（后台）$", "", text)
    text = re.sub(r"（后台）$", "", text)
    text = re.sub(r"页$", "", text)
    if text.startswith(module):
        return text
    return f"{module}-{text}"


# ---------------------------------------------------------------------------
# ID 偏移工具
# ---------------------------------------------------------------------------

# 匹配带字符串前缀的 id，如 "S1_2" → prefix="S1_", num="2"
_ID_PATTERN = re.compile(r'^([A-Za-z_]+?)(\d+)$')


def _offset_id(raw_id: str, module_index: int) -> str:
    """对单个 id 施加偏移，避免跨模块冲突。

    纯数字 id（除 "0" 和 "1"）加偏移量 module_index * 10000。
    带前缀的 id（如 S1_2）改为 m{module_index}_{原id}。
    """
    if raw_id in ("0", "1"):
        return raw_id

    # 纯数字
    if raw_id.isdigit():
        return str(int(raw_id) + module_index * 10000)

    # 带前缀 → 加模块前缀
    return f"m{module_index}_{raw_id}"


def _build_id_map(cells: list, module_index: int) -> dict:
    """扫描所有 mxCell，构建 old_id → new_id 映射表。"""
    id_map = {"0": "0", "1": "1"}
    for cell in cells:
        old_id = cell.get("id")
        if old_id is not None and old_id not in id_map:
            id_map[old_id] = _offset_id(old_id, module_index)
    # 也收集非 mxCell 但有 id 的子元素（如 object / UserObject）
    return id_map


def _apply_id_map(root: ET.Element, id_map: dict):
    """将 id_map 应用到整棵子树的 id / parent / source / target 属性。"""
    for elem in root.iter():
        for attr in ("id", "parent", "source", "target"):
            val = elem.get(attr)
            if val is not None and val in id_map:
                elem.set(attr, id_map[val])


# ---------------------------------------------------------------------------
# 解析单个 tmp XML
# ---------------------------------------------------------------------------

def _parse_tmp_xml(path: str):
    """解析一个 render.py 产出的 tmp XML 文件，返回 (diagram_elem, module_name)。"""
    tree = ET.parse(path)
    root = tree.getroot()
    # 支持根元素直接是 <diagram> 或包裹在别的元素里
    if root.tag == "diagram":
        diagram = root
    else:
        diagram = root.find(".//diagram")
        if diagram is None:
            raise ValueError(f"在 {path} 中未找到 <diagram> 元素")
    module_name = normalize_diagram_name(diagram.get("name", os.path.splitext(os.path.basename(path))[0]))
    return diagram, module_name


def _extract_swimlane_names(diagram: ET.Element) -> list:
    """从 diagram 内部提取所有 swimlane 的名称（label / value 属性）。"""
    names = []
    for elem in diagram.iter():
        style = elem.get("style", "")
        if "swimlane" in style:
            # 尝试 value → label 属性
            name = elem.get("value") or elem.get("label") or ""
            # 去除 HTML 标签
            name = re.sub(r"<[^>]+>", "", name).strip()
            if name:
                names.append(name)
    return names


def _mxgeometry(elem: ET.Element) -> Optional[ET.Element]:
    return elem.find("mxGeometry")


def _geometry_tuple(elem: ET.Element) -> tuple[float, float, float, float]:
    geo = _mxgeometry(elem)
    if geo is None:
        return (0.0, 0.0, 0.0, 0.0)
    return tuple(float(geo.get(attr, "0")) for attr in ("x", "y", "width", "height"))


def _set_geometry(elem: ET.Element, x: float, y: float, width: float, height: float):
    geo = _mxgeometry(elem)
    if geo is None:
        return
    geo.set("x", str(int(round(x))))
    geo.set("y", str(int(round(y))))
    geo.set("width", str(int(round(width))))
    geo.set("height", str(int(round(height))))


def _page_matches(label: str, normalized_name: str, include_pages: Optional[set[str]]) -> bool:
    if not include_pages:
        return True
    return label in include_pages or normalized_name in include_pages


def _split_diagram_by_swimlane(diagram: ET.Element, module_name: str, include_pages: Optional[set[str]]):
    graph = diagram.find("./mxGraphModel")
    graph_root = diagram.find("./mxGraphModel/root")
    if graph is None or graph_root is None:
        return []

    cells = {cell.get("id"): cell for cell in graph_root.findall("mxCell") if cell.get("id")}
    split_diagrams = []

    for cell in cells.values():
        style = cell.get("style", "")
        if "swimlane" not in style:
            continue

        raw_label = re.sub(r"<[^>]+>", "", cell.get("value", "") or "").strip()
        diagram_name = normalize_page_name(module_name, raw_label)
        if not _page_matches(raw_label, diagram_name, include_pages):
            continue

        lane_x, lane_y, lane_w, lane_h = _geometry_tuple(cell)
        shift_x = lane_x - 20
        shift_y = lane_y - 20
        lane_id = cell.get("id")

        new_diagram = ET.Element("diagram", id=diagram.get("id", ""), name=diagram_name)
        new_graph = ET.SubElement(new_diagram, "mxGraphModel", graph.attrib)
        new_root = ET.SubElement(new_graph, "root")
        ET.SubElement(new_root, "mxCell", id="0")
        ET.SubElement(new_root, "mxCell", id="1", parent="0")

        lane_clone = deepcopy(cell)
        _set_geometry(lane_clone, 20, 20, lane_w, lane_h)
        new_root.append(lane_clone)

        for child in cells.values():
            if child.get("parent") != lane_id:
                continue
            child_clone = deepcopy(child)
            child_x, child_y, child_w, child_h = _geometry_tuple(child_clone)
            _set_geometry(child_clone, child_x - shift_x, child_y - shift_y, child_w, child_h)
            new_root.append(child_clone)

        new_graph.set("pageWidth", str(int(round(lane_w + 120))))
        new_graph.set("pageHeight", str(int(round(lane_h + 120))))
        split_diagrams.append((diagram_name, raw_label, new_diagram))

    return split_diagrams


# ---------------------------------------------------------------------------
# 导航图生成
# ---------------------------------------------------------------------------

_NAV_NODE_W = 160
_NAV_NODE_H = 48
_NAV_NODE_GAP = 24
_NAV_GROUP_GAP = 60
_NAV_NODE_STYLE = "rounded=1;whiteSpace=wrap;html=1;fillColor=#e3f2fd;strokeColor=#1e88e5;fontSize=12;"
_NAV_GROUP_STYLE = "swimlane;startSize=30;fillColor=#f5f5f5;strokeColor=#bdbdbd;fontStyle=1;fontSize=13;"


def _snap8_int(value: int) -> int:
    return int(round(value / 8.0) * 8)


def _build_nav_diagram(modules: list) -> ET.Element:
    """生成导航图 diagram 元素。

    modules: [(module_name, [swimlane_name, ...]), ...]
    """
    diagram = ET.Element("diagram", id="nav", name="导航-页面跳转地图")
    graph = ET.SubElement(diagram, "mxGraphModel",
                          dx="1200", dy="800", grid="1", gridSize="10",
                          guides="1", tooltips="1", connect="1", arrows="1",
                          fold="1", page="1", pageScale="1",
                          pageWidth="1600", pageHeight="900", math="0", shadow="0")
    root_cell = ET.SubElement(graph, "root")
    ET.SubElement(root_cell, "mxCell", id="0")
    ET.SubElement(root_cell, "mxCell", id="1", parent="0")

    cell_id = 100  # 导航图 id 从 100 起
    x_offset = 16

    for mod_name, swimlane_names in modules:
        pages = swimlane_names if swimlane_names else [mod_name]
        group_h = _snap8_int(30 + len(pages) * (_NAV_NODE_H + _NAV_NODE_GAP) + _NAV_NODE_GAP)
        group_w = _snap8_int(_NAV_NODE_W + 40)

        # group 容器
        group_id = str(cell_id)
        cell_id += 1
        group_cell = ET.SubElement(root_cell, "mxCell",
                                   id=group_id, value=normalize_diagram_name(mod_name),
                                   style=_NAV_GROUP_STYLE,
                                   vertex="1", parent="1")
        ET.SubElement(group_cell, "mxGeometry",
                      x=str(x_offset), y="40",
                      width=str(group_w), height=str(group_h),
                      **{"as": "geometry"})

        # 页面节点
        node_y = _snap8_int(30 + _NAV_NODE_GAP)
        for page_name in pages:
            node_id = str(cell_id)
            cell_id += 1
            node_cell = ET.SubElement(root_cell, "mxCell",
                                      id=node_id, value=page_name,
                                      style=_NAV_NODE_STYLE,
                                      vertex="1", parent=group_id)
            ET.SubElement(node_cell, "mxGeometry",
                          x="24", y=str(node_y),
                          width=str(_NAV_NODE_W), height=str(_NAV_NODE_H),
                          **{"as": "geometry"})
            node_y = _snap8_int(node_y + _NAV_NODE_H + _NAV_NODE_GAP)

        x_offset = _snap8_int(x_offset + group_w + _NAV_GROUP_GAP)

    return diagram


# ---------------------------------------------------------------------------
# 主合并流程
# ---------------------------------------------------------------------------

def _indent_xml(elem: ET.Element, level: int = 0):
    """为 ElementTree 元素添加一致缩进（递归）。"""
    indent = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for i, child in enumerate(elem):
            _indent_xml(child, level + 1)
            if i < len(elem) - 1:
                if not child.tail or not child.tail.strip():
                    child.tail = indent + "  "
        # last child tail
        if not child.tail or not child.tail.strip():
            child.tail = indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent


def merge(
    output_path: str,
    product_name: str,
    tmp_files: list,
    keep_tmp: bool = False,
    split_swimlanes: bool = False,
    include_pages: Optional[set[str]] = None,
    add_nav: bool = True,
):
    """执行合并。

    Args:
        output_path: 输出 .drawio 文件路径
        product_name: 产品名称（写入 mxfile 注释）
        tmp_files: 排序后的 tmp XML 文件路径列表
        keep_tmp: 是否保留临时文件
    """
    if not tmp_files:
        print("错误：未提供任何 tmp XML 文件", file=sys.stderr)
        sys.exit(1)

    # 按文件名排序
    tmp_files = sorted(tmp_files, key=lambda p: os.path.basename(p))

    modules_info = []   # [(name, [swimlane_names]), ...]
    diagrams = []       # 偏移后的 diagram 元素列表
    total_cells = 0

    for idx, fpath in enumerate(tmp_files, start=1):
        if not os.path.isfile(fpath):
            print(f"警告：文件不存在，跳过 → {fpath}", file=sys.stderr)
            continue

        diagram, mod_name = _parse_tmp_xml(fpath)
        if split_swimlanes:
            split_items = _split_diagram_by_swimlane(diagram, mod_name, include_pages)
            kept_names = [name for name, _, _ in split_items]
            if kept_names:
                modules_info.append((mod_name, kept_names))
            for page_index, (diagram_name, _, split_diagram) in enumerate(split_items, start=1):
                split_diagram.set("id", f"module{idx}_page{page_index}")
                split_diagram.set("name", diagram_name)
                total_cells += len([e for e in split_diagram.iter() if e.tag == "mxCell"])
                diagrams.append(split_diagram)
            continue

        swimlane_names = _extract_swimlane_names(diagram)
        if include_pages:
            filtered_names = []
            for raw_name in swimlane_names:
                page_name = normalize_page_name(mod_name, raw_name)
                if _page_matches(raw_name, page_name, include_pages):
                    filtered_names.append(raw_name)
            if not filtered_names:
                continue
            swimlane_names = filtered_names
        modules_info.append((mod_name, swimlane_names))

        # 收集所有带 id 的元素，构建映射
        all_id_elems = [e for e in diagram.iter() if e.get("id") is not None]
        id_map = {}
        for e in all_id_elems:
            old = e.get("id")
            if old not in id_map:
                id_map[old] = _offset_id(old, idx)
        id_map["0"] = "0"
        id_map["1"] = "1"

        _apply_id_map(diagram, id_map)

        total_cells += len([e for e in diagram.iter() if e.tag == "mxCell"])

        diagram.set("id", f"module{idx}")
        diagram.set("name", normalize_diagram_name(mod_name))
        diagrams.append(diagram)

    if not diagrams:
        print("错误：没有成功解析任何模块", file=sys.stderr)
        sys.exit(1)

    # 构建导航图
    nav_diagram = None
    if add_nav:
        nav_diagram = _build_nav_diagram(modules_info)
        nav_cells = len([e for e in nav_diagram.iter() if e.tag == "mxCell"])
        total_cells += nav_cells

    # 构建 mxfile
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    mxfile = ET.Element("mxfile",
                        host="app.diagrams.net",
                        modified=now_iso,
                        agent="Claude",
                        version="24.0.0",
                        type="device")

    if nav_diagram is not None:
        mxfile.append(nav_diagram)
    for d in diagrams:
        mxfile.append(d)

    # 缩进
    _indent_xml(mxfile)

    # 序列化
    xml_str = ET.tostring(mxfile, encoding="unicode", xml_declaration=False)

    # XML 合法性基本检查
    try:
        ET.fromstring(xml_str)
    except ET.ParseError as e:
        print(f"警告：生成的 XML 可能不合法 → {e}", file=sys.stderr)

    # 写入
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)
        f.write("\n")

    # 清理临时文件
    if not keep_tmp:
        for fpath in tmp_files:
            if os.path.isfile(fpath):
                os.remove(fpath)

    n_modules = len(diagrams)
    print(f"合并完成：{n_modules} 个模块，{total_cells} 个 mxCell，已写入 {output_path}")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    if len(args) < 3:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(1)

    output_path = args[0]
    product_name = args[1]
    keep_tmp = "--keep-tmp" in args
    split_swimlanes = "--split-swimlanes" in args
    add_nav = "--no-nav" not in args

    # 移除 flag 参数
    consumed = {"--keep-tmp", "--split-swimlanes", "--no-nav"}
    rest = [a for a in args[2:] if a not in consumed]
    include_pages = None

    if "--include-pages" in rest:
        include_idx = rest.index("--include-pages")
        if include_idx + 1 >= len(rest):
            print("错误：--include-pages 后需要提供页面列表", file=sys.stderr)
            sys.exit(1)
        include_pages = {
            item.strip()
            for item in rest[include_idx + 1].split(",")
            if item.strip()
        }
        del rest[include_idx:include_idx + 2]

    # 检查 --glob 模式
    if "--glob" in rest:
        glob_idx = rest.index("--glob")
        if glob_idx + 1 >= len(rest):
            print("错误：--glob 后需要提供通配符模式", file=sys.stderr)
            sys.exit(1)
        pattern = rest[glob_idx + 1]
        tmp_files = glob_mod.glob(pattern)
        if not tmp_files:
            print(f"错误：未匹配到任何文件 → {pattern}", file=sys.stderr)
            sys.exit(1)
    else:
        tmp_files = rest

    merge(
        output_path,
        product_name,
        tmp_files,
        keep_tmp=keep_tmp,
        split_swimlanes=split_swimlanes,
        include_pages=include_pages,
        add_nav=add_nav,
    )


if __name__ == "__main__":
    main()
