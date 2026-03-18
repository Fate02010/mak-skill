# 非文本格式读取命令参考

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
unzip -l '[文件路径]'
unzip -o '[文件路径]' -d '[WORK_DIR]/unzipped/'
```

> 如缺少依赖库，运行：`pip3 install python-docx openpyxl python-pptx`，或改用 `pandoc` / `libreoffice --headless`。
