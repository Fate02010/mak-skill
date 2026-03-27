#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from html_utils import parse_page_spec, to_markdown
from requirements_utils import infer_page_shape, infer_terminal_type_from_module, safe_slug


VISUAL_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".pdf", ".drawio", ".html"}
IGNORED_TOP_LEVEL = {".prototype-generator", "requirements", "prototypes", ".git", "__pycache__"}
BLOCKED_SOURCE_PARTS = {"prototypes-html"}


def ensure_reference_pack(work_dir: str | Path) -> dict:
    root = Path(work_dir).resolve()
    artifact_dir = root / ".prototype-generator"
    page_specs_dir = artifact_dir / "page_specs"
    reference_dir = artifact_dir / "reference_pack"
    reference_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "generated_at": _utc_now(),
        "work_dir": str(root),
        "reference_pack_dir": str(reference_dir),
        "search_backend_configured": bool(os.environ.get("PROTOTYPE_GENERATOR_REFERENCE_SEARCH_CMD")),
        "allowed_sources": [],
        "blocked_sources": [],
        "policy_violations": [],
        "pages": [],
        "modules": [],
    }
    entries_by_module: dict[str, list[dict]] = {}
    source_scan = _collect_source_files(root)
    source_files = source_scan["allowed"]
    manifest["allowed_sources"] = [str(path) for path in source_files]
    manifest["blocked_sources"] = [str(path) for path in source_scan["blocked"]]
    manifest["policy_violations"] = [
        {"path": str(path), "reason": "引用了禁用来源目录"}
        for path in source_scan["blocked"]
    ]

    for spec_path in sorted(page_specs_dir.glob("page_spec_*.md")):
        spec = parse_page_spec(spec_path)
        module_entries: list[dict] = []
        module_key = spec.get("module_key") or safe_slug(spec.get("module_name", ""), "module")
        module_summary_path = reference_dir / f"references_{module_key}.md"
        for page in spec.get("pages", []):
            entry = _build_reference_entry(root, spec, page, source_files, module_summary_path)
            manifest["pages"].append(entry)
            module_entries.append(entry)
        module_summary_path.write_text(_module_summary_markdown(spec, module_entries), encoding="utf-8")
        manifest["modules"].append(
            {
                "module_name": spec.get("module_name", ""),
                "module_key": module_key,
                "summary_file": str(module_summary_path),
                "page_count": len(module_entries),
            }
        )
        entries_by_module[module_key] = module_entries

    (reference_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_reference_pack(work_dir: str | Path) -> dict:
    manifest_path = Path(work_dir).resolve() / ".prototype-generator" / "reference_pack" / "manifest.json"
    if not manifest_path.exists():
        return {"pages": [], "modules": [], "allowed_sources": [], "blocked_sources": [], "policy_violations": []}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def enrich_page_spec_file(spec_path: str | Path, manifest: dict) -> dict:
    path = Path(spec_path)
    spec = parse_page_spec(path)
    enriched = enrich_spec(spec, manifest)
    serialized = to_markdown(enriched)
    if path.read_text(encoding="utf-8") != serialized:
        path.write_text(serialized, encoding="utf-8")
    return enriched


def enrich_spec(spec: dict, manifest: dict) -> dict:
    enriched = copy.deepcopy(spec)
    page_map = {
        (item.get("module_name", ""), item.get("page_name", "")): item
        for item in manifest.get("pages", [])
    }
    module_fallback = {
        item.get("module_key", ""): item.get("summary_file", "")
        for item in manifest.get("modules", [])
    }
    for page in enriched.get("pages", []):
        page_name = page.get("page_name", "")
        module_name = enriched.get("module_name", "")
        entry = page_map.get((module_name, page_name), {})
        inferred_archetype = infer_page_shape(page_name)[1]
        page["page_archetype"] = page.get("page_archetype") or entry.get("page_archetype") or inferred_archetype
        page["reference_basis"] = entry.get("reference_basis", page.get("reference_basis", "fallback"))
        page["reference_summary"] = entry.get("reference_summary", page.get("reference_summary", ""))
        page["reference_sources"] = entry.get("reference_sources", page.get("reference_sources", []))
        page["layout_directives"] = entry.get("layout_directives", page.get("layout_directives", []))
        page["visual_cues"] = entry.get("visual_cues", page.get("visual_cues", []))
        page["interaction_patterns"] = entry.get("interaction_patterns", page.get("interaction_patterns", []))
        page["reference_pack_file"] = entry.get(
            "summary_file",
            page.get("reference_pack_file", module_fallback.get(enriched.get("module_key", ""), "")),
        )
    return enriched


def _build_reference_entry(root: Path, spec: dict, page: dict, source_files: list[Path], module_summary_path: Path) -> dict:
    module_name = spec.get("module_name", "")
    module_key = spec.get("module_key") or safe_slug(module_name, "module")
    page_name = page.get("page_name", "")
    page_type = page.get("page_type", "web_detail")
    page_archetype = page.get("page_archetype") or infer_page_shape(page_name)[1]
    local_refs = _match_local_references(page_name, module_name, source_files)
    external_refs: list[dict] = []
    query = _default_query(module_name, page_name, page_archetype)
    if not local_refs:
        external_refs = _search_external_references(
            {
                "work_dir": str(root),
                "module_name": module_name,
                "module_key": module_key,
                "page_name": page_name,
                "page_type": page_type,
                "page_archetype": page_archetype,
                "query": query,
            }
        )
    reference_basis = "internal" if local_refs else "external" if external_refs else "fallback"
    summary = _reference_summary(page_name, page_archetype, reference_basis, local_refs, external_refs)
    return {
        "module_name": module_name,
        "module_key": module_key,
        "page_name": page_name,
        "page_type": page_type,
        "page_archetype": page_archetype,
        "reference_basis": reference_basis,
        "reference_summary": summary,
        "reference_sources": _format_reference_sources(local_refs, external_refs),
        "layout_directives": _layout_directives(page_archetype, page_type),
        "visual_cues": _visual_cues(page_archetype, page_type),
        "interaction_patterns": _interaction_patterns(page_archetype, page),
        "summary_file": str(module_summary_path),
        "query": query,
    }


def _collect_source_files(root: Path) -> dict[str, list[Path]]:
    allowed: list[Path] = []
    blocked: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_TOP_LEVEL for part in path.relative_to(root).parts[:1]):
            continue
        if path.suffix.lower() not in VISUAL_SUFFIXES:
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in BLOCKED_SOURCE_PARTS for part in relative_parts):
            blocked.append(path)
            continue
        allowed.append(path)
    return {"allowed": allowed, "blocked": blocked}


