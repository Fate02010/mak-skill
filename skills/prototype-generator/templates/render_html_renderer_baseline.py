#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from html_utils import (
    build_body_prompt,
    build_body_spec,
    compose_page_html,
    generate_body_html,
    parse_page_spec,
)


def render_spec(page_spec_path: str | Path, prototypes_dir: str | Path, body_slots_dir: str | Path | None = None) -> dict:
    spec_path = Path(page_spec_path)
    output_dir = Path(prototypes_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    slots_dir = Path(body_slots_dir) if body_slots_dir else output_dir.parent / "body_slots"
    slots_dir.mkdir(parents=True, exist_ok=True)
    spec = parse_page_spec(spec_path)
    spec["site_pages"] = _load_site_pages(spec_path.parent)
    page_file_map = {
        page.get("page_name", ""): page.get("output_file", "")
        for page in spec.get("site_pages", spec.get("pages", []))
        if page.get("page_name") and page.get("output_file")
    }
    rendered = []
    for page in spec.get("pages", []):
        output_file = page.get("output_file") or "page.html"
        slug = Path(output_file).stem
        body_spec = build_body_spec(spec, page, page_file_map)
        body_prompt = build_body_prompt(spec, page, body_spec)
        try:
            body_html = generate_body_html(spec, page, page_file_map, body_spec, body_prompt)
        except ValueError as exc:
            raise SystemExit(str(exc))
        html_text = compose_page_html(spec, page, page_file_map, body_html)
        path = output_dir / output_file
        body_spec_path = slots_dir / f"body_spec_{slug}.json"
        body_prompt_path = slots_dir / f"body_prompt_{slug}.md"
        body_html_path = slots_dir / f"body_html_{slug}.html"
        body_spec_path.write_text(json.dumps(body_spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        body_prompt_path.write_text(body_prompt, encoding="utf-8")
        body_html_path.write_text(body_html.strip() + "\n", encoding="utf-8")
        path.write_text(html_text, encoding="utf-8")
        rendered.append(
            {
                "page_name": page.get("page_name", ""),
                "page_type": page.get("page_type", ""),
                "output_file": output_file,
                "path": str(path),
                "body_slot_artifacts": {
                    "body_spec": str(body_spec_path),
                    "body_prompt": str(body_prompt_path),
                    "body_html": str(body_html_path),
                },
            }
        )
    return {
        "module_name": spec.get("module_name", ""),
        "module_key": spec.get("module_key", ""),
        "page_spec": str(spec_path),
        "body_slots_dir": str(slots_dir),
        "rendered_pages": rendered,
    }


def _load_site_pages(page_specs_dir: Path) -> list[dict]:
    pages: list[dict] = []
    if not page_specs_dir.is_dir():
        return pages
    for sibling in sorted(page_specs_dir.glob("page_spec_*.md")):
        sibling_spec = parse_page_spec(sibling)
        module_name = sibling_spec.get("module_name", "")
        for page in sibling_spec.get("pages", []):
            pages.append({**page, "module_name": module_name})
    return pages


def main():
    parser = argparse.ArgumentParser(description="从冻结的 HTML page_spec 渲染 HTML 原型文件")
    parser.add_argument("page_spec_md")
    parser.add_argument("prototypes_dir")
    parser.add_argument("--body-slots-dir")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    report = render_spec(args.page_spec_md, args.prototypes_dir, body_slots_dir=args.body_slots_dir)
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        rendered = ", ".join(item["output_file"] for item in report["rendered_pages"])
        print(f"OK: {report['module_name']} -> {rendered}")


if __name__ == "__main__":
    main()
