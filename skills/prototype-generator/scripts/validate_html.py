#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PLACEHOLDER_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"Lorem ipsum",
        r"待补充",
        r"功能待定",
        r"示例文字",
        r"按钮N",
        r"字段[0-9一二三四五六七八九十]",
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
        return {"summary": {"fail": 1, "warn": 0, "pass": 0}, "results": [RuleResult("H0", "html_exists", "FAIL", 1, [str(target)]).to_dict()]}

    missing_structure: list[str] = []
    missing_css: list[str] = []
    placeholders: list[str] = []
    broken_links: list[str] = []
    missing_shell: list[str] = []
    missing_states: list[str] = []
    file_names = {file.name for file in files}
    for file in files:
        text = file.read_text(encoding="utf-8")
        lowered = text.lower()
        if "<html" not in lowered or "<head" not in lowered or "<body" not in lowered or "</html>" not in lowered or "<title>" not in lowered:
            missing_structure.append(file.name)
        if 'href="common.css"' not in text and "href='common.css'" not in text:
            missing_css.append(file.name)
        for pattern in PLACEHOLDER_PATTERNS:
            if pattern.search(text):
                placeholders.append(file.name)
                break
        if 'data-prototype-shell="1"' not in text or 'class="page-main"' not in text:
            missing_shell.append(file.name)
        if 'data-page-type="index"' not in text:
            has_empty = 'data-state="empty"' in text
            has_error = 'data-state="error"' in text
            has_processing = 'data-state="processing"' in text
            if not (has_empty and has_error):
                missing_states.append(file.name)
            if 'data-page-type="web_form"' in text or 'data-page-type="mobile_form"' in text or 'data-page-type="login"' in text:
                if not has_processing:
                    missing_states.append(file.name)
        hrefs = re.findall(r'href="([^"]+)"', text) + re.findall(r"href='([^']+)'", text)
        for href in hrefs:
            if href.startswith(("http://", "https://", "#")):
                continue
            if href.endswith(".html") and href not in file_names:
                broken_links.append(f"{file.name} -> {href}")
        for href in re.findall(r"location\.href\s*=\s*'([^']+)'", text):
            if href.endswith(".html") and href not in file_names:
                broken_links.append(f"{file.name} -> {href}")

    results = [
        RuleResult("H1", "html_document_structure", "FAIL" if missing_structure else "PASS", len(missing_structure), missing_structure),
        RuleResult("H2", "common_css_link", "FAIL" if missing_css else "PASS", len(missing_css), missing_css),
        RuleResult("H3", "placeholder_text", "FAIL" if placeholders else "PASS", len(placeholders), placeholders),
        RuleResult("H4", "broken_local_links", "FAIL" if broken_links else "PASS", len(broken_links), broken_links),
        RuleResult("H5", "page_shell_markers", "FAIL" if missing_shell else "PASS", len(missing_shell), missing_shell),
        RuleResult("H6", "state_coverage", "FAIL" if missing_states else "PASS", len(sorted(set(missing_states))), sorted(set(missing_states))),
    ]
    fail = sum(1 for item in results if item.status == "FAIL")
    return {
        "summary": {"fail": fail, "warn": 0, "pass": 1 if fail == 0 else 0},
        "results": [item.to_dict() for item in results],
    }


def main():
    parser = argparse.ArgumentParser(description="校验 HTML 原型结构与链接完整性")
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