def _match_local_references(page_name: str, module_name: str, files: list[Path]) -> list[str]:
    tokens = _keywords(page_name) | _keywords(module_name)
    matches: list[str] = []
    for path in files:
        name = path.name.lower()
        if any(token.lower() in name for token in tokens if token):
            matches.append(str(path))
        if len(matches) >= 4:
            break
    return matches


def _keywords(text: str) -> set[str]:
    raw = str(text or "").replace("-", " ").replace("_", " ").strip()
    keywords = {raw} if raw else set()
    for chunk in raw.split():
        if len(chunk) >= 2:
            keywords.add(chunk)
    for token in ("页面", "管理", "模块", "后台", "小程序", "App", "H5", "官网", "门户", "系统"):
        keywords.discard(token)
    return {item for item in keywords if item}


def _default_query(module_name: str, page_name: str, page_archetype: str) -> str:
    terminal_name = infer_terminal_type_from_module(module_name)[1]
    return f"{terminal_name} {page_name} {page_archetype} 竞品 行业案例"


def _search_external_references(payload: dict) -> list[dict]:
    command = os.environ.get("PROTOTYPE_GENERATOR_REFERENCE_SEARCH_CMD")
    if not command:
        return []
    completed = subprocess.run(
        shlex.split(command),
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(result, dict):
        items = result.get("references", [])
    elif isinstance(result, list):
        items = result
    else:
        items = []
    normalized: list[dict] = []
    for item in items[:4]:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "title": str(item.get("title", "")).strip() or "外部参考",
                "url": str(item.get("url", "")).strip(),
                "summary": str(item.get("summary", "")).strip(),
                "source": str(item.get("source", "")).strip() or "external",
            }
        )
    return normalized


def _format_reference_sources(local_refs: list[str], external_refs: list[dict]) -> list[str]:
    sources = [f"内部参考：{path}" for path in local_refs]
    sources.extend(
        f"外部参考：{item.get('title', '')} {item.get('url', '')}".strip()
        for item in external_refs
    )
    return sources


def _reference_summary(page_name: str, page_archetype: str, reference_basis: str, local_refs: list[str], external_refs: list[dict]) -> str:
    if reference_basis == "internal":
        return f"{page_name} 优先对齐内部资料中的视觉样式与结构，当前使用 {len(local_refs)} 份本地参考。"
    if reference_basis == "external":
        titles = " / ".join(item.get("title", "") for item in external_refs[:2])
        return f"{page_name} 缺少内部参照，已补充检索行业案例：{titles}，用于约束 {page_archetype} 的布局与视觉层级。"
    return f"{page_name} 未找到可复用参照，按 {page_archetype} 的高保真默认骨架生成，并保留显式布局指令。"


