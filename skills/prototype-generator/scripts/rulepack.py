#!/usr/bin/env python3
"""
rulepack.py - prototype-generator 规则包加载与自动识别。

目标：
    - 将行业 alias / 语义门禁 / 动作期望 / merge 规则从脚本中抽离
    - 支持 base + industry + project override 的叠加
    - 支持从 requirements 或 page_model 自动识别规则包
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
RULES_DIR = SKILL_DIR / "rules"

RULEPACK_FIELDS = {
    "module_aliases": dict,
    "page_aliases": dict,
    "action_aliases": dict,
    "merge_name_rules": dict,
    "semantic_profiles": dict,
    "action_expectations": list,
    "detection_keywords": list,
    "page_classification_rules": list,
    "layout_constraints": list,
    "forbidden_tokens": list,
    "required_tokens": list,
}


def normalize_token(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or "")).strip().lower()
    text = text.replace("（后台）", "").replace("(后台)", "")
    text = text.replace("页面", "").replace("页", "")
    text = text.replace("新增/编辑", "编辑")
    text = text.replace("删除确认弹窗", "删除确认")
    text = text.replace("新增/编辑弹窗", "编辑弹窗")
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)
    return text


def _empty_rulepack(name: str = "base") -> dict[str, Any]:
    return {
        "name": name,
        "module_aliases": {},
        "page_aliases": {},
        "action_aliases": {},
        "merge_name_rules": {},
        "semantic_profiles": {},
        "action_expectations": [],
        "detection_keywords": [],
        "page_classification_rules": [],
        "layout_constraints": [],
        "forbidden_tokens": [],
        "required_tokens": [],
    }


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_rulepack(raw: dict[str, Any], fallback_name: str) -> dict[str, Any]:
    pack = _empty_rulepack(str(raw.get("name", fallback_name) or fallback_name))
    for field, field_type in RULEPACK_FIELDS.items():
        value = raw.get(field)
        if isinstance(value, field_type):
            pack[field] = value
    return pack


def merge_rulepacks(*packs: dict[str, Any]) -> dict[str, Any]:
    merged = _empty_rulepack("base")
    merged["loaded_packs"] = []
    for pack in packs:
        if not pack:
            continue
        merged["loaded_packs"].append(pack.get("name", "unknown"))
        for field, field_type in RULEPACK_FIELDS.items():
            value = pack.get(field)
            if field_type is dict and isinstance(value, dict):
                merged[field].update(value)
            elif field_type is list and isinstance(value, list):
                merged[field].extend(value)
    if merged["loaded_packs"]:
        merged["name"] = merged["loaded_packs"][-1]
    return merged


def load_rulepack(name: str) -> dict[str, Any]:
    path = RULES_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"rulepack 不存在: {name}")
    return _normalize_rulepack(_read_json(path), name)


def load_override_rulepack(path: str | os.PathLike[str]) -> dict[str, Any]:
    override_path = Path(path)
    if not override_path.is_file():
        raise FileNotFoundError(f"rulepack override 不存在: {override_path}")
    return _normalize_rulepack(_read_json(override_path), "override")


def available_rulepacks() -> list[str]:
    names = []
    if RULES_DIR.is_dir():
        for file in sorted(RULES_DIR.glob("*.json")):
            names.append(file.stem)
    return names


def canonical_action_name(value: str, rulepack: dict[str, Any] | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    aliases = (rulepack or {}).get("action_aliases", {})
    canonical = aliases.get(text)
    if canonical:
        return str(canonical).strip()
    normalized = normalize_token(text)
    for key, mapped in aliases.items():
        if normalize_token(key) == normalized:
            return str(mapped).strip()
    return text


def canonical_page_name(value: str, rulepack: dict[str, Any] | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    aliases = (rulepack or {}).get("page_aliases", {})
    canonical = aliases.get(text)
    if canonical:
        return str(canonical).strip()
    normalized = normalize_token(text)
    for key, mapped in aliases.items():
        if normalize_token(key) == normalized:
            return str(mapped).strip()
    return text


def normalize_module_name(value: str, rulepack: dict[str, Any] | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"^(page[_-]?spec|spec|tmp)\s*[:：_-]?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", "", text)
    aliases = (rulepack or {}).get("module_aliases", {})
    if text in aliases:
        return str(aliases[text]).strip()
    normalized = normalize_token(text)
    for key, mapped in aliases.items():
        if normalize_token(key) == normalized:
            return str(mapped).strip()
    return text


def _collect_texts_from_model(model: dict[str, Any]) -> str:
    parts: list[str] = []
    if not isinstance(model, dict):
        return ""
    for key in ("product_name", "module_name", "module_key"):
        parts.append(str(model.get(key, "")).strip())
    pages = model.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if not isinstance(page, dict):
                continue
            for key in ("page_name", "page_type", "object_name", "purpose", "nav_context"):
                parts.append(str(page.get(key, "")).strip())
            for row in page.get("fields", []):
                if isinstance(row, dict):
                    parts.append(str(row.get("name", "")).strip())
            for value in page.get("table_columns", []):
                parts.append(str(value).strip())
            for action in page.get("actions", []):
                if isinstance(action, dict):
                    parts.append(str(action.get("name", "")).strip())
    return "\n".join(part for part in parts if part)


def _collect_texts_from_work_dir(work_dir: str | os.PathLike[str]) -> str:
    root = Path(work_dir)
    requirements_dir = root / "requirements"
    if not requirements_dir.is_dir():
        return ""
    parts: list[str] = []
    preferred = [
        requirements_dir / "index.md",
        requirements_dir / "详细需求文档_overview.md",
    ]
    for path in preferred:
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))
    briefs_dir = requirements_dir / "module_briefs"
    if briefs_dir.is_dir():
        for path in sorted(briefs_dir.glob("*.md")):
            parts.append(path.read_text(encoding="utf-8"))
    if not parts:
        for path in sorted(requirements_dir.glob("*.md")):
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _score_text_for_pack(text: str, pack: dict[str, Any]) -> int:
    lowered = str(text or "").lower()
    score = 0
    for keyword in pack.get("detection_keywords", []):
        token = str(keyword or "").strip().lower()
        if not token:
            continue
        score += lowered.count(token)
    return score


def detect_rulepack_name_from_text(text: str) -> tuple[str, dict[str, int]]:
    scores: dict[str, int] = {}
    for name in available_rulepacks():
        if name == "base":
            continue
        pack = load_rulepack(name)
        scores[name] = _score_text_for_pack(text, pack)
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ordered or ordered[0][1] <= 0:
        return "base", scores
    top_name, top_score = ordered[0]
    second_score = ordered[1][1] if len(ordered) > 1 else 0
    if top_score <= 0:
        return "base", scores
    if second_score > 0 and (top_score - second_score) / float(top_score) < 0.2:
        return "base", scores
    return top_name, scores


def detect_rulepack_name_for_model(model: dict[str, Any]) -> tuple[str, dict[str, int]]:
    return detect_rulepack_name_from_text(_collect_texts_from_model(model))


def detect_rulepack_name_for_work_dir(work_dir: str | os.PathLike[str]) -> tuple[str, dict[str, int]]:
    return detect_rulepack_name_from_text(_collect_texts_from_work_dir(work_dir))


def resolve_effective_rulepack(
    *,
    explicit_name: str | None = None,
    work_dir: str | os.PathLike[str] | None = None,
    model: dict[str, Any] | None = None,
    override_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    detected_name = "base"
    score_breakdown: dict[str, int] = {}
    if explicit_name:
        detected_name = explicit_name
    elif work_dir:
        detected_name, score_breakdown = detect_rulepack_name_for_work_dir(work_dir)
    elif model:
        detected_name, score_breakdown = detect_rulepack_name_for_model(model)

    base_pack = load_rulepack("base")
    packs = [base_pack]
    if detected_name and detected_name != "base":
        packs.append(load_rulepack(detected_name))

    resolved_override_path = None
    if override_path:
        resolved_override_path = Path(override_path)
    elif work_dir:
        candidate = Path(work_dir) / ".prototype-generator" / "rulepack.override.json"
        if candidate.is_file():
            resolved_override_path = candidate
    if resolved_override_path:
        packs.append(load_override_rulepack(resolved_override_path))

    effective = merge_rulepacks(*packs)
    effective["detected_pack"] = detected_name
    effective["score_breakdown"] = score_breakdown
    effective["override_source"] = str(resolved_override_path) if resolved_override_path else ""
    effective["effective_packs"] = effective.get("loaded_packs", [])
    return effective


def build_active_rulepack_metadata(rulepack: dict[str, Any]) -> dict[str, Any]:
    return {
        "detected_pack": rulepack.get("detected_pack", "base"),
        "effective_packs": rulepack.get("effective_packs", ["base"]),
        "score_breakdown": rulepack.get("score_breakdown", {}),
        "override_source": rulepack.get("override_source", ""),
    }
