#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from autofix import apply_html_repairs, repair_drawio_page_models
from review_finding import make_finding


DRAWIO_ESCALATION_MAP = {
    "html_render": "page_spec",
    "render_merge": "page_spec",
    "page_spec": "page_model",
    "page_model": "requirements",
}
HTML_ESCALATION_MAP = {
    "page_spec": "module_brief",
    "module_brief": "requirements",
    "reference_pack": "module_brief",
}
HTML_HANDLER_REGISTRY = {"page_spec", "module_brief", "requirements", "reference_pack", "html_render"}
STATE_SCHEMA_VERSION = 3
RUNNING_PHASES = {"round_started", "review_completed", "repairing", "skill_patching", "round_repaired"}
FINAL_PHASE = "completed"


def _run_command(cmd: list[str]) -> dict:
    completed = subprocess.run(cmd, capture_output=True, text=True)
    return {"cmd": cmd, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _parse_json_stdout(result: dict) -> dict:
    stdout = (result.get("stdout") or "").strip()
    return json.loads(stdout) if stdout else {}


def _pipeline_script(format_name: str) -> Path:
    if format_name == "drawio":
        return SCRIPT_DIR / "run_drawio_pipeline.py"
    if format_name == "html":
        return SCRIPT_DIR / "run_html_pipeline.py"
    raise ValueError(f"unsupported format: {format_name}")


def _run_pipeline(format_name: str, work_dir: Path, product_name: str, max_parallel: int) -> dict:
    script = _pipeline_script(format_name)
    result = _run_command([sys.executable, str(script), str(work_dir), product_name, "--max-parallel", str(max_parallel), "--json"])
    payload = _parse_json_stdout(result)
    if "summary" not in payload:
        payload["summary"] = {"fail": 1, "warn": 0, "pass": 0}
        payload.setdefault("review_findings", [])
        payload["review_findings"].append(
            make_finding(format=format_name, scope="all", page_or_sheet="", layer="render_merge", rule="PIPELINE", severity="error", message=result.get("stderr", "").strip() or "pipeline failed", repair_target="render_merge")
        )
    return payload


def _run_vision_review(mode: str, artifact_path: Path, format_name: str) -> dict:
    mode = str(mode or "auto")
    if mode == "off":
        return {"status": "skipped", "mode": mode, "findings": []}
    command = str(Path.cwd().joinpath(".prototype-generator-vision").resolve())  # placeholder path unlikely to exist
    env_command = None
    if "PROTOTYPE_GENERATOR_VISION_REVIEW_CMD" in os.environ:
        env_command = os.environ["PROTOTYPE_GENERATOR_VISION_REVIEW_CMD"]
    if not env_command:
        if mode == "required":
            return {
                "status": "failed",
                "mode": mode,
                "findings": [
                    make_finding(format=format_name, scope="all", page_or_sheet=artifact_path.name, layer="review", rule="VISION_BACKEND", severity="error", message="缺少视觉审图后端", repair_target="review"),
                ],
            }
        return {"status": "skipped", "mode": mode, "reason": f"no backend: {command}", "findings": []}
    cmd = shlex.split(env_command) + [str(artifact_path)]
    result = _run_command(cmd)
    payload = _parse_json_stdout(result)
    findings = payload.get("findings", [])
    if result["returncode"] != 0 and mode == "required":
        findings.append(make_finding(format=format_name, scope="all", page_or_sheet=artifact_path.name, layer="review", rule="VISION_BACKEND", severity="error", message=result.get("stderr", "").strip() or "视觉审图失败", repair_target="review"))
    return {"status": "ok" if result["returncode"] == 0 else "failed", "mode": mode, "findings": findings}


def _artifact_for_report(format_name: str, report: dict) -> Path | None:
    if format_name == "drawio":
        value = report.get("final_drawio", "")
    else:
        value = report.get("artifacts", {}).get("index_html", "")
    return Path(value) if value else None


def _apply_repairs(format_name: str, work_dir: Path, findings: list[dict]) -> dict:
    requirements_dir = work_dir / "requirements"
    artifact_dir = work_dir / ".prototype-generator"
    if format_name == "drawio":
        return {
            "status": "ok",
            "changes": repair_drawio_page_models(requirements_dir, artifact_dir / "page_models", findings),
            "executed_actions": ["rewrite_page_model"],
            "attempted_fix_scopes": ["page_model"],
            "regression": {"status": "skipped", "cmd": [], "returncode": 0, "stdout": "", "stderr": ""},
            "blocked_findings": [],
        }
    return apply_html_repairs(work_dir, findings, skill_dir=SCRIPT_DIR.parent)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _round_dir(rounds_dir: Path, round_no: int) -> Path:
    return rounds_dir / f"round_{round_no:02d}"


def _load_saved_pipeline_report(rounds_dir: Path, round_no: int | None) -> dict:
    if not round_no:
        return {}
    path = _round_dir(rounds_dir, round_no) / "pipeline_report.json"
    return _read_json(path) if path.exists() else {}


def _load_saved_findings(rounds_dir: Path, round_no: int | None) -> list[dict]:
    if not round_no:
        return []
    round_dir = _round_dir(rounds_dir, round_no)
    findings: list[dict] = []
    pipeline_path = round_dir / "pipeline_report.json"
    if pipeline_path.exists():
        findings.extend(_read_json(pipeline_path).get("review_findings", []))
    round_report_path = round_dir / "round_report.json"
    if round_report_path.exists():
        findings.extend(_read_json(round_report_path).get("vision_review", {}).get("findings", []))
    return findings


def _doc_mode(work_dir: Path) -> str:
    requirements_dir = work_dir / "requirements"
    if (requirements_dir / "index.md").exists():
        return "split"
    if (requirements_dir / "详细需求文档.md").exists():
        return "single"
    return "unknown"


def _state_matches_args(state: dict, work_dir: Path, product_name: str, format_name: str) -> bool:
    return (
        state.get("work_dir") == str(work_dir)
        and state.get("product_name") == product_name
        and state.get("format") == format_name
    )


def _load_resume_state(state_path: Path, work_dir: Path, product_name: str, format_name: str) -> dict:
    if not state_path.exists():
        raise ValueError(f"resume state not found: {state_path}")
    try:
        state = _read_json(state_path)
    except json.JSONDecodeError as exc:
        raise ValueError(f"resume state is not valid JSON: {state_path}") from exc
    if state.get("schema_version") not in {2, STATE_SCHEMA_VERSION}:
        raise ValueError(f"resume state schema mismatch: expected 2 or {STATE_SCHEMA_VERSION}")
    if not _state_matches_args(state, work_dir, product_name, format_name):
        raise ValueError("resume state does not match work_dir/product_name/format")
    phase = state.get("phase")
    status = state.get("status")
    if phase not in RUNNING_PHASES | {FINAL_PHASE}:
        raise ValueError(f"resume state phase is invalid: {phase}")
    if status not in {"running", "passed", "failed"}:
        raise ValueError(f"resume state status is invalid: {status}")
    if phase == FINAL_PHASE and status == "running":
        raise ValueError("resume state is inconsistent: completed phase cannot be running")
    if phase in RUNNING_PHASES and status != "running":
        raise ValueError("resume state is inconsistent: running phase must have running status")
    return state


def _escalate_finding(format_name: str, finding: dict) -> tuple[dict, dict | None]:
    target = str(finding.get("repair_target", ""))
    if format_name == "drawio":
        escalated_target = DRAWIO_ESCALATION_MAP.get(target, target)
        if escalated_target == target:
            return finding, None
        finding["repair_target"] = escalated_target
        finding["expected_fix_scope"] = escalated_target
        finding["stagnation_key"] = (
            f"{finding['repair_target']}::{finding.get('repair_action', '')}::{finding.get('rule', '')}::{finding.get('page_or_sheet') or 'all'}"
        )
        return finding, {"finding": finding.get("id", ""), "repair_target": escalated_target}

    if target == "html_render":
        finding["stop_category"] = "needs_skill_patch"
        finding["repair_action"] = "patch_renderer"
        finding["expected_fix_scope"] = "html_render"
        finding["stagnation_key"] = (
            f"{finding['repair_target']}::{finding.get('repair_action', '')}::{finding.get('rule', '')}::{finding.get('page_or_sheet') or 'all'}"
        )
        return finding, {"finding": finding.get("id", ""), "repair_target": "html_render", "stop_category": "needs_skill_patch"}

    escalated_target = HTML_ESCALATION_MAP.get(target, target)
    if escalated_target == target or escalated_target not in HTML_HANDLER_REGISTRY:
        return finding, None
    finding["repair_target"] = escalated_target
    if escalated_target == "module_brief":
        finding["repair_action"] = "rewrite_module_brief"
        finding["stop_category"] = "needs_refreeze"
    elif escalated_target == "requirements":
        finding["repair_action"] = "rewrite_requirements"
        finding["stop_category"] = "needs_refreeze"
    finding["expected_fix_scope"] = escalated_target
    finding["stagnation_key"] = (
        f"{finding['repair_target']}::{finding.get('repair_action', '')}::{finding.get('rule', '')}::{finding.get('page_or_sheet') or 'all'}"
    )
    return finding, {"finding": finding.get("id", ""), "repair_target": escalated_target}


def _failure_summary(findings: list[dict]) -> dict:
    by_rule: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for finding in findings:
        if str(finding.get("severity", "error")) != "error":
            continue
        rule = str(finding.get("rule", "")) or "unknown"
        by_rule[rule] = by_rule.get(rule, 0) + 1
        category = str(finding.get("stop_category", "")) or "auto_repairable"
        by_category[category] = by_category.get(category, 0) + 1
    return {"by_rule": by_rule, "by_stop_category": by_category}


def _repeated_failures(findings: list[dict], streaks: dict[str, int]) -> list[dict]:
    items = []
    for finding in findings:
        key = finding.get("stagnation_key") or ""
        streak = int(streaks.get(key, 0))
        if streak >= 2:
            items.append({"finding": finding.get("id", key), "streak": streak, "repair_target": finding.get("repair_target", "")})
    return items


def _stop_recommendation(findings: list[dict], repair_report: dict | None = None) -> str:
    if repair_report and repair_report.get("regression", {}).get("status") == "failed":
        return "需要修改 skill 脚本"
    if any(str(item.get("stop_category", "")) == "needs_skill_patch" for item in findings):
        return "需要修改 skill 脚本"
    if any(str(item.get("stop_category", "")) == "needs_refreeze" for item in findings):
        return "需要重冻规格"
    if any(str(item.get("severity", "error")) == "error" for item in findings):
        return "可自动修"
    return ""


def _last_unconverged_reason(findings: list[dict], repair_report: dict | None = None) -> str:
    if repair_report and repair_report.get("regression", {}).get("status") == "failed":
        return "renderer 回归测试失败，skill patch 未收敛"
    if not findings:
        return ""
    finding = findings[0]
    return str(finding.get("root_cause_hint") or finding.get("message") or finding.get("rule") or "")


def _status_markdown(state: dict, *, resume_source: str) -> str:
    status_map = {"running": "进行中", "passed": "已完成", "failed": "失败"}
    phase_map = {
        "round_started": "Step 6 / 轮次开始",
        "review_completed": "Step 6 / 审视完成",
        "repairing": "Step 6 / 修复中",
        "skill_patching": "Step 6 / Skill Patch",
        "round_repaired": "Step 6 / 本轮修复完成",
        "completed": "Step 6 / 全部完成",
    }
    lines = [
        "# 执行状态",
        "",
        "| 项目 | 内容 |",
        "|------|------|",
        f"| 产品名称 | {state.get('product_name', '')} |",
        f"| OUTPUT_FORMAT | {state.get('format', '')} |",
        f"| DOC_MODE | {_doc_mode(Path(state.get('work_dir', '.')))} |",
        f"| WORK_DIR | {state.get('work_dir', '')} |",
        f"| 整体状态 | {status_map.get(state.get('status', ''), state.get('status', ''))} |",
        f"| 当前阶段 | {phase_map.get(state.get('phase', ''), state.get('phase', ''))} |",
        f"| 当前轮次 | {state.get('current_round', '')} |",
        f"| 下一轮次 | {state.get('next_round', '')} |",
        f"| 恢复来源 | {resume_source} |",
        f"| 最后更新 | {state.get('updated_at', '')} |",
        "",
        "## Step 完成状态",
        "",
        "| Step | 状态 | 输出文件 |",
        "|------|------|----------|",
        "| Step 1 | - | - |",
        "| Step 2 | - | - |",
        "| Step 3 | - | - |",
        "| Step 4 | - | requirements/ |",
        "| Step 5 | - | .prototype-generator/page_models / page_specs / tmp / prototypes |",
        f"| Step 6 | {'✅ 完成' if state.get('status') == 'passed' else '🔄 进行中' if state.get('status') == 'running' else '❌ 阻塞'} | autoloop_state.json / rounds/ |",
        "",
        "## Step 6 迭代记录",
        "",
        "| 轮次 | 改进内容摘要 |",
        "|------|-------------|",
    ]
    for item in state.get("rounds", []):
        summary = item.get("summary", {})
        lines.append(
            f"| 第 {item.get('round', '')} 轮 | findings={item.get('finding_count', 0)} / "
            f"fail={summary.get('fail', 0)} / warn={summary.get('warn', 0)} / escalations={len(item.get('escalations', []))} / repairs={','.join(item.get('repair_actions', [])) or '-'} |"
        )
    if not state.get("rounds"):
        lines.append("| - | 尚未进入自治轮次 |")
    lines.extend(
        [
            "",
            "## 未收敛原因摘要",
            "",
            f"- 已尝试修复层：{', '.join(state.get('attempted_fix_scopes', [])) or '无'}",
            f"- 重复失败：{json.dumps(state.get('repeated_failures', []), ensure_ascii=False)}",
            f"- 最近未收敛原因：{state.get('last_unconverged_reason', '') or '无'}",
            f"- 建议：{state.get('stop_recommendation', '') or '无'}",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_status_files(state_path: Path, execution_status_path: Path, state: dict, *, resume_source: str) -> None:
    _write_json(state_path, state)
    execution_status_path.parent.mkdir(parents=True, exist_ok=True)
    execution_status_path.write_text(_status_markdown(state, resume_source=resume_source), encoding="utf-8")


def _build_state(
    *,
    work_dir: Path,
    product_name: str,
    format_name: str,
    max_rounds: int,
    max_parallel: int,
    vision_review: str,
    status: str,
    phase: str,
    current_round: int,
    next_round: int,
    rounds: list[dict],
    streaks: dict[str, int],
    latest_findings: list[dict],
    final_artifact: str = "",
    blocked_findings: list[dict] | None = None,
    failure_summary: dict | None = None,
    attempted_fix_scopes: list[str] | None = None,
    repeated_failures: list[dict] | None = None,
    last_unconverged_reason: str = "",
    stop_recommendation: str = "",
) -> dict:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "work_dir": str(work_dir),
        "product_name": product_name,
        "format": format_name,
        "max_rounds": max_rounds,
        "max_parallel": max_parallel,
        "vision_review": vision_review,
        "status": status,
        "phase": phase,
        "current_round": current_round,
        "next_round": next_round,
        "rounds": rounds,
        "streaks": streaks,
        "latest_findings": latest_findings,
        "blocked_findings": blocked_findings or [],
        "failure_summary": failure_summary or {"by_rule": {}, "by_stop_category": {}},
        "attempted_fix_scopes": attempted_fix_scopes or [],
        "repeated_failures": repeated_failures or [],
        "last_unconverged_reason": last_unconverged_reason,
        "stop_recommendation": stop_recommendation,
        "final_artifact": final_artifact,
        "updated_at": _now_iso(),
    }


def _final_payload(
    *,
    state_path: Path,
    status: str,
    rounds: list[dict],
    final_report: dict,
    blocked_findings: list[dict],
    resumed: bool,
    resume_from_phase: str | None,
    resume_from_round: int | None,
    error: str | None = None,
) -> dict:
    payload = {
        "state_path": str(state_path),
        "status": status,
        "rounds": rounds,
        "final_report": final_report,
        "blocked_findings": blocked_findings,
        "resumed": resumed,
        "resume_from_phase": resume_from_phase,
        "resume_from_round": resume_from_round,
    }
    if error:
        payload["error"] = error
    return payload


def _emit_payload(payload: dict, exit_code: int) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def main():
    parser = argparse.ArgumentParser(description="运行 prototype-generator 自治闭环主控器")
    parser.add_argument("work_dir")
    parser.add_argument("product_name")
    parser.add_argument("--format", choices=["drawio", "html"], required=True)
    parser.add_argument("--max-rounds", type=int, default=5)
    parser.add_argument("--max-parallel", type=int, default=3)
    parser.add_argument("--vision-review", choices=["auto", "off", "required"], default="auto")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    work_dir = Path(args.work_dir).resolve()
    artifact_dir = work_dir / ".prototype-generator"
    rounds_dir = artifact_dir / "rounds"
    rounds_dir.mkdir(parents=True, exist_ok=True)
    state_path = artifact_dir / "autoloop_state.json"
    execution_status_path = artifact_dir / "执行状态.md"

    resumed = False
    resume_from_phase: str | None = None
    resume_from_round: int | None = None
    resume_source = "fresh start"

    streaks: dict[str, int] = {}
    rounds: list[dict] = []
    final_report: dict = {}
    final_findings: list[dict] = []
    last_repair_report: dict = {}
    start_round = 1

    if args.resume:
        resumed = True
        try:
            state = _load_resume_state(state_path, work_dir, args.product_name, args.format)
        except ValueError as exc:
            _emit_payload(
                _final_payload(
                    state_path=state_path,
                    status="failed",
                    rounds=[],
                    final_report={},
                    blocked_findings=[],
                    resumed=True,
                    resume_from_phase=None,
                    resume_from_round=None,
                    error=str(exc),
                ),
                1,
            )
        resume_from_phase = str(state.get("phase", ""))
        resume_from_round = int(state.get("current_round") or state.get("next_round") or 0) or None
        resume_source = f"--resume from round {resume_from_round or '-'} / {resume_from_phase}"
        rounds = list(state.get("rounds", []))
        streaks = {str(key): int(value) for key, value in dict(state.get("streaks", {})).items()}
        current_round = int(state.get("current_round") or 0)
        next_round = int(state.get("next_round") or 0)
        final_findings = list(state.get("latest_findings", []))
        final_report = _load_saved_pipeline_report(rounds_dir, current_round or next_round - 1)

        if state.get("status") == "passed":
            _write_status_files(state_path, execution_status_path, state, resume_source=resume_source)
            _emit_payload(
                _final_payload(
                    state_path=state_path,
                    status="passed",
                    rounds=rounds,
                    final_report=final_report,
                    blocked_findings=[],
                    resumed=True,
                    resume_from_phase=resume_from_phase,
                    resume_from_round=resume_from_round,
                ),
                0,
            )

        if state.get("status") == "failed" and args.max_rounds <= len(rounds):
            _write_status_files(state_path, execution_status_path, state, resume_source=resume_source)
            _emit_payload(
                _final_payload(
                    state_path=state_path,
                    status="failed",
                    rounds=rounds,
                    final_report=final_report,
                    blocked_findings=list(state.get("blocked_findings", [])),
                    resumed=True,
                    resume_from_phase=resume_from_phase,
                    resume_from_round=resume_from_round,
                ),
                1,
            )

        if resume_from_phase == "round_started":
            start_round = max(1, current_round)
        elif resume_from_phase in {"review_completed", "repairing", "skill_patching"}:
            final_findings = final_findings or _load_saved_findings(rounds_dir, current_round)
            repair_phase = "skill_patching" if any(item.get("stop_category") == "needs_skill_patch" for item in final_findings) else "repairing"
            repairing_state = _build_state(
                work_dir=work_dir,
                product_name=args.product_name,
                format_name=args.format,
                max_rounds=args.max_rounds,
                max_parallel=max(1, min(args.max_parallel, 3)),
                vision_review=args.vision_review,
                status="running",
                phase=repair_phase,
                current_round=current_round,
                next_round=max(current_round + 1, next_round or current_round + 1),
                rounds=rounds,
                streaks=streaks,
                latest_findings=final_findings,
                final_artifact=str(_artifact_for_report(args.format, final_report) or ""),
                failure_summary=_failure_summary(final_findings),
                repeated_failures=_repeated_failures(final_findings, streaks),
                last_unconverged_reason=_last_unconverged_reason(final_findings),
                stop_recommendation=_stop_recommendation(final_findings),
            )
            _write_status_files(state_path, execution_status_path, repairing_state, resume_source=resume_source)
            repair_report = _apply_repairs(args.format, work_dir, final_findings)
            last_repair_report = repair_report
            repaired_state = _build_state(
                work_dir=work_dir,
                product_name=args.product_name,
                format_name=args.format,
                max_rounds=args.max_rounds,
                max_parallel=max(1, min(args.max_parallel, 3)),
                vision_review=args.vision_review,
                status="running",
                phase="round_repaired",
                current_round=current_round,
                next_round=max(current_round + 1, next_round or current_round + 1),
                rounds=rounds,
                streaks=streaks,
                latest_findings=final_findings,
                final_artifact=str(_artifact_for_report(args.format, final_report) or ""),
                blocked_findings=repair_report.get("blocked_findings", []),
                failure_summary=_failure_summary(final_findings),
                attempted_fix_scopes=repair_report.get("attempted_fix_scopes", []),
                repeated_failures=_repeated_failures(final_findings, streaks),
                last_unconverged_reason=_last_unconverged_reason(final_findings, repair_report),
                stop_recommendation=_stop_recommendation(final_findings, repair_report),
            )
            _write_status_files(state_path, execution_status_path, repaired_state, resume_source=resume_source)
            start_round = repaired_state["next_round"]
        elif resume_from_phase == "round_repaired":
            start_round = max(1, next_round or current_round + 1)
        elif resume_from_phase == "completed":
            start_round = max(1, next_round or len(rounds) + 1)
        else:
            _emit_payload(
                _final_payload(
                    state_path=state_path,
                    status="failed",
                    rounds=rounds,
                    final_report=final_report,
                    blocked_findings=list(state.get("blocked_findings", [])),
                    resumed=True,
                    resume_from_phase=resume_from_phase,
                    resume_from_round=resume_from_round,
                    error=f"unsupported resume phase: {resume_from_phase}",
                ),
                1,
            )

    status = "failed"
    max_parallel = max(1, min(args.max_parallel, 3))
    if start_round > max(1, args.max_rounds):
        final_state = _build_state(
            work_dir=work_dir,
            product_name=args.product_name,
            format_name=args.format,
            max_rounds=args.max_rounds,
            max_parallel=max_parallel,
            vision_review=args.vision_review,
            status="failed",
            phase=FINAL_PHASE,
            current_round=max(len(rounds), resume_from_round or 0),
            next_round=start_round,
            rounds=rounds,
            streaks=streaks,
            latest_findings=final_findings,
            final_artifact=str(_artifact_for_report(args.format, final_report) or ""),
            blocked_findings=[finding for finding in final_findings if finding.get("severity") == "error"],
            failure_summary=_failure_summary(final_findings),
            repeated_failures=_repeated_failures(final_findings, streaks),
            last_unconverged_reason=_last_unconverged_reason(final_findings),
            stop_recommendation=_stop_recommendation(final_findings),
        )
        _write_status_files(state_path, execution_status_path, final_state, resume_source=resume_source)
        _emit_payload(
            _final_payload(
                state_path=state_path,
                status="failed",
                rounds=rounds,
                final_report=final_report,
                blocked_findings=final_state["blocked_findings"],
                resumed=resumed,
                resume_from_phase=resume_from_phase,
                resume_from_round=resume_from_round,
            ),
            1,
        )

    for round_no in range(start_round, max(1, args.max_rounds) + 1):
        round_dir = rounds_dir / f"round_{round_no:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        round_started_state = _build_state(
            work_dir=work_dir,
            product_name=args.product_name,
            format_name=args.format,
            max_rounds=args.max_rounds,
            max_parallel=max_parallel,
            vision_review=args.vision_review,
            status="running",
            phase="round_started",
            current_round=round_no,
            next_round=round_no,
            rounds=rounds,
            streaks=streaks,
            latest_findings=[],
            final_artifact=str(_artifact_for_report(args.format, final_report) or ""),
        )
        _write_status_files(state_path, execution_status_path, round_started_state, resume_source=resume_source)
        pipeline_report = _run_pipeline(args.format, work_dir, args.product_name, max_parallel=max_parallel)
        artifact_path = _artifact_for_report(args.format, pipeline_report)
        vision_review = _run_vision_review(args.vision_review, artifact_path, args.format) if artifact_path and artifact_path.exists() else {"status": "skipped", "mode": args.vision_review, "findings": []}
        findings = list(pipeline_report.get("review_findings", [])) + list(vision_review.get("findings", []))
        escalations = []
        next_streaks = {}
        for finding in findings:
            key = finding.get("stagnation_key") or f"{finding.get('repair_target')}::{finding.get('repair_action', '')}::{finding.get('rule')}::{finding.get('page_or_sheet') or 'all'}"
            streak = streaks.get(key, 0) + 1
            if streak >= 2:
                finding, escalation = _escalate_finding(args.format, finding)
                if escalation:
                    escalations.append(escalation)
                    key = finding.get("stagnation_key", key)
                    streak = 1
            next_streaks[key] = streak
        failure_summary = _failure_summary(findings)
        repeated_failures = _repeated_failures(findings, next_streaks)
        round_report = {
            "round": round_no,
            "pipeline_report": pipeline_report,
            "vision_review": vision_review,
            "finding_count": len(findings),
            "escalations": escalations,
            "failure_summary": failure_summary,
        }
        _write_json(round_dir / "pipeline_report.json", pipeline_report)
        _write_json(round_dir / "round_report.json", round_report)
        rounds.append(
            {
                "round": round_no,
                "finding_count": len(findings),
                "escalations": escalations,
                "summary": pipeline_report.get("summary", {}),
                "repair_actions": sorted({str(item.get("repair_action", "")) for item in findings if item.get("repair_action")}),
                "stop_categories": sorted({str(item.get("stop_category", "")) for item in findings if item.get("stop_category")}),
            }
        )
        final_report = pipeline_report
        final_findings = findings
        review_completed_state = _build_state(
            work_dir=work_dir,
            product_name=args.product_name,
            format_name=args.format,
            max_rounds=args.max_rounds,
            max_parallel=max_parallel,
            vision_review=args.vision_review,
            status="running",
            phase="review_completed",
            current_round=round_no,
            next_round=round_no + 1,
            rounds=rounds,
            streaks=next_streaks,
            latest_findings=final_findings,
            final_artifact=str(_artifact_for_report(args.format, final_report) or ""),
            failure_summary=failure_summary,
            repeated_failures=repeated_failures,
            last_unconverged_reason=_last_unconverged_reason(final_findings),
            stop_recommendation=_stop_recommendation(final_findings),
        )
        _write_status_files(state_path, execution_status_path, review_completed_state, resume_source=resume_source)
        if pipeline_report.get("summary", {}).get("fail", 0) == 0 and not any(item.get("severity") == "error" for item in findings):
            status = "passed"
            streaks = next_streaks
            break
        repair_phase = "skill_patching" if any(item.get("stop_category") == "needs_skill_patch" for item in findings) else "repairing"
        repairing_state = _build_state(
            work_dir=work_dir,
            product_name=args.product_name,
            format_name=args.format,
            max_rounds=args.max_rounds,
            max_parallel=max_parallel,
            vision_review=args.vision_review,
            status="running",
            phase=repair_phase,
            current_round=round_no,
            next_round=round_no + 1,
            rounds=rounds,
            streaks=next_streaks,
            latest_findings=final_findings,
            final_artifact=str(_artifact_for_report(args.format, final_report) or ""),
            failure_summary=failure_summary,
            repeated_failures=repeated_failures,
            last_unconverged_reason=_last_unconverged_reason(final_findings),
            stop_recommendation=_stop_recommendation(final_findings),
        )
        _write_status_files(state_path, execution_status_path, repairing_state, resume_source=resume_source)
        repair_report = _apply_repairs(args.format, work_dir, findings)
        last_repair_report = repair_report
        round_report["repair_report"] = repair_report
        _write_json(round_dir / "round_report.json", round_report)
        streaks = next_streaks
        repaired_state = _build_state(
            work_dir=work_dir,
            product_name=args.product_name,
            format_name=args.format,
            max_rounds=args.max_rounds,
            max_parallel=max_parallel,
            vision_review=args.vision_review,
            status="running",
            phase="round_repaired",
            current_round=round_no,
            next_round=round_no + 1,
            rounds=rounds,
            streaks=streaks,
            latest_findings=final_findings,
            final_artifact=str(_artifact_for_report(args.format, final_report) or ""),
            blocked_findings=repair_report.get("blocked_findings", []),
            failure_summary=failure_summary,
            attempted_fix_scopes=repair_report.get("attempted_fix_scopes", []),
            repeated_failures=repeated_failures,
            last_unconverged_reason=_last_unconverged_reason(final_findings, repair_report),
            stop_recommendation=_stop_recommendation(final_findings, repair_report),
        )
        _write_status_files(state_path, execution_status_path, repaired_state, resume_source=resume_source)
        rounds[-1]["repair_actions"] = repair_report.get("executed_actions", rounds[-1].get("repair_actions", []))
        if repair_report.get("status") == "blocked":
            status = "failed"
            final_findings = repair_report.get("blocked_findings", []) or final_findings
            break

    final_state = _build_state(
        work_dir=work_dir,
        product_name=args.product_name,
        format_name=args.format,
        max_rounds=args.max_rounds,
        max_parallel=max_parallel,
        vision_review=args.vision_review,
        status=status,
        phase=FINAL_PHASE,
        current_round=rounds[-1]["round"] if rounds else 0,
        next_round=(rounds[-1]["round"] + 1) if rounds else start_round,
        rounds=rounds,
        streaks=streaks,
        latest_findings=final_findings,
        final_artifact=str(_artifact_for_report(args.format, final_report) or ""),
        blocked_findings=[finding for finding in final_findings if finding.get("severity") == "error"],
        failure_summary=_failure_summary(final_findings),
        repeated_failures=_repeated_failures(final_findings, streaks),
        last_unconverged_reason=_last_unconverged_reason(final_findings, last_repair_report),
        stop_recommendation=_stop_recommendation(final_findings, last_repair_report),
    )
    _write_status_files(state_path, execution_status_path, final_state, resume_source=resume_source)
    _emit_payload(
        _final_payload(
            state_path=state_path,
            status=status,
            rounds=rounds,
            final_report=final_report,
            blocked_findings=final_state["blocked_findings"],
            resumed=resumed,
            resume_from_phase=resume_from_phase,
            resume_from_round=resume_from_round,
        ),
        0 if status == "passed" else 1,
    )


if __name__ == "__main__":
    main()
