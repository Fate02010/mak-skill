#!/usr/bin/env python3
"""
build_page_spec.py - 从 page_model JSON 生成标准化 page_spec markdown。

用法:
    python3 build_page_spec.py <page_model_json> <output_page_spec_md>

page_model 采用强约束 JSON，示例:
{
  "terminal_type": "admin",
  "terminal_name": "后台",
  "module_name": "后台-用户管理",
  "module_key": "user",
  "pages": [
    {
      "page_id": "user_list",
      "page_name": "用户列表",
      "page_type": "web_list",
      "object_name": "用户",
      "role": "运营管理员",
      "purpose": "查询并维护用户",
      "is_nav_page": false,
      "needs_crud": true,
      "fields": [
        {"name": "用户名", "control": "input", "required": true, "validation": "2-20位"},
        {"name": "手机号", "control": "input", "required": false, "validation": "手机号格式"}
      ],
      "table_columns": ["用户名", "手机号", "状态", "创建时间"],
      "status_values": ["启用", "停用", "待审核"],
      "actions": [
        {"name": "查看详情", "target": "用户详情", "kind": "secondary"}
      ],
      "jump_targets": ["用户详情", "新增/编辑用户弹窗", "删除确认弹窗"]
    }
  ]
}
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rulepack as RULEPACK


GRID = 8
SWIMLANE_GAP = 40
START_X = 16
START_Y = 16

MOBILE_UI_W = 376
MOBILE_ANN_X = 400
MOBILE_ANN_W = 176
MOBILE_SWIMLANE_W = 592
MOBILE_SWIMLANE_H = 856

WEB_UI_W = 1440
WEB_ANN_X = 1464
WEB_ANN_W = 216
WEB_SWIMLANE_W = 1680
WEB_SWIMLANE_H = 960

BIGSCREEN_UI_W = 1920
BIGSCREEN_ANN_X = 1944
BIGSCREEN_ANN_W = 240
BIGSCREEN_SWIMLANE_W = 2208
BIGSCREEN_SWIMLANE_H = 1120

INDUSTRIAL_UI_W = 1368
INDUSTRIAL_ANN_X = 1392
INDUSTRIAL_ANN_W = 216
INDUSTRIAL_SWIMLANE_W = 1608
INDUSTRIAL_SWIMLANE_H = 960

ALLOWED_PAGE_TYPES = {
    "web_list",
    "mobile_list",
    "web_form",
    "mobile_form",
    "mobile_detail",
    "web_detail",
    "login",
    "dashboard",
    "mobile_home",
    "profile",
    "portal_home",
    "portal_content",
    "portal_hub",
    "bigscreen_dashboard",
    "industrial_console",
}

ALLOWED_ARCHETYPES = {
    "dashboard",
    "list_table",
    "detail_kv",
    "form_page",
    "modal_form",
    "drawer_permission",
    "dispatch_board",
    "tree_manage",
    "content_manage",
    "audit_log",
    "mobile_home",
    "profile",
    "login",
    "portal_landing",
    "portal_content",
    "portal_hub",
    "bigscreen_board",
    "industrial_hmi",
}

ALLOWED_PAGE_KINDS = {
    "list",
    "detail",
    "form_modal",
    "confirm_modal",
    "tree_list",
    "login",
    "dashboard",
    "landing",
    "content",
    "hub",
    "console",
    "monitor",
}

ALLOWED_LAYOUT_MODES = {
    "web",
    "mobile",
    "modal",
    "tree",
    "drawer",
    "login",
    "h5",
    "portal",
    "bigscreen",
    "industrial",
}

ALLOWED_TERMINAL_TYPES = {
    "admin",
    "miniapp",
    "app",
    "h5",
    "bigscreen",
    "portal",
    "industrial",
}

TERMINAL_NAME_BY_TYPE = {
    "admin": "后台",
    "miniapp": "小程序",
    "app": "App",
    "h5": "H5",
    "bigscreen": "大屏",
    "portal": "官网门户",
    "industrial": "工控机",
}

PLATFORM_DIMENSIONS = {
    "mobile": (MOBILE_UI_W, MOBILE_ANN_X, MOBILE_ANN_W),
    "web": (WEB_UI_W, WEB_ANN_X, WEB_ANN_W),
    "bigscreen": (BIGSCREEN_UI_W, BIGSCREEN_ANN_X, BIGSCREEN_ANN_W),
    "industrial": (INDUSTRIAL_UI_W, INDUSTRIAL_ANN_X, INDUSTRIAL_ANN_W),
}


def snap8(value: int) -> int:
    if value == 1:
        return 1
    snapped = int(round(value / GRID) * GRID)
    return snapped if snapped > 0 else GRID


def as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "是"}
    return bool(value)


def normalize_list(values) -> list[str]:
    if not values:
        return []
    if isinstance(values, list):
        return [str(v).strip() for v in values if str(v).strip()]
    return [str(values).strip()] if str(values).strip() else []


def first_non_empty(*values) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def tag_style_for_status(text: str) -> str:
    value = text.strip()
    if not value:
        return "tag_default"
    if any(token in value for token in ("成功", "完成", "启用", "已支付", "通过", "正常")):
        return "tag_success"
    if any(token in value for token in ("待", "处理中", "审核中", "排队")):
        return "tag_pending"
    if any(token in value for token in ("停用", "失败", "驳回", "异常", "关闭", "删除")):
        return "tag_error"
    if any(token in value for token in ("告警", "提醒", "预警")):
        return "tag_warning"
    return "tag_info"


def placeholder_value(name: str, idx: int) -> str:
    text = name.strip()
    if any(token in text for token in ("金额", "价格", "费用")):
        return f"¥{idx * 128 + 99}"
    if "数量" in text:
        return str(idx + 1)
    if any(token in text for token in ("时间", "日期")):
        return f"2026-03-{idx + 10:02d} 10:00"
    if any(token in text for token in ("手机号", "电话")):
        return f"138000000{idx}"
    if any(token in text for token in ("编号", "编码")):
        return f"{text[:2]}-{20260300 + idx}"
    if any(token in text for token in ("状态", "类型")):
        return "已启用"
    return f"{text}示例{idx}"


def canonical_action_name(value: str, rulepack: dict | None = None) -> str:
    return RULEPACK.canonical_action_name(value, rulepack)


def action_names(page: dict) -> list[str]:
    values = []
    actions = page.get("actions")
    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, dict):
                continue
            name = canonical_action_name(action.get("name", ""), page.get("_rulepack"))
            if name:
                values.append(name)
    return values


def field_names(page: dict) -> list[str]:
    rows = page.get("fields")
    if not isinstance(rows, list):
        return []
    names = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        if name:
            names.append(name)
    return names


def table_column_names(page: dict) -> list[str]:
    return normalize_list(page.get("table_columns"))


def page_terms(model: dict, page: dict) -> str:
    parts = [
        str(model.get("module_name", "")).strip(),
        str(model.get("product_name", "")).strip(),
        str(page.get("page_name", "")).strip(),
        str(page.get("object_name", "")).strip(),
        str(page.get("purpose", "")).strip(),
        str(page.get("nav_context", "")).strip(),
    ]
    parts.extend(field_names(page))
    parts.extend(table_column_names(page))
    parts.extend(normalize_list(page.get("jump_targets")))
    return " ".join(part for part in parts if part)


def contains_any(values: list[str], candidates: tuple[str, ...] | set[str]) -> bool:
    return any(any(token in value for token in candidates) for value in values)


def count_matches(values: list[str], candidates: tuple[str, ...] | set[str]) -> int:
    return sum(1 for value in values if any(token in value for token in candidates))


def delete_modal_name(object_name: str) -> str:
    value = str(object_name or "").strip() or "对象"
    return f"删除{value}确认弹窗"


def enable_disable_label(page_name: str) -> str:
    text = str(page_name or "")
    if any(token in text for token in ("评论", "公告", "轮播")):
        return "下线"
    return "停用"


def normalize_terminal_type(value: str) -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "backend": "admin",
        "admin": "admin",
        "web_admin": "admin",
        "miniapp": "miniapp",
        "mini_app": "miniapp",
        "wechat_miniapp": "miniapp",
        "wechat-miniapp": "miniapp",
        "app": "app",
        "mobile_app": "app",
        "mobile-app": "app",
        "h5": "h5",
        "mobile_web": "h5",
        "mobile-web": "h5",
        "web_h5": "h5",
        "web-h5": "h5",
        "bigscreen": "bigscreen",
        "big_screen": "bigscreen",
        "big-screen": "bigscreen",
        "datav": "bigscreen",
        "portal": "portal",
        "official_site": "portal",
        "official-site": "portal",
        "website": "portal",
        "industrial": "industrial",
        "industrial_hmi": "industrial",
        "industrial-hmi": "industrial",
        "hmi": "industrial",
        "ipc": "industrial",
    }
    return aliases.get(text, text)


def expected_terminal_name(terminal_type: str) -> str:
    return TERMINAL_NAME_BY_TYPE.get(normalize_terminal_type(terminal_type), "")


def normalize_terminal_name(value: str, terminal_type: str = "") -> str:
    text = str(value or "").strip()
    if text:
        return text
    return expected_terminal_name(terminal_type)


def normalize_module_name(value: str, rulepack: dict | None = None) -> str:
    return RULEPACK.normalize_module_name(value, rulepack)


def invalid_module_name_reason(value: str, rulepack: dict | None = None) -> str:
    text = normalize_module_name(value, rulepack)
    raw = str(value or "").strip()
    if not text:
        return "module_name 为空"
    if re.search(r"(page[_-]?spec|spec|tmp)\s*[:：_-]?", raw, flags=re.IGNORECASE):
        return "module_name 含中间产物前缀"
    if text in {"APP系统", "后台管理", "小程序端", "移动端", "Web端", "前台", "官网门户", "大屏", "工控机", "工控机界面", "H5"}:
        return "module_name 仍是系统层命名"
    if re.match(r"^(后台|小程序|H5|APP|App|Web|移动端|大屏|官网门户|工控机)[-—].*[与和及/].+", text):
        return "module_name 同时包含终端前缀和多个业务域，应拆分"
    return ""


def module_business_name(module_name: str, terminal_name: str) -> str:
    text = str(module_name or "").strip()
    prefix = f"{terminal_name}-" if terminal_name else ""
    if prefix and text.startswith(prefix):
        return text[len(prefix):].strip() or text
    return text


def resolve_model_rulepack(model: dict, explicit_rulepack: str | None = None) -> dict:
    return RULEPACK.resolve_effective_rulepack(explicit_name=explicit_rulepack, model=model)


def _profile_matches(profile: dict, page_name: str, page_type: str, text: str, archetype: str) -> bool:
    if profile.get("page_name_contains_all") and not all(token in page_name for token in profile["page_name_contains_all"]):
        return False
    if profile.get("page_name_contains_any") and not any(token in page_name for token in profile["page_name_contains_any"]):
        return False
    if profile.get("text_contains_any") and not any(token in text for token in profile["text_contains_any"]):
        return False
    if profile.get("text_excludes_any") and any(token in text for token in profile["text_excludes_any"]):
        return False
    if profile.get("page_type_any") and page_type not in set(profile["page_type_any"]):
        return False
    if profile.get("required_archetypes") and archetype not in set(profile["required_archetypes"]):
        return False
    return True


def _count_matches(values: list[str], expected: list[str]) -> int:
    expected_set = set(expected)
    return sum(1 for item in values if item in expected_set)


def _semantic_error_from_profile(profile: dict, page: dict, text: str, names: list[str], actions: set[str], archetype: str) -> str:
    page_name = str(page.get("page_name", "")).strip()
    page_type = str(page.get("page_type", "")).strip()
    if not _profile_matches(profile, page_name, page_type, text, archetype):
        return ""

    messages = profile.get("messages", {})
    any_fields = profile.get("required_fields_any", [])
    any_min = int(profile.get("required_fields_any_min", 0) or 0)
    any_hits = _count_matches(names, any_fields) if any_fields else 0
    if any_fields and any_hits < any_min:
        return messages.get("required_any", "页面缺少核心字段")

    core_fields = profile.get("required_fields_core", [])
    core_min = int(profile.get("required_fields_core_min", 0) or 0)
    core_hits = _count_matches(names, core_fields) if core_fields else 0
    if core_fields and core_hits < core_min:
        return messages.get("required_core", "页面缺少核心字段")

    required_actions = set(profile.get("required_actions", []))
    required_actions_min = int(profile.get("required_actions_min", 0) or 0)
    if required_actions and len(actions.intersection(required_actions)) < required_actions_min:
        return messages.get("required_actions", "页面缺少核心动作")

    forbidden_fields = profile.get("forbidden_fields", [])
    forbidden_min = int(profile.get("forbidden_fields_min", 0) or 0)
    forbidden_hits = _count_matches(names, forbidden_fields) if forbidden_fields else 0
    forbidden_when_required_below = profile.get("forbidden_when_required_below")
    if forbidden_fields and forbidden_hits >= forbidden_min:
        if forbidden_when_required_below is None or any_hits < int(forbidden_when_required_below):
            return messages.get("forbidden", "页面混入不应出现的字段")

    alt_forbidden = profile.get("alt_forbidden_group", [])
    alt_forbidden_min = int(profile.get("alt_forbidden_group_min", 0) or 0)
    alt_required = profile.get("alt_required_group", [])
    alt_required_min = int(profile.get("alt_required_group_min", 0) or 0)
    if alt_forbidden and _count_matches(names, alt_forbidden) >= alt_forbidden_min and _count_matches(names, alt_required) < alt_required_min:
        return messages.get("alt_forbidden", "页面字段语义漂移")

    required_rules_any = profile.get("required_rules_any", [])
    required_rules_any_min = int(profile.get("required_rules_any_min", 0) or 0)
    if required_rules_any and _count_matches(normalize_list(page.get("business_rules")), required_rules_any) < required_rules_any_min:
        return messages.get("required_rules", "页面缺少业务规则提示")

    allowed_context_fields = profile.get("allowed_context_fields", [])
    allowed_context_fields_min = int(profile.get("allowed_context_fields_min", 0) or 0)
    if forbidden_fields and forbidden_hits >= forbidden_min and allowed_context_fields:
        if _count_matches(names, allowed_context_fields) < allowed_context_fields_min:
            return messages.get("forbidden", "页面混入不应出现的字段")

    return ""


@dataclass
class PageContext:
    swimlane_id: str
    page: dict
    platform: str
    swimlane_x: int
    swimlane_y: int
    swimlane_w: int
    swimlane_h: int

    @property
    def ui_w(self) -> int:
        return PLATFORM_DIMENSIONS[self.platform][0]

    @property
    def ann_x(self) -> int:
        return PLATFORM_DIMENSIONS[self.platform][1]

    @property
    def ann_w(self) -> int:
        return PLATFORM_DIMENSIONS[self.platform][2]


class PageSpecBuilder:
    def __init__(self, model: dict, rulepack: dict | None = None):
        self.model = model
        self.rulepack = rulepack or resolve_model_rulepack(model)
        self.module_name = normalize_module_name(model.get("module_name", "模块"), self.rulepack)
        self.terminal_type = normalize_terminal_type(model.get("terminal_type", ""))
        self.terminal_name = normalize_terminal_name(model.get("terminal_name", ""), self.terminal_type)
        self.business_module_name = module_business_name(self.module_name, self.terminal_name)
        self.swimlanes: list[dict[str, str]] = []
        self.elements: list[dict[str, str]] = []
        self.next_swimlane = 1
        self.current_x = START_X
        self.next_element_id_by_swimlane: dict[str, int] = {}

    def add_swimlane(self, label: str, lane_type: str, width: int, height: int, style_key: str) -> PageContext:
        swimlane_id = f"S{self.next_swimlane}"
        self.next_swimlane += 1
        x = self.current_x
        y = START_Y
        self.current_x = snap8(self.current_x + width + SWIMLANE_GAP)
        lane = {
            "swimlane_id": swimlane_id,
            "swimlane_label": label,
            "type": lane_type,
            "x": str(x),
            "y": str(y),
            "width": str(width),
            "height": str(height),
            "style_key": style_key,
        }
        self.swimlanes.append(lane)
        self.next_element_id_by_swimlane[swimlane_id] = 2
        platform = {
            "mobile": "mobile",
            "h5": "mobile",
            "web": "web",
            "portal": "web",
            "modal": "web",
            "bigscreen": "bigscreen",
            "industrial": "industrial",
        }.get(lane_type, "web")
        return PageContext(swimlane_id, {}, platform, x, y, width, height)

    def add_element(
        self,
        swimlane_id: str,
        component_type: str,
        value: str,
        x: int,
        y: int,
        width: int,
        height: int,
        style_key: str,
        tooltip: str = "",
    ) -> int:
        element_id = self.next_element_id_by_swimlane[swimlane_id]
        self.next_element_id_by_swimlane[swimlane_id] += 1
        self.elements.append(
            {
                "id": str(element_id),
                "parent_swimlane": swimlane_id,
                "component_type": component_type,
                "value": value,
                "x": str(snap8(x)),
                "y": str(snap8(y)),
                "width": str(snap8(width)),
                "height": str(snap8(height)),
                "style_key": style_key,
                "tooltip": tooltip,
            }
        )
        return element_id

    def build(self):
        pages = self.model.get("pages")
        if not isinstance(pages, list) or not pages:
            raise ValueError("page_model 缺少非空 pages 数组")

        for page in pages:
            self._build_page(page)

        return self.module_name, self.swimlanes, self.elements

    def _build_page(self, page: dict):
        page_type = str(page.get("page_type", "")).strip()
        if not page_type:
            raise ValueError("page_model 中存在缺少 page_type 的页面")

        archetype = self._page_archetype(page)
        is_modal_page = self._is_modal_page(page, archetype)
        is_admin_login = page_type == "login" and self._is_admin_login_page(page)

        if is_modal_page:
            lane_type = "modal"
            width = 400 if self._is_confirm_modal_page(page) else 800
            height = 320 if self._is_confirm_modal_page(page) else self._modal_height(self._field_rows(page))
        elif page_type in {"mobile_list", "mobile_form", "mobile_detail", "mobile_home", "profile"}:
            lane_type = "h5" if self.terminal_type == "h5" else "mobile"
            width = MOBILE_SWIMLANE_W
            height = MOBILE_SWIMLANE_H
        elif page_type in {"portal_home", "portal_content", "portal_hub"}:
            lane_type = "portal"
            width = WEB_SWIMLANE_W
            height = WEB_SWIMLANE_H
        elif page_type == "bigscreen_dashboard":
            lane_type = "bigscreen"
            width = BIGSCREEN_SWIMLANE_W
            height = BIGSCREEN_SWIMLANE_H
        elif page_type == "industrial_console":
            lane_type = "industrial"
            width = INDUSTRIAL_SWIMLANE_W
            height = INDUSTRIAL_SWIMLANE_H
        elif page_type == "login" and not is_admin_login:
            lane_type = "h5" if self.terminal_type == "h5" else "mobile"
            width = MOBILE_SWIMLANE_W
            height = MOBILE_SWIMLANE_H
        elif page_type in {"web_list", "web_form", "web_detail", "dashboard"}:
            lane_type = "web"
            width = WEB_SWIMLANE_W
            height = WEB_SWIMLANE_H
        elif page_type == "login":
            lane_type = "web"
            width = WEB_SWIMLANE_W
            height = WEB_SWIMLANE_H
        else:
            raise ValueError(f"未知页面类型: {page_type}")

        ctx = self.add_swimlane(
            str(page.get("page_name", page_type)).strip() or page_type,
            lane_type,
            width,
            height,
            "swimlane_modal" if lane_type == "modal" else "swimlane",
        )
        ctx.page = page

        if archetype == "drawer_permission":
            self._build_drawer_permission(ctx)
        elif archetype == "tree_manage" or self._is_resource_tree_page(page):
            self._build_tree_manage(ctx)
        elif is_modal_page:
            if self._is_confirm_modal_page(page):
                self._build_confirm_modal_page(ctx)
            else:
                self._build_standalone_modal_form(ctx)
        elif page_type == "web_list":
            self._build_web_list(ctx)
        elif page_type == "mobile_list":
            if self.terminal_type == "h5":
                self._build_h5_list(ctx)
            else:
                self._build_mobile_list(ctx)
        elif page_type == "web_form":
            self._build_web_form(ctx)
        elif page_type == "mobile_form":
            if self.terminal_type == "h5":
                self._build_h5_form(ctx)
            else:
                self._build_mobile_form(ctx)
        elif page_type == "mobile_detail":
            if self.terminal_type == "h5":
                self._build_h5_detail(ctx)
            else:
                self._build_mobile_detail(ctx)
        elif page_type == "web_detail":
            if self._is_order_detail_page(page):
                self._build_order_detail(ctx)
            else:
                self._build_web_detail(ctx)
        elif page_type == "login":
            self._build_login(ctx)
        elif page_type == "dashboard":
            self._build_dashboard(ctx)
        elif page_type == "mobile_home":
            if self.terminal_type == "h5":
                self._build_h5_home(ctx)
            else:
                self._build_mobile_home(ctx)
        elif page_type == "profile":
            if self.terminal_type == "h5":
                self._build_h5_profile(ctx)
            else:
                self._build_profile(ctx)
        elif page_type == "portal_home":
            self._build_portal_home(ctx)
        elif page_type == "portal_content":
            self._build_portal_content(ctx)
        elif page_type == "portal_hub":
            self._build_portal_hub(ctx)
        elif page_type == "bigscreen_dashboard":
            self._build_bigscreen_dashboard(ctx)
        elif page_type == "industrial_console":
            self._build_industrial_console(ctx)

        if page_type in {"web_list", "mobile_list"} and as_bool(page.get("needs_crud")):
            self._build_modal_pair(page, lane_type)

    def _page_archetype(self, page: dict) -> str:
        explicit = str(page.get("page_archetype", "")).strip()
        if explicit in ALLOWED_ARCHETYPES:
            return explicit

        name = str(page.get("page_name", "")).strip()
        page_type = str(page.get("page_type", "")).strip()
        if "资源管理" in name:
            return "tree_manage"
        if page_type == "portal_home":
            return "portal_landing"
        if page_type == "portal_content":
            return "portal_content"
        if page_type == "portal_hub":
            return "portal_hub"
        if page_type == "bigscreen_dashboard":
            return "bigscreen_board"
        if page_type == "industrial_console":
            return "industrial_hmi"
        if "登录" in name or page_type == "login":
            return "login"
        if any(token in name for token in ("官网首页", "落地页", "品牌官网", "产品官网")):
            return "portal_landing"
        if any(token in name for token in ("门户首页", "业务门户", "门户工作台")):
            return "portal_hub"
        if any(token in name for token in ("官网", "门户", "案例", "资讯", "文章")) and page_type.startswith("portal"):
            return "portal_content"
        if any(token in name for token in ("大屏", "驾驶舱", "指挥中心")):
            return "bigscreen_board"
        if any(token in name for token in ("工控", "HMI", "产线控制台", "中控台", "设备监控台")):
            return "industrial_hmi"
        if "工作台" in name or ("首页" in name and page_type == "dashboard"):
            return "dashboard"
        if "授权" in name or ("权限" in name and "抽屉" in name):
            return "drawer_permission"
        if any(token in name for token in ("调度看板", "配送调度", "路线调度", "司机调度")):
            return "dispatch_board"
        if any(token in name for token in ("分类", "组织", "部门", "岗位", "树")):
            return "tree_manage"
        if any(token in name for token in ("日志", "审计", "反馈记录")):
            return "audit_log"
        if page_type == "dashboard":
            return "dashboard"
        if page_type == "web_detail":
            return "detail_kv"
        if page_type == "web_form":
            return "form_page"
        if page_type == "mobile_home":
            return "mobile_home"
        if page_type == "profile":
            return "profile"
        if page_type == "login":
            return "login"
        return "list_table"

    def _is_admin_login_page(self, page: dict) -> bool:
        if self.terminal_type == "admin":
            return True
        text = page_terms(self.model, page)
        return any(token in text for token in ("后台", "管理", "审计"))

    def _is_modal_page(self, page: dict, archetype: str) -> bool:
        page_name = str(page.get("page_name", "")).strip()
        page_type = str(page.get("page_type", "")).strip()
        if archetype == "drawer_permission":
            return False
        if page_type not in {"web_form", "web_detail"}:
            return False
        return any(token in page_name for token in ("弹窗", "确认", "拒绝", "审核"))

    def _is_confirm_modal_page(self, page: dict) -> bool:
        page_name = str(page.get("page_name", "")).strip()
        raw_fields = page.get("fields")
        if isinstance(raw_fields, list) and raw_fields:
            return False
        if "发货" in page_name:
            return False
        if any(token in page_name for token in ("删除", "关闭", "拒绝")):
            return True
        return "确认" in page_name

    def _nav_context(self, page: dict) -> str:
        explicit = str(page.get("nav_context", "")).strip()
        if explicit:
            return explicit
        page_type = str(page.get("page_type", "")).strip()
        if self.terminal_type == "admin" and (page_type.startswith("web") or page_type == "dashboard"):
            return f"{self.terminal_name} / {self.business_module_name}"
        if page_type in {"mobile_list", "mobile_form", "mobile_detail", "mobile_home", "profile"}:
            if self.terminal_type == "app":
                return "App主导航"
            if self.terminal_type == "miniapp":
                return "小程序主导航"
            if self.terminal_type == "h5":
                return "H5页面栈"
            return "移动端主导航"
        if page_type in {"portal_home", "portal_content"}:
            return "官网顶栏导航"
        if page_type == "portal_hub":
            return "门户主导航"
        if page_type == "bigscreen_dashboard":
            return "大屏场景导航"
        if page_type == "industrial_console":
            return "工位操作导航"
        return "独立页"

    def _add_h5_shell(self, swimlane: str, page_name: str):
        self.add_element(swimlane, "card", "", 8, 40, 360, 40, "card")
        self.add_element(swimlane, "text_link", "←", 16, 48, 24, 24, "text_link", "→ 返回上一页")
        self.add_element(swimlane, "text_hint", "浏览器地址栏 · 安全访问", 56, 48, 224, 24, "text_hint")
        self.add_element(swimlane, "text_link", "分享", 296, 48, 48, 24, "text_link", "→ 打开分享面板")
        self.add_element(swimlane, "nav", page_name, 0, 96, 376, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 152, 376, 648, "bg")

    def _table_behavior_lines(self, page: dict) -> list[str]:
        value = page.get("table_behaviors")
        lines: list[str] = []
        if isinstance(value, dict):
            pairs = [
                ("default_sort", "排序"),
                ("page_size", "分页"),
                ("export_scope", "导出"),
                ("data_scope", "数据范围"),
                ("batch_actions", "批量操作"),
            ]
            for key, label in pairs:
                text = first_non_empty(value.get(key))
                if text:
                    lines.append(f"{label}：{text}")
        else:
            for item in normalize_list(value):
                lines.append(item)
        return lines[:4]

    def _business_rules(self, page: dict) -> list[str]:
        rules: list[str] = []

        def add_rule(text: str):
            cleaned = str(text or "").strip()
            if cleaned and cleaned not in rules:
                rules.append(cleaned)

        for item in normalize_list(page.get("business_rules")):
            add_rule(item)

        for item in self._table_behavior_lines(page):
            add_rule(item)

        for field in self._field_rows(page):
            name = str(field.get("name", "")).strip()
            validation = str(field.get("validation", "")).strip()
            if name and validation and validation not in {"必填", "选填", "-", "无"}:
                add_rule(f"{name}：{validation}")
            options = normalize_list(field.get("options"))
            if name and len(options) >= 2:
                add_rule(f"{name}：{' / '.join(options[:4])}")

        return rules[:5]

    def _state_lines(self, page: dict) -> list[str]:
        lines: list[str] = []
        states = page.get("states")
        if isinstance(states, dict):
            for key, label in (
                ("empty", "空态"),
                ("loading", "加载态"),
                ("error", "错误态"),
                ("transition", "状态流转"),
                ("flow", "状态流转"),
            ):
                text = first_non_empty(states.get(key))
                if text:
                    lines.append(f"{label}：{text}")
        elif isinstance(states, list):
            for item in normalize_list(states)[:3]:
                lines.append(item)

        status_values = self._status_values(page)
        if status_values:
            lines.insert(0, "状态：" + " / ".join(status_values[:5]))
        return lines[:4]

    def _jump_lines(self, page: dict) -> list[str]:
        lines: list[str] = []
        actions = page.get("actions")
        if isinstance(actions, list):
            for action in actions[:3]:
                name = str(action.get("name", "")).strip()
                target = str(action.get("target", "")).strip()
                if name and target:
                    lines.append(f"{name} → {target}")
                elif name:
                    lines.append(name)

        for target in normalize_list(page.get("jump_targets"))[:4]:
            if target not in lines:
                lines.append(target)
        return lines[:4]

    def _annotation_blocks(self, page: dict) -> list[str]:
        page_name = str(page.get("page_name", "页面")).strip()
        purpose = str(page.get("purpose", "承载核心业务操作")).strip()
        role = str(page.get("role", "业务角色")).strip()
        actions = page.get("actions")
        main_action = ""
        if isinstance(actions, list) and actions:
            main_action = str(actions[0].get("name", "")).strip()
        if not main_action:
            main_action = "查看与操作"

        blocks = [
            (
                f"页面摘要&#xa;"
                f"页面：{page_name}&#xa;"
                f"导航：{self._nav_context(page)}&#xa;"
                f"用途：{purpose}&#xa;"
                f"角色：{role}&#xa;"
                f"主操作：{main_action}"
            )
        ]

        jump_lines = self._jump_lines(page)
        if jump_lines:
            blocks.append("跳转说明&#xa;" + "&#xa;".join(jump_lines))

        business_rules = self._business_rules(page)
        if business_rules:
            blocks.append("业务规则&#xa;" + "&#xa;".join(business_rules))

        state_lines = self._state_lines(page)
        if state_lines:
            blocks.append("状态与边界&#xa;" + "&#xa;".join(state_lines))

        return blocks

    def _annotation_height(self, value: str) -> int:
        line_count = max(1, value.count("&#xa;") + 1)
        return snap8(max(88, min(176, 24 + line_count * 18)))

    def _add_annotations(self, ctx: PageContext):
        y = 40
        for value in self._annotation_blocks(ctx.page):
            height = self._annotation_height(value)
            self.add_element(ctx.swimlane_id, "annotation_card", value, ctx.ann_x, y, ctx.ann_w, height, "annotation_card")
            y += height + 16

    def _inline_hints(self, page: dict, limit: int = 2) -> list[str]:
        hints = []
        for item in self._table_behavior_lines(page) + self._business_rules(page):
            if item not in hints:
                hints.append(item)
        return hints[:limit]

    def _field_rows(self, page: dict) -> list[dict]:
        rows = page.get("fields")
        if isinstance(rows, list) and rows:
            return rows
        return [
            {"name": "名称", "control": "input", "required": True, "validation": "必填"},
            {"name": "状态", "control": "select", "required": True, "options": ["启用", "停用"], "validation": ""},
            {"name": "备注", "control": "textarea", "required": False, "validation": "200字以内"},
        ]

    def _table_columns(self, page: dict) -> list[str]:
        columns = normalize_list(page.get("table_columns"))
        if columns:
            return columns[:6]
        fields = self._field_rows(page)
        derived = [str(item.get("name", "")).strip() for item in fields[:4] if str(item.get("name", "")).strip()]
        if "状态" not in derived:
            derived.append("状态")
        return derived[:5]

    def _status_values(self, page: dict) -> list[str]:
        values = normalize_list(page.get("status_values"))
        if values:
            return values
        return ["待处理", "处理中", "已完成", "已取消", "已归档"]

    def _page_text(self, page: dict) -> str:
        return page_terms(self.model, page)

    def _is_order_list_page(self, page: dict) -> bool:
        text = self._page_text(page)
        return (
            str(page.get("page_type", "")).strip() == "web_list"
            and "订单" in text
            and not any(token in text for token in ("售后", "退款", "发货单", "支付日志"))
        )

    def _is_order_detail_page(self, page: dict) -> bool:
        text = self._page_text(page)
        return (
            str(page.get("page_type", "")).strip() == "web_detail"
            and "订单" in text
            and not any(token in text for token in ("售后", "退款"))
        )

    def _is_resource_tree_page(self, page: dict) -> bool:
        text = self._page_text(page)
        return "资源管理" in text or ("资源" in text and str(page.get("page_type", "")).strip() == "web_list")

    def _order_row_actions(self, status: str) -> list[tuple[str, str, str]]:
        if "待支付" in status:
            return [
                ("详情", "btn_sm", "→ 订单详情页（后台）"),
                ("关闭", "btn_sm_danger", "→ 关闭订单确认弹窗"),
                ("备注", "btn_sm", "→ 备注弹窗"),
            ]
        if "待发货" in status:
            return [
                ("详情", "btn_sm", "→ 订单详情页（后台）"),
                ("发货", "btn_sm", "→ 确认发货弹窗"),
                ("关闭", "btn_sm_danger", "→ 关闭订单确认弹窗"),
            ]
        if "待收货" in status:
            return [
                ("详情", "btn_sm", "→ 订单详情页（后台）"),
                ("确认收货", "btn_sm", "→ 订单详情页（后台）"),
                ("备注", "btn_sm", "→ 备注弹窗"),
            ]
        if "已完成" in status:
            return [
                ("详情", "btn_sm", "→ 订单详情页（后台）"),
                ("查看售后", "btn_sm", "→ 售后订单页"),
                ("备注", "btn_sm", "→ 备注弹窗"),
            ]
        if "已关闭" in status:
            return [
                ("详情", "btn_sm", "→ 订单详情页（后台）"),
                ("备注", "btn_sm", "→ 备注弹窗"),
            ]
        return [
            ("详情", "btn_sm", "→ 订单详情页（后台）"),
            ("备注", "btn_sm", "→ 备注弹窗"),
        ]

    def _match_field(self, fields: list[dict], tokens: tuple[str, ...]) -> dict | None:
        for field in fields:
            name = str(field.get("name", "")).strip()
            if name and any(token in name for token in tokens):
                return field
        return None

    def _login_note(self, page: dict, show_captcha: bool) -> str:
        for rule in self._business_rules(page):
            if any(token in rule for token in ("验证码", "失败", "锁定", "限制")):
                return rule
        if show_captcha:
            return "连续失败超过 5 次将触发验证码限制"
        return "登录后进入业务工作台"

    def _list_action_specs(self, page: dict) -> tuple[str, list[tuple[str, str, str]]]:
        page_name = str(page.get("page_name", "")).strip()
        object_name = str(page.get("object_name", "")).strip() or "对象"
        actions = page.get("actions") if isinstance(page.get("actions"), list) else []

        if self._is_order_list_page(page):
            return "", self._order_row_actions("待发货")

        add_label = ""
        row_actions: list[tuple[str, str, str]] = []
        for action in actions:
            name = str(action.get("name", "")).strip()
            target = str(action.get("target", "")).strip()
            kind = str(action.get("kind", "")).strip()
            tooltip = f"→ {target}" if target else ""
            if name.startswith("新增"):
                add_label = name
                continue
            if any(token in name for token in ("编辑", "删除", "查看", "详情", "发货", "关闭", "备注", "处理", "授权", "审核", "导出", "下架", "停用", "解除", "改等级", "重置密码")):
                style = "btn_sm_danger" if kind == "danger" or "删除" in name or "关闭" in name else "btn_sm"
                row_actions.append((name, style, tooltip))

        if as_bool(page.get("needs_crud")):
            if not add_label:
                add_label = f"新增{object_name}"
            if not row_actions:
                row_actions = [
                    ("编辑", "btn_sm", f"→ 新增/编辑{object_name}弹窗"),
                    ("删除", "btn_sm_danger", f"→ {delete_modal_name(object_name)}"),
                ]

        if row_actions:
            deduped = []
            seen = set()
            for item in row_actions:
                if item[0] in seen:
                    continue
                seen.add(item[0])
                deduped.append(item)
            return add_label, deduped[:3]

        inferred = []
        if any(token in page_name for token in ("员工", "司机", "管理员")):
            add_label = add_label or f"新增{object_name if object_name != '对象' else page_name.replace('管理页', '')}"
            inferred = [("编辑", "btn_sm", f"→ 新增/编辑{object_name}弹窗"), (enable_disable_label(page_name), "btn_sm", "")]
        elif "分销会员" in page_name:
            inferred = [("审核", "btn_sm", ""), ("改等级", "btn_sm", "")]
        elif any(token in page_name for token in ("分销等级", "会员等级")):
            add_label = add_label or f"新增{object_name if object_name != '对象' else '等级'}"
            inferred = [("编辑", "btn_sm", ""), (enable_disable_label(page_name), "btn_sm", "")]
        elif any(token in page_name for token in ("满额优惠", "满减")):
            add_label = add_label or "新增满减"
            inferred = [("编辑", "btn_sm", "→ 营销活动表单页"), ("删除", "btn_sm_danger", "→ 删除活动确认弹窗")]
        elif "优惠券" in page_name and "领取记录" not in page_name:
            add_label = add_label or "新增优惠券"
            inferred = [("编辑", "btn_sm", "→ 营销活动表单页"), ("删除", "btn_sm_danger", "→ 删除优惠券确认弹窗")]
        elif "轮播图" in page_name:
            add_label = add_label or "新增轮播"
            inferred = [("编辑", "btn_sm", "→ 轮播编辑页"), ("下线", "btn_sm", "")]
        elif "公告" in page_name:
            inferred = [("查看", "btn_sm", "→ 公告编辑页"), ("编辑", "btn_sm", "→ 公告编辑页")]
        elif "评论" in page_name:
            inferred = [("详情", "btn_sm", "→ 评论详情页"), ("审核", "btn_sm", "")]
        elif "会员管理" in page_name:
            inferred = [("查看", "btn_sm", "→ 会员详情页"), ("编辑", "btn_sm", ""), (enable_disable_label(page_name), "btn_sm", "")]
        elif "黑名单" in page_name:
            inferred = [("查看", "btn_sm", ""), ("解除", "btn_sm", "")]
        elif any(token in page_name for token in ("运输桶", "显示屏", "设备")):
            add_label = add_label or f"新增{object_name if object_name != '对象' else page_name.replace('管理页', '')}"
            inferred = [("编辑", "btn_sm", ""), (enable_disable_label(page_name), "btn_sm", "")]
        elif "订单管理" in page_name:
            inferred = [("详情", "btn_sm", "→ 订单详情页（后台）"), ("发货", "btn_sm", "→ 确认发货弹窗"), ("关闭", "btn_sm_danger", "→ 关闭订单确认弹窗")]
        elif "发货单" in page_name:
            inferred = [("详情", "btn_sm", "→ 发货单详情页"), ("发货", "btn_sm", "")]
        else:
            inferred = [("查看", "btn_sm", f"→ {page_name}详情")]

        return add_label, inferred[:3]

    def _build_web_list(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "列表页")).strip()
        object_name = str(page.get("object_name", "对象")).strip()

        self.add_element(swimlane, "nav", page_name, 0, 40, 1440, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 1440, 864, "bg")
        self.add_element(swimlane, "breadcrumb", f"首页 / {self.module_name} / {page_name}", 24, 112, 432, 24, "breadcrumb")
        self.add_element(swimlane, "input", f"搜索{object_name}", 24, 160, 224, 48, "input")
        self.add_element(swimlane, "select", "状态筛选 ▼", 264, 160, 160, 48, "select")
        self.add_element(swimlane, "select", "时间范围 ▼", 440, 160, 176, 48, "select")
        self.add_element(swimlane, "btn_primary", "查询", 632, 160, 88, 48, "btn_primary")
        self.add_element(swimlane, "btn_secondary", "重置", 736, 160, 88, 48, "btn_secondary")
        add_label, row_actions = self._list_action_specs(page)
        if add_label:
            self.add_element(swimlane, "btn_primary", add_label, 1296, 160, 120, 48, "btn_primary", f"→ 新增/编辑{object_name}弹窗")

        columns = self._table_columns(page)
        widths = self._column_widths(columns)
        x_positions = []
        x = 24
        for width in widths:
            x_positions.append(x)
            x += width

        inline_hints = self._inline_hints(page)
        for idx, hint in enumerate(inline_hints):
            self.add_element(swimlane, "text_hint", hint, 24 + idx * 440, 224, 408, 20, "text_hint")

        header_y = 256
        row_start_y = 304
        for idx, name in enumerate(columns):
            self.add_element(swimlane, "table_header", name, x_positions[idx], header_y, widths[idx], 40, "table_header")
        self.add_element(swimlane, "table_header", "操作", 1296, header_y, 120, 40, "table_header")

        statuses = self._status_values(page)
        for row_idx in range(5):
            y = row_start_y + row_idx * 48
            row_style = "table_row_odd" if row_idx % 2 == 0 else "table_row_even"
            for col_idx, name in enumerate(columns):
                if "状态" in name:
                    value = statuses[row_idx % len(statuses)]
                else:
                    value = placeholder_value(name, row_idx + 1)
                self.add_element(swimlane, "table_cell", value, x_positions[col_idx], y, widths[col_idx], 48, row_style)
            effective_row_actions = row_actions
            if self._is_order_list_page(page):
                effective_row_actions = self._order_row_actions(statuses[row_idx % len(statuses)])
            action_width = 40 if len(effective_row_actions) >= 3 else 48 if len(effective_row_actions) == 2 else 56
            action_x = 1296
            for action_name, action_style, tooltip in effective_row_actions:
                self.add_element(swimlane, action_style, action_name, action_x, y + 8, action_width, 32, action_style, tooltip)
                action_x += action_width + 8

        pagination_y = row_start_y + 5 * 48 + 24
        self.add_element(swimlane, "pagination", "共 128 条 第 1/6 页 上一页 下一页", 24, pagination_y, 344, 40, "pagination")
        self._add_annotations(ctx)

    def _column_widths(self, columns: list[str]) -> list[int]:
        available = 1272
        weights = []
        for col in columns:
            if any(token in col for token in ("名称", "标题", "描述", "地址")):
                weights.append(2.0)
            elif any(token in col for token in ("时间", "日期", "编号", "编码")):
                weights.append(1.4)
            else:
                weights.append(1.0)
        total_weight = sum(weights) if weights else 1.0
        widths = [snap8(int(available * weight / total_weight)) for weight in weights]
        current = sum(widths)
        if widths:
            widths[-1] += available - current
            widths[-1] = snap8(widths[-1])
        return widths

    def _build_mobile_list(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "列表页")).strip()
        object_name = str(page.get("object_name", "对象")).strip()
        keywords = f"{page_name} {object_name} {' '.join(self._table_columns(page))}"

        self.add_element(swimlane, "nav", page_name, 0, 40, 376, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 376, 704, "bg")
        self.add_element(swimlane, "input", f"搜索{object_name}", 16, 112, 248, 48, "input")
        if as_bool(page.get("needs_crud")):
            self.add_element(swimlane, "btn_primary", "新增", 272, 112, 88, 48, "btn_primary", f"→ 新增/编辑{object_name}弹窗")
        else:
            self.add_element(swimlane, "btn_primary", "筛选", 272, 112, 88, 48, "btn_primary")

        statuses = self._status_values(page)
        if any(token in keywords for token in ("地址", "收货")):
            for idx in range(4):
                card_y = 176 + idx * 120
                self.add_element(swimlane, "card", "", 16, card_y, 344, 112, "card")
                self.add_element(swimlane, "text_subtitle", f"收货人{idx + 1}", 32, card_y + 16, 96, 24, "text_subtitle")
                self.add_element(swimlane, "text_hint", f"138000000{idx + 1}", 136, card_y + 18, 104, 20, "text_hint")
                tag = "默认地址" if idx == 0 else "常用地址"
                self.add_element(swimlane, "tag", tag, 264, card_y + 16, 72, 24, "tag_info")
                self.add_element(swimlane, "text_body", f"上海市浦东新区渔港路{idx + 18}号 冷链仓A座", 32, card_y + 48, 232, 24, "text_body")
                self.add_element(swimlane, "text_hint", "支持送货上门 / 冷链配送", 32, card_y + 76, 176, 20, "text_hint")
                self.add_element(swimlane, "btn_sm", "编辑", 248, card_y + 72, 40, 32, "btn_sm", f"→ 新增/编辑{object_name}弹窗")
                self.add_element(swimlane, "btn_sm_danger", "删除", 296, card_y + 72, 40, 32, "btn_sm_danger", f"→ {delete_modal_name(object_name)}")
        elif any(token in keywords for token in ("订单", "售后", "退款")):
            for idx in range(4):
                card_y = 176 + idx * 128
                status = statuses[idx % len(statuses)]
                self.add_element(swimlane, "card", "", 16, card_y, 344, 120, "card")
                self.add_element(swimlane, "text_subtitle", f"订单号 YYG-202603-{idx + 1:03d}", 32, card_y + 16, 192, 24, "text_subtitle")
                self.add_element(swimlane, "tag", status, 256, card_y + 16, 72, 24, tag_style_for_status(status))
                self.add_element(swimlane, "text_body", f"鲈鱼套餐 x{idx + 1} / 冷鲜配送", 32, card_y + 48, 184, 24, "text_body")
                self.add_element(swimlane, "text_value", f"实付 ¥{68 + idx * 32}", 32, card_y + 80, 112, 20, "text_value")
                self.add_element(swimlane, "btn_sm", "详情", 248, card_y + 72, 40, 32, "btn_sm", f"→ {page_name}详情")
                action = "售后" if "售后" in keywords or "退款" in keywords else "再次下单"
                self.add_element(swimlane, "btn_secondary", action, 296, card_y + 72, 40, 32, "btn_sm")
        elif any(token in keywords for token in ("商品", "分类", "购物车", "SKU", "SPU")):
            for idx in range(5):
                card_y = 176 + idx * 104
                self.add_element(swimlane, "card", "", 16, card_y, 344, 96, "card")
                self.add_element(swimlane, "img_placeholder", "图", 32, card_y + 16, 56, 56, "img_placeholder")
                self.add_element(swimlane, "text_subtitle", f"{object_name}{idx + 1}", 104, card_y + 16, 136, 24, "text_subtitle")
                self.add_element(swimlane, "text_hint", f"规格：{placeholder_value('规格', idx + 1)}", 104, card_y + 44, 136, 20, "text_hint")
                status = statuses[idx % len(statuses)]
                self.add_element(swimlane, "tag", status, 248, card_y + 16, 72, 24, tag_style_for_status(status))
                self.add_element(swimlane, "text_price", f"¥{39 + idx * 12}", 248, card_y + 48, 72, 20, "text_price")
                self.add_element(swimlane, "btn_sm", "查看", 280, card_y + 48, 48, 32, "btn_sm", f"→ {page_name}详情")
        else:
            primary_col = self._table_columns(page)[0] if self._table_columns(page) else object_name
            secondary_col = self._table_columns(page)[1] if len(self._table_columns(page)) > 1 else "更新时间"
            metric_col = self._table_columns(page)[2] if len(self._table_columns(page)) > 2 else "状态"
            for idx in range(5):
                card_y = 176 + idx * 104
                status = statuses[idx % len(statuses)]
                self.add_element(swimlane, "card", "", 16, card_y, 344, 96, "card")
                self.add_element(swimlane, "text_subtitle", placeholder_value(primary_col, idx + 1), 32, card_y + 16, 160, 24, "text_subtitle")
                self.add_element(swimlane, "text_hint", placeholder_value(secondary_col, idx + 1), 32, card_y + 48, 168, 20, "text_hint")
                self.add_element(swimlane, "tag", status, 248, card_y + 16, 72, 24, tag_style_for_status(status))
                self.add_element(swimlane, "text_value", placeholder_value(metric_col, idx + 1), 248, card_y + 48, 88, 20, "text_value")
                if as_bool(page.get("needs_crud")):
                    self.add_element(swimlane, "btn_sm", "编辑", 192, card_y + 48, 48, 32, "btn_sm", f"→ 新增/编辑{object_name}弹窗")
                    self.add_element(swimlane, "btn_sm_danger", "删除", 248, card_y + 48, 48, 32, "btn_sm_danger", f"→ {delete_modal_name(object_name)}")
                else:
                    self.add_element(swimlane, "btn_sm", "查看", 280, card_y + 48, 48, 32, "btn_sm", f"→ {page_name}详情")

        if as_bool(page.get("is_nav_page")):
            self.add_element(swimlane, "bottom_bar", "首页 · 列表 · 消息 · 我的", 0, 800, 376, 56, "bottom_bar")
        self._add_annotations(ctx)

    def _build_h5_list(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "H5列表页")).strip()
        object_name = str(page.get("object_name", "内容")).strip() or "内容"
        statuses = self._status_values(page)

        self._add_h5_shell(swimlane, page_name)
        self.add_element(swimlane, "search_input", f"搜索{object_name}", 16, 168, 344, 40, "search_input")
        self.add_element(swimlane, "text_hint", "筛选：最新发布 / 热门推荐 / 限时活动", 16, 224, 280, 20, "text_hint")
        for idx in range(4):
            y = 264 + idx * 120
            status = statuses[idx % len(statuses)]
            self.add_element(swimlane, "card", "", 16, y, 344, 104, "card")
            self.add_element(swimlane, "text_subtitle", f"{object_name}{idx + 1}", 32, y + 16, 168, 24, "text_subtitle")
            self.add_element(swimlane, "text_hint", placeholder_value("活动时间", idx + 1), 32, y + 48, 144, 20, "text_hint")
            self.add_element(swimlane, "tag", status, 248, y + 16, 80, 24, tag_style_for_status(status))
            self.add_element(swimlane, "btn_secondary", "查看详情", 232, y + 56, 96, 32, "btn_secondary", f"→ {page_name}详情")
        self.add_element(swimlane, "btn_primary", "联系客服", 16, 744, 344, 48, "btn_primary", "→ 在线咨询")
        self._add_annotations(ctx)

    def _build_web_form(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "表单页")).strip()
        fields = self._field_rows(page)
        content_h = max(392, snap8(len(fields) * 64 + 120))

        self.add_element(swimlane, "nav", page_name, 0, 40, 1440, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 1440, 864, "bg")
        self.add_element(swimlane, "breadcrumb", f"首页 / {self.module_name} / {page_name}", 24, 112, 440, 24, "breadcrumb")
        self.add_element(swimlane, "card", "", 24, 160, 816, content_h, "card")
        self.add_element(swimlane, "text_subtitle", "基础信息", 48, 184, 200, 24, "text_subtitle")

        y = 232
        for field in fields:
            name = str(field.get("name", "字段")).strip() or "字段"
            required = as_bool(field.get("required"))
            control = str(field.get("control", "input")).strip() or "input"
            label_style = "label_required" if required else "label"
            label_value = f"{name} *" if required else name
            self.add_element(swimlane, "label", label_value, 48, y, 96, 40, label_style)
            tooltip = ""
            options = normalize_list(field.get("options"))
            if options:
                tooltip = "可选值：" + " / ".join(options)
            style_key = "textarea" if control == "textarea" else "select" if control == "select" else "input"
            height = 88 if control == "textarea" else 48
            placeholder = ("请选择" if control == "select" else "请输入") + name
            self.add_element(swimlane, control, placeholder, 152, y, 344, height, style_key, tooltip)
            y += 104 if control == "textarea" else 64

        self.add_element(swimlane, "btn_primary", "提交", 152, y + 16, 120, 48, "btn_primary", "→ 提交后返回列表")
        self.add_element(swimlane, "btn_secondary", "取消", 288, y + 16, 88, 48, "btn_secondary", "→ 返回来源页")
        self._add_annotations(ctx)

    def _build_mobile_form(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "表单页")).strip()
        fields = self._field_rows(page)

        self.add_element(swimlane, "nav", page_name, 0, 40, 376, 56, "nav")
        self.add_element(swimlane, "nav_back", "← 返回", 0, 40, 72, 56, "nav_back", "→ 返回来源页")
        self.add_element(swimlane, "bg", "", 0, 96, 376, 704, "bg")

        y = 112
        for field in fields[:6]:
            name = str(field.get("name", "字段")).strip() or "字段"
            required = as_bool(field.get("required"))
            control = str(field.get("control", "input")).strip() or "input"
            label_style = "label_required" if required else "label"
            label_value = f"{name} *" if required else name
            self.add_element(swimlane, "label", label_value, 16, y, 80, 40, label_style)
            tooltip = ""
            options = normalize_list(field.get("options"))
            if options:
                tooltip = "可选值：" + " / ".join(options)
            style_key = "textarea" if control == "textarea" else "select" if control == "select" else "input"
            height = 88 if control == "textarea" else 48
            self.add_element(swimlane, control, ("请选择" if control == "select" else "请输入") + name, 104, y, 256, height, style_key, tooltip)
            y += 104 if control == "textarea" else 64

        self.add_element(swimlane, "btn_primary", "提交", 16, min(y + 16, 736), 344, 48, "btn_primary", "→ 提交成功后返回")
        self._add_annotations(ctx)

    def _build_h5_form(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "H5表单页")).strip()
        fields = self._field_rows(page)

        self._add_h5_shell(swimlane, page_name)
        y = 176
        for field in fields[:5]:
            name = str(field.get("name", "字段")).strip() or "字段"
            required = as_bool(field.get("required"))
            control = str(field.get("control", "input")).strip() or "input"
            label_style = "label_required" if required else "label"
            self.add_element(swimlane, "label", f"{name} *" if required else name, 16, y, 88, 24, label_style)
            style_key = "textarea" if control == "textarea" else "select" if control == "select" else "input"
            height = 88 if control == "textarea" else 48
            placeholder = ("请选择" if control == "select" else "请输入") + name
            self.add_element(swimlane, control, placeholder, 16, y + 24, 344, height, style_key)
            y += 120 if control == "textarea" else 88
        self.add_element(swimlane, "text_hint", "提交后将保留浏览器分享链路", 16, 704, 240, 20, "text_hint")
        self.add_element(swimlane, "btn_primary", "立即提交", 16, 736, 344, 48, "btn_primary", "→ 提交成功页")
        self._add_annotations(ctx)

    def _build_mobile_detail(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "详情页")).strip()
        fields = self._field_rows(page)
        keywords = f"{page_name} {' '.join(str(f.get('name','')) for f in fields)}"
        actions = page.get("actions") if isinstance(page.get("actions"), list) else []

        self.add_element(swimlane, "nav", page_name, 0, 40, 376, 56, "nav")
        self.add_element(swimlane, "nav_back", "← 返回", 0, 40, 72, 56, "nav_back", "→ 返回来源页")
        self.add_element(swimlane, "bg", "", 0, 96, 376, 704, "bg")

        if any(token in keywords for token in ("溯源", "二维码")):
            self.add_element(swimlane, "card", "", 16, 120, 344, 176, "card")
            self.add_element(swimlane, "img_placeholder", "溯源二维码", 128, 144, 120, 120, "img_placeholder")
            self.add_element(swimlane, "text_hint", "批次号：YYG-BATCH-20260324", 72, 272, 224, 20, "text_hint")
            timeline_y = 328
            for idx, label in enumerate(["养殖建档", "抽检通过", "装桶运输", "门店到货"]):
                y = timeline_y + idx * 72
                self.add_element(swimlane, "icon", str(idx + 1), 24, y, 32, 32, "icon")
                self.add_element(swimlane, "text_subtitle", label, 72, y, 120, 24, "text_subtitle")
                self.add_element(swimlane, "text_hint", f"2026-03-{10 + idx:02d} 10:00", 72, y + 28, 152, 20, "text_hint")
                self.add_element(swimlane, "tag", "已完成" if idx < 3 else "已同步", 248, y + 4, 72, 24, "tag_success")
            self.add_element(swimlane, "btn_secondary", "查看详情", 16, 736, 112, 48, "btn_secondary", "→ 进入溯源详情")
            self.add_element(swimlane, "btn_primary", "保存二维码", 248, 736, 112, 48, "btn_primary", "→ 保存图片")
        elif any(token in keywords for token in ("订单", "地址", "金额", "收货")):
            self.add_element(swimlane, "card", "", 16, 120, 344, 120, "card")
            self.add_element(swimlane, "text_subtitle", "收货信息", 32, 144, 120, 24, "text_subtitle")
            self.add_element(swimlane, "text_body", "渔友C  137****3333", 32, 176, 184, 24, "text_body")
            self.add_element(swimlane, "text_hint", "上海市浦东新区渔港路88号 冷链仓A座", 32, 208, 216, 20, "text_hint")
            self.add_element(swimlane, "card", "", 16, 256, 344, 216, "card")
            self.add_element(swimlane, "text_subtitle", "商品与金额", 32, 280, 120, 24, "text_subtitle")
            self.add_element(swimlane, "img_placeholder", "商品图", 32, 320, 64, 64, "img_placeholder")
            self.add_element(swimlane, "text_body", "鲜活鲈鱼 1.5kg-2kg/条", 112, 324, 160, 24, "text_body")
            self.add_element(swimlane, "text_hint", "规格：现杀冷鲜 / 数量：2", 112, 356, 160, 20, "text_hint")
            self.add_element(swimlane, "text_price", "¥136", 280, 332, 56, 20, "text_price")
            summary_y = 408
            for idx, (label, value) in enumerate([("商品金额", "¥136"), ("运费", "¥12"), ("优惠", "-¥10"), ("应付金额", "¥138")]):
                y = summary_y + idx * 24
                self.add_element(swimlane, "label", label, 32, y, 96, 20, "label")
                self.add_element(swimlane, "text_value", value, 272, y, 64, 20, "text_value")
            status_values = self._status_values(page)
            self.add_element(swimlane, "tag", status_values[0], 272, 144, 64, 24, tag_style_for_status(status_values[0]))
            primary_label = actions[0].get("name", "提交") if actions else ("提交订单" if "确认订单" in page_name else "确认收货")
            secondary_label = actions[1].get("name", "更多") if len(actions) > 1 else "返回"
            self.add_element(swimlane, "btn_secondary", secondary_label, 16, 736, 112, 48, "btn_secondary", "→ 返回来源页")
            self.add_element(swimlane, "btn_primary", primary_label, 232, 736, 128, 48, "btn_primary", f"→ {primary_label}")
        else:
            self.add_element(swimlane, "card", "", 16, 120, 344, 560, "card")
            self.add_element(swimlane, "text_subtitle", "详情信息", 32, 144, 120, 24, "text_subtitle")
            row_y = 184
            for idx, field in enumerate(fields[:8]):
                name = str(field.get("name", "字段")).strip() or "字段"
                self.add_element(swimlane, "label", name, 32, row_y, 88, 24, "label")
                self.add_element(swimlane, "text_value", placeholder_value(name, idx + 1), 136, row_y, 184, 24, "text_value")
                row_y += 48
            primary_label = actions[0].get("name", "确认") if actions else "确认"
            self.add_element(swimlane, "btn_secondary", "返回", 16, 736, 104, 48, "btn_secondary", "→ 返回来源页")
            self.add_element(swimlane, "btn_primary", primary_label, 248, 736, 112, 48, "btn_primary", f"→ {primary_label}")

        self._add_annotations(ctx)

    def _build_h5_detail(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "H5详情页")).strip()
        statuses = self._status_values(page)

        self._add_h5_shell(swimlane, page_name)
        self.add_element(swimlane, "card", "", 16, 176, 344, 184, "card")
        self.add_element(swimlane, "text_title", page_name, 32, 200, 224, 32, "text_title")
        self.add_element(swimlane, "tag", statuses[0], 264, 208, 64, 24, tag_style_for_status(statuses[0]))
        self.add_element(swimlane, "text_body", "活动亮点、流程说明、适用规则与用户权益摘要", 32, 248, 264, 48, "text_body")
        self.add_element(swimlane, "text_hint", "分享后保留当前活动参数与来源渠道", 32, 312, 248, 20, "text_hint")
        self.add_element(swimlane, "card", "", 16, 384, 344, 280, "card")
        self.add_element(swimlane, "text_subtitle", "详情说明", 32, 408, 120, 24, "text_subtitle")
        for idx, label in enumerate(["活动时间", "参与门槛", "使用范围", "客服说明"]):
            y = 448 + idx * 48
            self.add_element(swimlane, "label", label, 32, y, 88, 24, "label")
            self.add_element(swimlane, "text_value", placeholder_value(label, idx + 1), 136, y, 168, 24, "text_value")
        self.add_element(swimlane, "btn_secondary", "在线咨询", 16, 736, 112, 48, "btn_secondary", "→ 联系客服")
        self.add_element(swimlane, "btn_primary", "立即报名", 232, 736, 128, 48, "btn_primary", "→ 报名表单")
        self._add_annotations(ctx)

    def _build_order_detail(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "订单详情页（后台）")).strip()
        status_values = self._status_values(page)
        current_status = status_values[0] if status_values else "待发货"
        top_actions = self._order_row_actions(current_status)

        self.add_element(swimlane, "nav", page_name, 0, 40, 1440, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 1440, 864, "bg")
        self.add_element(swimlane, "breadcrumb", f"首页 / {self.module_name} / {page_name}", 24, 112, 440, 24, "breadcrumb")
        self.add_element(swimlane, "btn_secondary", "返回列表", 1296, 104, 120, 40, "btn_secondary", "→ 返回来源页")

        self.add_element(swimlane, "card", "", 24, 160, 1392, 120, "card")
        self.add_element(swimlane, "text_subtitle", "状态与操作", 48, 184, 200, 24, "text_subtitle")
        self.add_element(swimlane, "divider", "", 48, 216, 1344, 1, "divider")
        self.add_element(swimlane, "label", "当前状态", 48, 232, 88, 24, "label")
        self.add_element(swimlane, "tag", current_status, 152, 232, 88, 24, tag_style_for_status(current_status))
        self.add_element(swimlane, "text_hint", "状态流转：待支付 → 待发货 → 待收货 → 已完成 / 已关闭", 280, 232, 520, 24, "text_hint")

        button_x = 952
        for action_name, action_style, tooltip in top_actions:
            width = 104 if action_style == "btn_sm_danger" else 96 if len(action_name) >= 4 else 88
            style_key = "btn_danger_filled" if action_style == "btn_sm_danger" else "btn_secondary"
            if action_name in {"发货", "确认收货"}:
                style_key = "btn_primary"
                width = 104
            self.add_element(swimlane, style_key, action_name, button_x, 224, width, 40, style_key, tooltip)
            button_x += width + 16

        left_fields = ["订单编号", "订单状态", "用户信息", "收货地址", "商品明细", "金额明细"]
        right_fields = ["支付信息", "售后信息", "备注记录", "溯源摘要", "物流信息", "操作区"]

        self.add_element(swimlane, "card", "", 24, 304, 680, 264, "card")
        self.add_element(swimlane, "text_subtitle", "订单基础信息", 48, 328, 200, 24, "text_subtitle")
        self.add_element(swimlane, "divider", "", 48, 360, 632, 1, "divider")
        row_y = 376
        for idx, name in enumerate(left_fields):
            base_x = 48 if idx % 2 == 0 else 360
            value_x = 152 if idx % 2 == 0 else 464
            if idx and idx % 2 == 0:
                row_y += 48
            self.add_element(swimlane, "label", name, base_x, row_y, 88, 24, "label")
            self.add_element(swimlane, "text_value", placeholder_value(name, idx + 1), value_x, row_y, 176, 24, "text_value")

        self.add_element(swimlane, "card", "", 728, 304, 688, 264, "card")
        self.add_element(swimlane, "text_subtitle", "支付与售后", 752, 328, 200, 24, "text_subtitle")
        self.add_element(swimlane, "divider", "", 752, 360, 640, 1, "divider")
        row_y = 376
        for idx, name in enumerate(right_fields):
            base_x = 752 if idx % 2 == 0 else 1064
            value_x = 856 if idx % 2 == 0 else 1168
            if idx and idx % 2 == 0:
                row_y += 48
            self.add_element(swimlane, "label", name, base_x, row_y, 88, 24, "label")
            self.add_element(swimlane, "text_value", placeholder_value(name, idx + 7), value_x, row_y, 176, 24, "text_value")

        self.add_element(swimlane, "card", "", 24, 600, 1392, 248, "card")
        self.add_element(swimlane, "text_subtitle", "备注记录与处理轨迹", 48, 624, 220, 24, "text_subtitle")
        self.add_element(swimlane, "divider", "", 48, 656, 1344, 1, "divider")
        record_labels = ["下单成功", "客服备注", "履约处理"]
        for idx, label in enumerate(record_labels):
            y = 672 + idx * 48
            self.add_element(swimlane, "icon", str(idx + 1), 48, y, 24, 24, "icon")
            self.add_element(swimlane, "text_body", label, 88, y, 120, 24, "text_body")
            self.add_element(swimlane, "text_hint", f"2026-03-{12 + idx:02d} 10:3{idx}", 224, y, 176, 24, "text_hint")
            self.add_element(swimlane, "text_hint", "处理人：" + placeholder_value("处理人", idx + 1), 448, y, 176, 24, "text_hint")
            self.add_element(swimlane, "text_hint", "结果：" + status_values[min(idx, len(status_values) - 1)], 720, y, 176, 24, "text_hint")
            if idx < len(record_labels) - 1:
                self.add_element(swimlane, "divider", "", 88, y + 32, 1240, 1, "divider")

        self._add_annotations(ctx)

    def _build_web_detail(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "详情页")).strip()
        fields = self._field_rows(page)
        actions = page.get("actions") if isinstance(page.get("actions"), list) else []

        self.add_element(swimlane, "nav", page_name, 0, 40, 1440, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 1440, 864, "bg")
        self.add_element(swimlane, "breadcrumb", f"首页 / {self.module_name} / {page_name}", 24, 112, 440, 24, "breadcrumb")
        self.add_element(swimlane, "btn_secondary", "返回列表", 1296, 104, 120, 40, "btn_secondary", "→ 返回来源页")
        status_values = self._status_values(page)
        current_status = status_values[0]

        self.add_element(swimlane, "card", "", 24, 160, 1392, 104, "card")
        self.add_element(swimlane, "text_subtitle", "状态与处理", 48, 184, 200, 24, "text_subtitle")
        self.add_element(swimlane, "divider", "", 48, 216, 1008, 1, "divider")
        self.add_element(swimlane, "label", "当前状态", 48, 224, 88, 24, "label")
        self.add_element(swimlane, "tag", current_status, 152, 224, 88, 24, tag_style_for_status(current_status))
        if len(status_values) > 1:
            self.add_element(swimlane, "text_hint", "状态流转：" + " → ".join(status_values[:4]), 280, 224, 520, 24, "text_hint")

        button_x = 1088
        for action in actions[:3]:
            action_name = str(action.get("name", "")).strip()
            if not action_name:
                continue
            target = str(action.get("target", "")).strip()
            kind = str(action.get("kind", "")).strip()
            style = "btn_primary" if kind == "primary" else "btn_danger_filled" if kind == "danger" else "btn_secondary"
            width = 136 if style == "btn_primary" else 104 if style == "btn_danger_filled" else 88
            self.add_element(swimlane, style, action_name, button_x, 208, width, 40, style, f"→ {target}" if target else "")
            button_x += width + 16

        self.add_element(swimlane, "card", "", 24, 288, 672, 272, "card")
        self.add_element(swimlane, "text_subtitle", "基础信息", 48, 312, 200, 24, "text_subtitle")
        self.add_element(swimlane, "divider", "", 48, 344, 624, 1, "divider")
        row_y = 360
        for idx, field in enumerate(fields[:6]):
            name = str(field.get("name", "字段")).strip() or "字段"
            base_x = 48 if idx % 2 == 0 else 360
            value_x = 152 if idx % 2 == 0 else 464
            if idx and idx % 2 == 0:
                row_y += 48
            self.add_element(swimlane, "label", name, base_x, row_y, 88, 24, "label")
            self.add_element(swimlane, "text_value", placeholder_value(name, idx + 1), value_x, row_y, 176, 24, "text_value")

        self.add_element(swimlane, "card", "", 720, 288, 696, 272, "card")
        self.add_element(swimlane, "text_subtitle", "业务信息", 744, 312, 200, 24, "text_subtitle")
        self.add_element(swimlane, "divider", "", 744, 344, 648, 1, "divider")
        business_fields = fields[6:12] or fields[:6]
        row_y = 360
        for idx, field in enumerate(business_fields[:6]):
            name = str(field.get("name", "字段")).strip() or "字段"
            base_x = 744 if idx % 2 == 0 else 1064
            value_x = 848 if idx % 2 == 0 else 1168
            if idx and idx % 2 == 0:
                row_y += 48
            self.add_element(swimlane, "label", name, base_x, row_y, 88, 24, "label")
            self.add_element(swimlane, "text_value", placeholder_value(name, idx + 7), value_x, row_y, 176, 24, "text_value")

        self.add_element(swimlane, "card", "", 24, 592, 1392, 248, "card")
        self.add_element(swimlane, "text_subtitle", "处理记录", 48, 616, 200, 24, "text_subtitle")
        self.add_element(swimlane, "divider", "", 48, 648, 1344, 1, "divider")
        record_labels = ["提交申请", "系统审核", "人工处理"]
        for idx, label in enumerate(record_labels):
            y = 664 + idx * 48
            self.add_element(swimlane, "icon", str(idx + 1), 48, y, 24, 24, "icon")
            self.add_element(swimlane, "text_body", label, 88, y, 120, 24, "text_body")
            self.add_element(swimlane, "text_hint", f"2026-03-{12 + idx:02d} 10:3{idx}", 224, y, 176, 24, "text_hint")
            self.add_element(swimlane, "text_hint", "处理人：" + placeholder_value("处理人", idx + 1), 448, y, 176, 24, "text_hint")
            self.add_element(swimlane, "text_hint", "结果：" + status_values[idx % len(status_values)], 720, y, 176, 24, "text_hint")
            if idx < len(record_labels) - 1:
                self.add_element(swimlane, "divider", "", 88, y + 32, 1240, 1, "divider")

        self._add_annotations(ctx)

    def _build_login(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "登录页")).strip()
        product_name = str(self.model.get("product_name", self.module_name)).strip() or self.module_name

        fields = self._field_rows(page)
        account_field = self._match_field(fields, ("账号", "用户名", "手机号", "邮箱", "手机"))
        password_field = self._match_field(fields, ("密码",))
        captcha_field = self._match_field(fields, ("验证码", "校验码"))
        is_admin_login = self._is_admin_login_page(page)
        show_captcha = captcha_field is not None or is_admin_login
        show_self_service_links = not is_admin_login

        account_name = str((account_field or {}).get("name", "账号")).strip() or "账号"
        password_name = str((password_field or {}).get("name", "密码")).strip() or "密码"
        captcha_name = str((captcha_field or {}).get("name", "图形验证码")).strip() or "图形验证码"
        note_text = self._login_note(page, show_captcha)

        if ctx.platform == "web":
            bg_w = WEB_UI_W
            bg_h = 864
            card_w = 448
            card_x = snap8((bg_w - card_w) / 2)
            card_y = 160 if show_captcha else 184
            inner_x = card_x + 48
            content_w = 352
            title_w = 352
        else:
            bg_w = MOBILE_UI_W
            bg_h = 816
            card_w = 328
            card_x = 24
            card_y = 104 if show_captcha else 136
            inner_x = 48
            content_w = 280
            title_w = 240
        title_y = card_y + 32
        subtitle_y = title_y + 48
        y = subtitle_y + 56

        account_input_y = y + 32
        y = account_input_y + 72
        password_input_y = y + 32
        y = password_input_y + 72

        captcha_input_y = None
        if show_captcha:
            captcha_input_y = y + 32
            y = captcha_input_y + 72

        login_btn_y = y + 16
        note_y = login_btn_y + 72
        links_y = note_y + 32
        card_bottom = links_y + (32 if show_self_service_links else 0) + 40
        card_h = snap8(card_bottom - card_y)

        self.add_element(swimlane, "bg", "", 0, 40, bg_w, bg_h, "bg")
        self.add_element(swimlane, "card", "", card_x, card_y, card_w, card_h, "card")
        self.add_element(swimlane, "text_title", product_name, inner_x, title_y, title_w, 40, "text_title")
        self.add_element(swimlane, "text_hint", f"欢迎使用{page_name}", inner_x, subtitle_y, title_w, 24, "text_hint")

        self.add_element(swimlane, "label", account_name, inner_x, account_input_y - 32, content_w, 24, "label")
        account_placeholder = "请输入" + ("后台账号" if is_admin_login else account_name)
        self.add_element(swimlane, "input", account_placeholder, inner_x, account_input_y, content_w, 48, "input")

        self.add_element(swimlane, "label", password_name, inner_x, password_input_y - 32, content_w, 24, "label")
        self.add_element(swimlane, "input", "请输入登录密码", inner_x, password_input_y, content_w, 48, "input")

        if show_captcha and captcha_input_y is not None:
            self.add_element(swimlane, "label", captcha_name, inner_x, captcha_input_y - 32, content_w, 24, "label")
            self.add_element(swimlane, "input", "请输入验证码", inner_x, captcha_input_y, 144, 48, "input")
            self.add_element(swimlane, "btn_secondary", "刷新验证码", inner_x + 160, captcha_input_y, 120, 48, "btn_secondary")

        self.add_element(swimlane, "btn_primary", "登录", inner_x, login_btn_y, content_w, 48, "btn_primary", "→ 登录成功后进入首页")
        self.add_element(swimlane, "text_hint", note_text, inner_x, note_y, content_w, 24, "text_hint")
        if show_self_service_links:
            self.add_element(swimlane, "text_link", "忘记密码？", inner_x + 48, links_y, 96, 24, "text_link", "→ 忘记密码")
            self.add_element(swimlane, "text_link", "注册账号", inner_x + 160, links_y, 96, 24, "text_link", "→ 注册")
        self._add_annotations(ctx)

    def _build_dashboard(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "数据看板")).strip()
        sections = normalize_list(page.get("sections")) or ["今日订单", "待审核任务", "库存预警", "快捷入口"]

        self.add_element(swimlane, "nav", page_name, 0, 40, 1440, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 1440, 864, "bg")
        self.add_element(swimlane, "text_subtitle", "核心指标", 24, 120, 200, 24, "text_subtitle")
        card_positions = [(24, 160), (296, 160), (568, 160), (840, 160)]
        for idx, (x, y) in enumerate(card_positions):
            self.add_element(swimlane, "card", "", x, y, 248, 120, "card")
            self.add_element(swimlane, "text_hint", sections[idx % len(sections)], x + 24, y + 24, 120, 24, "text_hint")
            self.add_element(swimlane, "text_title", str((idx + 1) * 128), x + 24, y + 56, 120, 32, "text_title")
        self.add_element(swimlane, "card", "", 24, 320, 680, 248, "card")
        self.add_element(swimlane, "text_subtitle", "待办事项", 48, 344, 120, 24, "text_subtitle")
        for idx in range(4):
            self.add_element(swimlane, "list_row", f"待办任务 {idx + 1}", 48, 384 + idx * 40, 608, 32, "list_row")
        self.add_element(swimlane, "card", "", 728, 320, 688, 248, "card")
        self.add_element(swimlane, "text_subtitle", "快捷入口", 752, 344, 120, 24, "text_subtitle")
        for idx, label in enumerate(["用户管理", "订单处理", "营销活动", "报表导出"]):
            self.add_element(swimlane, "btn_secondary", label, 752 + (idx % 2) * 184, 392 + (idx // 2) * 72, 160, 48, "btn_secondary", f"→ {label}")
        self._add_annotations(ctx)

    def _build_portal_home(self, ctx: PageContext):
        swimlane = ctx.swimlane_id
        page = ctx.page
        page_name = str(page.get("page_name", "官网首页")).strip()

        self.add_element(swimlane, "nav", page_name, 0, 40, 1440, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 1440, 864, "bg")
        self.add_element(swimlane, "card", "", 24, 128, 1392, 248, "card")
        self.add_element(swimlane, "text_title", "品牌主张 / Hero 主视觉", 56, 168, 336, 40, "text_title")
        self.add_element(swimlane, "text_body", "突出产品价值、行业方案、典型场景和信任背书。", 56, 224, 360, 48, "text_body")
        self.add_element(swimlane, "btn_primary", "立即咨询", 56, 296, 120, 48, "btn_primary", "→ 联系销售")
        self.add_element(swimlane, "btn_secondary", "查看方案", 192, 296, 120, 48, "btn_secondary", "→ 方案中心")
        self.add_element(swimlane, "img_placeholder", "官网主视觉", 920, 152, 416, 176, "img_placeholder")

        self.add_element(swimlane, "text_subtitle", "核心能力", 24, 408, 120, 24, "text_subtitle")
        for idx, label in enumerate(["行业方案", "产品能力", "客户案例"]):
            x = 24 + idx * 456
            self.add_element(swimlane, "card", "", x, 448, 424, 152, "card")
            self.add_element(swimlane, "text_subtitle", label, x + 24, 472, 160, 24, "text_subtitle")
            self.add_element(swimlane, "text_body", f"{label}的关键卖点、场景说明和可信背书。", x + 24, 512, 248, 48, "text_body")
            self.add_element(swimlane, "text_link", "查看详情", x + 24, 568, 96, 24, "text_link", f"→ {label}")

        self.add_element(swimlane, "card", "", 24, 632, 1392, 176, "card")
        self.add_element(swimlane, "text_subtitle", "案例与新闻", 48, 656, 160, 24, "text_subtitle")
        for idx, label in enumerate(["客户案例", "行业资讯", "活动报名"]):
            self.add_element(swimlane, "list_row", label, 48, 704 + idx * 40, 320, 32, "list_row")
        self.add_element(swimlane, "text_hint", "页脚：联系方式 / 公司地址 / 法务链接 / 社媒入口", 48, 776, 392, 20, "text_hint")
        self._add_annotations(ctx)

    def _build_portal_content(self, ctx: PageContext):
        swimlane = ctx.swimlane_id
        page_name = str(ctx.page.get("page_name", "官网内容页")).strip()

        self.add_element(swimlane, "nav", page_name, 0, 40, 1440, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 1440, 864, "bg")
        self.add_element(swimlane, "breadcrumb", f"首页 / 官网门户 / {page_name}", 24, 120, 440, 24, "breadcrumb")
        self.add_element(swimlane, "card", "", 24, 168, 888, 624, "card")
        self.add_element(swimlane, "text_title", page_name, 56, 200, 480, 40, "text_title")
        self.add_element(swimlane, "text_hint", "发布时间：2026-03-26  来源：官网门户", 56, 248, 264, 20, "text_hint")
        self.add_element(swimlane, "img_placeholder", "内容头图", 56, 288, 824, 168, "img_placeholder")
        for idx, text in enumerate(["产品概述", "方案优势", "实施流程", "服务保障"]):
            self.add_element(swimlane, "text_subtitle", text, 56, 488 + idx * 72, 160, 24, "text_subtitle")
            self.add_element(swimlane, "text_body", f"{text}的详细内容、说明段落和关键信息摘要。", 56, 520 + idx * 72, 496, 32, "text_body")
        self.add_element(swimlane, "card", "", 944, 168, 472, 624, "card")
        self.add_element(swimlane, "text_subtitle", "推荐入口", 968, 200, 160, 24, "text_subtitle")
        for idx, label in enumerate(["预约演示", "下载白皮书", "联系顾问", "返回首页"]):
            self.add_element(swimlane, "btn_secondary", label, 968, 248 + idx * 72, 184, 48, "btn_secondary", f"→ {label}")
        self.add_element(swimlane, "text_hint", "侧栏：相关推荐 / 联系方式 / 表单入口", 968, 568, 232, 20, "text_hint")
        self._add_annotations(ctx)

    def _build_portal_hub(self, ctx: PageContext):
        swimlane = ctx.swimlane_id
        page_name = str(ctx.page.get("page_name", "业务门户")).strip()

        self.add_element(swimlane, "nav", page_name, 0, 40, 1440, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 1440, 864, "bg")
        self.add_element(swimlane, "card", "", 24, 128, 1392, 128, "card")
        self.add_element(swimlane, "text_title", "欢迎进入业务门户", 48, 160, 280, 40, "text_title")
        self.add_element(swimlane, "text_hint", "待办消息、快捷入口、常用模块和角色提醒统一聚合。", 48, 208, 360, 20, "text_hint")

        self.add_element(swimlane, "text_subtitle", "快捷入口", 24, 288, 120, 24, "text_subtitle")
        for idx, label in enumerate(["审批中心", "数据报表", "任务工单", "通知公告"]):
            x = 24 + idx * 344
            self.add_element(swimlane, "card", "", x, 328, 320, 128, "card")
            self.add_element(swimlane, "icon", str(idx + 1), x + 24, 360, 40, 40, "icon")
            self.add_element(swimlane, "text_subtitle", label, x + 80, 360, 136, 24, "text_subtitle")
            self.add_element(swimlane, "text_hint", "进入对应业务模块", x + 80, 392, 152, 20, "text_hint")

        self.add_element(swimlane, "card", "", 24, 496, 680, 248, "card")
        self.add_element(swimlane, "text_subtitle", "我的待办", 48, 520, 120, 24, "text_subtitle")
        for idx in range(4):
            self.add_element(swimlane, "list_row", f"待处理任务 {idx + 1}", 48, 568 + idx * 40, 608, 32, "list_row")

        self.add_element(swimlane, "card", "", 728, 496, 688, 248, "card")
        self.add_element(swimlane, "text_subtitle", "通知与公告", 752, 520, 160, 24, "text_subtitle")
        for idx in range(4):
            self.add_element(swimlane, "list_row", f"系统通知 {idx + 1}", 752, 568 + idx * 40, 616, 32, "list_row")
        self._add_annotations(ctx)

    def _build_bigscreen_dashboard(self, ctx: PageContext):
        swimlane = ctx.swimlane_id
        page_name = str(ctx.page.get("page_name", "大屏指挥中心")).strip()

        self.add_element(swimlane, "nav", page_name, 0, 40, BIGSCREEN_UI_W, 64, "nav")
        self.add_element(swimlane, "bg", "", 0, 104, BIGSCREEN_UI_W, 1016, "bg")
        for idx, label in enumerate(["全局总览", "生产态势", "告警中心"]):
            self.add_element(swimlane, "btn_secondary", label, 1248 + idx * 184, 56, 160, 40, "btn_secondary", f"→ {label}")
        self.add_element(swimlane, "text_subtitle", "实时指标", 32, 136, 120, 24, "text_subtitle")
        for idx in range(6):
            x = 32 + idx * 304
            self.add_element(swimlane, "card", "", x, 176, 272, 120, "card")
            self.add_element(swimlane, "text_hint", f"指标 {idx + 1}", x + 24, 200, 112, 24, "text_hint")
            self.add_element(swimlane, "text_title", str((idx + 1) * 128), x + 24, 232, 120, 32, "text_title")
        self.add_element(swimlane, "card", "", 32, 336, 616, 312, "card")
        self.add_element(swimlane, "text_subtitle", "区域态势图", 56, 360, 160, 24, "text_subtitle")
        self.add_element(swimlane, "img_placeholder", "地图 / 态势图", 56, 408, 568, 216, "img_placeholder")
        self.add_element(swimlane, "card", "", 680, 336, 600, 312, "card")
        self.add_element(swimlane, "text_subtitle", "趋势分析", 704, 360, 160, 24, "text_subtitle")
        for idx in range(5):
            self.add_element(swimlane, "list_row", f"趋势维度 {idx + 1}", 704, 408 + idx * 40, 528, 32, "list_row")
        self.add_element(swimlane, "card", "", 1312, 336, 576, 312, "card")
        self.add_element(swimlane, "text_subtitle", "告警与事件", 1336, 360, 160, 24, "text_subtitle")
        for idx in range(5):
            self.add_element(swimlane, "list_row", f"告警事件 {idx + 1}", 1336, 408 + idx * 40, 504, 32, "list_row")
        self.add_element(swimlane, "card", "", 32, 688, 1856, 200, "card")
        self.add_element(swimlane, "text_subtitle", "场景说明与轮播控制", 56, 712, 200, 24, "text_subtitle")
        self.add_element(swimlane, "text_body", "支持大屏轮播、自动刷新、场景切换和值班态展示。", 56, 752, 320, 32, "text_body")
        self._add_annotations(ctx)

    def _build_industrial_console(self, ctx: PageContext):
        swimlane = ctx.swimlane_id
        page_name = str(ctx.page.get("page_name", "工控机控制台")).strip()
        statuses = self._status_values(ctx.page)

        self.add_element(swimlane, "nav", page_name, 0, 40, INDUSTRIAL_UI_W, 64, "nav")
        self.add_element(swimlane, "bg", "", 0, 104, INDUSTRIAL_UI_W, 856, "bg")
        self.add_element(swimlane, "text_hint", "设备在线：12 / 12   班次：白班   网络状态：正常", 24, 120, 320, 20, "text_hint")
        for idx, label in enumerate(["产线状态", "设备稼动率", "待处理告警"]):
            x = 24 + idx * 320
            self.add_element(swimlane, "card", "", x, 160, 288, 112, "card")
            self.add_element(swimlane, "text_hint", label, x + 24, 184, 136, 24, "text_hint")
            self.add_element(swimlane, "text_title", "正常" if idx == 0 else str(90 + idx), x + 24, 216, 120, 32, "text_title")
        self.add_element(swimlane, "card", "", 24, 304, 792, 360, "card")
        self.add_element(swimlane, "text_subtitle", "工艺流程区", 48, 328, 160, 24, "text_subtitle")
        for idx, label in enumerate(["上料", "检测", "分拣", "封装"]):
            x = 64 + idx * 176
            self.add_element(swimlane, "icon", str(idx + 1), x, 432, 40, 40, "icon")
            self.add_element(swimlane, "text_subtitle", label, x - 16, 488, 80, 24, "text_subtitle")
            self.add_element(swimlane, "tag", statuses[idx % len(statuses)], x - 20, 528, 88, 24, tag_style_for_status(statuses[idx % len(statuses)]))
        self.add_element(swimlane, "card", "", 848, 304, 496, 360, "card")
        self.add_element(swimlane, "text_subtitle", "报警与处置", 872, 328, 160, 24, "text_subtitle")
        for idx in range(5):
            self.add_element(swimlane, "list_row", f"报警事件 {idx + 1}", 872, 376 + idx * 40, 424, 32, "list_row")
        self.add_element(swimlane, "btn_primary", "启动产线", 24, 712, 160, 56, "btn_primary", "→ 启动流程")
        self.add_element(swimlane, "btn_secondary", "暂停产线", 208, 712, 160, 56, "btn_secondary", "→ 暂停流程")
        self.add_element(swimlane, "btn_danger_filled", "急停", 392, 712, 160, 56, "btn_danger_filled", "→ 紧急停机")
        self.add_element(swimlane, "card", "", 584, 696, 760, 160, "card")
        self.add_element(swimlane, "text_subtitle", "参数面板", 608, 720, 120, 24, "text_subtitle")
        for idx, label in enumerate(["目标产量", "当前班次", "温度阈值", "维护模式"]):
            x = 608 + (idx % 2) * 320
            y = 760 + (idx // 2) * 40
            self.add_element(swimlane, "label", label, x, y, 96, 24, "label")
            self.add_element(swimlane, "text_value", placeholder_value(label, idx + 1), x + 120, y, 144, 24, "text_value")
        self._add_annotations(ctx)

    def _build_h5_home(self, ctx: PageContext):
        swimlane = ctx.swimlane_id
        page_name = str(ctx.page.get("page_name", "H5首页")).strip()

        self._add_h5_shell(swimlane, page_name)
        self.add_element(swimlane, "search_input", "搜索活动/资讯/服务", 16, 168, 344, 40, "search_input")
        self.add_element(swimlane, "img_placeholder", "H5活动 Banner", 16, 224, 344, 120, "img_placeholder")
        for idx, label in enumerate(["新品推荐", "限时活动", "服务说明"]):
            self.add_element(swimlane, "card", "", 16, 376 + idx * 112, 344, 96, "card")
            self.add_element(swimlane, "text_subtitle", label, 32, 400 + idx * 112, 144, 24, "text_subtitle")
            self.add_element(swimlane, "text_hint", "移动 Web 传播入口 / 分享链路 / 咨询转化", 32, 432 + idx * 112, 224, 20, "text_hint")
        self.add_element(swimlane, "btn_secondary", "在线咨询", 16, 744, 112, 48, "btn_secondary", "→ 联系客服")
        self.add_element(swimlane, "btn_primary", "立即参与", 232, 744, 128, 48, "btn_primary", "→ 活动详情")
        self._add_annotations(ctx)

    def _build_h5_profile(self, ctx: PageContext):
        swimlane = ctx.swimlane_id
        page_name = str(ctx.page.get("page_name", "H5个人中心")).strip()

        self._add_h5_shell(swimlane, page_name)
        self.add_element(swimlane, "card", "", 16, 176, 344, 120, "card")
        self.add_element(swimlane, "avatar", "头像", 32, 208, 56, 56, "avatar")
        self.add_element(swimlane, "text_title", "游客 / 会员", 104, 208, 144, 32, "text_title")
        self.add_element(swimlane, "text_hint", "手机号授权后同步浏览记录与报名记录", 104, 240, 176, 20, "text_hint")
        for idx, label in enumerate(["报名记录", "浏览历史", "优惠权益", "联系客服"]):
            y = 320 + idx * 72
            self.add_element(swimlane, "list_row", label, 16, y, 344, 48, "list_row")
        self.add_element(swimlane, "btn_primary", "授权手机号", 16, 736, 344, 48, "btn_primary", "→ 手机授权")
        self._add_annotations(ctx)

    def _build_mobile_home(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "首页")).strip()

        self.add_element(swimlane, "nav", page_name, 0, 40, 376, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 376, 704, "bg")
        self.add_element(swimlane, "search_input", "搜索商品/订单/活动", 16, 112, 344, 40, "search_input")
        self.add_element(swimlane, "img_placeholder", "轮播 Banner", 16, 168, 344, 120, "img_placeholder")
        category_labels = ["分类", "优惠", "热卖", "会员"]
        for idx, label in enumerate(category_labels):
            x = 24 + idx * 88
            self.add_element(swimlane, "icon", label[0], x, 312, 48, 48, "icon")
            self.add_element(swimlane, "text_hint", label, x - 8, 368, 64, 20, "text_hint")
        card_y = 408
        for idx in range(4):
            x = 16 if idx % 2 == 0 else 192
            y = card_y + (idx // 2) * 152
            self.add_element(swimlane, "card", "", x, y, 160, 136, "card")
            self.add_element(swimlane, "img_placeholder", "商品图", x + 16, y + 16, 128, 64, "img_placeholder")
            self.add_element(swimlane, "text_body", f"商品{idx + 1}", x + 16, y + 88, 80, 24, "text_body")
            self.add_element(swimlane, "text_price", f"¥{39 + idx * 10}", x + 16, y + 112, 72, 24, "text_price")
        self.add_element(swimlane, "bottom_bar", "首页 · 分类 · 购物车 · 我的", 0, 800, 376, 56, "bottom_bar")
        self._add_annotations(ctx)

    def _build_profile(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "我的")).strip()

        self.add_element(swimlane, "bg", "", 0, 40, 376, 816, "bg")
        self.add_element(swimlane, "user_header_bg", "", 0, 40, 376, 144, "user_header_bg")
        self.add_element(swimlane, "avatar", "头像", 24, 72, 56, 56, "avatar")
        self.add_element(swimlane, "text_title", "张三", 96, 80, 120, 32, "text_title")
        self.add_element(swimlane, "text_hint", "普通会员 / 已实名", 96, 112, 144, 20, "text_hint")
        self.add_element(swimlane, "btn_secondary", "编辑资料", 248, 88, 96, 40, "btn_secondary", "→ 编辑个人资料")
        for idx, label in enumerate(["我的订单", "收货地址", "账户设置", "帮助中心", "退出登录"]):
            y = 208 + idx * 64
            self.add_element(swimlane, "list_row", label, 16, y, 344, 48, "list_row")
        self.add_element(swimlane, "bottom_bar", "首页 · 分类 · 购物车 · 我的", 0, 800, 376, 56, "bottom_bar")
        self._add_annotations(ctx)

    def _build_drawer_permission(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "授权抽屉")).strip()
        role = str(page.get("role", "系统管理员")).strip() or "系统管理员"
        status_values = self._status_values(page)
        business_rules = self._business_rules(page)

        self.add_element(swimlane, "nav", page_name, 0, 40, 1440, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 1440, 864, "bg")
        self.add_element(swimlane, "breadcrumb", f"首页 / {self.module_name} / {page_name}", 24, 112, 440, 24, "breadcrumb")

        self.add_element(swimlane, "card", "", 24, 160, 496, 680, "card")
        self.add_element(swimlane, "text_subtitle", "角色列表", 48, 184, 120, 24, "text_subtitle")
        role_names = ["运营管理员", "门店经理", "财务人员", "客服主管"]
        for idx, label in enumerate(role_names):
            y = 232 + idx * 72
            self.add_element(swimlane, "list_row", label, 48, y, 432, 48, "list_row")
            tag_text = "当前编辑" if idx == 0 else "可授权"
            self.add_element(swimlane, "tag", tag_text, 376, y + 12, 80, 24, "tag_info" if idx == 0 else "tag_pending")

        self.add_element(swimlane, "card", "", 544, 160, 872, 680, "card")
        self.add_element(swimlane, "text_subtitle", page_name, 568, 184, 200, 24, "text_subtitle")
        self.add_element(swimlane, "text_hint", f"授权角色：{role}", 568, 216, 240, 24, "text_hint")
        self.add_element(swimlane, "tag", status_values[0], 1296, 184, 88, 24, tag_style_for_status(status_values[0]))

        self.add_element(swimlane, "card", "", 568, 256, 360, 456, "card")
        self.add_element(swimlane, "text_subtitle", "菜单权限树", 592, 280, 120, 24, "text_subtitle")
        menu_rows = [
            "☑ 工作台",
            "☑ 会员营销",
            "☑ 订单履约",
            "☐ 财务结算",
            "☑ 权限审计",
            "  └ ☑ 角色管理",
            "  └ ☑ 管理员管理",
        ]
        for idx, label in enumerate(menu_rows):
            self.add_element(swimlane, "list_row", label, 592, 328 + idx * 48, 304, 40, "list_row")

        self.add_element(swimlane, "card", "", 952, 256, 432, 192, "card")
        self.add_element(swimlane, "text_subtitle", "权限分组摘要", 976, 280, 120, 24, "text_subtitle")
        summary_lines = [
            "可见模块：5 个",
            "高风险操作：删除 / 导出",
            "数据范围：所属门店",
        ]
        for idx, text in enumerate(summary_lines):
            self.add_element(swimlane, "text_body", text, 976, 328 + idx * 32, 248, 24, "text_body")

        self.add_element(swimlane, "card", "", 952, 472, 432, 240, "card")
        self.add_element(swimlane, "text_subtitle", "数据权限", 976, 496, 120, 24, "text_subtitle")
        data_scope_rows = [
            "● 仅本人创建数据",
            "○ 所属门店数据",
            "○ 所属组织全部数据",
            "○ 全部数据",
        ]
        for idx, text in enumerate(data_scope_rows):
            self.add_element(swimlane, "list_row", text, 976, 544 + idx * 40, 344, 32, "list_row")

        if business_rules:
            self.add_element(swimlane, "text_hint", business_rules[0], 568, 736, 520, 24, "text_hint")
        self.add_element(swimlane, "btn_secondary", "取消", 1168, 776, 88, 48, "btn_secondary", "→ 返回角色列表")
        self.add_element(swimlane, "btn_primary", "保存授权", 1272, 776, 112, 48, "btn_primary", "→ 保存角色权限")
        self._add_annotations(ctx)

    def _build_tree_manage(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "树管理页")).strip()
        object_name = str(page.get("object_name", "对象")).strip() or "对象"
        statuses = self._status_values(page)
        is_resource = self._is_resource_tree_page(page)

        self.add_element(swimlane, "nav", page_name, 0, 40, 1440, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 1440, 864, "bg")
        self.add_element(swimlane, "breadcrumb", f"首页 / {self.module_name} / {page_name}", 24, 112, 440, 24, "breadcrumb")
        self.add_element(swimlane, "card", "", 24, 160, 328, 680, "card")
        self.add_element(swimlane, "text_subtitle", "资源树" if is_resource else f"{object_name}层级", 48, 184, 120, 24, "text_subtitle")
        tree_rows = (
            ["▾ 系统管理", "  ▾ 角色管理", "    • 新增角色", "  ▾ 资源管理", "    • 新增资源"]
            if is_resource
            else ["▾ 总部", "  ▸ 华东大区", "  ▾ 华南大区", "    • 广州门店", "    • 深圳门店"]
        )
        for idx, label in enumerate(tree_rows):
            self.add_element(swimlane, "list_row", label, 48, 232 + idx * 56, 272, 40, "list_row")

        self.add_element(swimlane, "card", "", 376, 160, 1040, 680, "card")
        self.add_element(swimlane, "input", f"搜索{object_name}", 400, 184, 224, 48, "input")
        self.add_element(swimlane, "select", ("资源类型 ▼" if is_resource else "状态 ▼"), 640, 184, 136, 48, "select")
        self.add_element(swimlane, "btn_primary", f"新增{object_name}", 1264, 184, 128, 48, "btn_primary", f"→ 新增/编辑{object_name}弹窗")

        if is_resource:
            columns = ["资源名称", "资源类型", "资源标识", "上级资源", "排序值", "状态"]
            widths = [216, 160, 208, 184, 136, 136]
            x_positions = [400, 616, 776, 984, 1168, 1304]
        else:
            columns = ["名称", "上级", "负责人", "状态", "更新时间"]
            widths = [224, 200, 176, 144, 216]
            x_positions = [400, 624, 824, 1000, 1144]
        for idx, name in enumerate(columns):
            self.add_element(swimlane, "table_header", name, x_positions[idx], 256, widths[idx], 40, "table_header")
        action_x = 1360 if not is_resource else 1448
        action_w = 56 if not is_resource else 120
        self.add_element(swimlane, "table_header", "操作", action_x, 256, action_w, 40, "table_header")

        for row_idx in range(4):
            y = 304 + row_idx * 48
            row_style = "table_row_odd" if row_idx % 2 == 0 else "table_row_even"
            values = (
                [
                    f"资源名称{row_idx + 1}",
                    ["menu", "page", "button", "menu"][row_idx],
                    f"system:resource:{row_idx + 1}",
                    "角色管理" if row_idx % 2 == 0 else "系统管理",
                    str((row_idx + 1) * 10),
                    statuses[row_idx % len(statuses)],
                ]
                if is_resource
                else [
                    f"{object_name}{row_idx + 1}",
                    "华南大区" if row_idx % 2 == 0 else "总部",
                    placeholder_value("负责人", row_idx + 1),
                    statuses[row_idx % len(statuses)],
                    placeholder_value("更新时间", row_idx + 1),
                ]
            )
            for col_idx, value in enumerate(values):
                self.add_element(swimlane, "table_cell", value, x_positions[col_idx], y, widths[col_idx], 48, row_style)
            self.add_element(swimlane, "btn_sm", "编辑", action_x, y + 8, 48, 32, "btn_sm", f"→ 新增/编辑{object_name}弹窗")
            if is_resource:
                self.add_element(swimlane, "btn_sm_danger", "删除", action_x + 56, y + 8, 48, 32, "btn_sm_danger", f"→ {delete_modal_name(object_name)}")

        self._add_annotations(ctx)

    def _build_modal_pair(self, page: dict, platform: str):
        object_name = str(page.get("object_name", "对象")).strip() or "对象"
        fields = self._field_rows(page)
        modal_w = 800 if platform == "web" else 592
        lane_type = "modal"

        edit_ctx = self.add_swimlane(f"新增/编辑{object_name}弹窗", lane_type, modal_w, self._modal_height(fields), "swimlane_modal")
        edit_ctx.page = page
        self._build_edit_modal(edit_ctx, object_name, fields)

        delete_ctx = self.add_swimlane(delete_modal_name(object_name), lane_type, 400, 320, "swimlane_modal")
        delete_ctx.page = page
        self._build_delete_modal(delete_ctx, object_name)

    def _build_standalone_modal_form(self, ctx: PageContext):
        page = ctx.page
        self._build_edit_modal(ctx, str(page.get("page_name", "弹窗")).strip() or "弹窗", self._field_rows(page))

    def _build_confirm_modal_page(self, ctx: PageContext):
        page = ctx.page
        page_name = str(page.get("page_name", "确认弹窗")).strip() or "确认弹窗"
        swimlane = ctx.swimlane_id
        self.add_element(swimlane, "modal_bg", "", 24, 40, 352, 240, "modal_bg")
        self.add_element(swimlane, "modal_title", page_name, 48, 56, 240, 24, "modal_title")
        self.add_element(swimlane, "divider", "", 48, 96, 304, 1, "divider")
        rules = self._business_rules(page)
        body = rules[0] if rules else "请确认当前操作是否继续执行。"
        self.add_element(swimlane, "text_body", body, 48, 124, 272, 56, "text_body")
        if len(rules) > 1:
            self.add_element(swimlane, "text_hint", rules[1], 48, 184, 272, 16, "text_hint")
        actions = page.get("actions") if isinstance(page.get("actions"), list) else []
        secondary_label = "取消"
        primary_label = "确认"
        danger = any(str(action.get("kind", "")).strip() == "danger" for action in actions)
        for action in actions:
            name = str(action.get("name", "")).strip()
            kind = str(action.get("kind", "")).strip()
            if kind == "secondary" and name:
                secondary_label = name
            elif kind in {"primary", "danger"} and name:
                primary_label = name
                danger = danger or kind == "danger"
        self.add_element(swimlane, "btn_secondary", secondary_label, 112, 208, 88, 48, "btn_secondary", "→ 关闭弹窗")
        primary_style = "btn_danger_filled" if danger or any(token in primary_label for token in ("删除", "关闭", "拒绝")) else "btn_primary"
        self.add_element(swimlane, primary_style, primary_label, 216, 208, 104, 48, primary_style, f"→ {primary_label}")

    def _modal_height(self, fields: list[dict]) -> int:
        rows_h = 0
        for field in fields[:6]:
            control = str(field.get("control", "input")).strip() or "input"
            rows_h += 104 if control == "textarea" else 64
        # 头部 + 表单区 + footer 操作区，确保按钮和最后一个字段之间留出明显间距
        content_h = 256 + rows_h
        return snap8(max(448, min(content_h, 760)))

    def _build_edit_modal(self, ctx: PageContext, object_name: str, fields: list[dict]):
        swimlane = ctx.swimlane_id
        page = ctx.page
        modal_x = 40 if ctx.swimlane_w >= 800 else 24
        modal_y = 48
        modal_w = ctx.swimlane_w - modal_x * 2
        modal_h = ctx.swimlane_h - 88
        label_x = modal_x + 24
        input_x = modal_x + 128
        input_w = min(320 if ctx.swimlane_w >= 800 else 248, modal_w - 168)
        modal_title = object_name if any(token in object_name for token in ("弹窗", "抽屉", "确认")) else f"新增/编辑{object_name}"
        actions = page.get("actions") if isinstance(page.get("actions"), list) else []
        page_name = str(page.get("page_name", "")).strip()
        page_type = str(page.get("page_type", "")).strip()
        secondary_label = "取消"
        primary_label = "确认"
        primary_tooltip = "→ 保存后关闭弹窗"
        if page_type in {"web_form", "web_detail"} and any(token in page_name for token in ("弹窗", "确认", "拒绝")):
            for action in actions:
                name = str(action.get("name", "")).strip()
                if not name:
                    continue
                target = str(action.get("target", "")).strip()
                kind = str(action.get("kind", "")).strip()
                if kind == "secondary":
                    secondary_label = name
                elif kind in {"primary", "danger"}:
                    primary_label = name
                    primary_tooltip = f"→ {target}" if target else f"→ {name}"

        self.add_element(swimlane, "modal_bg", "", modal_x, modal_y, modal_w, modal_h, "modal_bg")
        self.add_element(swimlane, "modal_title", modal_title, label_x, modal_y + 16, 240, 24, "modal_title")
        self.add_element(swimlane, "divider", "", label_x, modal_y + 56, modal_w - 48, 1, "divider")
        y = modal_y + 80
        for field in fields[:6]:
            name = str(field.get("name", "字段")).strip() or "字段"
            required = as_bool(field.get("required"))
            control = str(field.get("control", "input")).strip() or "input"
            label_style = "label_required" if required else "label"
            tooltip = ""
            options = normalize_list(field.get("options"))
            if options:
                tooltip = "可选值：" + " / ".join(options)
            self.add_element(swimlane, "label", f"{name} *" if required else name, label_x, y, 88, 40, label_style)
            style_key = "textarea" if control == "textarea" else "select" if control == "select" else "input"
            height = 88 if control == "textarea" else 48
            placeholder = ("请选择" if control == "select" else "请输入") + name
            self.add_element(swimlane, control, placeholder, input_x, y, input_w, height, style_key, tooltip)
            y += 104 if control == "textarea" else 64
        footer_top = max(y + 32, modal_y + modal_h - 88)
        btn_y = min(footer_top + 24, modal_y + modal_h - 56)
        self.add_element(swimlane, "divider", "", label_x, footer_top, modal_w - 48, 1, "divider")
        self.add_element(swimlane, "btn_secondary", secondary_label, modal_x + modal_w - 216, btn_y, 88, 48, "btn_secondary", "→ 关闭弹窗")
        self.add_element(swimlane, "btn_primary", primary_label, modal_x + modal_w - 112, btn_y, 104, 48, "btn_primary", primary_tooltip)

    def _build_delete_modal(self, ctx: PageContext, object_name: str):
        swimlane = ctx.swimlane_id
        self.add_element(swimlane, "modal_bg", "", 24, 40, 352, 232, "modal_bg")
        self.add_element(swimlane, "modal_title", f"删除{object_name}确认", 48, 56, 200, 24, "modal_title")
        self.add_element(swimlane, "divider", "", 48, 96, 304, 1, "divider")
        self.add_element(swimlane, "text_body", f"删除后将无法恢复，确认删除该{object_name}吗？", 48, 128, 272, 48, "text_body")
        self.add_element(swimlane, "btn_secondary", "取消", 112, 208, 88, 48, "btn_secondary", "→ 关闭弹窗")
        self.add_element(swimlane, "btn_danger_filled", "确认删除", 216, 208, 104, 48, "btn_danger_filled", "→ 删除后返回列表")


def validate_model(model: dict, rulepack: dict | None = None):
    if not isinstance(model, dict):
        raise ValueError("page_model 必须是 JSON 对象")
    rulepack = rulepack or resolve_model_rulepack(model)
    terminal_type = normalize_terminal_type(model.get("terminal_type", ""))
    terminal_name = normalize_terminal_name(model.get("terminal_name", ""), terminal_type)
    if not terminal_type:
        raise ValueError("page_model 缺少 terminal_type")
    if terminal_type not in ALLOWED_TERMINAL_TYPES:
        raise ValueError(f"page_model terminal_type 非法: {terminal_type}")
    if not terminal_name:
        raise ValueError("page_model 缺少 terminal_name")
    expected_name = expected_terminal_name(terminal_type)
    if terminal_name != expected_name:
        raise ValueError(f"page_model terminal_name 与 terminal_type 不匹配: {terminal_name}")
    if not str(model.get("module_name", "")).strip():
        raise ValueError("page_model 缺少 module_name")
    reason = invalid_module_name_reason(model.get("module_name", ""), rulepack)
    if reason:
        raise ValueError(f"page_model 的 module_name 不合法：{reason}")
    normalized_module_name = normalize_module_name(model.get("module_name", ""), rulepack)
    if not normalized_module_name.startswith(f"{terminal_name}-"):
        raise ValueError("page_model 的 module_name 必须以 terminal_name- 作为前缀")
    pages = model.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("page_model 缺少非空 pages")
    seen = set()
    for idx, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise ValueError(f"pages[{idx}] 不是对象")
        page_id = str(page.get("page_id", "")).strip()
        page_name = str(page.get("page_name", "")).strip()
        page_type = str(page.get("page_type", "")).strip()
        if not page_id:
            raise ValueError(f"pages[{idx}] 缺少 page_id")
        if page_id in seen:
            raise ValueError(f"pages[{idx}] page_id 重复: {page_id}")
        seen.add(page_id)
        if not page_name:
            raise ValueError(f"pages[{idx}] 缺少 page_name")
        if not page_type:
            raise ValueError(f"pages[{idx}] 缺少 page_type")
        if page_type not in ALLOWED_PAGE_TYPES:
            raise ValueError(f"pages[{idx}] page_type 非法: {page_type}")
        page_archetype = str(page.get("page_archetype", "")).strip()
        if page_archetype and page_archetype not in ALLOWED_ARCHETYPES:
            raise ValueError(f"pages[{idx}] page_archetype 非法: {page_archetype}")
        page_kind = str(page.get("page_kind", "")).strip()
        if page_kind and page_kind not in ALLOWED_PAGE_KINDS:
            raise ValueError(f"pages[{idx}] page_kind 非法: {page_kind}")
        layout_mode = str(page.get("layout_mode", "")).strip()
        if layout_mode and layout_mode not in ALLOWED_LAYOUT_MODES:
            raise ValueError(f"pages[{idx}] layout_mode 非法: {layout_mode}")
        canonical_page_name = str(page.get("canonical_page_name", "")).strip()
        if "canonical_page_name" in page and not canonical_page_name:
            raise ValueError(f"pages[{idx}] canonical_page_name 不能为空")
        page["_rulepack"] = rulepack
        semantic_error = semantic_validate_page(model, page)
        if semantic_error:
            raise ValueError(f"pages[{idx}] 语义校验失败: {semantic_error}")


def semantic_validate_page(model: dict, page: dict) -> str:
    page_name = str(page.get("page_name", "")).strip()
    page_type = str(page.get("page_type", "")).strip()
    object_name = str(page.get("object_name", "")).strip()
    archetype = str(page.get("page_archetype", "")).strip()
    names = field_names(page) + table_column_names(page)
    text = page_terms(model, page)
    actions = set(action_names(page))
    rulepack = page.get("_rulepack") or resolve_model_rulepack(model)

    if page_type == "login":
        if count_matches(field_names(page), {"账号", "用户名", "手机号", "邮箱"}) < 1:
            return "登录页缺少账号字段"
        if count_matches(field_names(page), {"密码"}) < 1:
            return "登录页缺少密码字段"

    if archetype == "dispatch_board":
        if any(token in page_name for token in ("弹窗", "确认", "拒绝")):
            return "发货/调度 archetype 不能直接用于确认弹窗"
        if count_matches(names, {"路线", "司机", "客户数", "件数", "发货单", "调度", "物流"}) < 2:
            return "dispatch_board 缺少路线/司机/物流等调度字段"

    for profile in (rulepack.get("semantic_profiles") or {}).values():
        message = _semantic_error_from_profile(profile, page, text, names, actions, archetype)
        if message:
            return message

    if "资源" in text:
        if count_matches(names, {"资源名称", "资源类型", "资源标识"}) < 2:
            return "资源页面缺少资源名称/资源类型/资源标识等核心字段"

    if any(token in page_name for token in ("分类", "品类")) or archetype == "tree_manage":
        if count_matches(names, {"分类名称", "品类名称", "父级分类", "上级分类", "排序值", "关联商品数", "状态"}) < 2:
            return "分类/品类页面缺少树管理核心字段"

    if any(token in page_name for token in ("部门", "成员", "员工")):
        expected = {"部门", "成员", "员工", "账号", "角色", "手机号", "上级", "所属部门", "负责人"}
        if count_matches(names, expected) < 2 and page_type != "login":
            return "组织人员页面缺少账号/部门/角色/手机号等核心字段"

    if page_type in {"web_form", "web_detail"} and any(token in page_name for token in ("弹窗", "确认")):
        if object_name and archetype not in {"modal_form", "detail_kv", "drawer_permission", ""} and "弹窗" in page_name:
            return "弹窗页面 archetype 不匹配 modal_form/detail_kv/drawer_permission"

    return ""


def to_markdown(module_name: str, swimlanes: list[dict[str, str]], elements: list[dict[str, str]]) -> str:
    lines = [f"# {module_name}", "", "## swimlane 布局"]
    lines.append("| swimlane_id | swimlane_label | type | x | y | width | height | style_key |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for lane in swimlanes:
        lines.append(
            "| {swimlane_id} | {swimlane_label} | {type} | {x} | {y} | {width} | {height} | {style_key} |".format(
                **lane
            )
        )

    lines.extend(["", "## 元素列表"])
    lines.append("| id | parent_swimlane | component_type | value | x | y | width | height | style_key | tooltip |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for element in elements:
        lines.append(
            "| {id} | {parent_swimlane} | {component_type} | {value} | {x} | {y} | {width} | {height} | {style_key} | {tooltip} |".format(
                **element
            )
        )
    lines.append("")
    return "\n".join(lines)


def normalize_output_path(model_path: str, output_path: str) -> str:
    raw = output_path.strip()
    if not raw:
        raise ValueError("output_page_spec_md 不能为空")

    model_abs = os.path.abspath(model_path)
    model_dir = os.path.dirname(model_abs)
    model_dir_name = os.path.basename(model_dir)
    if model_dir_name == "page_models":
        artifact_root = os.path.dirname(model_dir)
    elif model_dir_name == ".prototype-generator":
        artifact_root = model_dir
    else:
        artifact_root = os.path.join(model_dir, ".prototype-generator")
    work_dir = os.path.dirname(artifact_root)
    canonical_page_specs_dir = os.path.join(artifact_root, "page_specs")

    if os.path.isdir(raw):
        raw_abs = os.path.abspath(raw)
        output_name = os.path.basename(model_path).replace("page_model_", "page_spec_").replace(".json", ".md")
        if raw_abs in {work_dir, artifact_root, os.path.join(work_dir, "page_specs")}:
            return os.path.join(canonical_page_specs_dir, output_name)
        return os.path.join(raw_abs, output_name)

    abs_output = os.path.abspath(raw)
    output_dir = os.path.dirname(abs_output)
    output_name = os.path.basename(abs_output)

    # 兼容历史调用：若 page_spec 仍指向 WORK_DIR 根目录、WORK_DIR/page_specs/ 或中间目录根，统一收敛到 .prototype-generator/page_specs/
    if output_name.startswith("page_spec_") and output_name.endswith(".md"):
        legacy_dirs = {
            work_dir,
            artifact_root,
            os.path.join(work_dir, "page_specs"),
        }
        if output_dir in legacy_dirs:
            return os.path.join(canonical_page_specs_dir, output_name)

    return abs_output


def main():
    parser = argparse.ArgumentParser(description="从 page_model JSON 生成标准化 page_spec markdown")
    parser.add_argument("page_model_json")
    parser.add_argument("output_page_spec_md")
    parser.add_argument("--rulepack", default="")
    args = parser.parse_args()

    model_path = args.page_model_json
    output_path = normalize_output_path(model_path, args.output_page_spec_md)

    with open(model_path, "r", encoding="utf-8") as f:
        model = json.load(f)

    rulepack = resolve_model_rulepack(model, args.rulepack or None)
    validate_model(model, rulepack)
    builder = PageSpecBuilder(model, rulepack)
    module_name, swimlanes, elements = builder.build()
    markdown = to_markdown(module_name, swimlanes, elements)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(
        f"OK: {output_path} ({len(swimlanes)} swimlanes, {len(elements)} elements)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
