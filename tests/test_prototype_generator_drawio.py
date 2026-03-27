import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "prototype-generator"
SCRIPTS_DIR = SKILL_DIR / "scripts"
STEPS_DIR = SKILL_DIR / "steps"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _read_frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError(f"missing frontmatter in {path}")
    _, rest = text.split("---\n", 1)
    frontmatter, _ = rest.split("\n---\n", 1)
    return frontmatter


BUILD_PAGE_SPEC = _load_module("build_page_spec_test", SCRIPTS_DIR / "build_page_spec.py")
RENDER = _load_module("render_test", SCRIPTS_DIR / "render.py")
VALIDATE = _load_module("validate_test", SCRIPTS_DIR / "validate.py")
HTML_UTILS = _load_module("html_utils_test", SCRIPTS_DIR / "html_utils.py")
RENDER_HTML = _load_module("render_html_test", SCRIPTS_DIR / "render_html.py")
REFERENCE_UTILS = _load_module("reference_utils_test", SCRIPTS_DIR / "reference_utils.py")
AUTOFIX = _load_module("autofix_test", SCRIPTS_DIR / "autofix.py")
REQ_COMPRESS = _load_module("requirements_compression_test", SCRIPTS_DIR / "requirements_compression.py")
VALIDATE_HTML = _load_module("validate_html_test", SCRIPTS_DIR / "validate_html.py")
HTML_CONSISTENCY = _load_module("html_consistency_test", SCRIPTS_DIR / "check_html_consistency.py")
RUN_HTML_PIPELINE_MODULE = _load_module("run_html_pipeline_test", SCRIPTS_DIR / "run_html_pipeline.py")
MERGE = _load_module("merge_test", SCRIPTS_DIR / "merge.py")
CONSISTENCY = _load_module("consistency_test", SCRIPTS_DIR / "check_prototype_consistency.py")
BRIEF_CONSISTENCY = _load_module("brief_consistency_test", SCRIPTS_DIR / "check_module_brief_consistency.py")
CONTEXT_BUDGET = _load_module("context_budget_test", SCRIPTS_DIR / "check_context_budget.py")
RUN_PIPELINE = SCRIPTS_DIR / "run_drawio_pipeline.py"
RUN_HTML_PIPELINE = SCRIPTS_DIR / "run_html_pipeline.py"
RUN_AUTO_PIPELINE = SCRIPTS_DIR / "run_autonomous_pipeline.py"


def _build_page_spec_markdown(model: dict) -> str:
    BUILD_PAGE_SPEC.validate_model(model)
    builder = BUILD_PAGE_SPEC.PageSpecBuilder(model)
    module_name, swimlanes, elements = builder.build()
    return BUILD_PAGE_SPEC.to_markdown(module_name, swimlanes, elements)


def _parse_spec(markdown: str):
    return RENDER.parse_page_spec(markdown)


def _render_drawio(markdown: str, tmpdir: Path, diagram_id: str) -> Path:
    styles = RENDER.parse_styles((STEPS_DIR / "step5-component-styles.md").read_text(encoding="utf-8"))
    module_name, swimlanes, elements = RENDER.parse_page_spec(markdown)
    diagram_xml = RENDER.generate_xml(diagram_id, module_name, swimlanes, elements, styles).strip()
    drawio_path = tmpdir / f"{diagram_id}.drawio"
    drawio_path.write_text(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<mxfile host=\"app.diagrams.net\" modified=\"2026-03-25T00:00:00.000Z\" "
        "agent=\"prototype-generator-test\" version=\"24.0.0\" type=\"device\">\n"
        f"{diagram_xml}\n"
        "</mxfile>\n",
        encoding="utf-8",
    )
    return drawio_path


def _write_drawio(tmpdir: Path, diagram_id: str, diagram_name: str, swimlane_name: str, swimlane_width: int, cells: str) -> Path:
    drawio_path = tmpdir / f"{diagram_id}.drawio"
    drawio_path.write_text(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<mxfile host=\"app.diagrams.net\" modified=\"2026-03-25T00:00:00.000Z\" "
        "agent=\"prototype-generator-test\" version=\"24.0.0\" type=\"device\">\n"
        f"<diagram id=\"{diagram_id}\" name=\"{diagram_name}\">\n"
        f"  <mxGraphModel dx=\"1280\" dy=\"900\" grid=\"0\" gridSize=\"10\" guides=\"1\" tooltips=\"1\" connect=\"1\" arrows=\"1\" fold=\"1\" page=\"1\" pageScale=\"1\" pageWidth=\"1780\" pageHeight=\"1000\" math=\"0\" shadow=\"0\">\n"
        "    <root>\n"
        "      <mxCell id=\"0\" />\n"
        "      <mxCell id=\"1\" parent=\"0\" />\n"
        f"      <mxCell id=\"S1\" value=\"{swimlane_name}\" style=\"swimlane;startSize=30;fillColor=#f0f4ff;strokeColor=#1e88e5;fontStyle=1;fontSize=13;\" vertex=\"1\" parent=\"1\"><mxGeometry x=\"16\" y=\"16\" width=\"{swimlane_width}\" height=\"960\" as=\"geometry\" /></mxCell>\n"
        f"{cells}\n"
        "    </root>\n"
        "  </mxGraphModel>\n"
        "</diagram>\n"
        "</mxfile>\n",
        encoding="utf-8",
    )
    return drawio_path


def _rule_result(report: dict, rule: str) -> dict:
    for item in report["results"]:
        if item["rule"] == rule:
            return item
    raise AssertionError(f"missing rule {rule}")


def _report_message(report: dict) -> str:
    return json.dumps(
        {
            "summary": report["summary"],
            "results": report["results"],
        },
        ensure_ascii=False,
    )


def _find_element(elements: list[dict], *, parent: Optional[str] = None, style_key: Optional[str] = None, value: Optional[str] = None) -> dict:
    for element in elements:
        if parent is not None and element.get("parent_swimlane") != parent:
            continue
        if style_key is not None and element.get("style_key") != style_key:
            continue
        if value is not None and element.get("value") != value:
            continue
        return element
    raise AssertionError(f"missing element parent={parent!r} style_key={style_key!r} value={value!r}")


def _int_value(element: dict, key: str) -> int:
    return int(element[key])


def _terminalized(model: dict, terminal_type: str = "admin", terminal_name: str = "后台") -> dict:
    return {
        "terminal_type": terminal_type,
        "terminal_name": terminal_name,
        **model,
    }


def _drawer_permission_model() -> dict:
    return _terminalized({
        "module_name": "后台-组织权限",
        "module_key": "admin_auth",
        "pages": [
            {
                "page_id": "role_permission",
                "page_name": "角色授权抽屉",
                "page_type": "web_detail",
                "page_archetype": "drawer_permission",
                "object_name": "角色",
                "role": "系统管理员",
                "purpose": "配置菜单与数据权限",
                "nav_context": "后台-权限审计 / 角色管理",
                "fields": [
                    {"name": "角色名称", "control": "input", "required": True, "validation": "2-20位"},
                    {
                        "name": "数据范围",
                        "control": "select",
                        "required": True,
                        "options": ["本人", "所属门店", "全部"],
                        "validation": "",
                    },
                ],
                "status_values": ["已生效", "待生效", "已禁用"],
                "actions": [{"name": "保存授权", "target": "角色管理", "kind": "primary"}],
                "jump_targets": ["角色管理列表", "管理员管理页"],
                "business_rules": ["仅系统管理员可调整菜单权限", "禁用角色不可继续分配管理员"],
                "table_behaviors": {"data_scope": "默认沿用角色数据范围"},
                "states": {"loading": "保存中按钮禁用", "error": "保存失败保留勾选结果"},
            }
        ],
    })


def _detail_model() -> dict:
    return _terminalized({
        "module_name": "后台-订单管理",
        "module_key": "admin_order",
        "pages": [
            {
                "page_id": "order_detail",
                "page_name": "订单详情页（后台）",
                "page_type": "web_detail",
                "page_archetype": "detail_kv",
                "object_name": "订单",
                "role": "客服/履约",
                "purpose": "处理订单发货与售后",
                "nav_context": "后台-订单履约 / 订单管理",
                "fields": [
                    {"name": "订单编号", "control": "input", "required": True, "validation": "系统自动生成"},
                    {"name": "订单状态", "control": "select", "required": True, "options": ["待发货", "待收货", "已完成"], "validation": ""},
                    {"name": "用户信息", "control": "input", "required": True, "validation": ""},
                    {"name": "收货地址", "control": "input", "required": True, "validation": ""},
                    {"name": "商品明细", "control": "textarea", "required": True, "validation": ""},
                    {"name": "金额明细", "control": "textarea", "required": True, "validation": ""},
                    {"name": "支付信息", "control": "textarea", "required": True, "validation": ""},
                    {"name": "售后信息", "control": "textarea", "required": False, "validation": ""},
                    {"name": "备注记录", "control": "textarea", "required": False, "validation": "200字以内"},
                    {"name": "溯源摘要", "control": "input", "required": False, "validation": ""},
                    {"name": "操作区", "control": "input", "required": True, "validation": ""},
                ],
                "status_values": ["待发货", "已发货", "已完成", "已退款"],
                "actions": [
                    {"name": "发货", "target": "发货单详情页", "kind": "primary"},
                    {"name": "备注", "target": "订单备注弹窗", "kind": "secondary"},
                    {"name": "关闭", "target": "关闭订单确认弹窗", "kind": "danger"},
                ],
                "jump_targets": ["发货单详情页", "退款确认弹窗"],
                "business_rules": ["仅待发货订单可发货", "退款完成后订单不可再次发货"],
                "states": {
                    "loading": "详情加载中显示骨架屏",
                    "error": "详情加载失败可重试",
                    "transition": "待发货 → 已发货 → 已完成 / 已退款",
                },
            }
        ],
    })


def _login_model() -> dict:
    return _terminalized({
        "module_name": "后台-登录页",
        "module_key": "admin_login",
        "product_name": "渔易购后台管理系统",
        "pages": [
            {
                "page_id": "admin_login",
                "page_name": "后台登录页",
                "page_type": "login",
                "page_archetype": "login",
                "object_name": "管理员",
                "role": "后台用户/管理员",
                "purpose": "后台统一登录入口",
                "fields": [
                    {"name": "账号", "control": "input", "required": True, "validation": "请输入后台账号"},
                    {"name": "密码", "control": "input", "required": True, "validation": "请输入登录密码"},
                    {"name": "图形验证码", "control": "input", "required": True, "validation": "连续失败后强制校验"},
                ],
                "business_rules": ["连续失败超过 5 次将触发验证码限制"],
                "jump_targets": ["登录后台首页"],
                "states": {"error": "验证码错误时保留账号并刷新验证码"},
            }
        ],
    })


def _marketing_list_model() -> dict:
    return _terminalized({
        "module_name": "后台-会员运营",
        "module_key": "admin_marketing",
        "pages": [
            {
                "page_id": "campaign_list",
                "page_name": "营销活动管理页",
                "page_type": "web_list",
                "page_archetype": "list_table",
                "object_name": "营销活动",
                "role": "运营管理员",
                "purpose": "维护满减、优惠券和活动状态",
                "needs_crud": True,
                "fields": [
                    {"name": "活动名称", "control": "input", "required": True, "validation": "2-30位"},
                    {"name": "活动类型", "control": "select", "required": True, "options": ["满减", "优惠券"], "validation": ""},
                    {"name": "活动时间", "control": "input", "required": True, "validation": "开始时间不能晚于结束时间"},
                    {"name": "关联商品", "control": "input", "required": True, "validation": "至少关联一个商品"},
                    {"name": "活动说明", "control": "textarea", "required": False, "validation": "200字以内"},
                    {"name": "活动状态", "control": "select", "required": True, "options": ["未开始", "进行中", "已结束"], "validation": ""},
                ],
                "table_columns": ["活动名称", "活动类型", "开始时间", "结束时间", "关联商品数", "活动状态"],
                "status_values": ["未开始", "进行中", "已结束"],
                "actions": [{"name": "编辑", "target": "新增/编辑营销活动弹窗", "kind": "primary"}],
                "jump_targets": ["新增/编辑营销活动弹窗"],
            }
        ],
    })


def _shipping_modal_model() -> dict:
    return _terminalized({
        "module_name": "后台-订单管理",
        "module_key": "admin_order_shipping",
        "pages": [
            {
                "page_id": "order_ship_modal",
                "page_name": "确认发货弹窗",
                "page_type": "web_form",
                "page_archetype": "modal_form",
                "object_name": "发货",
                "role": "订单客服/履约人员",
                "purpose": "录入物流信息并完成发货",
                "fields": [
                    {"name": "物流公司", "control": "select", "required": True, "options": ["顺丰", "京东"], "validation": ""},
                    {"name": "物流单号", "control": "input", "required": True, "validation": "6-30位字母数字"},
                    {"name": "发货备注", "control": "textarea", "required": False, "validation": "200字以内"},
                ],
                "actions": [
                    {"name": "确认发货", "target": "订单列表页", "kind": "primary"},
                    {"name": "取消", "target": "订单列表页", "kind": "secondary"},
                ],
                "business_rules": ["仅待发货订单允许发货"],
                "status_values": ["待发货", "已发货", "已签收"],
            }
        ],
    })


def _bad_shipping_modal_model() -> dict:
    return _terminalized({
        "module_name": "后台-订单发货关闭",
        "module_key": "admin_order_ship_close",
        "pages": [
            {
                "page_id": "ship_modal",
                "page_name": "确认发货弹窗",
                "page_type": "web_form",
                "page_archetype": "dispatch_board",
                "object_name": "发货",
                "fields": [
                    {"name": "售后状态", "control": "select", "required": True, "options": ["启用", "停用"], "validation": ""},
                    {"name": "商品明细", "control": "input", "required": True, "validation": ""},
                    {"name": "支付状态", "control": "select", "required": False, "options": ["启用", "停用"], "validation": ""},
                    {"name": "收货地址", "control": "textarea", "required": False, "validation": ""},
                ],
            }
        ],
    })


def _bad_marketing_form_model() -> dict:
    return _terminalized({
        "module_name": "后台-营销表单",
        "module_key": "admin_marketing_form",
        "pages": [
            {
                "page_id": "marketing_form",
                "page_name": "营销活动表单页",
                "page_type": "web_form",
                "page_archetype": "form_page",
                "object_name": "营销活动",
                "fields": [
                    {"name": "TOP活动列表", "control": "input", "required": True, "validation": ""},
                    {"name": "新增会员数", "control": "input", "required": True, "validation": ""},
                    {"name": "核销率", "control": "input", "required": False, "validation": ""},
                    {"name": "活动带来的销售额", "control": "input", "required": False, "validation": ""},
                ],
            }
        ],
    })


def _bad_resource_model() -> dict:
    return _terminalized({
        "module_name": "后台-资源权限",
        "module_key": "admin_resource",
        "pages": [
            {
                "page_id": "resource_list",
                "page_name": "资源管理页",
                "page_type": "web_list",
                "page_archetype": "list_table",
                "object_name": "资源",
                "fields": [
                    {"name": "关键词", "control": "input", "required": True, "validation": ""},
                    {"name": "状态", "control": "select", "required": True, "options": ["启用", "停用"], "validation": ""},
                    {"name": "更新时间", "control": "input", "required": False, "validation": ""},
                ],
                "table_columns": ["关键词", "状态", "更新时间"],
            }
        ],
    })


def _bad_order_detail_model() -> dict:
    return _terminalized({
        "module_name": "后台-订单管理",
        "module_key": "admin_order_detail",
        "pages": [
            {
                "page_id": "order_detail",
                "page_name": "订单详情页（后台）",
                "page_type": "web_detail",
                "page_archetype": "detail_kv",
                "object_name": "订单",
                "fields": [
                    {"name": "订单编号", "control": "input", "required": True, "validation": ""},
                    {"name": "用户信息", "control": "input", "required": True, "validation": ""},
                    {"name": "收货地址", "control": "input", "required": True, "validation": ""},
                    {"name": "商品明细", "control": "textarea", "required": True, "validation": ""},
                    {"name": "金额明细", "control": "textarea", "required": True, "validation": ""},
                ],
                "actions": [{"name": "查看详情", "target": "订单详情页（后台）", "kind": "secondary"}],
            }
        ],
    })


