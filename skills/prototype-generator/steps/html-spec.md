# HTML 原型图规范

生成的 HTML 原型必须**可直接作为 UI 临摹的布局参考**，设计师拿到后可直接对照还原。

---

## 设计 Token（所有页面必须注入 :root，禁止使用魔法数字）

每个 HTML 文件的 `<style>` 最开头必须包含完整的 CSS 变量定义：

```css
:root {
  /* ── 颜色 ── */
  --primary:       #1e88e5;
  --primary-dark:  #1565c0;
  --primary-light: #e3f2fd;
  --success:       #2e7d32;
  --success-bg:    #e8f5e9;
  --warning:       #f57f17;
  --warning-bg:    #fff8e1;
  --danger:        #c62828;
  --danger-bg:     #ffebee;
  --text-primary:  #212121;
  --text-secondary:#757575;
  --text-hint:     #9e9e9e;
  --bg-page:       #f5f5f5;
  --bg-card:       #ffffff;
  --border:        #e0e0e0;
  --border-light:  #eeeeee;
  --shadow-sm:     0 1px 3px rgba(0,0,0,.12);
  --shadow-md:     0 2px 8px rgba(0,0,0,.15);

  /* ── 间距（8pt 网格）── */
  --sp-1: 4px;   --sp-2: 8px;   --sp-3: 12px;
  --sp-4: 16px;  --sp-5: 20px;  --sp-6: 24px;
  --sp-8: 32px;  --sp-10: 40px; --sp-12: 48px;

  /* ── 字号 ── */
  --text-xs:   11px;  /* 辅助说明、标签 */
  --text-sm:   13px;  /* 次要正文、表格内容 */
  --text-base: 15px;  /* 正文 */
  --text-md:   16px;  /* 小标题 */
  --text-lg:   18px;  /* 卡片标题 */
  --text-xl:   20px;  /* 页面标题 */
  --text-2xl:  24px;  /* Hero 标题 */

  /* ── 组件高度 ── */
  --h-nav:          56px;
  --h-tabbar:       56px;
  --h-input:        44px;
  --h-btn-primary:  44px;
  --h-btn-sm:       32px;
  --h-btn-xs:       24px;
  --h-table-header: 44px;
  --h-table-row:    52px;
  --h-card-header:  48px;
  --h-tag:          24px;
  --h-breadcrumb:   40px;
  --h-pagination:   40px;

  /* ── 圆角 ── */
  --radius-sm:  4px;
  --radius-md:  8px;
  --radius-lg:  12px;
  --radius-full:100px;

  /* ── 页面宽度 ── */
  --w-mobile: 375px;
  --w-content-mobile: 327px; /* 375 - 24*2 */
  --w-web: 1440px;
  --w-content-web: 1200px;
  --w-sidebar: 240px;
}
```

---

## 布局规范

### 固定宽度（UI 参照一致性）

- **移动端页面**：`body` 宽度固定 `var(--w-mobile)`，居中显示，不做响应式拉伸
- **Web/后台页面**：`body` 最大宽度 `var(--w-web)`，内容区 `var(--w-content-web)`，居中

```css
/* 移动端 */
body { width: var(--w-mobile); margin: 0 auto; background: var(--bg-page); }

/* Web 后台 */
.layout { display: flex; min-height: 100vh; }
.sidebar { width: var(--w-sidebar); background: var(--bg-card); }
.main-content { flex: 1; padding: var(--sp-6); }
```

### 间距规则

- 页面左右边距：`var(--sp-6)`（24px）
- 卡片内边距：`var(--sp-4)`（16px）
- 组件间垂直间距：`var(--sp-4)`（16px）；紧凑布局 `var(--sp-2)`（8px）
- 同行组件水平间距：`var(--sp-3)`（12px）
- **禁止**使用任意像素值，所有间距必须引用 `--sp-*` 变量

---

## 组件规范

### 导航栏

```css
.nav-bar {
  height: var(--h-nav);
  background: var(--primary);
  color: #fff;
  display: flex;
  align-items: center;
  padding: 0 var(--sp-4);
  font-size: var(--text-md);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}
```

