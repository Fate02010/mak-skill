#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from html_utils import parse_page_spec, render_page_html


def render_spec(page_spec_path: str | Path, prototypes_dir: str | Path) -> dict:
    spec_path = Path(page_spec_path)
    output_dir = Path(prototypes_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = parse_page_spec(spec_path)
    page_file_map = {
        page.get("page_name", ""): page.get("output_file", "")
        for page in spec.get("pages", [])
        if page.get("page_name") and page.get("output_file")
    }
    rendered = []
    for page in spec.get("pages", []):
        output_file = page.get("output_file") or "page.html"
        html_text = render_page_html(spec, page, page_file_map)
        path = output_dir / output_file
        path.write_text(html_text, encoding="utf-8")
        rendered.append(
            {
                "page_name": page.get("page_name", ""),
                "page_type": page.get("page_type", ""),
                "output_file": output_file,
                "path": str(path),
            }
        )
    return {
        "module_name": spec.get("module_name", ""),
        "module_key": spec.get("module_key", ""),
        "page_spec": str(spec_path),
        "rendered_pages": rendered,
    }


def main():
    parser = argparse.ArgumentParser(description="从冻结的 HTML page_spec 渲染 HTML 原型文件")
    parser.add_argument("page_spec_md")
    parser.add_argument("prototypes_dir")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    report = render_spec(args.page_spec_md, args.prototypes_dir)
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        rendered = ", ".join(item["output_file"] for item in report["rendered_pages"])
        print(f"OK: {report['module_name']} -> {rendered}")


if __name__ == "__main__":
    main()
