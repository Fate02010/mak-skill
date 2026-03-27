#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path


ADMIN_NAV_GROUP_ORDER = [
    "工作台",
    "商品管理",
    "订单履约",
    "会员营销",
    "分销管理",
    "物联溯源",
    "组织权限",
    "审计中心",
    "系统配置",
]


def infer_terminal_type_from_module(module_name: str) -> tuple[str, str]:
    text = str(module_name or "").strip()
    if text.startswith("后台-"):
        return "admin", "后台"
    if text.startswith("小程序-"):
        return "miniapp", "小程序"
    if text.startswith("App-") or text.startswith("APP-"):
        return "app", "App"
    if text.startswith("H5-"):
        return "h5", "H5"
    if text.startswith("大屏-"):
        return "bigscreen", "大屏"
    if text.startswith("官网门户-"):
        return "portal", "官网门户"
    if text.startswith("工控机-"):
        return "industrial", "工控机"
    return "admin", "后台"


def safe_slug(value: str, fallback: str = "module") -> str:
    lowered = str(value or "").strip().lower()
    lowered = re.sub(r"[^0-9a-z]+", "_", lowered).strip("_")
    return lowered or fallback


def sort_admin_nav_groups(values: list[str]) -> list[str]:
    unique = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in unique:
            unique.append(text)
    return sorted(unique, key=lambda item: (ADMIN_NAV_GROUP_ORDER.index(item) if item in ADMIN_NAV_GROUP_ORDER else len(ADMIN_NAV_GROUP_ORDER), item))


def infer_page_shape(page_name: str) -> tuple[str, str]:
    text = str(page_name or "")
    if "登录" in text:
        return "login", "login"
    if any(token in text for token in ("看板", "分析", "报表", "Dashboard")):
        return "dashboard", "dashboard"
    if any(token in text for token in ("大屏", "态势", "监控台")):
        return "bigscreen_dashboard", "bigscreen_board"
    if any(token in text for token in ("工控", "HMI", "工位", "控制台")):
        return "industrial_console", "industrial_hmi"
    if "官网" in text and any(token in text for token in ("首页", "主页")):
        return "portal_home", "portal_landing"
    if "门户" in text:
        return "portal_hub", "portal_hub"
    if any(token in text for token in ("详情", "授权", "档案")):
        return "web_detail", "detail_kv"
    if any(token in text for token in ("新增", "编辑", "表单", "配置", "设置", "弹窗", "确认")):
        return "web_form", "modal_form" if any(token in text for token in ("弹窗", "确认")) else "form_page"
    if any(token in text for token in ("首页", "我的")):
        return "mobile_home", "mobile_home"
    if any(token in text for token in ("列表", "管理", "中心")):
        return "web_list", "list_table"
    return "web_detail", "detail_kv"


def field_names_from_page(page: dict | None) -> list[str]:
    source = page or {}
    values: list[str] = []
    for field in source.get("fields", []) or []:
        if isinstance(field, dict):
            name = str(field.get("name", "")).strip()
        else:
            name = str(field).strip()
        if name:
            values.append(name)
    for column in source.get("table_columns", []) or []:
        if isinstance(column, dict):
            name = str(column.get("name", "")).strip()
        else:
            name = str(column).strip()
        if name:
            values.append(name)
    return values


def is_resource_management_page(module_name: str, page_name: str, field_names: list[str] | None = None) -> bool:
    page_text = str(page_name or "")
    module_text = str(module_name or "")
    combined = f"{module_text} {page_text}"
    fields = {str(item or "").strip() for item in (field_names or []) if str(item or "").strip()}
    resource_markers = {"资源名称", "资源类型", "资源标识", "上级资源", "排序值", "路由/接口标识"}
    has_resource_fields = len(resource_markers & fields) >= 3
    if "资源管理" in combined:
        return True
    if "权限管理" in page_text and has_resource_fields:
        return True
    return False


def canonical_admin_page_name(module_name: str, page_name: str, field_names: list[str] | None = None) -> str:
    text = str(page_name or "").strip()
    if not text:
        return text
    if is_resource_management_page(module_name, text, field_names):
        suffix = "页" if text.endswith("页") or "页面" in text else ""
        return f"资源管理{suffix}".strip() or "资源管理页"
    return text


def infer_object_name(page_name: str, module_name: str = "") -> str:
    text = str(page_name or "").strip()
    for token in ("列表页", "管理页", "详情页", "表单页", "弹窗", "页面", "页", "首页", "中心"):
        text = text.replace(token, "")
    text = text.replace("确认", "").replace("新增", "").replace("编辑", "").strip(" -")
    if text:
        return text
    module = str(module_name or "")
    if "-" in module:
        module = module.split("-", 1)[1]
    return module or "对象"


def infer_nav_label(page_name: str) -> str:
    text = str(page_name or "").strip()
    for token in ("（后台）", "(后台)", "页", "页面"):
        text = text.replace(token, "")
    return text.strip() or "未命名页面"