def _layout_directives(page_archetype: str, page_type: str) -> list[str]:
    directives = {
        "list_table": [
            "采用标题区 + 摘要卡 + 筛选区 + 主表格 + 右侧说明区的双列布局。",
            "主操作按钮固定在标题区右侧，筛选区控制项不超过四个。",
            "表格展示至少三行差异化数据，并保留分页和状态标签。",
        ],
        "detail_kv": [
            "顶部先展示状态摘要和关键操作，再展示键值信息区与跟进记录区。",
            "主信息区使用双列键值布局，右侧保留时间线或规则说明卡。",
        ],
        "modal_form": [
            "表单采用分组卡片布局，每组字段保持 2 列以内，底部固定操作栏。",
            "重要字段和校验提示放在首屏，次要配置放在后续分组卡片。",
        ],
        "form_page": [
            "表单采用分组卡片布局，每组字段保持 2 列以内，底部固定操作栏。",
            "重要字段和校验提示放在首屏，次要配置放在后续分组卡片。",
        ],
        "dashboard": [
            "顶部先给出核心指标卡和状态摘要，中部是主分析面板，右侧是待办与预警。",
            "避免纯文档式堆叠，主面板占据页面最大面积。",
        ],
        "mobile_home": [
            "首屏采用欢迎区 + 核心指标 + 快捷入口 + 内容流的顺序。",
            "底部保留 TabBar，核心 CTA 置于首屏可见区域。",
        ],
        "portal_landing": [
            "官网首页采用 Hero 主视觉 + 核心能力卡片 + 场景区块 + CTA 的顺序。",
            "首屏要有品牌标题、说明文案和主按钮，避免后台式表格骨架。",
        ],
        "login": [
            "登录页采用品牌信息区与登录卡片的双栏布局，不出现业务侧边栏。",
            "输入区聚焦账号、密码和主按钮，辅助链接位于卡片底部。",
        ],
    }
    return directives.get(page_archetype, directives.get("detail_kv", []))


def _visual_cues(page_archetype: str, page_type: str) -> list[str]:
    cues = {
        "list_table": [
            "使用 2-3 个摘要卡增强首屏层级，主色按钮只保留 1 个。",
            "状态字段使用 success / warning / danger 三类标签色。",
        ],
        "detail_kv": [
            "摘要状态卡使用浅色底与重点数字，详情区保持键值对对齐。",
            "主要操作和危险操作视觉区分明显，避免全部同权。",
        ],
        "modal_form": [
            "首屏分组卡标题突出，必填字段带显式星标。",
            "提交按钮使用主色实心，取消使用描边样式。",
        ],
        "form_page": [
            "首屏分组卡标题突出，必填字段带显式星标。",
            "提交按钮使用主色实心，取消使用描边样式。",
        ],
        "dashboard": [
            "指标卡使用深浅对比和数字放大，主分析面板保持深色或强对比容器。",
            "预警和异常信息使用 warning / danger 色强调。",
        ],
        "mobile_home": [
            "首页使用渐变欢迎区与圆角卡片，快捷入口以 4 列宫格出现。",
            "主 CTA 采用整宽按钮或强调色卡片入口。",
        ],
        "portal_landing": [
            "首屏需要大标题、说明文案和主视觉插槽，避免纯文字。",
            "能力卡片和场景卡片使用不同背景层次区分。",
        ],
        "login": [
            "品牌说明区使用渐变背景，登录卡片保持纯白高对比。",
            "主按钮宽度铺满卡片，输入框间距统一。",
        ],
    }
    return cues.get(page_archetype, ["主操作使用主色按钮突出，内容卡片保留层级和阴影。"])


def _interaction_patterns(page_archetype: str, page: dict) -> list[str]:
    actions = " ".join(page.get("actions", []))
    patterns: list[str] = []
    if page_archetype == "list_table":
        patterns.extend(["筛选 + 查询/重置", "表格行操作", "分页切换"])
        if "新增" in actions or "编辑" in actions:
            patterns.append("新增/编辑入口")
        if "删除" in actions:
            patterns.append("删除确认弹窗")
    elif page_archetype in {"form_page", "modal_form"}:
        patterns.extend(["表单校验", "提交后反馈", "取消返回"])
    elif page_archetype == "detail_kv":
        patterns.extend(["状态摘要", "详情键值区", "记录时间线"])
    elif page_archetype in {"dashboard", "mobile_home", "portal_landing"}:
        patterns.extend(["指标概览", "快捷入口", "内容区块切换"])
    elif page_archetype == "login":
        patterns.extend(["账号密码输入", "主按钮提交", "辅助入口"])
    else:
        patterns.append("主流程闭环")
    return patterns


def _module_summary_markdown(spec: dict, entries: list[dict]) -> str:
    lines = [
        f"# {spec.get('module_name', '')} 参考包",
        "",
        f"- 模块英文名：{spec.get('module_key', '')}",
        f"- 页面数：{len(entries)}",
        "",
    ]
    for item in entries:
        lines.extend(
            [
                f"## {item.get('page_name', '')}",
                f"- 页面类型：{item.get('page_type', '')}",
                f"- 页面原型：{item.get('page_archetype', '')}",
                f"- 参考来源：{item.get('reference_basis', '')}",
                f"- 参考摘要：{item.get('reference_summary', '')}",
                "",
                "### 布局指令",
            ]
        )
        for directive in item.get("layout_directives", []):
            lines.append(f"- {directive}")
        lines.extend(["", "### 视觉线索"])
        for cue in item.get("visual_cues", []):
            lines.append(f"- {cue}")
        lines.extend(["", "### 交互模式"])
        for pattern in item.get("interaction_patterns", []):
            lines.append(f"- {pattern}")
        lines.extend(["", "### 参考来源"])
        for source in item.get("reference_sources", []):
            lines.append(f"- {source}")
        lines.append("")
    return "\n".join(lines)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
