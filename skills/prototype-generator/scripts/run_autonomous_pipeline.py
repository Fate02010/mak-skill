#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from autofix import repair_drawio_page_models, repair_html_page_specs
from review_finding import make_finding


ESCALATION_MAP = {
    "html_render": "page_spec",
    "render_merge": "page_spec",
    "page_spec": "page_model",
    "page_model": "requirements",
}


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
    if "PROTOTYPE_GENERATOR_VISION_REVIEW_CMD" in __import__("os").environ:
        env_command = __import__("os").environ["PROTOTYPE_GENERATOR_VISION_REVIEW_CMD"]
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


def _apply_repairs(format_name: str, work_dir: Path, findings: list[dict]) -> list[dict]:
    requirements_dir = work_dir / "requirements"
    artifact_dir = work_dir / ".prototype-generator"
    if format_name == "drawio":
        return repair_drawio_page_models(requirements_dir, artifact_dir / "page_models", findings)
    return repair_html_page_specs(requirements_dir, artifact_dir / "page_specs", findings)


def main():
    parser = argparse.ArgumentParser(description="运行 prototype-generator 自治闭环主控器")
    parser.add_argument("work_dir")
    parser.add_argument("product_name")
    parser.add_argument("--format", choices=["drawio", "html"], required=True)
    parser.add_argument("--max-rounds", type=int, default=5)
    parser.add_argument("--max-parallel", type=int, default=3)
    parser.add_argument("--vision-review", choices=["auto", "off", "required"], default="auto")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    work_dir = Path(args.work_dir).resolve()
    artifact_dir = work_dir / ".prototype-generator"
    rounds_dir = artifact_dir / "rounds"
    rounds_dir.mkdir(parents=True, exist_ok=True)
    state_path = artifact_dir / "autoloop_state.json"

    streaks: dict[str, int] = {}
    rounds = []
    final_report = {}
    final_findings: list[dict] = []
    status = "failed"
    for round_no in range(1, max(1, args.max_rounds) + 1):
        round_dir = rounds_dir / f"round_{round_no:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        pipeline_report = _run_pipeline(args.format, work_dir, args.product_name, max_parallel=max(1, min(args.max_parallel, 3)))
        artifact_path = _artifact_for_report(args.format, pipeline_report)
        vision_review = _run_vision_review(args.vision_review, artifact_path, args.format) if artifact_path and artifact_path.exists() else {"status": "skipped", "mode": args.vision_review, "findings": []}
        findings = list(pipeline_report.get("review_findings", [])) + list(vision_review.get("findings", []))
        escalations = []
        next_streaks = {}
        for finding in findings:
            key = finding.get("stagnation_key") or f"{finding.get('repair_target')}::{finding.get('rule')}::{finding.get('page_or_sheet') or 'all'}"
            streak = streaks.get(key, 0) + 1
            if streak >= 2:
                escalated_target = ESCALATION_MAP.get(finding.get("repair_target", ""), finding.get("repair_target", ""))
                if escalated_target != finding.get("repair_target", ""):
                    finding["repair_target"] = escalated_target
                    finding["stagnation_key"] = f"{escalated_target}::{finding.get('rule')}::{finding.get('page_or_sheet') or 'all'}"
                    escalations.append({"finding": finding.get("id", key), "repair_target": escalated_target})
                    key = finding["stagnation_key"]
                    streak = 1
            next_streaks[key] = streak
        round_report = {
            "round": round_no,
            "pipeline_report": pipeline_report,
            "vision_review": vision_review,
            "finding_count": len(findings),
            "escalations": escalations,
        }
        (round_dir / "pipeline_report.json").write_text(json.dumps(pipeline_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (round_dir / "round_report.json").write_text(json.dumps(round_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rounds.append({"round": round_no, "finding_count": len(findings), "escalations": escalations, "summary": pipeline_report.get("summary", {})})
        final_report = pipeline_report
        final_findings = findings
        state_payload = {
            "work_dir": str(work_dir),
            "product_name": args.product_name,
            "format": args.format,
            "max_rounds": args.max_rounds,
            "vision_review": args.vision_review,
            "status": "running",
            "rounds": rounds,
            "latest_findings": findings,
        }
        state_path.write_text(json.dumps(state_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if pipeline_report.get("summary", {}).get("fail", 0) == 0 and not any(item.get("severity") == "error" for item in findings):
            status = "passed"
            break
        _apply_repairs(args.format, work_dir, findings)
        streaks = next_streaks

    final_state = {
        "work_dir": str(work_dir),
        "product_name": args.product_name,
        "format": args.format,
        "max_rounds": args.max_rounds,
        "vision_review": args.vision_review,
        "status": status,
        "rounds": rounds,
        "blocked_findings": [finding for finding in final_findings if finding.get("severity") == "error"],
        "final_artifact": str(_artifact_for_report(args.format, final_report) or ""),
    }
    state_path.write_text(json.dumps(final_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = {"state_path": str(state_path), "status": status, "rounds": rounds, "final_report": final_report, "blocked_findings": final_state["blocked_findings"]}
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if status == "passed" else 1)


if __name__ == "__main__":
    main()
