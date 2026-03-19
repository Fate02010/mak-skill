# Step 2：扫描资料，生成 RountMap.md

**目标：** 快速摸清产品资料的整体结构，建立资料导航索引，重点识别业务实体、字段定义和业务规则。

## 支持的文件格式

| 格式 | 扩展名 | 读取方式 |
|------|--------|---------|
| Markdown | `.md` | `Read` 工具直接读取 |
| HTML | `.html` / `.htm` | `Read` 工具直接读取 |
| PDF | `.pdf` | `Read` 工具（超过10页需指定页码范围） |
| Word | `.docx` / `.doc` | 见 `SKILL_DIR/steps/step1-file-readers.md` |
| Excel | `.xlsx` / `.xls` / `.csv` | 见 `SKILL_DIR/steps/step1-file-readers.md` |
| PPT | `.pptx` / `.ppt` | 见 `SKILL_DIR/steps/step1-file-readers.md` |
| 图片 | `.png` / `.jpg` / `.jpeg` / `.gif` / `.webp` | `Read` 工具（视觉理解） |
| ZIP | `.zip` | 见 `SKILL_DIR/steps/step1-file-readers.md` |
| SQL | `.sql` | `Read` 工具（作为现有结构参考） |

> 遇到 Word / Excel / PPT / ZIP 文件时，Read `SKILL_DIR/steps/step1-file-readers.md` 获取读取命令。

## 执行步骤

### 阶段 2-1：扫描文件列表

使用 `Glob` 扫描 `WORK_DIR`，匹配扩展名：
`*.md, *.html, *.htm, *.pdf, *.docx, *.doc, *.xlsx, *.xls, *.csv, *.pptx, *.ppt, *.png, *.jpg, *.jpeg, *.gif, *.webp, *.zip, *.sql`

对每个文件读取文件名和前 20 行做初步类型判断；ZIP 用 `unzip -l` 查看内容清单。

### 阶段 2-2：向用户展示文件列表，确认分级

以表格展示所有文件和 AI 初步判断，**必须等待用户回复后继续**：

```
扫描到以下 N 个文件，请确认优先级：

| # | 文件 | 格式 | 初步判断 | AI 建议优先级 |
|---|------|------|---------|-------------|
| 1 | PRD.md | Markdown | 产品需求文档 | ⭐⭐⭐ 核心 |
| 2 | 数据字典.xlsx | Excel | 字段说明 | ⭐⭐⭐ 核心 |
| 3 | 流程图.png | 图片 | 业务流程 | ⭐⭐ 参考 |

请回复：
- "按你的建议"：使用 AI 推荐的优先级
- 指定编号（如"1,2 核心，3 参考，4 跳过"）：自定义分级
```

### 阶段 2-3：分级读取，生成 RountMap.md

- **核心文件**：完整读取，重点提取业务实体、字段定义、业务规则、约束
- **参考文件**：读取摘要（前 50 行或关键段落）
- **跳过文件**：记录在 RountMap.md 但不读取内容

Read `SKILL_DIR/steps/step1-routemap-format.md` 获取格式规范，生成 `WORK_DIR/RountMap.md`。

> 文件超过 20 个时，先扫描目录结构，再按子目录分批读取，避免一次加载过多内容。
