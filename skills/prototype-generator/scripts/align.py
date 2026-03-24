#!/usr/bin/env python3
"""坐标 8 倍数自动对齐工具。

用法:
    python3 align.py <drawio_file> [--dry-run]

选项:
    --dry-run  只报告不修改文件
"""
import re
import sys


def align8(val):
    """Round to nearest multiple of 8."""
    return round(val / 8) * 8


def process(filepath, dry_run=False):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    fixes = []

    def fix_geometry(match):
        x, y, w, h = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        if h == 1:  # divider 豁免
            return match.group(0)
        nx, ny, nw, nh = align8(x), align8(y), align8(w), align8(h)
        if nw == 0:
            nw = 8
        if nh == 0:
            nh = 8
        if (nx, ny, nw, nh) != (x, y, w, h):
            changes = []
            if x != nx:
                changes.append(f"x={x}→{nx}")
            if y != ny:
                changes.append(f"y={y}→{ny}")
            if w != nw:
                changes.append(f"w={w}→{nw}")
            if h != nh:
                changes.append(f"h={h}→{nh}")
            fixes.append(", ".join(changes))
        return f'<mxGeometry x="{nx}" y="{ny}" width="{nw}" height="{nh}"'

    new_content = re.sub(
        r'<mxGeometry\s+x="(\d+)"\s+y="(\d+)"\s+width="(\d+)"\s+height="(\d+)"',
        fix_geometry,
        content,
    )

    if not fixes:
        print("✅ 所有坐标已对齐，无需修复")
        return 0

    print(f"发现 {len(fixes)} 处未对齐坐标：")
    for i, fix in enumerate(fixes[:20], 1):
        print(f"  {i}. {fix}")
    if len(fixes) > 20:
        print(f"  ... 还有 {len(fixes) - 20} 处")

    if dry_run:
        print(f"\n--dry-run 模式，未修改文件")
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"\n✅ 已修复 {len(fixes)} 处，写入 {filepath}")

    return len(fixes)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    filepath = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    try:
        count = process(filepath, dry_run)
        sys.exit(0 if count == 0 else 1)
    except FileNotFoundError:
        print(f"❌ 文件不存在: {filepath}", file=sys.stderr)
        sys.exit(2)
