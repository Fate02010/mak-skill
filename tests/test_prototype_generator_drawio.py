import importlib.util
import json
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


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BUILD_PAGE_SPEC = _load_module("build_page_spec_test", SCRIPTS_DIR / "build_page_spec.py")
RENDER = _load_module("render_test", SCRIPTS_DIR / "render.py")
VALIDATE = _load_module("validate_test", SCRIPTS_DIR / "validate.py")
MERGE = _load_module("merge_test", SCRIPTS_DIR / "merge.py")
CONSISTENCY = _load_module("consistency_test", SCRIPTS_DIR / "check_prototype_consistency.py")
BRIEF_CONSISTENCY = _load_module("brief_consistency_test", SCRIPTS_DIR / "check_module_brief_consistency.py")
CONTEXT_BUDGET = _load_module("context_budget_test", SCRIPTS_DIR / "check_context_budget.py")
RUN_PIPELINE = SCRIPTS_DIR / "run_drawio_pipeline.py"


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


def _drawer_permission_model() -> dict:
    return {
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
    }


def _detail_model() -> dict:
    return {
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
                    {"name": "下单时间", "control": "input", "required": True, "validation": ""},
                    {"name": "会员名称", "control": "input", "required": True, "validation": ""},
                    {"name": "手机号", "control": "input", "required": True, "validation": "手机号格式"},
                    {
                        "name": "配送方式",
                        "control": "select",
                        "required": True,
                        "options": ["冷链配送", "门店自提"],
                        "validation": "",
                    },
                    {
                        "name": "支付方式",
                        "control": "select",
                        "required": True,
                        "options": ["微信支付", "余额支付"],
                        "validation": "",
                    },
                    {"name": "收货地址", "control": "input", "required": True, "validation": ""},
                    {"name": "商品金额", "control": "input", "required": True, "validation": ""},
                    {"name": "运费", "control": "input", "required": True, "validation": ""},
                    {"name": "优惠金额", "control": "input", "required": False, "validation": ""},
                    {"name": "应付金额", "control": "input", "required": True, "validation": ""},
                    {"name": "客服备注", "control": "textarea", "required": False, "validation": "200字以内"},
                ],
                "status_values": ["待发货", "已发货", "已完成", "已退款"],
                "actions": [
                    {"name": "发货", "target": "发货单详情页", "kind": "primary"},
                    {"name": "备注", "target": "订单备注弹窗", "kind": "secondary"},
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
    }


def _login_model() -> dict:
    return {
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
    }


def _marketing_list_model() -> dict:
    return {
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
                    {"name": "门槛金额", "control": "input", "required": True, "validation": "金额格式"},
                    {"name": "优惠值", "control": "input", "required": True, "validation": "金额格式"},
                    {"name": "生效时间", "control": "input", "required": True, "validation": "开始时间不能晚于结束时间"},
                    {"name": "发布状态", "control": "select", "required": True, "options": ["草稿", "生效"], "validation": ""},
                ],
                "table_columns": ["活动名称", "活动类型", "门槛金额", "优惠值", "发布状态", "更新时间"],
                "status_values": ["草稿", "生效", "已结束"],
                "actions": [{"name": "编辑", "target": "新增/编辑营销活动弹窗", "kind": "primary"}],
                "jump_targets": ["新增/编辑营销活动弹窗"],
            }
        ],
    }


def _shipping_modal_model() -> dict:
    return {
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
    }


def _bad_shipping_modal_model() -> dict:
    return {
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
    }


def _bad_marketing_form_model() -> dict:
    return {
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
    }


def _bad_resource_model() -> dict:
    return {
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
    }


def _employee_list_model() -> dict:
    return {
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
    }


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
    return {
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
    }


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


def _run_pipeline_cli(workdir: Path, product_name: str) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, str(RUN_PIPELINE), str(workdir), product_name, "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    return completed.returncode, payload


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
                        "- 生效时间\n"
                        "列表展示列：\n"
                        "| 字段 | 说明 |\n"
                        "| --- | --- |\n"
                        "| 活动名称 | 活动名称 |\n"
                        "| 活动类型 | 活动类型 |\n"
                        "| 门槛金额 | 满足门槛 |\n"
                        "| 优惠值 | 优惠内容 |\n"
                        "| 发布状态 | 当前状态 |\n"
                        "| 更新时间 | 更新时间 |\n"
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

    def test_edit_modal_keeps_footer_actions_below_last_field(self):
        markdown = _build_page_spec_markdown(_marketing_list_model())
        self.assertIn("新增/编辑营销活动", markdown)
        _, swimlanes, elements = _parse_spec(markdown)
        modal_lane = next(sw for sw in swimlanes if sw["swimlane_label"] == "新增/编辑营销活动弹窗")
        modal_lane_id = modal_lane["swimlane_id"]
        modal_bg = _find_element(elements, parent=modal_lane_id, style_key="modal_bg")
        confirm_button = _find_element(elements, parent=modal_lane_id, value="确认")
        last_field = _find_element(elements, parent=modal_lane_id, value="请选择发布状态")
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

    def test_consistency_scope_ignores_miniapp_requirements_for_backend_bundle(self):
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

            report = CONSISTENCY.check_consistency(str(workdir / "requirements"), str(page_specs_dir), 0.8, "backend")
            self.assertEqual(report["scope"], "backend")
            self.assertNotIn("首页", report["missing_pages"])
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

    def test_run_drawio_pipeline_uses_backend_scope_when_product_name_mentions_admin(self):
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
            self.assertEqual(payload["consistency_scope"], "backend")
            self.assertNotIn("首页", payload["consistency"]["missing_pages"])

    def test_run_drawio_pipeline_fails_when_module_brief_drops_required_pages(self):
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
            self.assertEqual(payload["module_brief_consistency"]["summary"]["fail"], 1)
            self.assertEqual(payload["failure_routing"][0]["layer"], "requirements")

    def test_run_drawio_pipeline_fails_when_context_budget_is_unsafe(self):
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

            self.assertNotEqual(returncode, 0, json.dumps(payload, ensure_ascii=False))
            self.assertEqual(payload["context_budget"]["summary"]["fail"], 1)
            self.assertEqual(payload["failure_routing"][0]["layer"], "requirements")

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


if __name__ == "__main__":
    unittest.main()
