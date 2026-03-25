import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


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


def _build_page_spec_markdown(model: dict) -> str:
    BUILD_PAGE_SPEC.validate_model(model)
    builder = BUILD_PAGE_SPEC.PageSpecBuilder(model)
    module_name, swimlanes, elements = builder.build()
    return BUILD_PAGE_SPEC.to_markdown(module_name, swimlanes, elements)


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


class PrototypeGeneratorDrawioTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