def _bad_close_order_modal_model() -> dict:
    return _terminalized({
        "module_name": "后台-订单管理",
        "module_key": "admin_order_close",
        "pages": [
            {
                "page_id": "close_order_modal",
                "page_name": "关闭订单确认弹窗",
                "page_type": "web_form",
                "page_archetype": "modal_form",
                "object_name": "订单关闭",
                "fields": [
                    {"name": "提示文案", "control": "textarea", "required": False, "validation": ""},
                ],
                "business_rules": ["关闭前需提示退款风险"],
                "actions": [{"name": "确认关闭", "target": "订单列表页", "kind": "danger"}],
            }
        ],
    })


def _employee_list_model() -> dict:
    return _terminalized({
        "module_name": "后台-组织权限",
        "module_key": "admin_staff",
        "pages": [
            {
                "page_id": "employee_list",
                "page_name": "员工管理页",
                "page_type": "web_list",
                "page_archetype": "list_table",
                "object_name": "员工",
                "role": "系统管理员",
                "purpose": "维护员工账号和岗位状态",
                "needs_crud": False,
                "table_columns": ["姓名", "账号", "手机号", "角色", "状态", "更新时间"],
                "status_values": ["启用", "停用"],
                "jump_targets": ["员工详情页"],
                "business_rules": ["关键词：姓名/账号/手机号", "账号状态：启用 / 停用"],
            }
        ],
    })


def _employee_crud_model() -> dict:
    model = _employee_list_model()
    model["pages"][0]["needs_crud"] = True
    return model


def _employee_detail_page() -> dict:
    return {
        "page_id": "employee_detail",
        "page_name": "员工详情页",
        "page_type": "web_detail",
        "page_archetype": "detail_kv",
        "object_name": "员工",
        "role": "系统管理员",
        "purpose": "查看员工账号与岗位状态",
        "fields": [
            {"name": "姓名", "control": "input", "required": True, "validation": ""},
            {"name": "账号", "control": "input", "required": True, "validation": ""},
            {"name": "手机号", "control": "input", "required": True, "validation": "手机号格式"},
            {"name": "角色", "control": "select", "required": True, "options": ["运营", "客服"], "validation": ""},
            {"name": "状态", "control": "select", "required": True, "options": ["启用", "停用"], "validation": ""},
            {"name": "更新时间", "control": "input", "required": True, "validation": ""},
        ],
        "status_values": ["启用", "停用", "待生效"],
        "actions": [
            {"name": "编辑", "target": "新增/编辑员工弹窗", "kind": "primary"},
            {"name": "备注", "target": "备注弹窗", "kind": "secondary"},
        ],
        "jump_targets": ["新增/编辑员工弹窗"],
        "business_rules": ["仅系统管理员可停用员工"],
        "states": {
            "loading": "详情加载中显示骨架屏",
            "error": "详情加载失败时可重试",
            "transition": "启用 → 停用",
        },
    }


def _analysis_dashboard_model() -> dict:
    return _terminalized({
        "module_name": "后台-订单分析",
        "module_key": "admin_order_analytics",
        "pages": [
            {
                "page_id": "order_analysis",
                "page_name": "订单分析页",
                "page_type": "dashboard",
                "page_archetype": "dashboard",
                "object_name": "订单",
                "role": "订单客服/履约人员、系统管理员",
                "purpose": "查看订单趋势、转化情况以及支付日志",
                "nav_context": "后台-订单管理 / 订单分析",
                "sections": ["订单总览", "支付成功率", "退款率", "趋势图"],
                "actions": [
                    {"name": "切换时间范围", "target": "订单分析页", "kind": "secondary"},
                    {"name": "导出", "target": "订单分析页", "kind": "secondary"},
                ],
                "jump_targets": ["支付日志详情页"],
                "business_rules": ["选择时间范围后刷新统计结果", "支持导出订单分析报表"],
                "states": {"loading": "图表骨架屏", "error": "分析加载失败"},
            }
        ],
    })


def _app_profile_model() -> dict:
    return _terminalized(
        {
            "module_name": "App-会员中心",
            "module_key": "app_member_center",
            "product_name": "渔易购会员App",
            "pages": [
                {
                    "page_id": "member_profile",
                    "page_name": "会员中心",
                    "page_type": "profile",
                    "page_archetype": "profile",
                    "object_name": "会员",
                    "role": "C端会员",
                    "purpose": "查看会员资料、订单入口与服务入口",
                    "fields": [
                        {"name": "会员昵称", "control": "input", "required": True, "validation": ""},
                        {"name": "手机号", "control": "input", "required": True, "validation": "手机号格式"},
                    ],
                    "jump_targets": ["订单列表页", "收货地址页", "售后记录页"],
                    "states": {"empty": "暂无会员权益时展示升级引导"},
                }
            ],
        },
        terminal_type="app",
        terminal_name="App",
    )


def _h5_home_model() -> dict:
    return _terminalized(
        {
            "module_name": "H5-活动报名",
            "module_key": "h5_campaign",
            "product_name": "渔易购活动H5",
            "pages": [
                {
                    "page_id": "campaign_home",
                    "page_name": "活动报名H5首页",
                    "page_type": "mobile_home",
                    "page_archetype": "mobile_home",
                    "object_name": "活动",
                    "role": "渠道访客",
                    "purpose": "浏览活动并发起报名",
                    "jump_targets": ["活动详情页", "活动报名页", "在线咨询"],
                    "business_rules": ["分享时保留渠道参数", "提交报名后跳转成功页"],
                }
            ],
        },
        terminal_type="h5",
        terminal_name="H5",
    )


def _portal_home_model() -> dict:
    return _terminalized(
        {
            "module_name": "官网门户-产品官网",
            "module_key": "portal_site",
            "product_name": "渔易购官网门户",
            "pages": [
                {
                    "page_id": "official_site_home",
                    "page_name": "产品官网首页",
                    "page_type": "portal_home",
                    "page_archetype": "portal_landing",
                    "object_name": "官网门户",
                    "role": "访客/潜在客户",
                    "purpose": "展示品牌价值、方案与联系入口",
                    "jump_targets": ["方案中心", "客户案例", "立即咨询"],
                    "sections": ["Hero主视觉", "方案能力", "客户案例", "联系顾问"],
                }
            ],
        },
        terminal_type="portal",
        terminal_name="官网门户",
    )


def _bigscreen_dashboard_model() -> dict:
    return _terminalized(
        {
            "module_name": "大屏-指挥中心",
            "module_key": "bigscreen_command",
            "product_name": "渔易购大屏",
            "pages": [
                {
                    "page_id": "command_center",
                    "page_name": "渔业指挥大屏",
                    "page_type": "bigscreen_dashboard",
                    "page_archetype": "bigscreen_board",
                    "object_name": "指挥中心",
                    "role": "值班长/运营总控",
                    "purpose": "查看实时指标、态势和告警",
                    "sections": ["全局总览", "生产态势", "告警中心", "地图态势"],
                    "actions": [
                        {"name": "切换场景", "target": "生产态势", "kind": "secondary"},
                        {"name": "查看告警", "target": "告警中心", "kind": "secondary"},
                    ],
                }
            ],
        },
        terminal_type="bigscreen",
        terminal_name="大屏",
    )


def _industrial_console_model() -> dict:
    return _terminalized(
        {
            "module_name": "工控机-产线监控",
            "module_key": "industrial_line",
            "product_name": "渔易购工控机",
            "pages": [
                {
                    "page_id": "line_console",
                    "page_name": "产线工控机控制台",
                    "page_type": "industrial_console",
                    "page_archetype": "industrial_hmi",
                    "object_name": "产线",
                    "role": "现场操作员",
                    "purpose": "查看设备状态并执行控制动作",
                    "status_values": ["正常", "预警", "告警", "维护中"],
                    "actions": [
                        {"name": "启动产线", "target": "产线运行中", "kind": "primary"},
                        {"name": "暂停产线", "target": "产线暂停", "kind": "secondary"},
                        {"name": "急停", "target": "紧急停机", "kind": "danger"},
                    ],
                    "business_rules": ["急停需要二次确认", "报警未清除前禁止再次启动"],
                }
            ],
        },
        terminal_type="industrial",
        terminal_name="工控机",
    )


def _payment_log_page() -> dict:
    return {
        "page_id": "payment_log",
        "page_name": "支付日志页",
        "page_type": "web_list",
        "page_archetype": "list_table",
        "object_name": "支付日志",
        "role": "财务/系统管理员",
        "purpose": "查询支付结果与回调记录",
        "fields": [
            {"name": "订单编号", "control": "input", "required": True, "validation": ""},
            {"name": "支付状态", "control": "select", "required": True, "options": ["成功", "失败"], "validation": ""},
            {"name": "回调时间", "control": "input", "required": False, "validation": ""},
        ],
        "table_columns": ["订单编号", "支付流水号", "支付状态", "支付金额", "回调时间"],
        "status_values": ["成功", "失败", "处理中"],
        "actions": [{"name": "详情", "target": "支付日志详情页", "kind": "secondary"}],
        "jump_targets": ["支付日志详情页"],
        "business_rules": ["默认按回调时间倒序", "失败记录支持重试检索"],
        "table_behaviors": {"default_sort": "回调时间倒序"},
        "states": {"empty": "暂无支付日志", "error": "日志加载失败时支持重试"},
    }


def _order_analytics_bundle_model(include_payment_log: bool = False) -> dict:
    model = _analysis_dashboard_model()
    if include_payment_log:
        model["pages"].append(_payment_log_page())
    return model


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_pages_from_doc(content: str) -> list[str]:
    pages = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- **页面/界面：**"):
            raw = stripped.split("**页面/界面：**", 1)[1].strip()
            for page in re.split(r"[、，,；;]\s*", raw):
                page = page.strip()
                if page and page not in pages:
                    pages.append(page)
    return pages


def _extract_fields_from_doc(content: str) -> list[str]:
    fields = []
    lines = content.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        if stripped.startswith("- ") and not stripped.startswith("- **"):
            value = stripped[2:].strip()
            value = value.split("（", 1)[0].split("(", 1)[0].strip()
            if value and value not in fields and len(value) <= 40:
                fields.append(value)
            idx += 1
            continue
        if "列表展示列：" in stripped or "新增/编辑表单字段规格" in stripped:
            idx += 1
            while idx < len(lines):
                row = lines[idx].strip()
                if not row.startswith("|"):
                    break
                if not re.match(r"^\|[\s\-:|]+\|$", row):
                    cells = [cell.strip() for cell in row.strip("|").split("|")]
                    if cells and cells[0] not in {"列名", "字段名", "字段", "--------", "------"} and cells[0] not in fields:
                        fields.append(cells[0])
                idx += 1
            continue
        if "展示字段：" in stripped:
            raw = stripped.split("展示字段：", 1)[1].strip()
            for field in re.split(r"[、，,；;]\s*", raw):
                field = field.strip()
                if field and field not in fields:
                    fields.append(field)
        idx += 1
    return fields[:12]


def _make_module_brief(module_name: str, content: str) -> str:
    pages = _extract_pages_from_doc(content)
    fields = _extract_fields_from_doc(content)
    page_lines = "\n".join(f"- {page}" for page in pages) or "- 无页面"
    field_lines = "\n".join(f"- {field}" for field in fields) or "- 无字段"
    return (
        f"# {module_name} 模块摘要\n\n"
        "## 1. 模块目标与边界\n"
        f"- 模块：{module_name}\n\n"
        "## 2. 页面清单与页面 archetype\n"
        f"{page_lines}\n\n"
        "## 3. 关键字段索引\n"
        f"{field_lines}\n"
    )


