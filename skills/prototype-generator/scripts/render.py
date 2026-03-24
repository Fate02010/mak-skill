#!/usr/bin/env python3
"""
render.py — 读取 page_spec markdown + 样式字典 markdown，生成 draw.io XML 片段（单个 <diagram>）。

用法:
    python3 render.py <styles_md> <page_spec_md> <output_xml>

输出的是一个 <diagram> 元素（不含 <mxfile> 包裹，由 merge.py 负责合并）。
仅依赖 Python 标准库。
"""

import re
import sys
import os


HEADING_RE = re.compile(r'^(#{2,6})\s+(.+?)\s*$')


# ---------------------------------------------------------------------------
# 1. XML 特殊字符转义
# ---------------------------------------------------------------------------

def xml_escape(text: str) -> str:
    """转义 XML 特殊字符，但不重复转义已有的实体引用。"""
    if not text:
        return ""
    # 先把已有的实体引用临时替换掉，避免重复转义
    # 匹配 &amp; &lt; &gt; &quot; &apos; &#数字; &#x十六进制;
    placeholders = {}
    counter = [0]

    def _protect(m):
        key = f"\x00ENTITY{counter[0]}\x00"
        placeholders[key] = m.group(0)
        counter[0] += 1
        return key

    protected = re.sub(r'&(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);', _protect, text)

    # 转义裸 &
    protected = protected.replace('&', '&amp;')
    protected = protected.replace('<', '&lt;')
    protected = protected.replace('>', '&gt;')
    protected = protected.replace('"', '&quot;')

    # 还原之前保护的实体
    for key, val in placeholders.items():
        protected = protected.replace(key, val)

    # 处理换行：\n 或字面 &#xa; 统一为 &#xa;
    protected = protected.replace('\\n', '&#xa;')

    return protected


# ---------------------------------------------------------------------------
# 2. 坐标校验与修正（8 的倍数）
# ---------------------------------------------------------------------------

def snap8(value: int, field_name: str, context: str) -> int:
    """将数值对齐到最近的 8 的倍数。height=1（分隔线）例外。"""
    if value == 1 and field_name == "height":
        return value
    if value % 8 != 0:
        snapped = round(value / 8) * 8
        if snapped == 0 and value > 0:
            snapped = 8
        print(f"SNAP: {context} {field_name}={value} → {snapped}", file=sys.stderr)
        return snapped
    return value


# ---------------------------------------------------------------------------
# 3. Markdown 表格解析
# ---------------------------------------------------------------------------

def parse_md_table(lines: list[str]) -> list[dict[str, str]]:
    """解析 markdown 表格，返回 list of dict。跳过分隔行（---）。"""
    if not lines:
        return []

    # 找到表头行
    header_line = lines[0]
    headers = [h.strip().strip('`') for h in header_line.strip().strip('|').split('|')]

    rows = []
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        # 跳过分隔行
        if re.match(r'^\|[\s\-:|]+\|$', stripped):
            continue
        cells = [c.strip().strip('`') for c in stripped.strip('|').split('|')]
        # 补齐或截断到 header 长度
        while len(cells) < len(headers):
            cells.append('')
        row = {headers[i]: cells[i] for i in range(len(headers))}
        rows.append(row)

    return rows


def extract_section_table(content: str, section_heading: str) -> list[dict[str, str]]:
    """提取指定标题下的第一个 markdown 表格，兼容 ## / ###。"""
    lines = content.splitlines()
    in_section = False
    section_level = None
    table_lines = []
    collecting = False

    for line in lines:
        heading_match = HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            if title == section_heading:
                in_section = True
                section_level = level
                continue
            if in_section and section_level is not None and level <= section_level:
                break

        if not in_section:
            continue

        stripped = line.strip()
        if stripped.startswith('|') and not collecting:
            collecting = True
        if collecting:
            if stripped.startswith('|'):
                table_lines.append(stripped)
            elif stripped == '':
                continue
            else:
                break

    return parse_md_table(table_lines)


def _normalized_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_")


