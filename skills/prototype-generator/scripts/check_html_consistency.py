#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from requirements_utils import parse_requirement_modules


def check_consistency(requirements_path: str | Path, prototypes_dir: str | Path, threshold: float = 0.8) -> dict:
    requirements = parse_requirement_modules(requirements_path)
    root = Path(prototypes_dir)
    html_files = sorted(root.glob("*.html"))
    generated_pages: dict[str, dict] = {}
    for path in html_files:
        text = path.read_text(encoding="utf-8")
        page_name = _extract_attr(text, "data-page-name") or path.stem
        page_type = _extract_attr(text, "data-page-type")
        page_archetype = _extract_attr(text, "data-page-archetype")
        generated_pages[page_name] = {
            "file": path.name,
            "text": text,
            "page_type": page_type,
            "page_archetype": page_archetype,
            "has_body_slot": _extract_attr(text, "data-body-slot") == "1" or 'data-body-slot="1"' in text or "data-body-slot='1'" in text,
        }

    missing_pages: list[str] = []
    missing_field_pages: list[dict] = []
    low_coverage_pages: list[dict] = []
    layout_mismatch_pages: list[dict] = []
    for module in requirements.values():
        for page_name, req in module["pages"].items():
            generated = generated_pages.get(page_name)
            if not generated:
                missing_pages.append(page_name)
                continue
            expected_archetype = req.get("page_archetype", "")
            actual_archetype = generated.get("page_archetype", "")
            if expected_archetype and actual_archetype and expected_archetype != actual_archetype:
                layout_mismatch_pages.append({"page": page_name, "expected": expected_archetype, "actual": actual_archetype})
            fields = req.get("fields", [])
            if not fields:
                continue
            present = [field for field in fields if field in generated["text"]]
            coverage = len(present) / max(len(fields), 1)
            if coverage < threshold:
                low_coverage_pages.append({"page": page_name, "coverage": round(coverage, 2), "missing_fields": [field for field in fields if field not in present]})
            if len(present) < len(fields):
                missing_field_pages.append({"page": page_name, "missing_fields": [field for field in fields if field not in present]})
    fail = 1 if missing_pages or low_coverage_pages or layout_mismatch_pages else 0
    return {
        "summary": {"fail": fail, "warn": 0, "pass": 1 if fail == 0 else 0},
        "missing_pages": missing_pages,
        "missing_field_pages": missing_field_pages,
        "low_coverage_pages": low_coverage_pages,
        "action_mismatch_pages": [],
        "layout_mismatch_pages": layout_mismatch_pages,
        "generated_pages": {
            key: {"file": value["file"], "has_body_slot": value["has_body_slot"]}
            for key, value in generated_pages.items()
        },
    }


def _extract_attr(text: str, attr: str) -> str:
    for quote in ('"', "'"):
        marker = f"{attr}={quote}"
        if marker in text:
            return text.split(marker, 1)[1].split(quote, 1)[0]
    return ""


def main():
    parser = argparse.ArgumentParser(description="校验 requirements 与 HTML 原型的一致性")
    parser.add_argument("requirements_path")
    parser.add_argument("prototypes_dir")
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    report = check_consistency(args.requirements_path, args.prototypes_dir, args.threshold)
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["summary"]["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