### 主按钮 / 次要按钮

```css
.btn-primary {
  height: var(--h-btn-primary);
  padding: 0 var(--sp-6);
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: transform .1s;
}
.btn-primary:active { transform: scale(0.97); }

.btn-secondary {
  height: var(--h-btn-primary);
  padding: 0 var(--sp-6);
  background: var(--bg-card);
  color: var(--primary);
  border: 1px solid var(--primary);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  cursor: pointer;
}

.btn-danger { background: var(--danger); color: #fff; border: none; }
.btn-sm { height: var(--h-btn-sm); padding: 0 var(--sp-4); font-size: var(--text-sm); border-radius: var(--radius-sm); }
```

### 输入框

```css
.input {
  height: var(--h-input);
  width: 100%;
  padding: 0 var(--sp-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: var(--text-base);
  color: var(--text-primary);
  background: var(--bg-card);
  box-sizing: border-box;
}
.input:focus { outline: none; border-color: var(--primary); }
.input::placeholder { color: var(--text-hint); }
```

### 卡片

```css
.card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  padding: var(--sp-4);
  margin-bottom: var(--sp-4);
}
```

### Tag 状态标签

```css
.tag { display: inline-flex; align-items: center; height: var(--h-tag); padding: 0 var(--sp-2); border-radius: var(--radius-sm); font-size: var(--text-xs); font-weight: 500; }
.tag-success  { background: var(--success-bg);  color: var(--success); }
.tag-warning  { background: var(--warning-bg);  color: var(--warning); }
.tag-danger   { background: var(--danger-bg);   color: var(--danger); }
.tag-default  { background: var(--border-light); color: var(--text-secondary); }
```

### 表格（后台列表页）

```css
.table { width: 100%; border-collapse: collapse; }
.table th {
  height: var(--h-table-header);
  background: var(--bg-page);
  border-bottom: 1px solid var(--border);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: 500;
  text-align: left;
  padding: 0 var(--sp-3);
}
.table td {
  height: var(--h-table-row);
  border-bottom: 1px solid var(--border-light);
  font-size: var(--text-sm);
  color: var(--text-primary);
  padding: 0 var(--sp-3);
  vertical-align: middle;
}
```

### 分页

```css
.pagination { display: flex; align-items: center; gap: var(--sp-2); height: var(--h-pagination); }
.pagination-btn { height: 32px; min-width: 32px; padding: 0 var(--sp-2); border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-card); font-size: var(--text-sm); cursor: pointer; }
.pagination-btn.active { background: var(--primary); color: #fff; border-color: var(--primary); }
```

### 底部标签栏（移动端）

```css
.tab-bar {
  position: fixed;
  bottom: 0; left: 50%;
  transform: translateX(-50%);
  width: var(--w-mobile);
  height: var(--h-tabbar);
  background: var(--bg-card);
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
}
.tab-bar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: var(--text-xs);
  color: var(--text-hint);
  cursor: pointer;
}
.tab-bar-item.active { color: var(--primary); }
```

---

## 技术规范

- 纯 HTML + CSS + 原生 JS（不依赖外部库）
- 禁止使用魔法数字：所有尺寸/颜色/间距必须引用 `:root` 变量
- 每个文件完整独立（含完整 `<html><head><body>`）

## 内容规范

- **真实数据**：使用符合业务场景的示例数据，不用"Lorem ipsum"或"文字1"
- **完整界面**：导航栏、主内容区、操作按钮、空态/错误态至少展示默认态

## 交互要求

- 所有页面跳转用 `<a href="相对路径">` 或 `location.href` 实现，可真实点击
- 页面进入淡入动效（opacity 0→1，300ms）
- 按钮点击缩放反馈（scale 0.97，100ms）
- 表单提交有加载态（按钮文字变"处理中..."，disabled）
- 弹窗用动效展开（translateY/scale，200ms）
- 未生成的目标页面用 `alert("跳转到[目标功能]")` 占位，不得留空

## 功能闭环

- 所有按钮和链接必须有明确去向
- 表单提交后必须有成功/失败反馈
- 列表空态必须有引导操作