def normalize_rows(rows: list[dict[str, str]], aliases: dict[str, str]) -> list[dict[str, str]]:
    """按别名归一化 markdown 表头。"""
    normalized_rows = []
    for row in rows:
        normalized = {}
        for key, value in row.items():
            mapped_key = aliases.get(_normalized_key(key), _normalized_key(key))
            normalized[mapped_key] = value.strip() if isinstance(value, str) else value
        normalized_rows.append(normalized)
    return normalized_rows


# ---------------------------------------------------------------------------
# 4. 解析样式字典
# ---------------------------------------------------------------------------

def parse_styles(styles_content: str) -> dict[str, str]:
    """解析样式字典 markdown，返回 {style_key: style_string}。"""
    styles = {}
    lines = styles_content.splitlines()
    in_table = False
    header_found = False

    # 找到 ## 样式字典 下的表格
    in_section = False
    for line in lines:
        if re.match(r'^##\s+样式字典', line):
            in_section = True
            continue
        if in_section and re.match(r'^##\s+', line):
            break
        if not in_section:
            continue

        stripped = line.strip()
        if not stripped.startswith('|'):
            if in_table:
                break
            continue

        if not header_found:
            header_found = True
            continue  # skip header

        # 跳过分隔行
        if re.match(r'^\|[\s\-:|]+\|$', stripped):
            continue

        in_table = True
        cells = [c.strip().strip('`') for c in stripped.strip('|').split('|')]
        if len(cells) >= 2:
            key = cells[0].strip()
            style = cells[1].strip()
            if key:
                styles[key] = style

    return styles


# ---------------------------------------------------------------------------
# 5. 解析 page_spec
# ---------------------------------------------------------------------------

def parse_page_spec(spec_content: str):
    """解析 page_spec markdown，返回 (module_name, swimlanes, elements)。"""
    # 提取模块名：从第一个 # 标题中获取
    module_name = "page"
    for line in spec_content.splitlines():
        m = re.match(r'^#\s+(.+)', line)
        if m:
            module_name = m.group(1).strip()
            break

    swimlanes = normalize_rows(
        extract_section_table(spec_content, "swimlane 布局"),
        {
            "swimlane_id": "swimlane_id",
            "id": "swimlane_id",
            "label": "swimlane_label",
            "swimlane_label": "swimlane_label",
            "name": "swimlane_label",
            "type": "type",
            "x": "x",
            "y": "y",
            "width": "width",
            "height": "height",
            "style_key": "style_key",
            "style": "style_key",
        },
    )
    elements = normalize_rows(
        extract_section_table(spec_content, "元素列表"),
        {
            "id": "id",
            "parent_swimlane": "parent_swimlane",
            "parent": "parent_swimlane",
            "component_type": "component_type",
            "value": "value",
            "x": "x",
            "y": "y",
            "width": "width",
            "w": "width",
            "height": "height",
            "h": "height",
            "style_key": "style_key",
            "style": "style_key",
            "tooltip": "tooltip",
        },
    )

    return module_name, swimlanes, elements


# ---------------------------------------------------------------------------
# 6. 从文件名提取模块英文名（用作 diagram id）
# ---------------------------------------------------------------------------

def extract_module_id(filepath: str) -> str:
    """从 page_spec 文件名中提取模块英文名作为 diagram id。"""
    basename = os.path.basename(filepath)
    name = os.path.splitext(basename)[0]
    # 移除常见前缀如 page_spec_ 或 page-spec-
    name = re.sub(r'^page[_-]?spec[_-]?', '', name, flags=re.IGNORECASE)
    if not name:
        name = "page"
    # 清理为合法 XML id（字母数字下划线）
    name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', name)
    return name


# ---------------------------------------------------------------------------
# 7. style_key 查找
# ---------------------------------------------------------------------------

def resolve_style(style_key: str, styles: dict[str, str]) -> str:
    """精确匹配样式字典，未找到则用 text_default 兜底。"""
    if style_key in styles:
        return styles[style_key]
    print(f"WARNING: style_key '{style_key}' not found, using text_default", file=sys.stderr)
    return styles.get('text_default', '')


