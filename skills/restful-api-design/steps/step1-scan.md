# Step 1：扫描资料，生成 RountMap.md

**目标：** 快速摸清产品资料的整体结构，建立资料导航索引，重点识别业务模块、接口需求、数据对象。

## 支持的文件格式

| 格式 | 扩展名 | 读取方式 |
|------|--------|---------|
| Markdown | `.md` | `Read` 工具 |
| PDF | `.pdf` | `Read` 工具（超 10 页需指定页码范围） |
| HTML | `.html/.htm` | `Read` 工具 |
| Word/Excel/PPT/ZIP | `.docx/.xlsx/.pptx/.zip` 等 | 见 `SKILL_DIR/steps/step1-file-readers.md` |
| 图片 | `.png/.jpg/.jpeg` | `Read` 工具（视觉理解） |

## 阶段 1-1：扫描文件列表

使用 `Glob` 扫描 `WORK_DIR`，匹配：`*.md, *.html, *.htm, *.pdf, *.docx, *.doc, *.xlsx, *.xls, *.csv, *.pptx, *.ppt, *.png, *.jpg, *.jpeg, *.zip`

对每个文件读取文件名和前 20 行做初步类型判断。

## 阶段 1-2：展示文件列表，等待用户确认分级

**必须等待用户回复后继续：**

```
扫描到以下 N 个文件，请确认优先级：

| # | 文件 | 格式 | 初步判断 | AI 建议优先级 |
|---|------|------|---------|-------------|
| 1 | PRD.md | Markdown | 产品需求文档 | ⭐⭐⭐ 核心 |
| 2 | 接口说明.xlsx | Excel | 接口清单 | ⭐⭐⭐ 核心 |
| 3 | 流程图.png | 图片 | 业务流程 | ⭐⭐ 参考 |

请回复：
- "按你的建议"：使用 AI 推荐的优先级
- 指定编号（如"1,2 核心，3 参考，4 跳过"）：自定义分级
```

## 阶段 1-3：分级读取，生成 RountMap.md

- **核心文件**：完整读取，重点提取业务模块、接口需求、数据对象、业务规则
- **参考文件**：读取摘要（前 50 行或关键段落）
- **跳过文件**：记录在 RountMap.md 但不读取内容

Read `SKILL_DIR/steps/step1-routemap-format.md` 获取格式规范，生成 `WORK_DIR/RountMap.md`。
