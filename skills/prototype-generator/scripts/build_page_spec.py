#!/usr/bin/env python3
"""
build_page_spec.py - 从 page_model JSON 生成标准化 page_spec markdown。

用法:
    python3 build_page_spec.py <page_model_json> <output_page_spec_md>

page_model 采用强约束 JSON，示例:
{
  "module_name": "用户模块",
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
from dataclasses import dataclass


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


def delete_modal_name(object_name: str) -> str:
    value = str(object_name or "").strip() or "对象"
    return f"删除{value}确认弹窗"


def normalize_module_name(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^(page[_-]?spec|spec|tmp)\s*[:：_-]?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", "", text)
    replacements = {
        "后台-通用与看板": "后台-工作台",
        "后台-人员与权限": "后台-组织权限",
        "后台-商品与内容": "后台-商品管理",
        "后台-会员与营销": "后台-会员运营",
        "后台-订单与履约": "后台-订单管理",
        "后台-物联与溯源基础数据": "后台-溯源基础数据",
        "小程序-账号与首页": "小程序-首页",
        "小程序-商品与交易": "小程序-商品交易",
        "小程序-订单与会员": "小程序-订单中心",
    }
    return replacements.get(text, text)


def invalid_module_name_reason(value: str) -> str:
    text = normalize_module_name(value)
    raw = str(value or "").strip()
    if not text:
        return "module_name 为空"
    if re.search(r"(page[_-]?spec|spec|tmp)\s*[:：_-]?", raw, flags=re.IGNORECASE):
        return "module_name 含中间产物前缀"
    if text in {"APP系统", "后台管理", "小程序端", "移动端", "Web端", "前台"}:
        return "module_name 仍是系统层命名"
    if text in {
        "后台-人员与权限",
        "后台-商品与内容",
        "后台-会员与营销",
        "后台-订单与履约",
        "后台-通用与看板",
        "后台-物联与溯源基础数据",
        "小程序-账号与首页",
        "小程序-商品与交易",
        "小程序-订单与会员",
    }:
        return "module_name 仍是聚合模块命名，应拆分为更具体业务模块"
    if re.match(r"^(后台|小程序|H5|APP|App|Web|移动端)[-—].*[与和及/].+", text):
        return "module_name 同时包含终端前缀和多个业务域，应拆分"
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
        return MOBILE_UI_W if self.platform == "mobile" else WEB_UI_W

    @property
    def ann_x(self) -> int:
        return MOBILE_ANN_X if self.platform == "mobile" else WEB_ANN_X

    @property
    def ann_w(self) -> int:
        return MOBILE_ANN_W if self.platform == "mobile" else WEB_ANN_W


class PageSpecBuilder:
    def __init__(self, model: dict):
        self.model = model
        self.module_name = normalize_module_name(model.get("module_name", "模块"))
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
        platform = "mobile" if lane_type == "mobile" else "web"
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

        if page_type in {"mobile_list", "mobile_form", "mobile_detail", "login", "mobile_home", "profile"}:
            lane_type = "mobile"
            width = MOBILE_SWIMLANE_W
            height = MOBILE_SWIMLANE_H
        elif page_type in {"web_list", "web_form", "web_detail", "dashboard"}:
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
            "swimlane",
        )
        ctx.page = page

        if page_type == "web_list":
            self._build_web_list(ctx)
        elif page_type == "mobile_list":
            self._build_mobile_list(ctx)
        elif page_type == "web_form":
            self._build_web_form(ctx)
        elif page_type == "mobile_form":
            self._build_mobile_form(ctx)
        elif page_type == "mobile_detail":
            self._build_mobile_detail(ctx)
        elif page_type == "web_detail":
            self._build_web_detail(ctx)
        elif page_type == "login":
            self._build_login(ctx)
        elif page_type == "dashboard":
            self._build_dashboard(ctx)
        elif page_type == "mobile_home":
            self._build_mobile_home(ctx)
        elif page_type == "profile":
            self._build_profile(ctx)

        if page_type in {"web_list", "mobile_list"} and as_bool(page.get("needs_crud")):
            self._build_modal_pair(page, lane_type)

    def _annotation_value(self, page: dict) -> str:
        targets = normalize_list(page.get("jump_targets"))
        jump_text = " / ".join(targets[:4]) if targets else "本模块内流转"
        purpose = str(page.get("purpose", "承载核心业务操作")).strip()
        role = str(page.get("role", "业务角色")).strip()
        main_action = ""
        actions = page.get("actions")
        if isinstance(actions, list) and actions:
            main_action = str(actions[0].get("name", "")).strip()
        if not main_action:
            main_action = "查看与操作"
        page_name = str(page.get("page_name", "页面")).strip()
        return (
            f"页面：{page_name}&#xa;"
            f"用途：{purpose}&#xa;"
            f"角色：{role}&#xa;"
            f"主操作：{main_action}&#xa;"
            f"跳转去向：{jump_text}"
        )

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
        if as_bool(page.get("needs_crud")):
            self.add_element(swimlane, "btn_primary", f"新增{object_name}", 1296, 160, 120, 48, "btn_primary", f"→ 新增/编辑{object_name}弹窗")
        else:
            self.add_element(swimlane, "text_hint", "共 128 条记录", 1248, 172, 168, 24, "text_hint")

        columns = self._table_columns(page)
        widths = self._column_widths(columns)
        x_positions = []
        x = 24
        for width in widths:
            x_positions.append(x)
            x += width

        header_y = 224
        row_start_y = 272
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
            if as_bool(page.get("needs_crud")):
                self.add_element(swimlane, "btn_sm", "编辑", 1296, y + 8, 48, 32, "btn_sm", f"→ 新增/编辑{object_name}弹窗")
                self.add_element(swimlane, "btn_sm_danger", "删除", 1352, y + 8, 48, 32, "btn_sm_danger", f"→ {delete_modal_name(object_name)}")
            else:
                self.add_element(swimlane, "btn_sm", "查看", 1320, y + 8, 56, 32, "btn_sm", f"→ {page_name}详情")

        pagination_y = row_start_y + 5 * 48 + 24
        self.add_element(swimlane, "pagination", "共 128 条 第 1/6 页 上一页 下一页", 24, pagination_y, 344, 40, "pagination")
        self.add_element(swimlane, "annotation_card", self._annotation_value(page), WEB_ANN_X, 40, WEB_ANN_W, 120, "annotation_card")

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
        self.add_element(swimlane, "annotation_card", self._annotation_value(page), MOBILE_ANN_X, 40, MOBILE_ANN_W, 120, "annotation_card")

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
        self.add_element(swimlane, "annotation_card", self._annotation_value(page), WEB_ANN_X, 40, WEB_ANN_W, 120, "annotation_card")

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
        self.add_element(swimlane, "annotation_card", self._annotation_value(page), MOBILE_ANN_X, 40, MOBILE_ANN_W, 120, "annotation_card")

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

        self.add_element(swimlane, "annotation_card", self._annotation_value(page), MOBILE_ANN_X, 40, MOBILE_ANN_W, 120, "annotation_card")

    def _build_web_detail(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "详情页")).strip()
        fields = self._field_rows(page)

        self.add_element(swimlane, "nav", page_name, 0, 40, 1440, 56, "nav")
        self.add_element(swimlane, "bg", "", 0, 96, 1440, 864, "bg")
        self.add_element(swimlane, "breadcrumb", f"首页 / {self.module_name} / {page_name}", 24, 112, 440, 24, "breadcrumb")
        self.add_element(swimlane, "btn_secondary", "返回列表", 1296, 104, 120, 40, "btn_secondary", "→ 返回来源页")
        self.add_element(swimlane, "card", "", 24, 160, 1392, 448, "card")
        self.add_element(swimlane, "text_subtitle", "基础信息", 48, 184, 200, 24, "text_subtitle")

        row_y = 232
        for idx, field in enumerate(fields[:8]):
            name = str(field.get("name", "字段")).strip() or "字段"
            base_x = 48 if idx % 2 == 0 else 480
            value_x = 176 if idx % 2 == 0 else 608
            if idx and idx % 2 == 0:
                row_y += 40
            self.add_element(swimlane, "label", name, base_x, row_y, 120, 32, "label")
            sample = placeholder_value(name, idx + 1)
            self.add_element(swimlane, "text_value", sample, value_x, row_y, 280, 32, "text_value")

        status_y = row_y + 56
        status = self._status_values(page)[0]
        self.add_element(swimlane, "label", "当前状态", 48, status_y, 120, 32, "label")
        self.add_element(swimlane, "tag", status, 176, status_y, 80, 24, tag_style_for_status(status))
        self.add_element(swimlane, "btn_primary", "编辑", 48, status_y + 56, 120, 48, "btn_primary", f"→ 编辑{page_name}")
        object_name = str(page.get("object_name", page_name)).strip() or page_name
        self.add_element(swimlane, "btn_danger_filled", "删除", 184, status_y + 56, 120, 48, "btn_danger_filled", f"→ {delete_modal_name(object_name)}")
        self.add_element(swimlane, "annotation_card", self._annotation_value(page), WEB_ANN_X, 40, WEB_ANN_W, 120, "annotation_card")

    def _build_login(self, ctx: PageContext):
        page = ctx.page
        swimlane = ctx.swimlane_id
        page_name = str(page.get("page_name", "登录页")).strip()
        product_name = str(self.model.get("product_name", self.module_name)).strip() or self.module_name

        self.add_element(swimlane, "bg", "", 0, 40, 376, 816, "bg")
        self.add_element(swimlane, "card", "", 24, 208, 328, 376, "card")
        self.add_element(swimlane, "text_title", product_name, 48, 232, 240, 40, "text_title")
        self.add_element(swimlane, "text_hint", f"欢迎使用{page_name}", 48, 280, 240, 24, "text_hint")
        self.add_element(swimlane, "label", "账号", 48, 320, 280, 24, "label")
        self.add_element(swimlane, "input", "请输入手机号/邮箱", 48, 352, 280, 48, "input")
        self.add_element(swimlane, "label", "密码", 48, 424, 280, 24, "label")
        self.add_element(swimlane, "input", "请输入密码", 48, 456, 280, 48, "input")
        self.add_element(swimlane, "btn_primary", "登录", 48, 528, 280, 48, "btn_primary", "→ 登录成功后进入首页")
        self.add_element(swimlane, "text_link", "忘记密码？", 96, 592, 96, 24, "text_link", "→ 忘记密码")
        self.add_element(swimlane, "text_link", "注册账号", 208, 592, 96, 24, "text_link", "→ 注册")
        self.add_element(swimlane, "annotation_card", self._annotation_value(page), MOBILE_ANN_X, 40, MOBILE_ANN_W, 120, "annotation_card")

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
        self.add_element(swimlane, "annotation_card", self._annotation_value(page), WEB_ANN_X, 40, WEB_ANN_W, 120, "annotation_card")

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
        self.add_element(swimlane, "annotation_card", self._annotation_value(page), MOBILE_ANN_X, 40, MOBILE_ANN_W, 120, "annotation_card")

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
        self.add_element(swimlane, "annotation_card", self._annotation_value(page), MOBILE_ANN_X, 40, MOBILE_ANN_W, 120, "annotation_card")

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

    def _modal_height(self, fields: list[dict]) -> int:
        rows_h = 0
        for field in fields[:6]:
            control = str(field.get("control", "input")).strip() or "input"
            rows_h += 104 if control == "textarea" else 64
        # 头部 + 表单区 + footer 操作区，确保按钮不会压住最后一个字段
        content_h = 224 + rows_h
        return snap8(max(416, min(content_h, 720)))

    def _build_edit_modal(self, ctx: PageContext, object_name: str, fields: list[dict]):
        swimlane = ctx.swimlane_id
        modal_w = 720 if ctx.swimlane_w >= 800 else 520
        modal_h = ctx.swimlane_h - 64
        self.add_element(swimlane, "modal_bg", "", 24, 40, modal_w, modal_h, "modal_bg")
        self.add_element(swimlane, "modal_title", f"新增/编辑{object_name}", 48, 56, 240, 24, "modal_title")
        self.add_element(swimlane, "divider", "", 48, 96, modal_w - 48, 1, "divider")
        y = 120
        input_w = 320 if ctx.swimlane_w >= 800 else 248
        for field in fields[:6]:
            name = str(field.get("name", "字段")).strip() or "字段"
            required = as_bool(field.get("required"))
            control = str(field.get("control", "input")).strip() or "input"
            label_style = "label_required" if required else "label"
            tooltip = ""
            options = normalize_list(field.get("options"))
            if options:
                tooltip = "可选值：" + " / ".join(options)
            self.add_element(swimlane, "label", f"{name} *" if required else name, 48, y, 88, 40, label_style)
            style_key = "textarea" if control == "textarea" else "select" if control == "select" else "input"
            height = 88 if control == "textarea" else 48
            placeholder = ("请选择" if control == "select" else "请输入") + name
            self.add_element(swimlane, control, placeholder, 152, y, input_w, height, style_key, tooltip)
            y += 104 if control == "textarea" else 64
        footer_y = max(y + 24, ctx.swimlane_h - 96)
        self.add_element(swimlane, "divider", "", 48, footer_y - 24, modal_w - 48, 1, "divider")
        self.add_element(swimlane, "btn_secondary", "取消", modal_w - 216, footer_y, 88, 48, "btn_secondary", "→ 关闭弹窗")
        self.add_element(swimlane, "btn_primary", "确认", modal_w - 112, footer_y, 104, 48, "btn_primary", "→ 保存后关闭弹窗")

    def _build_delete_modal(self, ctx: PageContext, object_name: str):
        swimlane = ctx.swimlane_id
        self.add_element(swimlane, "modal_bg", "", 24, 40, 352, 232, "modal_bg")
        self.add_element(swimlane, "modal_title", f"删除{object_name}确认", 48, 56, 200, 24, "modal_title")
        self.add_element(swimlane, "divider", "", 48, 96, 304, 1, "divider")
        self.add_element(swimlane, "text_body", f"删除后将无法恢复，确认删除该{object_name}吗？", 48, 128, 272, 48, "text_body")
        self.add_element(swimlane, "btn_secondary", "取消", 112, 208, 88, 48, "btn_secondary", "→ 关闭弹窗")
        self.add_element(swimlane, "btn_danger_filled", "确认删除", 216, 208, 104, 48, "btn_danger_filled", "→ 删除后返回列表")


def validate_model(model: dict):
    if not isinstance(model, dict):
        raise ValueError("page_model 必须是 JSON 对象")
    if not str(model.get("module_name", "")).strip():
        raise ValueError("page_model 缺少 module_name")
    reason = invalid_module_name_reason(model.get("module_name", ""))
    if reason:
        raise ValueError(f"page_model 的 module_name 不合法：{reason}")
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
    work_dir = model_dir

    if os.path.isdir(raw):
        return os.path.join(raw, os.path.basename(model_path).replace("page_model_", "page_spec_").replace(".json", ".md"))

    abs_output = os.path.abspath(raw)
    output_dir = os.path.dirname(abs_output)
    output_name = os.path.basename(abs_output)

    # 兼容历史调用：如果把 page_spec 文件直接指向 WORK_DIR 根目录，自动收敛到 page_specs/ 子目录
    if output_dir == work_dir and output_name.startswith("page_spec_") and output_name.endswith(".md"):
        return os.path.join(work_dir, "page_specs", output_name)

    return abs_output


def main():
    if len(sys.argv) != 3:
        print(f"用法: python3 {sys.argv[0]} <page_model_json> <output_page_spec_md>", file=sys.stderr)
        sys.exit(1)

    model_path = sys.argv[1]
    output_path = normalize_output_path(model_path, sys.argv[2])

    with open(model_path, "r", encoding="utf-8") as f:
        model = json.load(f)

    validate_model(model)
    builder = PageSpecBuilder(model)
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