# ---------------------------------------------------------------------------
# 8. 解析整数，容错处理
# ---------------------------------------------------------------------------

def safe_int(val: str, default: int = 0) -> int:
    """安全解析整数。"""
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def infer_swimlane_style(sw: dict[str, str]) -> str:
    style_key = sw.get("style_key", "").strip()
    if style_key:
        return style_key

    swimlane_type = sw.get("type", "").strip().lower()
    if swimlane_type == "modal":
        return "swimlane_modal"
    return "swimlane"


def validate_page_spec(module_name: str, swimlanes: list[dict], elements: list[dict]):
    """对结构化 page_spec 做基础校验，缺失关键字段时直接报错。"""
    errors = []

    if not swimlanes:
        errors.append("未解析到 `## swimlane 布局` 表格")
    if not elements:
        errors.append("未解析到 `## 元素列表` 表格")

    for index, sw in enumerate(swimlanes, start=1):
        swimlane_id = sw.get("swimlane_id", "").strip()
        swimlane_label = sw.get("swimlane_label", "").strip()
        if not swimlane_id:
            errors.append(f"swimlane[{index}] 缺少 swimlane_id")
        if not swimlane_label:
            errors.append(f"swimlane[{index}] 缺少 swimlane_label/label")
        for field in ("x", "y", "width", "height"):
            if not str(sw.get(field, "")).strip():
                errors.append(f"swimlane[{index}] 缺少 {field}")

    swimlane_ids = {sw.get("swimlane_id", "").strip() for sw in swimlanes if sw.get("swimlane_id", "").strip()}
    for index, el in enumerate(elements, start=1):
        element_id = el.get("id", "").strip()
        parent = el.get("parent_swimlane", "").strip()
        style_key = el.get("style_key", "").strip()
        if not element_id:
            errors.append(f"element[{index}] 缺少 id")
        if not parent:
            errors.append(f"element[{index}] 缺少 parent_swimlane")
        elif parent not in swimlane_ids:
            errors.append(f"element[{index}] parent_swimlane={parent} 未在 swimlane 布局中定义")
        if not style_key:
            errors.append(f"element[{index}] 缺少 style_key")
        for field in ("x", "y", "width", "height"):
            if not str(el.get(field, "")).strip():
                errors.append(f"element[{index}] 缺少 {field}")

    if errors:
        error_text = "\n".join(f"- {item}" for item in errors)
        raise ValueError(f"{module_name} 的 page_spec 不合法：\n{error_text}")


# ---------------------------------------------------------------------------
# 9. 生成 XML
# ---------------------------------------------------------------------------