def infer_admin_nav_group(module_name: str, page_name: str) -> str:
    module_text = str(module_name or "")
    page_text = str(page_name or "")
    combined = f"{module_text} {page_text}"
    if any(token in combined for token in ("首页", "工作台", "消息", "通知")):
        return "工作台"
    if any(token in combined for token in ("商品", "分类", "轮播", "公告", "评论", "内容")):
        return "商品管理"
    if any(token in combined for token in ("订单", "发货", "售后", "退款", "履约", "支付")):
        return "订单履约"
    if any(token in combined for token in ("会员", "优惠", "营销", "黑名单")):
        return "会员营销"
    if any(token in combined for token in ("分销", "海报", "提现")):
        return "分销管理"
    if any(token in combined for token in ("鱼塘", "运输桶", "显示屏", "批次", "设备", "溯源", "物联")):
        return "物联溯源"
    if any(token in combined for token in ("员工", "司机", "部门", "岗位", "角色", "管理员", "权限", "资源", "组织", "用户")):
        return "组织权限"
    if any(token in combined for token in ("日志", "审计", "反馈")):
        return "审计中心"
    if any(token in combined for token in ("设置", "配置", "个人", "资料", "账号")):
        return "系统配置"
    return "工作台"


def infer_admin_nav_parent(module_name: str, page_name: str, nav_group: str | None = None) -> str:
    group = str(nav_group or infer_admin_nav_group(module_name, page_name))
    page_text = str(page_name or "")
    if group == "工作台":
        if "消息" in page_text:
            return "消息中心"
        if any(token in page_text for token in ("设置", "个人")):
            return "系统设置"
        return "控制台"
    if group == "商品管理":
        if any(token in page_text for token in ("分类",)):
            return "分类管理"
        if any(token in page_text for token in ("轮播", "公告", "评论", "内容")):
            return "内容运营"
        return "商品中心"
    if group == "订单履约":
        if any(token in page_text for token in ("发货", "司机", "履约")):
            return "履约中心"
        if any(token in page_text for token in ("售后", "退款")):
            return "售后中心"
        if any(token in page_text for token in ("分析", "报表")):
            return "订单分析"
        return "订单中心"
    if group == "会员营销":
        if any(token in page_text for token in ("优惠", "营销")):
            return "营销活动"
        return "会员中心"
    if group == "分销管理":
        return "分销中心"
    if group == "物联溯源":
        if any(token in page_text for token in ("批次", "溯源")):
            return "批次溯源"
        return "基础设备"
    if group == "组织权限":
        if any(token in page_text for token in ("角色", "权限", "资源")):
            return "角色权限"
        return "组织成员"
    if group == "审计中心":
        if "反馈" in page_text:
            return "用户反馈"
        return "审计日志"
    return "系统设置"


def infer_page_semantics(
    module_name: str,
    page_name: str,
    page_type: str = "",
    page_archetype: str = "",
    field_names: list[str] | None = None,
) -> dict:
    display_name = canonical_admin_page_name(module_name, page_name, field_names)
    normalized_type, normalized_archetype = infer_page_shape(display_name)
    page_type = str(page_type or normalized_type)
    page_archetype = str(page_archetype or normalized_archetype)
    terminal_type, _ = infer_terminal_type_from_module(module_name)
    nav_label = infer_nav_label(display_name)
    shell_variant = terminal_type
    design_system = "prototype-default"
    nav_group = ""
    nav_parent = ""
    is_overlay_page = page_type == "login" or page_archetype == "modal_form" or any(token in str(display_name or "") for token in ("弹窗", "确认", "抽屉"))
    is_entry_page = False
    is_nav_page = False

    if terminal_type == "admin":
        if is_resource_management_page(module_name, page_name, field_names):
            page_type = "web_list"
            page_archetype = "tree_manage"
        if page_type == "mobile_home":
            page_type = "dashboard"
        if page_archetype == "mobile_home":
            page_archetype = "dashboard"
        design_system = "ant-pro"
        shell_variant = "auth" if page_type == "login" else "admin_console"
        nav_group = infer_admin_nav_group(module_name, display_name)
        nav_parent = infer_admin_nav_parent(module_name, display_name, nav_group)
        is_entry_page = page_type == "dashboard" or any(token in str(display_name or "") for token in ("首页", "工作台"))
        is_nav_page = (
            not is_overlay_page
            and (
                is_entry_page
                or page_type in {"dashboard", "web_list"}
                or any(token in str(display_name or "") for token in ("设置", "中心", "管理", "列表", "首页"))
            )
        )
    elif terminal_type == "portal":
        shell_variant = "portal_shell"
        design_system = "portal-marketing"
    elif terminal_type == "bigscreen":
        shell_variant = "bigscreen_shell"
        design_system = "ops-bigscreen"
    elif terminal_type == "industrial":
        shell_variant = "industrial_shell"
        design_system = "industrial-console"
    else:
        shell_variant = f"{terminal_type}_shell"
        design_system = f"{terminal_type}-default"

    nav_context = " / ".join(item for item in (nav_group, nav_parent) if item)
    return {
        "terminal_type": terminal_type,
        "page_type": page_type,
        "page_archetype": page_archetype,
        "display_page_name": display_name,
        "nav_group": nav_group,
        "nav_parent": nav_parent,
        "nav_label": nav_label,
        "nav_context": nav_context,
        "is_nav_page": is_nav_page,
        "is_entry_page": is_entry_page,
        "is_overlay_page": is_overlay_page,
        "shell_variant": shell_variant,
        "design_system": design_system,
    }


