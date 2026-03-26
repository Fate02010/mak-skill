#!/usr/bin/env python3
"""
check_context_budget.py - 预检 Codex 5.4 Medium / 200K 的上下文预算风险。

用法:
    python3 check_context_budget.py <work_dir> [--json]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path


WINDOW_TOKENS = 200000
RESERVE_RATIO = 0.35
USABLE_TOKENS = int(WINDOW_TOKENS * (1 - RESERVE_RATIO))
PROMPT_OVERHEAD_TOKENS = 15000
PAGE_SPEC_ALLOWANCE_TOKENS = 12000
OVERVIEW_WARN_TOKENS = 25000
OVERVIEW_FAIL_TOKENS = 35000
BRIEF_WARN_TOKENS = 7000
BRIEF_FAIL_TOKENS = 10000
DETAIL_WARN_TOKENS = 30000
DETAIL_FAIL_TOKENS = 45000
SINGLE_WARN_TOKENS = 70000
SINGLE_FAIL_TOKENS = 100000


def estimate_tokens(text: str) -> int:
    cjk_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    non_space = sum(1 for ch in text if not ch.isspace())
    non_cjk = max(0, non_space - cjk_chars)
    return cjk_chars + math.ceil(non_cjk / 4)


def read_tokens(path: Path) -> int:
    return estimate_tokens(path.read_text(encoding="utf-8"))


def assess_work_dir(work_dir: str) -> dict:
    root = Path(work_dir)
    requirements_dir = root / "requirements"
    index_path = requirements_dir / "index.md"
    overview_path = requirements_dir / "详细需求文档_overview.md"
    single_path = requirements_dir / "详细需求文档.md"
    briefs_dir = requirements_dir / "module_briefs"

    warnings: list[str] = []
    failures: list[str] = []
    mode = "split" if index_path.exists() else "single"
    report: dict = {
        "mode": mode,
        "window_tokens": WINDOW_TOKENS,
        "reserve_ratio": RESERVE_RATIO,
        "usable_tokens": USABLE_TOKENS,
    }

    if mode == "single":
        if not single_path.exists():
            failures.append("single 模式缺少 requirements/详细需求文档.md")
            report["single_file_tokens"] = 0
        else:
            single_tokens = read_tokens(single_path)
            report["single_file_tokens"] = single_tokens
            if single_tokens > SINGLE_FAIL_TOKENS:
                failures.append(f"单文件需求文档过大：{single_tokens} tokens，建议拆分为 overview + module_briefs")
            elif single_tokens > SINGLE_WARN_TOKENS:
                warnings.append(f"单文件需求文档偏大：{single_tokens} tokens，已接近 200K 安全预算")
        report["worst_case_task_tokens"] = report.get("single_file_tokens", 0) + PROMPT_OVERHEAD_TOKENS + PAGE_SPEC_ALLOWANCE_TOKENS
    else:
        brief_tokens = {}
        detail_tokens = {}
        if not overview_path.exists():
            failures.append("split 模式缺少 requirements/详细需求文档_overview.md")
            overview_tokens = 0
        else:
            overview_tokens = read_tokens(overview_path)
            if overview_tokens > OVERVIEW_FAIL_TOKENS:
                failures.append(f"overview 过大：{overview_tokens} tokens，需继续压缩全局章节")
            elif overview_tokens > OVERVIEW_WARN_TOKENS:
                warnings.append(f"overview 偏大：{overview_tokens} tokens")
        report["overview_tokens"] = overview_tokens

        if not briefs_dir.is_dir():
            failures.append("split 模式缺少 requirements/module_briefs/")
        else:
            for path in sorted(briefs_dir.glob("模块摘要_*.md")):
                tokens = read_tokens(path)
                brief_tokens[path.name] = tokens
                if tokens > BRIEF_FAIL_TOKENS:
                    failures.append(f"{path.name} 过大：{tokens} tokens，module_brief 应进一步压缩")
                elif tokens > BRIEF_WARN_TOKENS:
                    warnings.append(f"{path.name} 偏大：{tokens} tokens")
        report["brief_tokens"] = brief_tokens

        for path in sorted(requirements_dir.glob("详细需求文档_*.md")):
            if path.name == "详细需求文档_overview.md":
                continue
            tokens = read_tokens(path)
            detail_tokens[path.name] = tokens
            if tokens > DETAIL_FAIL_TOKENS:
                failures.append(f"{path.name} 过大：{tokens} tokens，单模块详细文档已超安全预算")
            elif tokens > DETAIL_WARN_TOKENS:
                warnings.append(f"{path.name} 偏大：{tokens} tokens")
        report["detail_tokens"] = detail_tokens

        max_brief = max(brief_tokens.values()) if brief_tokens else 0
        max_detail = max(detail_tokens.values()) if detail_tokens else 0
        worst_case = overview_tokens + max_brief + max_detail + PROMPT_OVERHEAD_TOKENS + PAGE_SPEC_ALLOWANCE_TOKENS
        report["worst_case_task_tokens"] = worst_case
        if worst_case > USABLE_TOKENS:
            failures.append(
                f"最坏单任务上下文估算为 {worst_case} tokens，超过安全可用预算 {USABLE_TOKENS}"
            )
        elif worst_case > int(USABLE_TOKENS * 0.85):
            warnings.append(
                f"最坏单任务上下文估算为 {worst_case} tokens，已接近安全可用预算 {USABLE_TOKENS}"
            )

    report["warnings"] = warnings
    report["failures"] = failures
    report["summary"] = {
        "fail": 1 if failures else 0,
        "warn": 1 if warnings else 0,
        "pass": 0 if failures else 1,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="预检 Codex 5.4 Medium / 200K 上下文预算风险")
    parser.add_argument("work_dir")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if not os.path.isdir(args.work_dir):
        print(f"错误：work_dir 不存在 — {args.work_dir}", file=sys.stderr)
        raise SystemExit(1)

    report = assess_work_dir(args.work_dir)
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== context budget precheck ===")
        print(f"mode: {report['mode']}")
        print(f"usable_tokens: {report['usable_tokens']}")
        print(f"worst_case_task_tokens: {report['worst_case_task_tokens']}")
        for item in report["warnings"]:
            print(f"WARN: {item}")
        for item in report["failures"]:
            print(f"FAIL: {item}")

    raise SystemExit(1 if report["summary"]["fail"] else 0)


if __name__ == "__main__":
    main()