def generate_xml(module_id: str, module_name: str, swimlanes: list[dict],
                 elements: list[dict], styles: dict[str, str]) -> str:
    """生成 <diagram> XML 片段。"""
    indent = "  "
    lines = []

    # 计算 pageWidth / pageHeight
    max_x = 0
    max_y = 0
    for sw in swimlanes:
        sx = safe_int(sw.get('x', '0'))
        sy = safe_int(sw.get('y', '0'))
        sw_w = safe_int(sw.get('width', '0'))
        sw_h = safe_int(sw.get('height', '0'))
        max_x = max(max_x, sx + sw_w)
        max_y = max(max_y, sy + sw_h)

    page_width = max_x + 100
    page_height = max_y + 100

    # 最小尺寸保底
    if page_width < 200:
        page_width = 1280
    if page_height < 200:
        page_height = 900

    lines.append(f'<diagram id="{xml_escape(module_id)}" name="{xml_escape(module_name)}">')
    lines.append(f'{indent}<mxGraphModel dx="1280" dy="900" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{page_width}" pageHeight="{page_height}" math="0" shadow="0">')
    lines.append(f'{indent}{indent}<root>')
    lines.append(f'{indent}{indent}{indent}<mxCell id="0" />')
    lines.append(f'{indent}{indent}{indent}<mxCell id="1" parent="0" />')

    # Swimlanes
    for sw in swimlanes:
        sw_id = sw.get('swimlane_id', '').strip()
        sw_label = sw.get('swimlane_label', '').strip()
        sw_style_key = infer_swimlane_style(sw)
        sx = snap8(safe_int(sw.get('x', '0')), 'x', f'swimlane {sw_id}')
        sy = snap8(safe_int(sw.get('y', '0')), 'y', f'swimlane {sw_id}')
        sw_w = snap8(safe_int(sw.get('width', '0')), 'width', f'swimlane {sw_id}')
        sw_h = snap8(safe_int(sw.get('height', '0')), 'height', f'swimlane {sw_id}')
        style = resolve_style(sw_style_key, styles)

        lines.append(
            f'{indent}{indent}{indent}<mxCell id="{xml_escape(sw_id)}" '
            f'value="{xml_escape(sw_label)}" '
            f'style="{xml_escape(style)}" '
            f'vertex="1" parent="1">'
        )
        lines.append(
            f'{indent}{indent}{indent}{indent}<mxGeometry x="{sx}" y="{sy}" '
            f'width="{sw_w}" height="{sw_h}" as="geometry" />'
        )
        lines.append(f'{indent}{indent}{indent}</mxCell>')

    # Elements
    for el in elements:
        el_id = el.get('id', '').strip()
        parent = el.get('parent_swimlane', '').strip()
        value = el.get('value', '').strip()
        style_key = el.get('style_key', '').strip()
        tooltip = el.get('tooltip', '').strip()
        ex = snap8(safe_int(el.get('x', '0')), 'x', f'element {parent}_{el_id}')
        ey = snap8(safe_int(el.get('y', '0')), 'y', f'element {parent}_{el_id}')
        ew = snap8(safe_int(el.get('width', '0')), 'width', f'element {parent}_{el_id}')
        eh = snap8(safe_int(el.get('height', '0')), 'height', f'element {parent}_{el_id}')
        style = resolve_style(style_key, styles)

        cell_id = f"{parent}_{el_id}" if parent else el_id
        parent_ref = parent if parent else "1"

        # 构建属性
        attrs = (
            f'id="{xml_escape(cell_id)}" '
            f'value="{xml_escape(value)}" '
            f'style="{xml_escape(style)}" '
            f'vertex="1" '
            f'parent="{xml_escape(parent_ref)}"'
        )
        if tooltip:
            attrs += f' tooltip="{xml_escape(tooltip)}"'

        lines.append(f'{indent}{indent}{indent}<mxCell {attrs}>')
        lines.append(
            f'{indent}{indent}{indent}{indent}<mxGeometry x="{ex}" y="{ey}" '
            f'width="{ew}" height="{eh}" as="geometry" />'
        )
        lines.append(f'{indent}{indent}{indent}</mxCell>')

    lines.append(f'{indent}{indent}</root>')
    lines.append(f'{indent}</mxGraphModel>')
    lines.append('</diagram>')

    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 4:
        print(f"用法: python3 {sys.argv[0]} <styles_md> <page_spec_md> <output_xml>", file=sys.stderr)
        sys.exit(1)

    styles_path = sys.argv[1]
    spec_path = sys.argv[2]
    output_path = sys.argv[3]

    # 读取文件
    with open(styles_path, 'r', encoding='utf-8') as f:
        styles_content = f.read()
    with open(spec_path, 'r', encoding='utf-8') as f:
        spec_content = f.read()

    # 解析
    styles = parse_styles(styles_content)
    if not styles:
        print("ERROR: 未能从样式字典中解析到任何样式", file=sys.stderr)
        sys.exit(1)

    module_name, swimlanes, elements = parse_page_spec(spec_content)
    module_id = extract_module_id(spec_path)

    validate_page_spec(module_name, swimlanes, elements)

    # 生成 XML
    xml = generate_xml(module_id, module_name, swimlanes, elements, styles)

    # 写入输出
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml)

    print(f"OK: {output_path} ({len(swimlanes)} swimlanes, {len(elements)} elements)", file=sys.stderr)


if __name__ == '__main__':
    main()