def _write_requirements_split(workdir: Path, module_docs: dict[str, str]):
    requirements_dir = workdir / "requirements"
    requirements_dir.mkdir(parents=True, exist_ok=True)
    module_briefs_dir = requirements_dir / "module_briefs"
    module_briefs_dir.mkdir(parents=True, exist_ok=True)
    (requirements_dir / "详细需求文档_overview.md").write_text(
        "# 渔易购详细需求文档 — Overview\n\n## 7. 原型图清单\n- 测试用 overview\n",
        encoding="utf-8",
    )
    index_lines = [
        "# 需求文档索引",
        "",
        "## 共用文件",
        "- requirements/详细需求文档_overview.md",
        "",
        "## 模块文件",
    ]
    for filename, content in module_docs.items():
        (requirements_dir / filename).write_text(content, encoding="utf-8")
        module_name = filename.replace("详细需求文档_", "").replace(".md", "")
        brief_name = f"模块摘要_{module_name}.md"
        (module_briefs_dir / brief_name).write_text(_make_module_brief(module_name, content), encoding="utf-8")
        index_lines.append(
            f"- {module_name}: requirements/{filename} | requirements/module_briefs/{brief_name}"
        )
    (requirements_dir / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")


def _write_requirements_detail_only(workdir: Path, module_docs: dict[str, str]):
    requirements_dir = workdir / "requirements"
    requirements_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in module_docs.items():
        (requirements_dir / filename).write_text(content, encoding="utf-8")


def _run_pipeline_cli(workdir: Path, product_name: str) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, str(RUN_PIPELINE), str(workdir), product_name, "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    return completed.returncode, payload


def _run_html_pipeline_cli(workdir: Path, product_name: str, env: Optional[dict] = None) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, str(RUN_HTML_PIPELINE), str(workdir), product_name, "--json"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    return completed.returncode, payload


def _run_autoloop_cli(
    workdir: Path,
    product_name: str,
    format_name: str,
    *,
    max_rounds: int = 5,
    resume: bool = False,
    vision_review: str = "auto",
) -> tuple[int, dict]:
    cmd = [
        sys.executable,
        str(RUN_AUTO_PIPELINE),
        str(workdir),
        product_name,
        "--format",
        format_name,
        "--max-rounds",
        str(max_rounds),
        "--vision-review",
        vision_review,
        "--json",
    ]
    if resume:
        cmd.append("--resume")
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    return completed.returncode, payload


def _write_html_page_spec(path: Path, module_name: str, module_key: str, pages: list[dict]):
    payload = {
        "module_name": module_name,
        "module_key": module_key,
        "output_format": "html",
        "pages": pages,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HTML_UTILS.to_markdown(payload), encoding="utf-8")


def _write_autoloop_state(
    workdir: Path,
    *,
    product_name: str,
    format_name: str,
    status: str,
    phase: str,
    current_round: int,
    next_round: int,
    rounds: list[dict],
    latest_findings: list[dict],
    max_rounds: int = 5,
    max_parallel: int = 3,
    vision_review: str = "auto",
    streaks: Optional[dict] = None,
    blocked_findings: Optional[list[dict]] = None,
    final_artifact: str = "",
    failure_summary: Optional[dict] = None,
    attempted_fix_scopes: Optional[list[str]] = None,
    repeated_failures: Optional[list[dict]] = None,
    last_unconverged_reason: str = "",
    stop_recommendation: str = "",
):
    _write_json(
        workdir / ".prototype-generator" / "autoloop_state.json",
        {
            "schema_version": 3,
            "work_dir": str(workdir.resolve()),
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
            "streaks": streaks or {},
            "latest_findings": latest_findings,
            "blocked_findings": blocked_findings or [],
            "failure_summary": failure_summary or {"by_rule": {}, "by_stop_category": {}},
            "attempted_fix_scopes": attempted_fix_scopes or [],
            "repeated_failures": repeated_failures or [],
            "last_unconverged_reason": last_unconverged_reason,
            "stop_recommendation": stop_recommendation,
            "final_artifact": final_artifact,
            "updated_at": "2026-03-26T00:00:00Z",
        },
    )


class PrototypeGeneratorDrawioTests(unittest.TestCase):
    def test_normalize_output_path_coerces_legacy_root_paths_into_hidden_artifact_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            legacy_model = workdir / "page_model_user.json"
            legacy_model.write_text("{}", encoding="utf-8")
            legacy_page_specs = workdir / "page_specs"
            legacy_page_specs.mkdir()

            self.assertEqual(
                BUILD_PAGE_SPEC.normalize_output_path(str(legacy_model), str(workdir / "page_spec_user.md")),
                str(workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md"),
            )
            self.assertEqual(
                BUILD_PAGE_SPEC.normalize_output_path(str(legacy_model), str(legacy_page_specs / "page_spec_user.md")),
                str(workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md"),
            )

            artifact_page_models = workdir / ".prototype-generator" / "page_models"
            artifact_page_models.mkdir(parents=True)
            canonical_model = artifact_page_models / "page_model_user.json"
            canonical_model.write_text("{}", encoding="utf-8")
            self.assertEqual(
                BUILD_PAGE_SPEC.normalize_output_path(str(canonical_model), str(workdir)),
                str(workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md"),
            )

    def test_workflow_docs_keep_intermediate_artifacts_under_hidden_directory(self):
        expectations = {
            SKILL_DIR / "SKILL.md": [
                "WORK_DIR/.prototype-generator/page_models/page_model_*.json",
                "WORK_DIR/.prototype-generator/page_specs/page_spec_*.md",
                "draw.io 主流程默认最多自迭代 5 轮",
            ],
            SKILL_DIR / "AGENTS.md": [
                "最多只允许 3 个并行 agent",
                "每轮修复都必须重新生成真实 `.drawio`",
            ],
            STEPS_DIR / "step5-common.md": [
                ".prototype-generator/原型任务清单.md",
                ".prototype-generator/原型DoD.md",
                ".prototype-generator/tmp/drawio_*_tmp.xml",
                "当前模式：interactive / autonomous",
            ],
            STEPS_DIR / "step5-drawio.md": [
                "WORK_DIR/.prototype-generator/page_models/page_model_[模块英文名].json",
                "WORK_DIR/.prototype-generator/page_specs/page_spec_[模块英文名].md",
                "WORK_DIR/.prototype-generator/tmp/drawio_[模块英文名]_tmp.xml",
                "真实产物自迭代闭环",
            ],
            STEPS_DIR / "step6-iteration.md": [
                "先判断需求文档模式",
                "默认最多 5 轮",
            ],
        }
        for path, required_snippets in expectations.items():
            text = path.read_text(encoding="utf-8")
            for snippet in required_snippets:
                self.assertIn(snippet, text, path.as_posix())

    def test_docs_promote_unified_autonomous_entrypoint(self):
        for path in (
            SKILL_DIR / "SKILL.md",
            STEPS_DIR / "step5-drawio.md",
            STEPS_DIR / "step5-html.md",
            STEPS_DIR / "step6-iteration.md",
        ):
            text = path.read_text(encoding="utf-8")
            self.assertIn("run_autonomous_pipeline.py", text, path.as_posix())

    def test_workflow_docs_require_forced_context_compression(self):
        expectations = {
            SKILL_DIR / "SKILL.md": [
                "本 Skill 默认将“上下文压缩”视为正式门禁",
                "Codex 5.4 Medium / 200K 上下文窗口",
                "保留 `30%~40%` 余量",
                "功能点数 `> 12`",
                "预计原型页面 / swimlane 数 `> 8`",
                "requirements/module_briefs/模块摘要_*.md",
                "`index.md -> overview -> module_brief -> 模块详细文档 -> page_spec`",
            ],
            SKILL_DIR / "AGENTS.md": [
                "默认强制压缩模式",
                "Codex 5.4 Medium / 200K",
                "禁止按 200K 满额拼接输入",
                "requirements/module_briefs/模块摘要_[模块中文名].md",
                "`index.md -> overview -> module_brief -> 模块详细文档 -> page_spec`",
                "Step 6 审视优先对照 `module_brief + page_spec + 任务清单`",
            ],
            STEPS_DIR / "step4-requirements.md": [
                "判断是否进入默认强制压缩模式",
                "200K 预算规则",
                "功能点数 `> 12`",
                "关键用户角色数 `> 3`",
                "必须生成：",
                "requirements/module_briefs/模块摘要_[模块中文名].md",
            ],
            STEPS_DIR / "step4-parallel.md": [
                "module_briefs/",
                "模块摘要_[模块中文名].md",
                "先读对应模块摘要",
                "Step 5 / Step 6 默认读取顺序",
            ],
            STEPS_DIR / "step5-common.md": [
                "分拆模式下，子 agent 的默认读取顺序必须是 `index.md -> overview -> module_brief -> 模块详细文档 -> page_spec`",
                "面向 `Codex 5.4 Medium / 200K`",
                "缺少 `module_brief` 时，禁止启动 Step 5 子 agent",
            ],
            STEPS_DIR / "step5-agent-prompt.md": [
                "先读取模块摘要，提取页面清单、页面 archetype、关键字段索引、状态摘要、CRUD 闭环和跨模块跳转",
                "面向 `Codex 5.4 Medium / 200K`",
            ],
            STEPS_DIR / "step5-html.md": [
                "200K 预算规则",
                "再读取 [WORK_DIR]/requirements/module_briefs/模块摘要_[模块中文名].md 作为最小执行上下文",
            ],
            STEPS_DIR / "step5-drawio.md": [
                "200K 预算规则",
                "缺少 `module_brief`，禁止启动生成",
                "按 `index.md -> overview -> module_brief -> 模块详细文档` 顺序读取",
            ],
            STEPS_DIR / "step6-iteration.md": [
                "Codex 5.4 Medium / 200K",
                "分拆模式下优先对照 `module_brief + page_spec + 原型任务清单`",
                "优先用 `module_brief + page_spec + 原型任务清单` 做结构化字段 diff",
            ],
            STEPS_DIR / "codex-rules.md": [
                "Codex 5.4 Medium / 200K",
                "保留 `30%~40%` 余量",
                "每个模块文档完成后，必须继续生成 `requirements/module_briefs/模块摘要_[模块中文名].md`",
                "一旦命中任一项，Step 4 不得继续生成单一合并大 PRD",
            ],
        }
        for path, required_snippets in expectations.items():
            text = path.read_text(encoding="utf-8")
            for snippet in required_snippets:
                self.assertIn(snippet, text, path.as_posix())

    def test_docs_cover_extended_terminal_types(self):
        expectations = {
            SKILL_DIR / "SKILL.md": [
                "`admin` / `miniapp` / `app` / `h5` / `bigscreen` / `portal` / `industrial`",
            ],
            STEPS_DIR / "page-model-spec.md": [
                "`portal_home`",
                "`bigscreen_dashboard`",
                "`industrial_console`",
                "`官网门户`",
                "`工控机`",
            ],
            STEPS_DIR / "step4-doc-format.md": [
                "`h5`",
                "`bigscreen`",
                "`portal`",
                "`industrial`",
                "## 3.7 官网门户导航结构",
                "## 3.8 大屏场景结构",
                "## 3.9 工控机界面结构",
            ],
            STEPS_DIR / "step5-spec-agent-prompt.md": [
                "portal_home",
                "portal_hub",
                "bigscreen_dashboard",
                "industrial_console",
            ],
            STEPS_DIR / "drawio-spec.md": [
                "`portal_landing`",
                "`bigscreen_board`",
                "`industrial_hmi`",
            ],
            STEPS_DIR / "html-spec.md": [
                "`<body class=\"h5\">`",
                "`.portal-shell`",
                "`.bigscreen-shell`",
                "`.industrial-shell`",
            ],
        }
        for path, required_snippets in expectations.items():
            text = path.read_text(encoding="utf-8")
            for snippet in required_snippets:
                self.assertIn(snippet, text, path.as_posix())

    def test_skill_frontmatter_aligns_with_best_practices(self):
        frontmatter = _read_frontmatter(SKILL_DIR / "SKILL.md")
        self.assertIn("name: prototype-generator", frontmatter)
        self.assertIn("compatibility:", frontmatter)
        self.assertIn("metadata:", frontmatter)
        description_match = re.search(r"description:\s*\|\n((?:\s{2}.+\n?)*)", frontmatter)
        self.assertIsNotNone(description_match)
        description = "".join(
            line[2:] if line.startswith("  ") else line
            for line in description_match.group(1).splitlines(True)
        ).strip()
        self.assertLess(len(description), 1024)
        self.assertIn("生成 HTML 原型图", description)
        self.assertIn("生成 draw.io/drawio", description)
        self.assertIn("新增XX功能的原型", description)
        self.assertIn("Do not use for纯视觉润色", description)
        self.assertNotIn("界面设计", description)
        self.assertNotIn("页面设计", description)
        self.assertNotIn("产品界面", description)

    def test_skill_references_are_populated_and_linked_from_skill_md(self):
        references_dir = SKILL_DIR / "references"
        expected_files = [
            references_dir / "skill-positioning.md",
            references_dir / "terminal-model.md",
            references_dir / "output-modes.md",
            references_dir / "quality-gates.md",
        ]
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for path in expected_files:
            self.assertTrue(path.exists(), path.as_posix())
            self.assertGreater(len(path.read_text(encoding="utf-8").strip()), 20, path.as_posix())
            self.assertIn(path.name, skill_text, path.as_posix())
        self.assertFalse((SKILL_DIR / "README.md").exists())

    def test_readme_positions_prototype_generator_by_outcome_and_sync_model(self):
        expectations = {
            REPO_ROOT / "README.md": [
                "review-ready prototypes",
                "source of truth for the skills",
                "根据 PRD 出线框图",
            ],
            REPO_ROOT / "README.zh.md": [
                "可评审、可交付的原型",
                "标准源",
                "根据 PRD 出线框图",
            ],
        }
        for path, required_snippets in expectations.items():
            text = path.read_text(encoding="utf-8")
            for snippet in required_snippets:
                self.assertIn(snippet, text, path.as_posix())

    def test_evals_cover_positive_negative_and_extended_terminal_cases(self):
        payload = json.loads((SKILL_DIR / "evals" / "evals.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["skill_name"], "prototype-generator")
        evals = payload["evals"]
        self.assertGreaterEqual(len(evals), 10)
        positive = [item for item in evals if item.get("should_trigger") is True]
        negative = [item for item in evals if item.get("should_trigger") is False]
        self.assertGreaterEqual(len(positive), 5)
        self.assertGreaterEqual(len(negative), 2)
        serialized = json.dumps(evals, ensure_ascii=False)
        for token in ("H5", "官网门户", "大屏", "工控机"):
            self.assertIn(token, serialized)

    def test_html_common_css_supports_extended_terminal_classes(self):
        css = (SKILL_DIR / "templates" / "common.css").read_text(encoding="utf-8")
        for snippet in (
            "--w-bigscreen",
            "--w-industrial",
            "body.h5",
            ".h5-browser-bar",
            ".portal-shell",
            ".bigscreen-shell",
            ".industrial-shell",
            ".industrial-action-bar",
        ):
            self.assertIn(snippet, css)

    def test_html_common_css_stabilizes_font_stack_and_anchor_buttons(self):
        css = (SKILL_DIR / "templates" / "common.css").read_text(encoding="utf-8")
        for snippet in (
            "--font-ui:",
            "PingFang SC",
            "-webkit-text-size-adjust: 100%",
            "text-size-adjust: 100%",
            ".btn-primary,",
            ".pagination-btn {",
            "display: inline-flex;",
            "text-decoration: none;",
            "font-family: var(--font-ui);",
        ):
            self.assertIn(snippet, css)
        self.assertNotIn("transform: scale(0.97)", css)
        self.assertNotIn("transition: transform", css)

    def test_validate_c13_treats_analysis_pages_as_dashboard(self):
        markdown = _build_page_spec_markdown(_analysis_dashboard_model())
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _render_drawio(markdown, Path(tmp), "order_analysis")
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(_rule_result(report, "C13")["status"], "PASS", _report_message(report))

    def test_run_drawio_pipeline_generates_real_bundle_from_workdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-登录页.md": (
                        "# 渔易购 — 后台-登录页需求\n\n"
                        "## 3. 功能模块清单 — 后台-登录页\n\n"
                        "#### 功能点 1.1：后台登录\n"
                        "- **页面/界面：** 后台登录页\n"
                    ),
                    "详细需求文档_后台-会员运营.md": (
                        "# 渔易购 — 后台-会员运营需求\n\n"
                        "## 3. 功能模块清单 — 后台-会员运营\n\n"
                        "#### 功能点 1.1：营销活动管理\n"
                        "- **页面/界面：** 营销活动管理页\n"
                        "筛选条件：\n"
                        "- 活动名称\n"
                        "- 活动类型\n"
                        "- 活动时间\n"
                        "列表展示列：\n"
                        "| 字段 | 说明 |\n"
                        "| --- | --- |\n"
                        "| 活动名称 | 活动名称 |\n"
                        "| 活动类型 | 活动类型 |\n"
                        "| 开始时间 | 活动开始时间 |\n"
                        "| 结束时间 | 活动结束时间 |\n"
                        "| 关联商品数 | 关联商品数 |\n"
                        "| 活动状态 | 当前状态 |\n"
                    ),
                    "详细需求文档_后台-订单分析.md": (
                        "# 渔易购 — 后台-订单分析需求\n\n"
                        "## 3. 功能模块清单 — 后台-订单分析\n\n"
                        "#### 功能点 1.1：订单分析\n"
                        "- **页面/界面：** 订单分析页\n"
                    ),
                },
            )
            _write_json(workdir / ".prototype-generator" / "page_models" / "page_model_admin_login.json", _login_model())
            _write_json(workdir / ".prototype-generator" / "page_models" / "page_model_admin_marketing.json", _marketing_list_model())
            _write_json(workdir / ".prototype-generator" / "page_models" / "page_model_admin_order_analytics.json", _analysis_dashboard_model())

            returncode, payload = _run_pipeline_cli(workdir, "渔易购-后台管理")

            self.assertEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["summary"]["fail"], 0, json.dumps(payload, ensure_ascii=False))
            self.assertTrue((workdir / "prototypes" / "渔易购-后台管理.drawio").exists())
            self.assertFalse(any(workdir.glob("page_spec_*.md")))
            self.assertFalse(any(workdir.glob("drawio_*_tmp.xml")))
            self.assertEqual(payload["final_validation"]["summary"]["fail"], 0, json.dumps(payload, ensure_ascii=False))

    def test_run_drawio_pipeline_passes_after_upstream_page_model_fix(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-订单分析.md": (
                        "# 渔易购 — 后台-订单分析需求\n\n"
                        "## 3. 功能模块清单 — 后台-订单分析\n\n"
                        "#### 功能点 1.1：订单分析与日志\n"
                        "- **页面/界面：** 订单分析页、支付日志页\n"
                        "筛选条件：\n"
                        "- 订单编号\n"
                        "- 支付状态\n"
                        "- 回调时间\n"
                        "列表展示列：\n"
                        "| 字段 | 说明 |\n"
                        "| --- | --- |\n"
                        "| 订单编号 | 订单编号 |\n"
                        "| 支付流水号 | 流水号 |\n"
                        "| 支付状态 | 成功失败 |\n"
                        "| 支付金额 | 支付金额 |\n"
                        "| 回调时间 | 回调时间 |\n"
                    ),
                },
            )
            _write_json(workdir / ".prototype-generator" / "page_models" / "page_model_admin_order_analytics.json", _order_analytics_bundle_model(include_payment_log=False))

            first_code, first_payload = _run_pipeline_cli(workdir, "渔易购-后台管理")
            self.assertNotEqual(first_code, 0, json.dumps(first_payload, ensure_ascii=False))
            self.assertIn("支付日志页", first_payload["consistency"]["missing_pages"])

            _write_json(workdir / ".prototype-generator" / "page_models" / "page_model_admin_order_analytics.json", _order_analytics_bundle_model(include_payment_log=True))

            second_code, second_payload = _run_pipeline_cli(workdir, "渔易购-后台管理")
            self.assertEqual(second_code, 0, json.dumps(second_payload, ensure_ascii=False))
            self.assertEqual(second_payload["summary"]["fail"], 0, json.dumps(second_payload, ensure_ascii=False))

    def test_drawer_permission_page_spec_contains_rich_annotations(self):
        markdown = _build_page_spec_markdown(_drawer_permission_model())
        self.assertIn("菜单权限树", markdown)
        self.assertIn("权限分组摘要", markdown)
        self.assertIn("页面摘要&#xa;", markdown)
        self.assertIn("业务规则&#xa;", markdown)
        self.assertIn("状态与边界&#xa;", markdown)
        self.assertGreaterEqual(markdown.count("annotation_card"), 4)

    def test_detail_page_spec_contains_status_business_and_records(self):
        markdown = _build_page_spec_markdown(_detail_model())
        self.assertIn("状态与处理", markdown)
        self.assertIn("基础信息", markdown)
        self.assertIn("业务信息", markdown)
        self.assertIn("处理记录", markdown)
        self.assertIn("状态流转：待发货 → 已发货 → 已完成 → 已退款", markdown)
        self.assertGreaterEqual(markdown.count("divider"), 5)

    def test_validate_c14_warns_for_summary_only_annotation(self):
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = Path(tmp) / "summary_only.drawio"
            drawio_path.write_text(
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                "<mxfile host=\"app.diagrams.net\" modified=\"2026-03-25T00:00:00.000Z\" "
                "agent=\"prototype-generator-test\" version=\"24.0.0\" type=\"device\">\n"
                "<diagram id=\"summary_only\" name=\"后台-测试模块\">\n"
                "  <mxGraphModel dx=\"1280\" dy=\"900\" grid=\"0\" gridSize=\"10\" guides=\"1\" tooltips=\"1\" "
                "connect=\"1\" arrows=\"1\" fold=\"1\" page=\"1\" pageScale=\"1\" pageWidth=\"1780\" "
                "pageHeight=\"1000\" math=\"0\" shadow=\"0\">\n"
                "    <root>\n"
                "      <mxCell id=\"0\" />\n"
                "      <mxCell id=\"1\" parent=\"0\" />\n"
                "      <mxCell id=\"S1\" value=\"订单管理页\" "
                "style=\"swimlane;startSize=30;fillColor=#f0f4ff;strokeColor=#1e88e5;fontStyle=1;fontSize=13;\" "
                "vertex=\"1\" parent=\"1\"><mxGeometry x=\"16\" y=\"16\" width=\"1680\" height=\"960\" as=\"geometry\" /></mxCell>\n"
                "      <mxCell id=\"S1_2\" value=\"订单管理页\" style=\"rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;verticalAlign=middle;shadow=1;\" vertex=\"1\" parent=\"S1\"><mxGeometry x=\"0\" y=\"40\" width=\"1440\" height=\"56\" as=\"geometry\" /></mxCell>\n"
                "      <mxCell id=\"S1_3\" value=\"\" style=\"rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;\" vertex=\"1\" parent=\"S1\"><mxGeometry x=\"0\" y=\"96\" width=\"1440\" height=\"864\" as=\"geometry\" /></mxCell>\n"
                "      <mxCell id=\"S1_4\" value=\"页面摘要&#xa;页面：订单管理页&#xa;用途：查看订单&#xa;角色：客服\" style=\"rounded=1;whiteSpace=wrap;html=1;fillColor=#fffde7;strokeColor=#f9a825;fontSize=10;fontColor=#5d4037;align=left;verticalAlign=top;spacingLeft=8;spacingTop=8;\" vertex=\"1\" parent=\"S1\"><mxGeometry x=\"1464\" y=\"40\" width=\"216\" height=\"96\" as=\"geometry\" /></mxCell>\n"
                "      <mxCell id=\"S1_5\" value=\"跳转说明&#xa;查看详情 → 订单详情页\" style=\"rounded=1;whiteSpace=wrap;html=1;fillColor=#fffde7;strokeColor=#f9a825;fontSize=10;fontColor=#5d4037;align=left;verticalAlign=top;spacingLeft=8;spacingTop=8;\" vertex=\"1\" parent=\"S1\"><mxGeometry x=\"1464\" y=\"152\" width=\"216\" height=\"80\" as=\"geometry\" /></mxCell>\n"
                "    </root>\n"
                "  </mxGraphModel>\n"
                "</diagram>\n"
                "</mxfile>\n",
                encoding="utf-8",
            )
            result = VALIDATE.check_c14(VALIDATE.DrawioFile(str(drawio_path)))
            self.assertEqual(result.status, "WARN")
            self.assertEqual(result.count, 1)

    def test_end_to_end_drawer_permission_drawio_passes_quality_rules(self):
        markdown = _build_page_spec_markdown(_drawer_permission_model())
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _render_drawio(markdown, Path(tmp), "drawer_permission")
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(report["summary"]["fail"], 0, _report_message(report))
        self.assertEqual(report["summary"]["warn"], 0, _report_message(report))
        self.assertEqual(_rule_result(report, "C14")["status"], "PASS")
        self.assertEqual(_rule_result(report, "C13")["status"], "PASS")

    def test_end_to_end_detail_drawio_passes_quality_rules(self):
        markdown = _build_page_spec_markdown(_detail_model())
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _render_drawio(markdown, Path(tmp), "order_detail")
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(report["summary"]["fail"], 0, _report_message(report))
        self.assertEqual(report["summary"]["warn"], 0, _report_message(report))
        self.assertEqual(_rule_result(report, "C3")["status"], "PASS")
        self.assertEqual(_rule_result(report, "C14")["status"], "PASS")

    def test_login_page_keeps_captcha_and_login_button_inside_card(self):
        markdown = _build_page_spec_markdown(_login_model())
        self.assertIn("刷新验证码", markdown)
        module_name, swimlanes, elements = _parse_spec(markdown)
        self.assertEqual(module_name, "后台-登录页")
        self.assertEqual(swimlanes[0]["type"], "web")
        lane_id = swimlanes[0]["swimlane_id"]
        card = _find_element(elements, parent=lane_id, style_key="card")
        captcha_input = _find_element(elements, parent=lane_id, value="请输入验证码")
        captcha_refresh = _find_element(elements, parent=lane_id, value="刷新验证码")
        login_button = _find_element(elements, parent=lane_id, value="登录")
        note = _find_element(elements, parent=lane_id, value="连续失败超过 5 次将触发验证码限制")

        card_right = _int_value(card, "x") + _int_value(card, "width")
        card_bottom = _int_value(card, "y") + _int_value(card, "height")
        self.assertGreaterEqual(_int_value(card, "height"), 488)
        self.assertLessEqual(_int_value(captcha_input, "x") + _int_value(captcha_input, "width"), card_right - 24)
        self.assertLessEqual(_int_value(captcha_refresh, "x") + _int_value(captcha_refresh, "width"), card_right - 24)
        self.assertLessEqual(_int_value(login_button, "y") + _int_value(login_button, "height"), card_bottom - 56)
        self.assertLessEqual(_int_value(note, "y") + _int_value(note, "height"), card_bottom - 24)

    def test_end_to_end_login_drawio_passes_quality_rules(self):
        markdown = _build_page_spec_markdown(_login_model())
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _render_drawio(markdown, Path(tmp), "admin_login")
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(report["summary"]["fail"], 0, _report_message(report))
        self.assertEqual(_rule_result(report, "C8")["status"], "PASS")
        self.assertEqual(_rule_result(report, "C13")["status"], "PASS")
        self.assertEqual(_rule_result(report, "C15")["status"], "PASS")

    def test_shipping_modal_renders_as_modal_without_nav_bar(self):
        markdown = _build_page_spec_markdown(_shipping_modal_model())
        _, swimlanes, elements = _parse_spec(markdown)
        self.assertEqual(swimlanes[0]["type"], "modal")
        self.assertEqual(swimlanes[0]["style_key"], "swimlane_modal")
        self.assertIn("确认发货弹窗", markdown)
        self.assertNotIn("| 2 | S1 | nav | 确认发货弹窗 |", markdown)
        self.assertTrue(any(element["component_type"] == "modal_title" for element in elements))

    def test_validate_model_rejects_shipping_modal_with_order_detail_fields(self):
        with self.assertRaisesRegex(ValueError, "发货"):
            BUILD_PAGE_SPEC.validate_model(_bad_shipping_modal_model())

    def test_validate_model_rejects_marketing_form_with_analysis_metrics(self):
        with self.assertRaisesRegex(ValueError, "营销活动页面"):
            BUILD_PAGE_SPEC.validate_model(_bad_marketing_form_model())

    def test_validate_model_rejects_resource_page_missing_core_fields(self):
        with self.assertRaisesRegex(ValueError, "资源页面"):
            BUILD_PAGE_SPEC.validate_model(_bad_resource_model())

    def test_validate_model_requires_terminal_fields(self):
        model = _login_model()
        model.pop("terminal_type")
        with self.assertRaisesRegex(ValueError, "terminal_type"):
            BUILD_PAGE_SPEC.validate_model(model)

    def test_app_profile_defaults_to_app_navigation_context(self):
        markdown = _build_page_spec_markdown(_app_profile_model())
        self.assertIn("导航：App主导航", markdown)

    def test_h5_home_defaults_to_h5_navigation_context_and_browser_shell(self):
        markdown = _build_page_spec_markdown(_h5_home_model())
        self.assertIn("导航：H5页面栈", markdown)
        self.assertIn("浏览器地址栏 · 安全访问", markdown)

    def test_portal_home_uses_portal_nav_context_and_hero(self):
        markdown = _build_page_spec_markdown(_portal_home_model())
        _, swimlanes, _ = _parse_spec(markdown)
        self.assertEqual(swimlanes[0]["type"], "portal")
        self.assertIn("导航：官网顶栏导航", markdown)
        self.assertIn("Hero 主视觉", markdown)

    def test_bigscreen_dashboard_uses_dedicated_swimlane_and_navigation(self):
        markdown = _build_page_spec_markdown(_bigscreen_dashboard_model())
        _, swimlanes, _ = _parse_spec(markdown)
        self.assertEqual(swimlanes[0]["type"], "bigscreen")
        self.assertEqual(int(swimlanes[0]["width"]), BUILD_PAGE_SPEC.BIGSCREEN_SWIMLANE_W)
        self.assertIn("导航：大屏场景导航", markdown)
        self.assertIn("地图 / 态势图", markdown)

    def test_industrial_console_uses_dedicated_navigation_context_and_actions(self):
        markdown = _build_page_spec_markdown(_industrial_console_model())
        _, swimlanes, _ = _parse_spec(markdown)
        self.assertEqual(swimlanes[0]["type"], "industrial")
        self.assertIn("导航：工位操作导航", markdown)
        self.assertIn("急停", markdown)

    def test_validate_model_rejects_order_detail_missing_payment_after_sale_and_actions(self):
        with self.assertRaisesRegex(ValueError, "订单详情页"):
            BUILD_PAGE_SPEC.validate_model(_bad_order_detail_model())

    def test_validate_model_rejects_close_order_modal_without_reason(self):
        with self.assertRaisesRegex(ValueError, "关闭订单确认弹窗"):
            BUILD_PAGE_SPEC.validate_model(_bad_close_order_modal_model())

    def test_edit_modal_keeps_footer_actions_below_last_field(self):
        markdown = _build_page_spec_markdown(_marketing_list_model())
        self.assertIn("新增/编辑营销活动", markdown)
        _, swimlanes, elements = _parse_spec(markdown)
        modal_lane = next(sw for sw in swimlanes if sw["swimlane_label"] == "新增/编辑营销活动弹窗")
        modal_lane_id = modal_lane["swimlane_id"]
        modal_bg = _find_element(elements, parent=modal_lane_id, style_key="modal_bg")
        confirm_button = _find_element(elements, parent=modal_lane_id, value="确认")
        last_field = _find_element(elements, parent=modal_lane_id, value="请选择活动状态")
        footer_divider = None
        for element in elements:
            if element.get("parent_swimlane") != modal_lane_id:
                continue
            if element.get("style_key") != "divider":
                continue
            if _int_value(element, "y") > _int_value(last_field, "y"):
                footer_divider = element
                break
        self.assertIsNotNone(footer_divider)

        modal_bottom = _int_value(modal_bg, "y") + _int_value(modal_bg, "height")
        last_field_bottom = _int_value(last_field, "y") + _int_value(last_field, "height")
        self.assertGreaterEqual(_int_value(footer_divider, "y"), last_field_bottom + 24)
        self.assertLessEqual(_int_value(confirm_button, "y") + _int_value(confirm_button, "height"), modal_bottom - 8)

    def test_end_to_end_marketing_list_drawio_has_operation_buttons(self):
        markdown = _build_page_spec_markdown(_marketing_list_model())
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _render_drawio(markdown, Path(tmp), "marketing_list")
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(report["summary"]["fail"], 0, _report_message(report))
        self.assertEqual(_rule_result(report, "C16")["status"], "PASS")

    def test_consistency_scope_ignores_miniapp_requirements_for_admin_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-登录页.md": (
                        "# 渔易购 — 后台-登录页需求\n\n"
                        "#### 功能点 1.1：后台登录\n"
                        "- **页面/界面：** 后台登录页\n"
                    ),
                    "详细需求文档_小程序-首页.md": (
                        "# 渔易购 — 小程序-首页需求\n\n"
                        "#### 功能点 1.1：首页\n"
                        "- **页面/界面：** 首页、商品分类页\n"
                    ),
                },
            )
            page_specs_dir = workdir / ".prototype-generator" / "page_specs"
            page_specs_dir.mkdir(parents=True)
            (page_specs_dir / "page_spec_admin_login.md").write_text(
                _build_page_spec_markdown(_login_model()),
                encoding="utf-8",
            )

            report = CONSISTENCY.check_consistency(str(workdir / "requirements"), str(page_specs_dir), 0.8, "admin")
            self.assertEqual(report["scope"], "admin")
            self.assertNotIn("首页", report["missing_pages"])
            self.assertEqual(report["summary"]["fail"], 0, json.dumps(report, ensure_ascii=False))

    def test_consistency_alias_maps_order_management_and_shipping_modal(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            requirements_dir = workdir / "requirements"
            requirements_dir.mkdir(parents=True, exist_ok=True)
            (requirements_dir / "详细需求文档_后台-订单中心.md").write_text(
                "# 渔易购 — 后台-订单中心需求\n\n"
                "#### 功能点 1.1：订单管理\n"
                "- **页面/界面：** 订单列表页、发货弹窗\n"
                "列表展示列：\n"
                "| 列名 | 字段说明 |\n"
                "| --- | --- |\n"
                "| 操作 | 查看详情/发货/关闭/备注 |\n",
                encoding="utf-8",
            )
            page_specs_dir = workdir / ".prototype-generator" / "page_specs"
            page_specs_dir.mkdir(parents=True, exist_ok=True)
            (page_specs_dir / "page_spec_order.md").write_text(
                "# 后台-订单管理\n\n"
                "## swimlane 布局\n"
                "| swimlane_id | swimlane_label | type | x | y | width | height | style_key |\n"
                "|---|---|---|---|---|---|---|---|\n"
                "| S1 | 订单管理页（后台） | web | 16 | 16 | 1680 | 960 | swimlane |\n"
                "| S2 | 确认发货弹窗 | modal | 1736 | 16 | 520 | 400 | swimlane_modal |\n\n"
                "## 元素列表\n"
                "| id | parent_swimlane | component_type | value | x | y | width | height | style_key | tooltip |\n"
                "|---|---|---|---|---|---|---|---|---|---|\n"
                "| 2 | S1 | btn_sm | 详情 | 1296 | 312 | 40 | 32 | btn_sm | |\n"
                "| 3 | S1 | btn_sm | 发货 | 1344 | 312 | 40 | 32 | btn_sm | |\n"
                "| 4 | S1 | btn_sm_danger | 关闭 | 1392 | 312 | 40 | 32 | btn_sm_danger | |\n"
                "| 5 | S1 | btn_sm | 备注 | 1440 | 312 | 40 | 32 | btn_sm | |\n"
                "| 2 | S2 | label | 物流公司 | 48 | 120 | 88 | 40 | label | |\n"
                "| 3 | S2 | select | 请选择物流公司 | 152 | 120 | 224 | 48 | select | |\n"
                "| 4 | S2 | label | 物流单号 | 48 | 184 | 88 | 40 | label | |\n"
                "| 5 | S2 | input | 请输入物流单号 | 152 | 184 | 224 | 48 | input | |\n"
                "| 6 | S2 | label | 发货备注 | 48 | 248 | 88 | 40 | label | |\n"
                "| 7 | S2 | textarea | 请输入发货备注 | 152 | 248 | 224 | 88 | textarea | |\n",
                encoding="utf-8",
            )

            report = CONSISTENCY.check_consistency(str(requirements_dir), str(page_specs_dir), 0.8, "admin")
            self.assertNotIn("订单列表页", report["missing_pages"])
            self.assertNotIn("发货弹窗", report["missing_pages"])

    def test_consistency_flags_layout_mismatch_for_resource_tree_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            requirements_dir = workdir / "requirements"
            requirements_dir.mkdir(parents=True, exist_ok=True)
            (requirements_dir / "详细需求文档_后台-组织与权限.md").write_text(
                "# 渔易购 — 后台-组织与权限需求\n\n"
                "#### 功能点 1.1：资源管理\n"
                "- **页面/界面：** 资源管理页\n",
                encoding="utf-8",
            )
            page_specs_dir = workdir / ".prototype-generator" / "page_specs"
            page_specs_dir.mkdir(parents=True, exist_ok=True)
            (page_specs_dir / "page_spec_resource.md").write_text(
                "# 后台-资源管理\n\n"
                "## swimlane 布局\n"
                "| swimlane_id | swimlane_label | type | x | y | width | height | style_key |\n"
                "|---|---|---|---|---|---|---|---|\n"
                "| S1 | 资源管理页 | web | 16 | 16 | 1680 | 960 | swimlane |\n\n"
                "## 元素列表\n"
                "| id | parent_swimlane | component_type | value | x | y | width | height | style_key | tooltip |\n"
                "|---|---|---|---|---|---|---|---|---|---|\n"
                "| 2 | S1 | nav | 资源管理页 | 8 | 40 | 1440 | 56 | nav | |\n"
                "| 3 | S1 | pagination | 共 128 条 第 1/6 页 | 24 | 568 | 344 | 40 | pagination | |\n",
                encoding="utf-8",
            )

            report = CONSISTENCY.check_consistency(str(requirements_dir), str(page_specs_dir), 0.8, "admin")
            self.assertEqual(report["layout_mismatch_pages"][0]["page"], "资源管理页")

    def test_consistency_scope_detects_app_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_App-会员中心.md": (
                        "# 渔易购 — App-会员中心需求\n\n"
                        "#### 功能点 1.1：会员中心\n"
                        "- **页面/界面：** 会员中心\n"
                    ),
                    "详细需求文档_后台-登录页.md": (
                        "# 渔易购 — 后台-登录页需求\n\n"
                        "#### 功能点 1.1：后台登录\n"
                        "- **页面/界面：** 后台登录页\n"
                    ),
                },
            )
            page_specs_dir = workdir / ".prototype-generator" / "page_specs"
            page_specs_dir.mkdir(parents=True)
            (page_specs_dir / "page_spec_app_profile.md").write_text(
                _build_page_spec_markdown(_app_profile_model()),
                encoding="utf-8",
            )

            report = CONSISTENCY.check_consistency(str(workdir / "requirements"), str(page_specs_dir), 0.8, "app")
            self.assertEqual(report["scope"], "app")
            self.assertNotIn("后台登录页", report["missing_pages"])
            self.assertEqual(report["summary"]["fail"], 0, json.dumps(report, ensure_ascii=False))

    def test_consistency_scope_detects_h5_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_H5-活动报名.md": (
                        "# 渔易购 — H5-活动报名需求\n\n"
                        "#### 功能点 1.1：活动报名\n"
                        "- **页面/界面：** 活动报名H5首页\n"
                    ),
                    "详细需求文档_后台-登录页.md": (
                        "# 渔易购 — 后台-登录页需求\n\n"
                        "#### 功能点 1.1：后台登录\n"
                        "- **页面/界面：** 后台登录页\n"
                    ),
                },
            )
            page_specs_dir = workdir / ".prototype-generator" / "page_specs"
            page_specs_dir.mkdir(parents=True)
            (page_specs_dir / "page_spec_h5_campaign.md").write_text(
                _build_page_spec_markdown(_h5_home_model()),
                encoding="utf-8",
            )

            report = CONSISTENCY.check_consistency(str(workdir / "requirements"), str(page_specs_dir), 0.8, "h5")
            self.assertEqual(report["scope"], "h5")
            self.assertNotIn("后台登录页", report["missing_pages"])
            self.assertEqual(report["summary"]["fail"], 0, json.dumps(report, ensure_ascii=False))

    def test_module_brief_consistency_fails_when_pages_are_missing_from_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-订单中心.md": (
                        "# 渔易购 — 后台-订单中心需求\n\n"
                        "#### 功能点 1.1：订单管理\n"
                        "- **页面/界面：** 订单列表页、订单详情页、发货弹窗\n"
                        "筛选条件：\n"
                        "- 订单编号\n"
                        "- 订单状态\n"
                    ),
                },
            )
            brief_path = workdir / "requirements" / "module_briefs" / "模块摘要_后台-订单中心.md"
            brief_path.write_text(
                "# 后台-订单中心 模块摘要\n\n## 2. 页面清单与页面 archetype\n- 订单列表页\n",
                encoding="utf-8",
            )

            report = BRIEF_CONSISTENCY.check_requirements(str(workdir / "requirements"), 0.6)
            self.assertEqual(report["summary"]["fail"], 1, json.dumps(report, ensure_ascii=False))
            self.assertEqual(report["missing_pages"][0]["module"], "后台-订单中心")
            self.assertIn("订单详情页", report["missing_pages"][0]["pages"])

    def test_context_budget_precheck_flags_oversized_module_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-订单中心.md": (
                        "# 渔易购 — 后台-订单中心需求\n\n"
                        "#### 功能点 1.1：订单管理\n"
                        "- **页面/界面：** 订单列表页\n"
                    ),
                },
            )
            brief_path = workdir / "requirements" / "module_briefs" / "模块摘要_后台-订单中心.md"
            brief_path.write_text("# 超长摘要\n\n" + ("字段摘要\n" * 12000), encoding="utf-8")

            report = CONTEXT_BUDGET.assess_work_dir(str(workdir))
            self.assertEqual(report["summary"]["fail"], 1, json.dumps(report, ensure_ascii=False))
            self.assertTrue(any("module_brief" in item for item in report["failures"]))

    def test_run_drawio_pipeline_uses_admin_scope_when_product_name_mentions_admin(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-登录页.md": (
                        "# 渔易购 — 后台-登录页需求\n\n"
                        "#### 功能点 1.1：后台登录\n"
                        "- **页面/界面：** 后台登录页\n"
                    ),
                    "详细需求文档_小程序-首页.md": (
                        "# 渔易购 — 小程序-首页需求\n\n"
                        "#### 功能点 1.1：首页\n"
                        "- **页面/界面：** 首页、商品分类页\n"
                    ),
                },
            )
            _write_json(workdir / ".prototype-generator" / "page_models" / "page_model_admin_login.json", _login_model())

            returncode, payload = _run_pipeline_cli(workdir, "渔易购-后台管理")

            self.assertEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["consistency_scope"], "admin")
            self.assertNotIn("首页", payload["consistency"]["missing_pages"])

    def test_run_drawio_pipeline_auto_repairs_module_brief_when_pages_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-登录页.md": (
                        "# 渔易购 — 后台-登录页需求\n\n"
                        "#### 功能点 1.1：后台登录\n"
                        "- **页面/界面：** 后台登录页、修改密码页\n"
                    ),
                },
            )
            brief_path = workdir / "requirements" / "module_briefs" / "模块摘要_后台-登录页.md"
            brief_path.write_text(
                "# 后台-登录页 模块摘要\n\n## 2. 页面清单与页面 archetype\n- 后台登录页\n",
                encoding="utf-8",
            )
            _write_json(workdir / ".prototype-generator" / "page_models" / "page_model_admin_login.json", _login_model())

            returncode, payload = _run_pipeline_cli(workdir, "渔易购-后台管理")

            self.assertNotEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["module_brief_consistency"]["summary"]["fail"], 0)
            self.assertEqual(payload["requirements_compression"]["status"], "rewritten")
            self.assertIn("修改密码页", brief_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["failure_routing"][0]["layer"], "page_model")

    def test_run_drawio_pipeline_auto_repairs_oversized_module_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-登录页.md": (
                        "# 渔易购 — 后台-登录页需求\n\n"
                        "#### 功能点 1.1：后台登录\n"
                        "- **页面/界面：** 后台登录页\n"
                    ),
                },
            )
            brief_path = workdir / "requirements" / "module_briefs" / "模块摘要_后台-登录页.md"
            brief_path.write_text("# 超长摘要\n\n" + ("字段摘要\n" * 12000), encoding="utf-8")
            _write_json(workdir / ".prototype-generator" / "page_models" / "page_model_admin_login.json", _login_model())

            returncode, payload = _run_pipeline_cli(workdir, "渔易购-后台管理")

            self.assertEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["context_budget"]["summary"]["fail"], 0)
            self.assertEqual(payload["requirements_compression"]["status"], "rewritten")
            self.assertLess(
                CONTEXT_BUDGET.read_tokens(workdir / "requirements" / "module_briefs" / "模块摘要_后台-登录页.md"),
                10000,
            )

    def test_employee_management_infers_add_edit_disable_actions(self):
        markdown = _build_page_spec_markdown(_employee_list_model())
        self.assertIn("新增员工", markdown)
        self.assertIn("| 26 | S1 | btn_sm | 编辑 |", markdown)
        self.assertIn("| 27 | S1 | btn_sm | 停用 |", markdown)

        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _render_drawio(markdown, Path(tmp), "employee_list")
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(_rule_result(report, "C18")["status"], "PASS", _report_message(report))

    def test_list_page_no_longer_renders_top_right_record_count_hint(self):
        markdown = _build_page_spec_markdown(_employee_list_model())
        self.assertNotIn("共 128 条记录", markdown)

    def test_validate_c15_fails_when_login_controls_overflow_card(self):
        cells = """
      <mxCell id="S1_2" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;" vertex="1" parent="S1"><mxGeometry x="0" y="40" width="376" height="816" as="geometry" /></mxCell>
      <mxCell id="S1_3" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e0e0e0;shadow=1;arcSize=8;" vertex="1" parent="S1"><mxGeometry x="24" y="120" width="328" height="360" as="geometry" /></mxCell>
      <mxCell id="S1_4" value="请输入后台账号" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;arcSize=4;" vertex="1" parent="S1"><mxGeometry x="48" y="256" width="280" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_5" value="请输入登录密码" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;arcSize=4;" vertex="1" parent="S1"><mxGeometry x="48" y="344" width="280" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_6" value="请输入验证码" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;arcSize=4;" vertex="1" parent="S1"><mxGeometry x="48" y="448" width="144" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_7" value="刷新验证码" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1e88e5;fontColor=#1e88e5;fontSize=13;" vertex="1" parent="S1"><mxGeometry x="208" y="448" width="120" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_8" value="登录" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;shadow=1;arcSize=4;" vertex="1" parent="S1"><mxGeometry x="48" y="528" width="280" height="48" as="geometry" /></mxCell>
        """
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _write_drawio(Path(tmp), "bad_login", "后台-登录页", "后台登录页", 592, cells)
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(_rule_result(report, "C15")["status"], "FAIL", _report_message(report))

    def test_validate_c16_fails_when_operation_column_has_no_row_buttons(self):
        cells = """
      <mxCell id="S1_2" value="满减优惠管理页" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;verticalAlign=middle;shadow=1;" vertex="1" parent="S1"><mxGeometry x="208" y="40" width="1440" height="56" as="geometry" /></mxCell>
      <mxCell id="S1_3" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;" vertex="1" parent="S1"><mxGeometry x="208" y="96" width="1440" height="864" as="geometry" /></mxCell>
      <mxCell id="S1_4" value="查询" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;" vertex="1" parent="S1"><mxGeometry x="752" y="152" width="88" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_5" value="重置" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1e88e5;fontColor=#1e88e5;fontSize=13;" vertex="1" parent="S1"><mxGeometry x="856" y="152" width="88" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_6" value="新增满减" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;" vertex="1" parent="S1"><mxGeometry x="1152" y="152" width="120" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_7" value="活动/券名称" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="232" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_8" value="类型" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="388" y="232" width="120" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_9" value="门槛" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="508" y="232" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_10" value="优惠内容" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="656" y="232" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_11" value="活动状态" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="804" y="232" width="136" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_12" value="操作" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="1108" y="232" width="120" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_13" value="周末满减" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="280" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_14" value="满减" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="388" y="280" width="120" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_15" value="满199" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="508" y="280" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_16" value="减20元" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="656" y="280" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_17" value="生效" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="804" y="280" width="136" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_18" value="会员满减" style="text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="328" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_19" value="满减" style="text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="388" y="328" width="120" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_20" value="满299" style="text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="508" y="328" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_21" value="减30元" style="text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="656" y="328" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_22" value="生效" style="text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="804" y="328" width="136" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_23" value="礼盒专享" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="376" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_24" value="满减" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="388" y="376" width="120" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_25" value="满399" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="508" y="376" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_26" value="减50元" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="656" y="376" width="148" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_27" value="草稿" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="804" y="376" width="136" height="48" as="geometry" /></mxCell>
        """
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _write_drawio(Path(tmp), "bad_operation_col", "后台-会员运营", "满减优惠管理页", 1680, cells)
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(_rule_result(report, "C16")["status"], "FAIL", _report_message(report))

    def test_validate_c17_fails_when_blank_blue_blocks_exist(self):
        cells = """
      <mxCell id="S1_2" value="员工管理页" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;" vertex="1" parent="S1"><mxGeometry x="8" y="40" width="1440" height="56" as="geometry" /></mxCell>
      <mxCell id="S1_3" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;" vertex="1" parent="S1"><mxGeometry x="0" y="96" width="1440" height="864" as="geometry" /></mxCell>
      <mxCell id="S1_4" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#e3f2fd;strokeColor=#90caf9;arcSize=8;" vertex="1" parent="S1"><mxGeometry x="872" y="224" width="56" height="24" as="geometry" /></mxCell>
      <mxCell id="S1_5" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#e3f2fd;strokeColor=#90caf9;arcSize=8;" vertex="1" parent="S1"><mxGeometry x="952" y="224" width="56" height="24" as="geometry" /></mxCell>
        """
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _write_drawio(Path(tmp), "bad_blue_blocks", "后台-组织权限", "员工管理页", 1680, cells)
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(_rule_result(report, "C17")["status"], "FAIL", _report_message(report))

    def test_validate_c18_fails_when_management_page_actions_are_too_weak(self):
        cells = """
      <mxCell id="S1_2" value="员工管理页" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;" vertex="1" parent="S1"><mxGeometry x="8" y="40" width="1440" height="56" as="geometry" /></mxCell>
      <mxCell id="S1_3" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;" vertex="1" parent="S1"><mxGeometry x="0" y="96" width="1440" height="864" as="geometry" /></mxCell>
      <mxCell id="S1_4" value="查询" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;" vertex="1" parent="S1"><mxGeometry x="632" y="160" width="88" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_5" value="查看" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1e88e5;fontColor=#1e88e5;fontSize=12;" vertex="1" parent="S1"><mxGeometry x="1320" y="312" width="56" height="32" as="geometry" /></mxCell>
      <mxCell id="S1_6" value="停用" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1e88e5;fontColor=#1e88e5;fontSize=12;" vertex="1" parent="S1"><mxGeometry x="1384" y="312" width="56" height="32" as="geometry" /></mxCell>
        """
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _write_drawio(Path(tmp), "bad_management_actions", "后台-组织权限", "员工管理页", 1680, cells)
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(_rule_result(report, "C18")["status"], "FAIL", _report_message(report))

    def test_render_generate_xml_deduplicates_duplicate_element_ids(self):
        styles = RENDER.parse_styles((STEPS_DIR / "step5-component-styles.md").read_text(encoding="utf-8"))
        swimlanes = [
            {"swimlane_id": "S1", "swimlane_label": "测试页", "type": "web", "x": "16", "y": "16", "width": "1680", "height": "960", "style_key": "swimlane"}
        ]
        elements = [
            {"id": "2", "parent_swimlane": "S1", "component_type": "text", "value": "标题A", "x": "8", "y": "40", "width": "240", "height": "40", "style_key": "text_title", "tooltip": ""},
            {"id": "2", "parent_swimlane": "S1", "component_type": "text", "value": "标题B", "x": "8", "y": "88", "width": "240", "height": "40", "style_key": "text_title", "tooltip": ""},
        ]
        xml = RENDER.generate_xml("dup_id_test", "测试模块", swimlanes, elements, styles)
        self.assertIn('id="S1_2"', xml)
        self.assertIn('id="S1_2_2"', xml)

    def test_merge_cleans_blank_blue_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            tmp_xml = tmpdir / "drawio_tmp.xml"
            tmp_xml.write_text(
                "<diagram id=\"tmp\" name=\"后台-组织权限\">"
                "<mxGraphModel dx=\"1280\" dy=\"900\" grid=\"0\" gridSize=\"10\" guides=\"1\" tooltips=\"1\" connect=\"1\" arrows=\"1\" fold=\"1\" page=\"1\" pageScale=\"1\" pageWidth=\"1780\" pageHeight=\"1000\" math=\"0\" shadow=\"0\">"
                "<root>"
                "<mxCell id=\"0\" />"
                "<mxCell id=\"1\" parent=\"0\" />"
                "<mxCell id=\"S1\" value=\"员工管理页\" style=\"swimlane;startSize=30;fillColor=#f0f4ff;strokeColor=#1e88e5;fontStyle=1;fontSize=13;\" vertex=\"1\" parent=\"1\"><mxGeometry x=\"16\" y=\"16\" width=\"1680\" height=\"960\" as=\"geometry\" /></mxCell>"
                "<mxCell id=\"S1_2\" value=\"员工管理页\" style=\"rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;\" vertex=\"1\" parent=\"S1\"><mxGeometry x=\"8\" y=\"40\" width=\"1440\" height=\"56\" as=\"geometry\" /></mxCell>"
                "<mxCell id=\"S1_3\" value=\"\" style=\"rounded=1;whiteSpace=wrap;html=1;fillColor=#e3f2fd;strokeColor=#90caf9;arcSize=8;\" vertex=\"1\" parent=\"S1\"><mxGeometry x=\"872\" y=\"224\" width=\"56\" height=\"24\" as=\"geometry\" /></mxCell>"
                "</root></mxGraphModel></diagram>",
                encoding="utf-8",
            )
            output_path = tmpdir / "merged.drawio"
            MERGE.merge(str(output_path), "测试产品", [str(tmp_xml)], keep_tmp=True, add_nav=False)
            merged = output_path.read_text(encoding="utf-8")
        self.assertNotIn("strokeColor=#90caf9", merged)

    def test_validate_c13_accepts_rendered_text_table_rows(self):
        cells = """
      <mxCell id="S1_2" value="员工管理页" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;verticalAlign=middle;shadow=1;" vertex="1" parent="S1"><mxGeometry x="208" y="40" width="1440" height="56" as="geometry" /></mxCell>
      <mxCell id="S1_3" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;" vertex="1" parent="S1"><mxGeometry x="208" y="96" width="1440" height="864" as="geometry" /></mxCell>
      <mxCell id="S1_4" value="关键词搜索" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;arcSize=4;" vertex="1" parent="S1"><mxGeometry x="240" y="152" width="200" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_5" value="状态▼" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;arcSize=4;" vertex="1" parent="S1"><mxGeometry x="456" y="152" width="120" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_6" value="时间范围▼" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;arcSize=4;" vertex="1" parent="S1"><mxGeometry x="592" y="152" width="144" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_7" value="查询" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;" vertex="1" parent="S1"><mxGeometry x="752" y="152" width="88" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_8" value="新增员工" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;" vertex="1" parent="S1"><mxGeometry x="1152" y="152" width="120" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_9" value="员工姓名" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="232" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_10" value="员工账号" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="368" y="232" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_11" value="状态" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="496" y="232" width="96" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_12" value="张运营" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="280" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_13" value="ops_zhang" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="368" y="280" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_14" value="正常" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="496" y="280" width="96" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_15" value="李商品" style="text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="328" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_16" value="goods_li" style="text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="368" y="328" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_17" value="正常" style="text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="496" y="328" width="96" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_18" value="王客服" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="376" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_19" value="service_wang" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="368" y="376" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_20" value="停用" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="496" y="376" width="96" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_21" value="页面摘要&#xa;页面：员工管理页&#xa;用途：员工账号维护&#xa;角色：系统管理员" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fffde7;strokeColor=#f9a825;fontSize=10;fontColor=#5d4037;align=left;verticalAlign=top;spacingLeft=8;spacingTop=8;" vertex="1" parent="S1"><mxGeometry x="1464" y="40" width="216" height="96" as="geometry" /></mxCell>
      <mxCell id="S1_22" value="业务规则&#xa;默认按更新时间倒序&#xa;仅系统管理员可停用员工" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fffde7;strokeColor=#f9a825;fontSize=10;fontColor=#5d4037;align=left;verticalAlign=top;spacingLeft=8;spacingTop=8;" vertex="1" parent="S1"><mxGeometry x="1464" y="152" width="216" height="96" as="geometry" /></mxCell>
        """
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _write_drawio(Path(tmp), "rendered_list", "后台-组织权限", "员工管理页", 1680, cells)
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(_rule_result(report, "C13")["status"], "PASS", _report_message(report))

    def test_validate_c13_treats_login_logs_as_list_pages(self):
        cells = """
      <mxCell id="S1_2" value="管理后台登录日志页" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;verticalAlign=middle;shadow=1;" vertex="1" parent="S1"><mxGeometry x="208" y="40" width="1440" height="56" as="geometry" /></mxCell>
      <mxCell id="S1_3" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;" vertex="1" parent="S1"><mxGeometry x="208" y="96" width="1440" height="864" as="geometry" /></mxCell>
      <mxCell id="S1_4" value="操作人" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="232" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_5" value="登录时间" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="368" y="232" width="176" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_6" value="结果" style="text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="544" y="232" width="96" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_7" value="查询" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;" vertex="1" parent="S1"><mxGeometry x="752" y="152" width="88" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_8" value="导出日志" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1e88e5;fontColor=#1e88e5;fontSize=13;" vertex="1" parent="S1"><mxGeometry x="856" y="152" width="104" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_9" value="管理员A" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="280" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_10" value="2026-03-25 10:00" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="368" y="280" width="176" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_11" value="成功" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="544" y="280" width="96" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_12" value="管理员B" style="text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="328" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_13" value="2026-03-25 09:40" style="text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="368" y="328" width="176" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_14" value="失败" style="text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="544" y="328" width="96" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_15" value="管理员C" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="240" y="376" width="128" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_16" value="2026-03-25 09:00" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="368" y="376" width="176" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_17" value="成功" style="text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;" vertex="1" parent="S1"><mxGeometry x="544" y="376" width="96" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_18" value="页面摘要&#xa;页面：管理后台登录日志页&#xa;用途：查看登录记录&#xa;角色：管理员" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fffde7;strokeColor=#f9a825;fontSize=10;fontColor=#5d4037;align=left;verticalAlign=top;spacingLeft=8;spacingTop=8;" vertex="1" parent="S1"><mxGeometry x="1464" y="40" width="216" height="96" as="geometry" /></mxCell>
      <mxCell id="S1_19" value="业务规则&#xa;默认保留90天登录日志&#xa;支持按结果筛选" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fffde7;strokeColor=#f9a825;fontSize=10;fontColor=#5d4037;align=left;verticalAlign=top;spacingLeft=8;spacingTop=8;" vertex="1" parent="S1"><mxGeometry x="1464" y="152" width="216" height="96" as="geometry" /></mxCell>
        """
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _write_drawio(Path(tmp), "login_log", "后台-审计反馈", "管理后台登录日志页", 1680, cells)
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(_rule_result(report, "C13")["status"], "PASS", _report_message(report))

    def test_validate_c13_treats_rejection_confirm_dialog_as_form_modal(self):
        cells = """
      <mxCell id="S1_2" value="提现拒绝确认弹窗" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=15;fontStyle=1;" vertex="1" parent="S1"><mxGeometry x="48" y="72" width="240" height="24" as="geometry" /></mxCell>
      <mxCell id="S1_3" value="拒绝原因" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=13;" vertex="1" parent="S1"><mxGeometry x="48" y="112" width="88" height="24" as="geometry" /></mxCell>
      <mxCell id="S1_4" value="请输入拒绝原因" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;arcSize=4;" vertex="1" parent="S1"><mxGeometry x="144" y="112" width="200" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_5" value="通知用户" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=13;" vertex="1" parent="S1"><mxGeometry x="48" y="168" width="88" height="24" as="geometry" /></mxCell>
      <mxCell id="S1_6" value="短信/站内信" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;arcSize=4;" vertex="1" parent="S1"><mxGeometry x="144" y="168" width="200" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_7" value="补充说明" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=13;" vertex="1" parent="S1"><mxGeometry x="48" y="224" width="88" height="24" as="geometry" /></mxCell>
      <mxCell id="S1_8" value="输入处理建议" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;arcSize=4;" vertex="1" parent="S1"><mxGeometry x="144" y="224" width="200" height="48" as="geometry" /></mxCell>
      <mxCell id="S1_9" value="取消" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1e88e5;fontColor=#1e88e5;fontSize=13;" vertex="1" parent="S1"><mxGeometry x="224" y="288" width="80" height="40" as="geometry" /></mxCell>
      <mxCell id="S1_10" value="确认" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;" vertex="1" parent="S1"><mxGeometry x="312" y="288" width="80" height="40" as="geometry" /></mxCell>
        """
        with tempfile.TemporaryDirectory() as tmp:
            drawio_path = _write_drawio(Path(tmp), "reject_modal", "后台-分销管理", "提现拒绝确认弹窗", 592, cells)
            report = VALIDATE.run_checks(str(drawio_path))
        self.assertEqual(_rule_result(report, "C13")["status"], "PASS", _report_message(report))

    def test_html_pipeline_renders_index_and_review_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                        "- 手机号\n"
                        "- 状态\n"
                    ),
                },
            )
            _write_html_page_spec(
                workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md",
                "后台-用户管理",
                "user",
                [
                    {
                        "page_name": "用户列表页",
                        "page_type": "web_list",
                        "output_file": "user-list.html",
                        "is_nav_page": False,
                        "fields": [{"name": "用户名", "control": "input", "required": "否", "note": ""}],
                        "table_columns": [{"name": "用户名", "note": ""}],
                        "actions": ["新增用户", "编辑"],
                        "jumps": [{"action": "新增用户", "target": "用户列表页"}],
                        "states": ["启用", "停用"],
                    }
                ],
            )

            returncode, payload = _run_html_pipeline_cli(workdir, "渔易购-后台管理")

            self.assertNotEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertTrue((workdir / "prototypes" / "index.html").is_file())
            self.assertEqual(payload["failure_routing"][0]["layer"], "page_spec")
            self.assertTrue(any(item["rule"] == "LOW_COVERAGE" for item in payload["review_findings"]))

    def test_validate_html_flags_broken_links_and_missing_css(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "broken.html").write_text(
                "<!DOCTYPE html><html><head><title>Broken</title></head><body>"
                "<div class='page-shell' data-prototype-shell='1' data-page-name='坏页' data-page-type='web_list'>"
                "<main class='page-main'><a href='missing.html'>缺失</a></main>"
                "</div></body></html>",
                encoding="utf-8",
            )
            report = VALIDATE_HTML.run_checks(root)
        self.assertEqual(next(item for item in report["results"] if item["rule"] == "H2")["status"], "FAIL")
        self.assertEqual(next(item for item in report["results"] if item["rule"] == "H4")["status"], "FAIL")

    def test_reference_pack_prefers_local_visual_references_and_enriches_page_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "用户列表页参考.png").write_bytes(b"fake")
            spec_path = workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md"
            _write_html_page_spec(
                spec_path,
                "后台-用户管理",
                "user",
                [
                    {
                        "page_name": "用户列表页",
                        "page_type": "web_list",
                        "output_file": "user-list.html",
                        "fields": [{"name": "用户名", "control": "input", "required": "否", "note": ""}],
                        "table_columns": [{"name": "用户名", "note": ""}],
                        "actions": ["新增用户"],
                        "jumps": [{"action": "新增用户", "target": "用户列表页"}],
                        "states": ["启用", "停用"],
                    }
                ],
            )

            manifest = REFERENCE_UTILS.ensure_reference_pack(workdir)
            enriched = REFERENCE_UTILS.enrich_page_spec_file(spec_path, manifest)

            self.assertEqual(manifest["pages"][0]["reference_basis"], "internal")
            self.assertIn("用户列表页参考.png", "".join(manifest["pages"][0]["reference_sources"]))
            self.assertEqual(enriched["pages"][0]["page_archetype"], "list_table")
            serialized = spec_path.read_text(encoding="utf-8")
            self.assertIn("### 参考依据", serialized)
            self.assertIn("### 布局指令", serialized)

    def test_requirements_compression_generates_overview_briefs_and_index_from_detail_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_detail_only(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "### 后台-用户管理\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页、用户详情页\n"
                        "- 用户名\n"
                        "- 手机号\n"
                        "- 状态\n"
                    )
                },
            )

            report = REQ_COMPRESS.ensure_compressed_requirements(workdir, force=True)

            self.assertEqual(report["mode"], "split")
            self.assertTrue((workdir / "requirements" / "详细需求文档_overview.md").is_file())
            self.assertTrue((workdir / "requirements" / "module_briefs" / "模块摘要_后台-用户管理.md").is_file())
            self.assertTrue((workdir / "requirements" / "index.md").is_file())
            overview = (workdir / "requirements" / "详细需求文档_overview.md").read_text(encoding="utf-8")
            self.assertIn("原型图清单", overview)
            self.assertIn("用户列表页", overview)

    def test_html_pipeline_auto_generates_compressed_requirements_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_detail_only(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "### 后台-用户管理\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                        "- 手机号\n"
                        "- 状态\n"
                    )
                },
            )
            _write_html_page_spec(
                workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md",
                "后台-用户管理",
                "user",
                [
                    {
                        "page_name": "用户列表页",
                        "page_type": "web_list",
                        "page_archetype": "list_table",
                        "output_file": "user-list.html",
                        "fields": [
                            {"name": "用户名", "control": "input", "required": "否", "note": ""},
                            {"name": "手机号", "control": "input", "required": "否", "note": ""},
                            {"name": "状态", "control": "select", "required": "否", "note": ""},
                        ],
                        "table_columns": [
                            {"name": "用户名", "note": ""},
                            {"name": "手机号", "note": ""},
                            {"name": "状态", "note": ""},
                        ],
                        "actions": ["新增用户", "编辑"],
                        "jumps": [{"action": "新增用户", "target": "用户列表页"}],
                        "states": ["启用", "停用"],
                    }
                ],
            )

            returncode, payload = _run_html_pipeline_cli(workdir, "渔易购-后台管理")

            self.assertEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["requirements_compression"]["mode"], "split")
            self.assertTrue((workdir / "requirements" / "index.md").is_file())
            self.assertTrue((workdir / "requirements" / "module_briefs" / "模块摘要_后台-用户管理.md").is_file())

    def test_drawio_pipeline_auto_generates_compressed_requirements_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_detail_only(
                workdir,
                {
                    "详细需求文档_后台-登录页.md": (
                        "# 渔易购 — 后台-登录页需求\n\n"
                        "### 后台-登录页\n\n"
                        "#### 功能点 1.1：后台登录\n"
                        "- **页面/界面：** 后台登录页\n"
                        "- 账号\n"
                        "- 密码\n"
                        "- 图形验证码\n"
                    )
                },
            )
            _write_json(workdir / ".prototype-generator" / "page_models" / "page_model_admin_login.json", _login_model())

            returncode, payload = _run_pipeline_cli(workdir, "渔易购-后台管理")

            self.assertEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["requirements_compression"]["mode"], "split")
            self.assertTrue((workdir / "requirements" / "详细需求文档_overview.md").is_file())
            self.assertTrue((workdir / "requirements" / "index.md").is_file())

    def test_reference_pack_uses_search_hook_when_local_reference_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            hook_path = workdir / "search_hook.py"
            hook_path.write_text(
                "import json, sys\n"
                "payload = json.loads(sys.stdin.read())\n"
                "print(json.dumps({'references': [{'title': payload['page_name'] + ' 竞品案例', 'url': 'https://example.com/case', 'summary': '参考行业案例'}]}, ensure_ascii=False))\n",
                encoding="utf-8",
            )
            spec_path = workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md"
            _write_html_page_spec(
                spec_path,
                "后台-用户管理",
                "user",
                [
                    {
                        "page_name": "用户列表页",
                        "page_type": "web_list",
                        "output_file": "user-list.html",
                        "fields": [{"name": "用户名", "control": "input", "required": "否", "note": ""}],
                        "table_columns": [{"name": "用户名", "note": ""}],
                        "actions": ["新增用户"],
                        "jumps": [{"action": "新增用户", "target": "用户列表页"}],
                        "states": ["启用", "停用"],
                    }
                ],
            )

            previous = os.environ.get("PROTOTYPE_GENERATOR_REFERENCE_SEARCH_CMD")
            os.environ["PROTOTYPE_GENERATOR_REFERENCE_SEARCH_CMD"] = f"{sys.executable} {hook_path}"
            try:
                manifest = REFERENCE_UTILS.ensure_reference_pack(workdir)
            finally:
                if previous is None:
                    os.environ.pop("PROTOTYPE_GENERATOR_REFERENCE_SEARCH_CMD", None)
                else:
                    os.environ["PROTOTYPE_GENERATOR_REFERENCE_SEARCH_CMD"] = previous

            self.assertEqual(manifest["pages"][0]["reference_basis"], "external")
            self.assertIn("https://example.com/case", "".join(manifest["pages"][0]["reference_sources"]))

    def test_html_pipeline_writes_reference_pack_and_reference_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "用户列表页参考.png").write_bytes(b"fake")
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                        "- 手机号\n"
                        "- 状态\n"
                    ),
                },
            )
            _write_html_page_spec(
                workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md",
                "后台-用户管理",
                "user",
                [
                    {
                        "page_name": "用户列表页",
                        "page_type": "web_list",
                        "output_file": "user-list.html",
                        "fields": [
                            {"name": "用户名", "control": "input", "required": "否", "note": ""},
                            {"name": "手机号", "control": "input", "required": "否", "note": ""},
                            {"name": "状态", "control": "select", "required": "否", "note": ""},
                        ],
                        "table_columns": [
                            {"name": "用户名", "note": ""},
                            {"name": "手机号", "note": ""},
                            {"name": "状态", "note": ""},
                        ],
                        "actions": ["新增用户", "编辑", "删除"],
                        "jumps": [{"action": "新增用户", "target": "用户列表页"}],
                        "states": ["启用", "审核中", "停用"],
                    }
                ],
            )

            returncode, payload = _run_html_pipeline_cli(workdir, "渔易购-后台管理")

            self.assertEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            reference_manifest = workdir / ".prototype-generator" / "reference_pack" / "manifest.json"
            self.assertTrue(reference_manifest.is_file())
            self.assertEqual(Path(payload["artifacts"]["reference_pack"]).resolve(), (workdir / ".prototype-generator" / "reference_pack").resolve())
            html_text = (workdir / "prototypes" / "user-list.html").read_text(encoding="utf-8")
            self.assertIn('data-page-archetype="list_table"', html_text)
            self.assertIn('data-reference-basis="internal"', html_text)

    def test_validate_html_flags_missing_reference_metadata_and_weak_list_skeleton(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "weak.html").write_text(
                "<!DOCTYPE html><html><head><title>Weak</title><link rel='stylesheet' href='common.css'></head><body>"
                "<div data-prototype-shell='1' data-page-name='弱列表' data-page-type='web_list'>"
                "<main><table><tr><td>一行</td></tr></table><a class='btn-primary' href='#'>新增</a>"
                "<div data-state='empty'></div><div data-state='error'></div></main></div></body></html>",
                encoding="utf-8",
            )
            report = VALIDATE_HTML.run_checks(root)

        self.assertEqual(next(item for item in report["results"] if item["rule"] == "H7")["status"], "FAIL")
        self.assertEqual(next(item for item in report["results"] if item["rule"] == "H8")["status"], "FAIL")

    def test_validate_html_flags_unstable_font_and_scale_styles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "unstable.html").write_text(
                "<!DOCTYPE html><html><head><title>Unstable</title><link rel='stylesheet' href='common.css'>"
                "<style>.bad-button{font-family:'Times New Roman';transform:scale(0.9);}</style></head><body>"
                "<div data-prototype-shell='1' data-page-name='不稳定页面' data-page-type='web_form' "
                "data-page-archetype='modal_form' data-reference-basis='internal'>"
                "<main><section class='prototype-card'><div class='form-group'><label>名称</label>"
                "<input class='input' placeholder='名称'></div><div class='form-group'><label>备注</label>"
                "<textarea class='input prototype-textarea' placeholder='备注'></textarea></div></section>"
                "<section class='prototype-card sticky-action-card'><a class='btn-primary bad-button' href='#'>提交</a>"
                "<a class='btn-secondary' href='#'>取消</a></section>"
                "<div data-state='processing'></div><div data-state='empty'></div><div data-state='error'></div></main>"
                "</div></body></html>",
                encoding="utf-8",
            )
            report = VALIDATE_HTML.run_checks(root)

        self.assertEqual(next(item for item in report["results"] if item["rule"] == "H10")["status"], "FAIL")

    def test_html_renderer_login_page_excludes_admin_navigation(self):
        spec = {"module_name": "后台-登录页"}
        page = {
            "page_name": "后台登录页",
            "page_type": "login",
            "page_archetype": "login",
            "reference_basis": "internal",
            "reference_summary": "登录页参考摘要",
            "fields": [
                {"name": "账号", "control": "input", "required": "是", "note": ""},
                {"name": "密码", "control": "input", "required": "是", "note": ""},
                {"name": "图形验证码", "control": "input", "required": "是", "note": ""},
            ],
            "actions": ["登录", "联系管理员"],
            "jumps": [],
            "states": ["默认", "验证码错误"],
        }
        html_text = HTML_UTILS.render_page_html(spec, page, {})

        self.assertIn("prototype-login-card", html_text)
        self.assertNotIn("prototype-sidebar", html_text)
        self.assertNotIn("nav-item", html_text)

    def test_html_renderer_list_page_contains_filter_table_and_pagination(self):
        spec = {"module_name": "后台-用户管理"}
        page = {
            "page_name": "用户列表页",
            "page_type": "web_list",
            "page_archetype": "list_table",
            "reference_basis": "internal",
            "reference_summary": "列表页参考摘要",
            "fields": [
                {"name": "用户名", "control": "input", "required": "否", "note": ""},
                {"name": "手机号", "control": "input", "required": "否", "note": ""},
                {"name": "状态", "control": "select", "required": "否", "note": ""},
            ],
            "table_columns": [{"name": "用户名", "note": ""}, {"name": "手机号", "note": ""}, {"name": "状态", "note": ""}],
            "actions": ["新增用户", "导出", "查看详情"],
            "jumps": [{"action": "新增用户", "target": "用户列表页"}],
            "states": ["启用", "停用"],
        }
        html_text = HTML_UTILS.render_page_html(spec, page, {"用户列表页": "user-list.html"})

        self.assertIn("filter-grid", html_text)
        self.assertIn("<table", html_text)
        self.assertIn("prototype-pagination", html_text)

    def test_html_renderer_detail_page_keeps_detail_skeleton_for_h8(self):
        spec = {"module_name": "后台-订单管理"}
        page = {
            "page_name": "订单详情页",
            "page_type": "web_detail",
            "page_archetype": "detail_kv",
            "reference_basis": "internal",
            "reference_summary": "详情页参考摘要",
            "fields": [
                {"name": "订单编号", "control": "input", "required": "是", "note": ""},
                {"name": "订单状态", "control": "input", "required": "是", "note": ""},
                {"name": "用户信息", "control": "input", "required": "是", "note": ""},
            ],
            "actions": ["返回", "编辑"],
            "jumps": [],
            "states": ["待处理", "已完成"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "common.css").write_text("/* ok */", encoding="utf-8")
            (root / "detail.html").write_text(HTML_UTILS.render_page_html(spec, page, {}), encoding="utf-8")
            report = VALIDATE_HTML.run_checks(root)

        self.assertEqual(next(item for item in report["results"] if item["rule"] == "H8")["status"], "PASS")

    def test_html_renderer_confirm_page_distinguishes_primary_and_secondary_actions_for_h9(self):
        spec = {"module_name": "后台-订单管理"}
        page = {
            "page_name": "关闭订单确认弹窗",
            "page_type": "web_form",
            "page_archetype": "modal_form",
            "reference_basis": "internal",
            "reference_summary": "确认页参考摘要",
            "fields": [{"name": "关闭原因", "control": "textarea", "required": "是", "note": ""}],
            "actions": ["确认", "取消"],
            "jumps": [],
            "states": ["处理中", "失败"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "common.css").write_text("/* ok */", encoding="utf-8")
            (root / "confirm.html").write_text(HTML_UTILS.render_page_html(spec, page, {}), encoding="utf-8")
            report = VALIDATE_HTML.run_checks(root)

        self.assertEqual(next(item for item in report["results"] if item["rule"] == "H9")["status"], "PASS")

    def test_html_renderer_outputs_consistency_markers(self):
        spec = {"module_name": "后台-用户管理"}
        page = {
            "page_name": "用户列表页",
            "page_type": "web_list",
            "page_archetype": "list_table",
            "reference_basis": "external",
            "reference_summary": "列表页参考摘要",
            "fields": [{"name": "用户名", "control": "input", "required": "否", "note": ""}],
            "table_columns": [{"name": "用户名", "note": ""}],
            "actions": ["新增用户", "编辑"],
            "jumps": [],
            "states": ["启用", "停用"],
        }
        html_text = HTML_UTILS.render_page_html(spec, page, {})

        self.assertIn('data-page-type="web_list"', html_text)
        self.assertIn('data-page-archetype="list_table"', html_text)
        self.assertIn('data-reference-basis="external"', html_text)
        self.assertIn('data-prototype-shell="1"', html_text)
        self.assertIn('data-body-slot="1"', html_text)
        self.assertIn("BODY_SLOT_START", html_text)
        self.assertIn("BODY_SLOT_END", html_text)

    def test_render_html_writes_body_slot_artifacts(self):
        spec = {"module_name": "后台-用户管理", "module_key": "admin_user"}
        page = {
            "page_name": "用户列表页",
            "page_type": "web_list",
            "page_archetype": "list_table",
            "output_file": "user-list.html",
            "reference_basis": "internal",
            "reference_summary": "列表页参考摘要",
            "fields": [{"name": "用户名", "control": "input", "required": "否", "note": ""}],
            "table_columns": [{"name": "用户名", "note": ""}],
            "actions": ["新增用户", "编辑"],
            "jumps": [],
            "states": ["启用", "停用"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page_spec_path = root / "page_spec_user.md"
            page_spec_path.write_text(HTML_UTILS.to_markdown({"module_name": "后台-用户管理", "module_key": "admin_user", "output_format": "html", "pages": [page]}), encoding="utf-8")
            report = RENDER_HTML.render_spec(page_spec_path, root / "prototypes", body_slots_dir=root / "body_slots")

            artifacts = report["rendered_pages"][0]["body_slot_artifacts"]
            self.assertTrue(Path(artifacts["body_spec"]).is_file())
            self.assertTrue(Path(artifacts["body_prompt"]).is_file())
            self.assertTrue(Path(artifacts["body_html"]).is_file())
            self.assertIn('"slot_mode": "controlled_body"', Path(artifacts["body_spec"]).read_text(encoding="utf-8"))
            self.assertIn("只输出 body slot 片段", Path(artifacts["body_prompt"]).read_text(encoding="utf-8"))
            self.assertIn("filter-grid", Path(artifacts["body_html"]).read_text(encoding="utf-8"))

    def test_html_pipeline_routes_layout_mismatch_to_module_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                        "- 手机号\n"
                        "- 状态\n"
                    ),
                },
            )
            _write_html_page_spec(
                workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md",
                "后台-用户管理",
                "user",
                [
                    {
                        "page_name": "用户列表页",
                        "page_type": "web_detail",
                        "page_archetype": "detail_kv",
                        "output_file": "user-list.html",
                        "fields": [{"name": "用户名", "control": "input", "required": "否", "note": ""}],
                        "actions": ["返回", "编辑"],
                        "jumps": [],
                        "states": ["正常", "异常"],
                    }
                ],
            )

            returncode, payload = _run_html_pipeline_cli(workdir, "渔易购-后台管理")

            self.assertNotEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            finding = next(item for item in payload["review_findings"] if item["rule"] == "LAYOUT_MISMATCH")
            self.assertEqual(finding["repair_target"], "module_brief")
            self.assertEqual(finding["repair_action"], "rewrite_module_brief")

    def test_html_pipeline_routes_h8_to_patch_renderer_when_archetype_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                    ),
                },
            )
            root = workdir / "prototypes"
            root.mkdir(parents=True, exist_ok=True)
            (root / "user-list.html").write_text(
                "<!DOCTYPE html><html><head><title>Weak</title><link rel='stylesheet' href='common.css'></head><body>"
                "<div data-prototype-shell='1' data-page-name='用户列表页' data-page-type='web_list' data-page-archetype='list_table' data-reference-basis='internal'>"
                "<main><table><tr><td>一行</td></tr></table><a class='btn-primary' href='#'>新增</a>"
                "<div data-state='empty'></div><div data-state='error'></div></main></div></body></html>",
                encoding="utf-8",
            )
            generated_meta = RUN_HTML_PIPELINE_MODULE._load_generated_page_meta(root)
            findings = RUN_HTML_PIPELINE_MODULE._collect_review_findings(
                scope="admin",
                consistency={"missing_pages": [], "missing_field_pages": [], "low_coverage_pages": [], "layout_mismatch_pages": []},
                html_validation={
                    "results": [
                        {"rule": "H8", "status": "FAIL", "details": ["user-list.html: 列表页缺少真实表格或数据行不足"]},
                    ]
                },
                requirements_dir=workdir / "requirements",
                generated_meta=generated_meta,
            )

        self.assertEqual(findings[0]["repair_target"], "html_render")
        self.assertEqual(findings[0]["repair_action"], "patch_renderer")

    def test_html_pipeline_routes_h10_to_patch_renderer(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户表单页\n"
                        "- 用户名\n"
                    ),
                },
            )
            root = workdir / "prototypes"
            root.mkdir(parents=True, exist_ok=True)
            (root / "user-form.html").write_text(
                "<!DOCTYPE html><html><head><title>Unstable</title><link rel='stylesheet' href='common.css'>"
                "<style>.bad-button{font-family:'Times New Roman';transform:scale(0.9);}</style></head><body>"
                "<div data-prototype-shell='1' data-page-name='用户表单页' data-page-type='web_form' "
                "data-page-archetype='modal_form' data-reference-basis='internal'>"
                "<main><section class='prototype-card'><div class='form-group'><label>用户名</label>"
                "<input class='input' placeholder='用户名'></div><div class='form-group'><label>备注</label>"
                "<textarea class='input prototype-textarea' placeholder='备注'></textarea></div></section>"
                "<section class='prototype-card sticky-action-card'><a class='btn-primary bad-button' href='#'>提交</a>"
                "<a class='btn-secondary' href='#'>取消</a></section>"
                "<div data-state='processing'></div><div data-state='empty'></div><div data-state='error'></div></main>"
                "</div></body></html>",
                encoding="utf-8",
            )
            generated_meta = RUN_HTML_PIPELINE_MODULE._load_generated_page_meta(root)
            findings = RUN_HTML_PIPELINE_MODULE._collect_review_findings(
                scope="admin",
                consistency={"missing_pages": [], "missing_field_pages": [], "low_coverage_pages": [], "layout_mismatch_pages": []},
                html_validation={
                    "results": [
                        {"rule": "H10", "status": "FAIL", "details": ["user-form.html: 命中不稳定样式 `font-family\\s*:`"]},
                    ]
                },
                requirements_dir=workdir / "requirements",
                generated_meta=generated_meta,
            )

        self.assertEqual(findings[0]["repair_target"], "html_render")
        self.assertEqual(findings[0]["repair_action"], "patch_renderer")

    def test_validate_html_flags_missing_body_slot_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "missing-slot.html").write_text(
                "<!DOCTYPE html><html><head><title>Missing Slot</title><link rel='stylesheet' href='common.css'></head><body>"
                "<div data-prototype-shell='1' data-page-name='用户列表页' data-page-type='web_list' "
                "data-page-archetype='list_table' data-reference-basis='internal'>"
                "<main><div class='filter-grid'></div><table class='prototype-table'><tr></tr><tr></tr><tr></tr><tr></tr></table>"
                "<div class='prototype-pagination'></div><div data-state='empty'></div><div data-state='error'></div></main>"
                "</div></body></html>",
                encoding="utf-8",
            )
            report = VALIDATE_HTML.run_checks(root)

        self.assertEqual(next(item for item in report["results"] if item["rule"] == "H11")["status"], "FAIL")

    def test_html_pipeline_routes_h11_to_patch_renderer(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                    ),
                },
            )
            root = workdir / "prototypes"
            root.mkdir(parents=True, exist_ok=True)
            (root / "user-list.html").write_text(
                "<!DOCTYPE html><html><head><title>Weak</title><link rel='stylesheet' href='common.css'></head><body>"
                "<div data-prototype-shell='1' data-page-name='用户列表页' data-page-type='web_list' "
                "data-page-archetype='list_table' data-reference-basis='internal'>"
                "<main><div class='filter-grid'></div><table class='prototype-table'><tr></tr><tr></tr><tr></tr><tr></tr></table>"
                "<div class='prototype-pagination'></div><div data-state='empty'></div><div data-state='error'></div></main>"
                "</div></body></html>",
                encoding="utf-8",
            )
            generated_meta = RUN_HTML_PIPELINE_MODULE._load_generated_page_meta(root)
            findings = RUN_HTML_PIPELINE_MODULE._collect_review_findings(
                scope="admin",
                consistency={"missing_pages": [], "missing_field_pages": [], "low_coverage_pages": [], "layout_mismatch_pages": []},
                html_validation={
                    "results": [
                        {"rule": "H11", "status": "FAIL", "details": ["user-list.html: 缺少 body slot 标记"]},
                    ]
                },
                requirements_dir=workdir / "requirements",
                generated_meta=generated_meta,
            )

        self.assertEqual(findings[0]["repair_target"], "html_render")
        self.assertEqual(findings[0]["repair_action"], "patch_renderer")

    def test_reference_pack_blocks_prototypes_html_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            (workdir / "prototypes-html").mkdir(parents=True, exist_ok=True)
            (workdir / "prototypes-html" / "用户列表页参考.html").write_text("<html></html>", encoding="utf-8")
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                    ),
                },
            )
            _write_html_page_spec(
                workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md",
                "后台-用户管理",
                "user",
                [
                    {
                        "page_name": "用户列表页",
                        "page_type": "web_list",
                        "page_archetype": "list_table",
                        "output_file": "user-list.html",
                        "fields": [{"name": "用户名", "control": "input", "required": "否", "note": ""}],
                        "table_columns": [{"name": "用户名", "note": ""}],
                        "actions": ["新增用户", "编辑"],
                        "jumps": [],
                        "states": ["启用", "停用"],
                    }
                ],
            )

            manifest = REFERENCE_UTILS.ensure_reference_pack(workdir)
            returncode, payload = _run_html_pipeline_cli(workdir, "渔易购-后台管理")

            self.assertTrue(manifest["blocked_sources"])
            self.assertTrue(manifest["policy_violations"])
            self.assertNotEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["review_findings"][0]["rule"], "REFERENCE_POLICY")

    def test_repair_html_renderer_restores_baseline_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_root = Path(tmp) / "prototype-generator"
            (skill_root / "scripts").mkdir(parents=True, exist_ok=True)
            (skill_root / "templates").mkdir(parents=True, exist_ok=True)
            (skill_root / "templates" / "html_utils_renderer_baseline.py").write_text(
                (SKILL_DIR / "templates" / "html_utils_renderer_baseline.py").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (skill_root / "templates" / "render_html_renderer_baseline.py").write_text(
                (SKILL_DIR / "templates" / "render_html_renderer_baseline.py").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (skill_root / "templates" / "common_renderer_baseline.css").write_text(
                (SKILL_DIR / "templates" / "common_renderer_baseline.css").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (skill_root / "scripts" / "html_utils.py").write_text("# broken renderer\n", encoding="utf-8")
            (skill_root / "scripts" / "render_html.py").write_text("# broken render entry\n", encoding="utf-8")
            (skill_root / "templates" / "common.css").write_text("/* broken */\n", encoding="utf-8")

            changes = AUTOFIX.repair_html_renderer(skill_root, [{"repair_action": "patch_renderer"}])

            self.assertTrue(changes)
            self.assertEqual(
                (skill_root / "scripts" / "html_utils.py").read_text(encoding="utf-8"),
                (skill_root / "templates" / "html_utils_renderer_baseline.py").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (skill_root / "scripts" / "render_html.py").read_text(encoding="utf-8"),
                (skill_root / "templates" / "render_html_renderer_baseline.py").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (skill_root / "templates" / "common.css").read_text(encoding="utf-8"),
                (skill_root / "templates" / "common_renderer_baseline.css").read_text(encoding="utf-8"),
            )

    def test_autonomous_html_pipeline_repairs_page_spec_and_converges(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                        "- 手机号\n"
                        "- 状态\n"
                    ),
                },
            )
            _write_html_page_spec(
                workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md",
                "后台-用户管理",
                "user",
                [
                    {
                        "page_name": "用户列表页",
                        "page_type": "web_list",
                        "output_file": "user-list.html",
                        "is_nav_page": False,
                        "fields": [{"name": "用户名", "control": "input", "required": "否", "note": ""}],
                        "table_columns": [{"name": "用户名", "note": ""}],
                        "actions": ["新增用户"],
                        "jumps": [{"action": "新增用户", "target": "用户列表页"}],
                        "states": ["启用"],
                    }
                ],
            )

            returncode, payload = _run_autoloop_cli(workdir, "渔易购-后台管理", "html")

            self.assertEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["status"], "passed")
            self.assertGreaterEqual(len(payload["rounds"]), 2)
            repaired_spec = (workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md").read_text(encoding="utf-8")
            self.assertIn("手机号", repaired_spec)
            self.assertIn("状态", repaired_spec)

    def test_autonomous_drawio_pipeline_repairs_page_model_and_converges(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-登录页.md": (
                        "# 渔易购 — 后台-登录页需求\n\n"
                        "#### 功能点 1.1：后台登录\n"
                        "- **页面/界面：** 后台登录页\n"
                        "- 账号\n"
                        "- 密码\n"
                        "- 图形验证码\n"
                    ),
                },
            )
            broken_login = _login_model()
            broken_login["pages"][0]["fields"] = [{"name": "账号", "control": "input", "required": True, "validation": "请输入后台账号"}]
            _write_json(workdir / ".prototype-generator" / "page_models" / "page_model_admin_login.json", broken_login)

            returncode, payload = _run_autoloop_cli(workdir, "渔易购-后台管理", "drawio")

            self.assertEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["status"], "passed")
            self.assertGreaterEqual(len(payload["rounds"]), 2)
            repaired = json.loads((workdir / ".prototype-generator" / "page_models" / "page_model_admin_login.json").read_text(encoding="utf-8"))
            repaired_fields = [item["name"] for item in repaired["pages"][0]["fields"]]
            self.assertIn("密码", repaired_fields)
            self.assertIn("图形验证码", repaired_fields)

    def test_autonomous_pipeline_resume_from_review_completed_repairs_and_converges(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                        "- 手机号\n"
                        "- 状态\n"
                    ),
                },
            )
            _write_html_page_spec(
                workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md",
                "后台-用户管理",
                "user",
                [
                    {
                        "page_name": "用户列表页",
                        "page_type": "web_list",
                        "output_file": "user-list.html",
                        "is_nav_page": False,
                        "fields": [{"name": "用户名", "control": "input", "required": "否", "note": ""}],
                        "table_columns": [{"name": "用户名", "note": ""}],
                        "actions": ["新增用户"],
                        "jumps": [{"action": "新增用户", "target": "用户列表页"}],
                        "states": ["启用"],
                    }
                ],
            )

            first_returncode, first_payload = _run_html_pipeline_cli(workdir, "渔易购-后台管理")
            self.assertNotEqual(first_returncode, 0, json.dumps(first_payload, ensure_ascii=False))

            round_dir = workdir / ".prototype-generator" / "rounds" / "round_01"
            _write_json(round_dir / "pipeline_report.json", first_payload)
            _write_json(
                round_dir / "round_report.json",
                {
                    "round": 1,
                    "pipeline_report": first_payload,
                    "vision_review": {"status": "skipped", "mode": "auto", "findings": []},
                    "finding_count": len(first_payload["review_findings"]),
                    "escalations": [],
                },
            )
            _write_autoloop_state(
                workdir,
                product_name="渔易购-后台管理",
                format_name="html",
                status="running",
                phase="review_completed",
                current_round=1,
                next_round=2,
                rounds=[{"round": 1, "finding_count": len(first_payload["review_findings"]), "escalations": [], "summary": first_payload["summary"]}],
                latest_findings=first_payload["review_findings"],
                final_artifact=first_payload["artifacts"]["index_html"],
            )

            returncode, payload = _run_autoloop_cli(workdir, "渔易购-后台管理", "html", resume=True)

            self.assertEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertTrue(payload["resumed"])
            self.assertEqual(payload["resume_from_phase"], "review_completed")
            self.assertEqual(payload["resume_from_round"], 1)
            self.assertEqual([item["round"] for item in payload["rounds"]], [1, 2])
            repaired_spec = (workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md").read_text(encoding="utf-8")
            self.assertIn("手机号", repaired_spec)
            self.assertIn("状态", repaired_spec)
            execution_state = (workdir / ".prototype-generator" / "执行状态.md").read_text(encoding="utf-8")
            self.assertIn("--resume from round 1 / review_completed", execution_state)

    def test_autonomous_pipeline_resume_from_round_repaired_starts_next_round(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                        "- 手机号\n"
                        "- 状态\n"
                    ),
                },
            )
            _write_html_page_spec(
                workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md",
                "后台-用户管理",
                "user",
                [
                    {
                        "page_name": "用户列表页",
                        "page_type": "web_list",
                        "output_file": "user-list.html",
                        "is_nav_page": False,
                        "fields": [
                            {"name": "用户名", "control": "input", "required": "否", "note": ""},
                            {"name": "手机号", "control": "input", "required": "否", "note": ""},
                            {"name": "状态", "control": "select", "required": "否", "note": ""},
                        ],
                        "table_columns": [
                            {"name": "用户名", "note": ""},
                            {"name": "手机号", "note": ""},
                            {"name": "状态", "note": ""},
                        ],
                        "actions": ["新增用户"],
                        "jumps": [{"action": "新增用户", "target": "用户列表页"}],
                        "states": ["启用", "禁用"],
                    }
                ],
            )
            _write_autoloop_state(
                workdir,
                product_name="渔易购-后台管理",
                format_name="html",
                status="running",
                phase="round_repaired",
                current_round=1,
                next_round=2,
                rounds=[{"round": 1, "finding_count": 2, "escalations": [], "summary": {"fail": 1, "warn": 0, "pass": 0}}],
                latest_findings=[{"severity": "error", "rule": "MISSING_FIELDS", "page_or_sheet": "用户列表页"}],
                final_artifact=str(workdir / "prototypes" / "index.html"),
            )

            returncode, payload = _run_autoloop_cli(workdir, "渔易购-后台管理", "html", resume=True)

            self.assertEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["resume_from_phase"], "round_repaired")
            self.assertEqual([item["round"] for item in payload["rounds"]], [1, 2])

    def test_autonomous_pipeline_resume_returns_existing_pass_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            round_dir = workdir / ".prototype-generator" / "rounds" / "round_01"
            pipeline_report = {
                "summary": {"fail": 0, "warn": 0, "pass": 1},
                "artifacts": {"index_html": str(workdir / "prototypes" / "index.html")},
            }
            _write_json(round_dir / "pipeline_report.json", pipeline_report)
            _write_autoloop_state(
                workdir,
                product_name="渔易购-后台管理",
                format_name="html",
                status="passed",
                phase="completed",
                current_round=1,
                next_round=2,
                rounds=[{"round": 1, "finding_count": 0, "escalations": [], "summary": {"fail": 0, "warn": 0, "pass": 1}}],
                latest_findings=[],
                final_artifact=str(workdir / "prototypes" / "index.html"),
            )

            returncode, payload = _run_autoloop_cli(workdir, "渔易购-后台管理", "html", resume=True)

            self.assertEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["status"], "passed")
            self.assertTrue(payload["resumed"])
            self.assertEqual(payload["resume_from_phase"], "completed")
            self.assertEqual(len(payload["rounds"]), 1)

    def test_autonomous_pipeline_resume_fails_when_state_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)

            returncode, payload = _run_autoloop_cli(workdir, "渔易购-后台管理", "html", resume=True)

            self.assertNotEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertIn("resume state not found", payload["error"])

    def test_autonomous_pipeline_resume_fails_when_state_is_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            state_path = workdir / ".prototype-generator" / "autoloop_state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text("{bad json", encoding="utf-8")

            returncode, payload = _run_autoloop_cli(workdir, "渔易购-后台管理", "html", resume=True)

            self.assertNotEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertIn("resume state is not valid JSON", payload["error"])

    def test_autonomous_pipeline_resume_fails_when_state_context_mismatches(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_autoloop_state(
                workdir,
                product_name="别的产品",
                format_name="html",
                status="running",
                phase="round_started",
                current_round=1,
                next_round=1,
                rounds=[],
                latest_findings=[],
            )

            returncode, payload = _run_autoloop_cli(workdir, "渔易购-后台管理", "html", resume=True)

            self.assertNotEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertIn("resume state does not match", payload["error"])

    def test_autonomous_pipeline_failed_state_requires_higher_max_rounds_to_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                    ),
                },
            )
            _write_html_page_spec(
                workdir / ".prototype-generator" / "page_specs" / "page_spec_user.md",
                "后台-用户管理",
                "user",
                [
                    {
                        "page_name": "用户列表页",
                        "page_type": "web_list",
                        "output_file": "user-list.html",
                        "is_nav_page": False,
                        "fields": [{"name": "用户名", "control": "input", "required": "否", "note": ""}],
                        "table_columns": [{"name": "用户名", "note": ""}],
                        "actions": ["新增用户"],
                        "jumps": [{"action": "新增用户", "target": "用户列表页"}],
                        "states": ["启用"],
                    }
                ],
            )
            _write_autoloop_state(
                workdir,
                product_name="渔易购-后台管理",
                format_name="html",
                status="failed",
                phase="completed",
                current_round=2,
                next_round=3,
                rounds=[
                    {"round": 1, "finding_count": 1, "escalations": [], "summary": {"fail": 1, "warn": 0, "pass": 0}},
                    {"round": 2, "finding_count": 1, "escalations": [], "summary": {"fail": 1, "warn": 0, "pass": 0}},
                ],
                latest_findings=[{"severity": "error", "rule": "VISION_BACKEND", "page_or_sheet": "index.html"}],
                blocked_findings=[{"severity": "error", "rule": "VISION_BACKEND", "page_or_sheet": "index.html"}],
                max_rounds=2,
                vision_review="required",
            )

            fail_code, fail_payload = _run_autoloop_cli(workdir, "渔易购-后台管理", "html", resume=True, max_rounds=2, vision_review="required")
            self.assertNotEqual(fail_code, 0, json.dumps(fail_payload, ensure_ascii=False))
            self.assertEqual(len(fail_payload["rounds"]), 2)

            continue_code, continue_payload = _run_autoloop_cli(workdir, "渔易购-后台管理", "html", resume=True, max_rounds=3, vision_review="required")
            self.assertNotEqual(continue_code, 0, json.dumps(continue_payload, ensure_ascii=False))
            self.assertEqual([item["round"] for item in continue_payload["rounds"]], [1, 2, 3])

    def test_autonomous_pipeline_records_blockers_after_max_rounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_requirements_split(
                workdir,
                {
                    "详细需求文档_后台-用户管理.md": (
                        "# 渔易购 — 后台-用户管理需求\n\n"
                        "#### 功能点 1.1：用户管理\n"
                        "- **页面/界面：** 用户列表页\n"
                        "- 用户名\n"
                    ),
                },
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(RUN_AUTO_PIPELINE),
                    str(workdir),
                    "渔易购-后台管理",
                    "--format",
                    "html",
                    "--max-rounds",
                    "2",
                    "--vision-review",
                    "required",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(completed.stdout) if completed.stdout.strip() else {}

            self.assertNotEqual(completed.returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["status"], "failed")
            self.assertTrue(payload["blocked_findings"])
            state = json.loads((workdir / ".prototype-generator" / "autoloop_state.json").read_text(encoding="utf-8"))
            self.assertIn("failure_summary", state)
            self.assertIn("stop_recommendation", state)
            self.assertTrue(state["last_unconverged_reason"])


if __name__ == "__main__":
    unittest.main()
