# 特殊格式文件读取命令

## Word (.docx)
```bash
pandoc "[文件路径]" -t plain 2>/dev/null || python3 -c "
from docx import Document
doc = Document('[文件路径]')
for p in doc.paragraphs: print(p.text)
"
```

## Excel (.xlsx / .xls / .csv)
```bash
# CSV 直接读取
cat "[文件路径]"

# xlsx
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('[文件路径]')
for sheet in wb.sheetnames:
    ws = wb[sheet]
    print(f'=== {sheet} ===')
    for row in ws.iter_rows(values_only=True):
        print('\t'.join(str(c) if c else '' for c in row))
"
```

## PPT (.pptx)
```bash
python3 -c "
from pptx import Presentation
prs = Presentation('[文件路径]')
for i, slide in enumerate(prs.slides):
    print(f'=== Slide {i+1} ===')
    for shape in slide.shapes:
        if hasattr(shape, 'text'): print(shape.text)
"
```

## ZIP
```bash
unzip -l "[文件路径]"   # 查看内容清单
unzip -p "[文件路径]" "[内部文件名]"  # 读取特定文件
```
