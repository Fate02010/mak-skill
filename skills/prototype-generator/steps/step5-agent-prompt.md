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
所有文件必须保存在 WORK_DIR/prototypes/ 下，严禁写入 /private/tmp 或其他系统临时目录。

【本模块负责的页面】
1. [页面名称1] → 保存为 prototypes/[文件名1].drawio
2. [页面名称2] → 保存为 prototypes/[文件名2].drawio
...

【需求文档】
Read WORK_DIR/详细需求文档.md 中以下章节获取各页面需求（不要读取整个文档）：
- [页面名称1] → 章节：[### 模块名 > #### 功能点名]
- [页面名称2] → 章节：[### 模块名 > #### 功能点名]

【页面跳转关系】（用 tooltip 属性 + 跳转说明文字框标注，不实现真实跳转）
- [页面名称1]：从 [来源页.drawio] 跳入，[按钮A] → [目标页A.drawio]，[返回] → [来源页.drawio]
- [页面名称2]：从 [来源页.drawio] 跳入，[按钮B] → [目标页B.drawio]

【设计风格】[风格]，主色调：[颜色]

【需求变更记录要求】
发现假设决策/遗漏/新增时，在对应 .drawio 文件的 diagram 标签上追加 metadata 注释：
<!-- REQUIREMENT_CHANGES
[变更类型: 假设/遗漏/新增]
页面: [页面名]
描述: [具体内容]
建议更新需求文档: [章节及建议]
-->

所有页面生成完毕后，输出一行汇报：
"✅ [模块名] 完成，生成 N 个文件：[文件名1.drawio, 文件名2.drawio, ...]"
禁止在控制台输出 draw.io XML 正文内容。
```