def default_actions_for_page(page_name: str, object_name: str) -> list[str]:
    text = str(page_name or "")
    if "登录" in text:
        return ["登录"]
    if any(token in text for token in ("详情", "授权", "档案")):
        return ["返回", "编辑"]
    if any(token in text for token in ("弹窗", "确认")):
        return ["确认", "取消"]
    if any(token in text for token in ("表单", "新增", "编辑", "配置", "设置")):
        return ["提交", "取消"]
    if any(token in text for token in ("看板", "分析", "报表", "首页")):
        return ["查看详情"]
    if any(token in text for token in ("列表", "管理", "中心")):
        return [f"新增{object_name}", "编辑", "删除", "查看详情"]
    return ["查看详情"]


def default_states_for_page(page_name: str) -> list[str]:
    text = str(page_name or "")
    if "登录" in text:
        return ["默认", "验证码错误", "账号锁定"]
    if any(token in text for token in ("看板", "分析", "报表")):
        return ["正常", "无数据", "刷新失败"]
    if any(token in text for token in ("列表", "管理", "中心")):
        return ["启用", "停用", "草稿"]
    return ["正常", "处理中", "异常"]


def parse_requirement_modules(requirements_path: str | os.PathLike[str]) -> dict[str, dict]:
    root = Path(requirements_path)
    if root.is_file():
        files = [root]
    else:
        files = sorted(
            path
            for path in root.glob("*.md")
            if path.name.startswith("详细需求文档_") and path.name != "详细需求文档_overview.md"
        )
    modules: dict[str, dict] = {}
    for path in files:
        module_name = path.stem.replace("详细需求文档_", "", 1)
        content = path.read_text(encoding="utf-8")
        entry = modules.setdefault(module_name, {"module_name": module_name, "doc_path": str(path), "pages": {}})
        entry["pages"].update(_parse_requirement_pages(content, module_name))
    return modules


def _parse_requirement_pages(content: str, module_name: str) -> dict[str, dict]:
    pages: dict[str, dict] = {}
    lines = content.splitlines()
    current_pages: list[str] = []
    field_bucket: list[str] = []
    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.startswith("- **页面/界面：**"):
            if current_pages:
                _assign_fields(pages, current_pages, field_bucket, module_name)
            raw_pages = line.split("**页面/界面：**", 1)[1].strip()
            current_pages = [item.strip() for item in re.split(r"[、，,；;]\s*", raw_pages) if item.strip()]
            field_bucket = []
            for page_name in current_pages:
                page = pages.setdefault(page_name, _empty_page(page_name, module_name))
                page["doc_line"] = idx + 1
            continue
        if current_pages and line.startswith("- ") and not line.startswith("- **"):
            value = line[2:].strip()
            value = value.split("（", 1)[0].split("(", 1)[0].strip()
            if value and value not in field_bucket and len(value) <= 40:
                field_bucket.append(value)
            continue
        if current_pages and line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if cells and cells[0] not in {"字段名", "字段", "列名", "--------", "------", "---"}:
                field = cells[0].strip()
                if field and field not in field_bucket and len(field) <= 40:
                    field_bucket.append(field)
            continue
        if current_pages and line.startswith("#### "):
            _assign_fields(pages, current_pages, field_bucket, module_name)
            current_pages = []
            field_bucket = []
    if current_pages:
        _assign_fields(pages, current_pages, field_bucket, module_name)
    return pages


def _empty_page(page_name: str, module_name: str) -> dict:
    page_type, archetype = infer_page_shape(page_name)
    object_name = infer_object_name(page_name, module_name)
    return {
        "page_name": page_name,
        "page_type": page_type,
        "page_archetype": archetype,
        "object_name": object_name,
        "fields": [],
        "actions": default_actions_for_page(page_name, object_name),
        "states": default_states_for_page(page_name),
    }


def _assign_fields(pages: dict[str, dict], current_pages: list[str], field_bucket: list[str], module_name: str):
    for page_name in current_pages:
        page = pages.setdefault(page_name, _empty_page(page_name, module_name))
        for field in field_bucket:
            if field not in page["fields"]:
                page["fields"].append(field)
