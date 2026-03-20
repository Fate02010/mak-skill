# subagent 提示词模板

根据 OUTPUT_FORMAT 选择对应模板，填入模块数据后启动。

---

## HTML 模式（OUTPUT_FORMAT=html）

```
你是 [模块名] 的原型生成 Agent。

先读取 [SKILL_DIR]/steps/html-spec.md 获取 HTML 原型规范，然后生成以下页面。

【工作目录】
WORK_DIR = [WORK_DIR的绝对路径]
所有文件必须保存在 WORK_DIR/prototypes/ 下，严禁写入 /private/tmp 或其他系统临时目录。

【本模块负责的页面】
1. [页面名称1] → 保存为 prototypes/[文件名1].html
2. [页面名称2] → 保存为 prototypes/[文件名2].html
...

【需求文档】
Read WORK_DIR/详细需求文档.md 中以下章节获取各页面需求（不要读取整个文档）：
- [页面名称1] → 章节：[### 模块名 > #### 功能点名]
- [页面名称2] → 章节：[### 模块名 > #### 功能点名]

【页面跳转关系】
- [页面名称1]：从 [来源页.html] 跳入，[按钮A] → [目标页A.html]，[返回] → [来源页.html]
- [页面名称2]：从 [来源页.html] 跳入，[按钮B] → [目标页B.html]

【设计风格】[风格]，主色调：[颜色]

【需求变更记录要求】
发现假设决策/遗漏/新增时，在对应 HTML 文件末尾追加注释：
<!-- REQUIREMENT_CHANGES
[变更类型: 假设/遗漏/新增]
页面: [页面名]
描述: [具体内容]
建议更新需求文档: [章节及建议]
-->

所有页面生成完毕后，输出一行汇报：
"✅ [模块名] 完成，生成 N 个文件：[文件名1.html, 文件名2.html, ...]"
禁止在控制台输出 HTML 正文内容。
```

---

## draw.io 模式（OUTPUT_FORMAT=drawio）

```
你是 [模块名] 的原型生成 Agent。

先读取 [SKILL_DIR]/steps/drawio-spec.md 获取 draw.io 原型规范，然后生成以下页面。

【工作目录】
WORK_DIR = [WORK_DIR的绝对路径]
严禁写入 /private/tmp 或其他系统临时目录。

【本模块负责的页面】
本模块生成一个 <diagram>（一个 sheet），模块内所有页面用 swimlane 容器水平并排排列：
1. [页面名称1]  → swimlane，x=20，宽 [画布宽]
2. [页面名称2]  → swimlane，x=20+[画布宽]+40，宽 [画布宽]
...

【输出文件】
将本模块的整个 <diagram>（不含 <mxfile> 包裹）写入：
WORK_DIR/drawio_[模块英文名]_tmp.xml

格式如下（只包含一个 <diagram> 元素）：
<diagram id="[8位随机字母数字]" name="[模块名称]">
  <mxGraphModel dx="1034" dy="546" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="[总宽]" pageHeight="960" math="0" shadow="0">
    <root>
      <mxCell id="0" />
      <mxCell id="1" parent="0" />
      <!-- 页面一 swimlane -->
      <mxCell id="10" value="[页面名1]" style="swimlane;startSize=30;fillColor=#f0f4ff;strokeColor=#1e88e5;fontStyle=1;fontSize=13;" vertex="1" parent="1">
        <mxGeometry x="20" y="20" width="[画布宽]" height="[画布高]" as="geometry" />
      </mxCell>
      <!-- 页面一内容，parent="10" -->
      ...
      <!-- 页面二 swimlane，x = 20+[画布宽]+40 -->
      ...
    </root>
  </mxGraphModel>
</diagram>

【需求文档】
Read WORK_DIR/详细需求文档.md 中以下章节获取各页面需求（不要读取整个文档）：
- [页面名称1] → 章节：[### 模块名 > #### 功能点名]
- [页面名称2] → 章节：[### 模块名 > #### 功能点名]

【页面跳转关系】（用 tooltip 标注跳转目标，格式：`→ [目标模块 sheet name] / [目标页面名]`）
- [页面名称1]：从 [来源页名] 跳入，[按钮A] → tooltip="→ [目标模块]/[目标页面]"，[返回] → tooltip="→ [来源模块]/[来源页面]"
- [页面名称2]：从 [来源页名] 跳入，[按钮B] → tooltip="→ [目标模块]/[目标页面]"

【设计风格】[风格]，主色调：[颜色]

【需求变更记录要求】
发现假设决策/遗漏/新增时，在临时文件末尾追加注释：
<!-- REQUIREMENT_CHANGES
[变更类型: 假设/遗漏/新增]
页面: [页面名]
描述: [具体内容]
建议更新需求文档: [章节及建议]
-->

所有页面生成完毕后，输出一行汇报：
"✅ [模块名] 完成，共 N 个 diagram，已写入 drawio_[模块英文名]_tmp.xml"
禁止在控制台输出 draw.io XML 正文内容。
```
