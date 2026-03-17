# Step 1：扫描资料，生成 RountMap.md

**目标：** 快速摸清产品资料的整体结构，建立一份"资料导航索引"，方便后续按需精准读取。

## 支持的文件格式及读取方式

| 格式 | 扩展名 | 读取方式 |
|------|--------|---------|
| Markdown | `.md` | `Read` 工具直接读取 |
| HTML | `.html` / `.htm` | `Read` 工具直接读取 |
| PDF | `.pdf` | `Read` 工具读取（超过10页需指定页码范围，每次最多20页） |
| Word | `.docx` / `.doc` | `Bash: python3 -c "import docx; ..."` 提取文本，或 `pandoc` 转 md 后读取 |
| Excel | `.xlsx` / `.xls` / `.csv` | `Bash: python3 -c "import openpyxl/pandas; ..."` 提取表格内容 |
| PPT | `.pptx` / `.ppt` | `Bash: python3 -c "from pptx import Presentation; ..."` 提取每页文本 |
| 图片 | `.png` / `.jpg` / `.jpeg` / `.gif` / `.webp` | `Read` 工具直接读取（Claude 支持视觉理解） |
| ZIP | `.zip` | `Bash: unzip -l` 查看内容清单，再按需解压到 `WORK_DIR/unzipped/` 后读取 |

### 各格式读取命令参考

**Word (.docx)：**
```bash
python3 -c "
import docx
doc = docx.Document('[文件路径]')
for p in doc.paragraphs:
    print(p.text)
" 2>/dev/null || pandoc '[文件路径]' -t plain 2>/dev/null
```

**Excel (.xlsx)：**
```bash
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('[文件路径]', read_only=True)
for sheet in wb.sheetnames:
    ws = wb[sheet]
    print(f'=== {sheet} ===')
    for row in ws.iter_rows(max_row=50, values_only=True):
        print(row)
" 2>/dev/null
```

**PPT (.pptx)：**
```bash
python3 -c "
from pptx import Presentation
prs = Presentation('[文件路径]')
for i, slide in enumerate(prs.slides):
    print(f'=== 第{i+1}页 ===')
    for shape in slide.shapes:
        if hasattr(shape, 'text'):
            print(shape.text)
" 2>/dev/null
```

**ZIP：**
```bash
# 先查看内容
unzip -l '[文件路径]'
# 按需解压到 WORK_DIR
unzip -o '[文件路径]' -d '[WORK_DIR]/unzipped/'
```

## 执行步骤

1. 使用 `Glob` 工具扫描用户指定的产品资料文件夹，获取所有文件列表（包含子目录），匹配以下扩展名：
   `*.md, *.html, *.htm, *.pdf, *.docx, *.doc, *.xlsx, *.xls, *.csv, *.pptx, *.ppt, *.png, *.jpg, *.jpeg, *.gif, *.webp, *.zip`
2. 对每个文件，根据上方表格选择对应的读取方式，提取文件摘要（前 50 行或等量内容），判断其主要内容类型
3. ZIP 文件先查看内容清单，若包含有价值的资料则解压后递归扫描
4. 生成 `RountMap.md` 文件，保存到 `WORK_DIR`

> **依赖检查：** 如果 python3 命令不可用，或缺少 `python-docx` / `openpyxl` / `python-pptx` 库，用 `pip3 install python-docx openpyxl python-pptx` 安装，或改用 `pandoc` / `libreoffice --headless` 等替代方案。

## RountMap.md 格式

```markdown
# 产品资料导航 (RountMap)

## 资料概览
[简短描述产品是什么，基于扫描到的资料推断]

## 文件索引

| 文件路径 | 格式 | 内容类型 | 适用场景 | 优先级 |
|---------|------|---------|---------|-------|
| docs/PRD.md | Markdown | 产品需求文档 | 了解完整功能需求时读取 | 高 |
| docs/UI设计.pptx | PPT | 设计规范 | 生成原型时读取样式要求 | 中 |
| assets/流程图.png | 图片 | 业务流程 | 理解核心流程时参考 | 高 |
| ... | ... | ... | ... | ... |

## 按场景索引

### 理解产品定位时读
- [文件路径] - [一句话说明]

### 了解功能需求时读
- [文件路径] - [一句话说明]

### 生成原型图时读
- [文件路径] - [一句话说明]

### 了解用户/角色时读
- [文件路径] - [一句话说明]
```

> **分块提示：** 如果文件夹中文件超过 20 个，先扫描目录结构，再按子目录分批读取文件摘要，避免一次加载过多内容。
