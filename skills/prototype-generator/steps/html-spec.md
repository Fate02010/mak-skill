# HTML 原型图规范

生成的 HTML 原型必须**可直接作为 UI 临摹的布局参考**，设计师拿到后可直接对照还原。

---

## 共享样式引用（禁止内联复制）

所有 HTML 页面通过外部样式表引用共享 CSS，**禁止在 `<style>` 中重复定义设计 Token 和组件样式**：

```html
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>页面标题</title>
  <link rel="stylesheet" href="common.css">
  <style>
    /* 仅放页面特有样式，禁止重复 :root 变量和通用组件样式 */
  </style>
</head>
```

> `common.css` 已包含：`:root` 设计 Token、全局重置、页面动效、布局（移动端/Web/登录页）、
> 导航栏、按钮、输入框、卡片、Tag、表格、分页、标签栏、弹窗、面包屑、空态、表单组。
> 所有变量名和 class 名参见 `SKILL_DIR/templates/common.css`。

**可用的 CSS 变量**（在 `<style>` 和行内 `style` 中直接使用）：

- 颜色：`--primary` `--primary-dark` `--primary-light` `--success` `--warning` `--danger` 及对应 `-bg` 变体
- 文字：`--text-primary` `--text-secondary` `--text-hint`
- 背景：`--bg-page` `--bg-card`
- 边框：`--border` `--border-light`
- 阴影：`--shadow-sm` `--shadow-md`
- 间距：`--sp-1`(4) `--sp-2`(8) `--sp-3`(12) `--sp-4`(16) `--sp-5`(20) `--sp-6`(24) `--sp-8`(32) `--sp-10`(40) `--sp-12`(48)
- 字号：`--text-xs`(11) `--text-sm`(13) `--text-base`(15) `--text-md`(16) `--text-lg`(18) `--text-xl`(20) `--text-2xl`(24)
- 高度：`--h-nav` `--h-tabbar` `--h-input` `--h-btn-primary` `--h-btn-sm` `--h-btn-xs` `--h-table-header` `--h-table-row` `--h-tag` `--h-pagination`
- 圆角：`--radius-sm`(4) `--radius-md`(8) `--radius-lg`(12) `--radius-full`(100)
- 宽度：`--w-mobile`(375) `--w-content-mobile`(327) `--w-web`(1440) `--w-content-web`(1200) `--w-sidebar`(240)

**可用的 CSS class**（直接在 HTML 中使用）：

| 类别 | class 名 |
|------|---------|
| 布局 | `mobile`(body) `layout` `sidebar` `main-content` `login-page` `login-card` |
| 导航 | `nav-bar` `nav-item` `nav-item.active` |
| 按钮 | `btn-primary` `btn-secondary` `btn-danger` `btn-sm` `btn-xs` |
| 输入 | `input` |
| 卡片 | `card` |
| 标签 | `tag` `tag-success` `tag-warning` `tag-danger` `tag-default` |
| 表格 | `table` |
| 分页 | `pagination` `pagination-btn` `pagination-btn.active` |
| 移动端 | `tab-bar` `tab-bar-item` `tab-bar-item.active` |
| 弹窗 | `modal-overlay` `modal-overlay.show` `modal` |
| 面包屑 | `breadcrumb` |
| 空态 | `empty-state` |
| 表单 | `form-group` `.required` |

---

## 布局规范

### 固定宽度（UI 参照一致性）

- **移动端页面**：`<body class="mobile">`，宽度固定 375px，居中显示
- **Web/后台页面**：使用 `.layout` > `.sidebar` + `.main-content` 结构
- **后台登录页**：属于未登录独立页，使用 `.login-page` > `.login-card` 结构，禁止带左侧菜单、顶部业务导航

### 登录页专用规则

- 后台登录页禁止出现 `.sidebar`、业务菜单、面包屑、模块切换入口。
- 默认字段为账号、密码；验证码仅在需求文档明确写明时才允许渲染。
- 如果是短信验证码登录，必须在资料中有"验证码登录"或同义描述，不能由模型自行脑补。

### 间距规则

- 页面左右边距：`var(--sp-6)`（24px）
- 卡片内边距：`var(--sp-4)`（16px）
- 组件间垂直间距：`var(--sp-4)`（16px）；紧凑布局 `var(--sp-2)`（8px）
- 同行组件水平间距：`var(--sp-3)`（12px）
- **禁止**使用任意像素值，所有间距必须引用 `--sp-*` 变量

---

## 页面骨架隔离规则（禁止跨类型复用导航）

> 骨架由**页面类型**决定，不由**系统类型**决定。同一个后台系统的登录页与列表页是不同类型，必须用不同骨架。

**独立页面**（以下类型是全屏独立页面，严禁出现侧边栏/顶部业务导航/面包屑）：

| 独立页面类型 | 正确骨架 |
|------------|---------|
| 登录页 / 注册页 | `.login-page` > `.login-card`，无任何导航 |
| 落地页 / 欢迎页 | 全宽 hero 区，无侧边栏 |
| 错误页（404/无权限/异常） | 居中插图 + 文案 + 返回按钮，无导航 |
| 支付结果页 | 居中结果卡片，无侧边栏 |

**自查**：生成每个 HTML 文件前，先判断是否属于独立页面类型，若是则去掉所有导航元素。

---

## 多模式互斥展示规则（禁止堆叠所有方式）

> 需求说"支持 A 和 B 两种方式"，页面同一时刻**只展示一种**。用 Tab 或切换按钮实现，不得把两种方式的字段同时平铺。

**触发关键词**：支持 X 和 Y 两种方式、可选 A 或 B、多种方式、两种模式

**实现方式（原生 JS Tab 切换）：**

```html
<!-- Tab 切换示例：两种登录方式 -->
<div class="tab-switch" style="display:flex;border-bottom:2px solid var(--border);margin-bottom:var(--sp-4);">
  <button id="tab-pwd" onclick="switchTab('pwd')"
    style="flex:1;height:var(--h-btn-sm);background:none;border:none;
           border-bottom:2px solid var(--primary);color:var(--primary);
           font-weight:600;cursor:pointer;">账号登录</button>
  <button id="tab-sms" onclick="switchTab('sms')"
    style="flex:1;height:var(--h-btn-sm);background:none;border:none;
           color:var(--text-secondary);cursor:pointer;">验证码登录</button>
</div>
<div id="panel-pwd"><!-- 账号+密码字段 --></div>
<div id="panel-sms" style="display:none;"><!-- 手机号+验证码字段 --></div>
<script>
function switchTab(t){
  document.getElementById('panel-pwd').style.display = t==='pwd'?'':'none';
  document.getElementById('panel-sms').style.display = t==='sms'?'':'none';
  document.getElementById('tab-pwd').style.color = t==='pwd'?'var(--primary)':'var(--text-secondary)';
  document.getElementById('tab-pwd').style.borderBottom = t==='pwd'?'2px solid var(--primary)':'none';
  document.getElementById('tab-sms').style.color = t==='sms'?'var(--primary)':'var(--text-secondary)';
  document.getElementById('tab-sms').style.borderBottom = t==='sms'?'2px solid var(--primary)':'none';
}
</script>
```

**正确 vs 禁止对照：**

| 需求描述 | 正确做法 | 禁止做法 |
|---------|---------|---------|
| 支持账号密码和手机验证码两种登录 | Tab 切换，每个 Tab 只显示对应字段 | 账号+密码+手机号+验证码全部在同一表单 |
| 支持微信支付和银行卡两种支付 | Tab 切换，默认展示第一种 | 微信二维码和银行卡输入框同时展示 |
| 支持快递和自提两种配送方式 | 单选切换，切换后只显示对应地址区 | 收货地址和自提门店选择同时展示 |

---

## 导航栏一致性规则

同一产品所有带导航的页面（非独立页面），导航栏菜单项必须完全一致：

- **菜单项相同**：所有页面的导航栏包含相同的菜单项，顺序一致
- **active 状态**：当前页对应的菜单项加 `.active` class
- **实现方式**：

```html
<nav class="nav-bar">
  <span style="font-size:var(--text-lg);font-weight:700;">产品名称</span>
  <div style="display:flex;gap:var(--sp-6);margin-left:var(--sp-10);">
    <a href="page-a.html" class="nav-item active">功能A</a>
    <a href="page-b.html" class="nav-item">功能B</a>
    <a href="page-c.html" class="nav-item">功能C</a>
  </div>
</nav>
```

**禁止**：A 页有 5 个菜单项，B 页只有 3 个；或各页面菜单顺序不一致。

---

## 技术规范

- 纯 HTML + CSS + 原生 JS（不依赖外部库）
- 禁止使用魔法数字：所有尺寸/颜色/间距必须引用 `:root` 变量或 common.css 中的 class
- 每个文件完整独立（含完整 `<html><head><body>`），通过 `<link>` 引用 common.css
- **禁止在 `<style>` 中重复定义 `:root` 变量或 common.css 已有的组件样式**

## 内容规范

- **真实数据**：使用符合业务场景的示例数据，严禁使用 `Lorem ipsum`、`文字1`、`按钮A`、`示例文字`、`功能待定`、`待补充`、`数据N` 等占位内容
- **完整界面**：导航栏、主内容区、操作按钮、空态/错误态至少展示默认态
- **禁止空容器**：卡片（`.card`）、分组容器内必须有真实 UI 内容（输入框/键值对/按钮/列表等），严禁只写区块标题（如 "基础信息"、"状态与处理"）而内部为空的空白卡片；渲染前先从需求文档提取字段列表，再逐字段写入容器
- **禁止占位字段名**：表单字段的 `<label>` 和输入框 `placeholder` 必须是真实业务名称（如"品类名称"、"收货人"、"订单编号"），禁止使用 `字段一`、`字段二`、`字段三`、`InputA`、`Input_1`、`选项N` 等序号内容
- **表单页字段来源**：生成表单页前必须先从需求文档对应章节列出所有字段（字段名 | 类型 | 是否必填），再按列表逐行渲染 Label + Input/Select/Textarea；严禁先画骨架后用序号填充
- **详情页展示键值对**：详情页展示的是只读键值对（"订单编号：YYG-2024-001"），value 必须是符合业务的示例数据，严禁用空白输入框或 "字段一" 代替

## 链接路径规则（必须遵守，错误路径导致点击后 404）

所有 HTML 原型文件和 `common.css` 保存在同一目录 `prototypes/` 下，**文件间跳转统一使用同级相对路径**：

```html
<!-- ✅ 正确：同目录文件直接引用文件名 -->
<a href="user-list.html">用户列表</a>
<a href="order-detail.html">订单详情</a>
location.href = 'login.html';

<!-- ❌ 错误：不要加目录前缀 -->
<a href="./prototypes/user-list.html">错误写法</a>
<a href="/prototypes/user-list.html">错误写法</a>
<a href="../prototypes/user-list.html">错误写法</a>
```

`index.html` 同样在 `prototypes/` 目录内，链接到其他页面也使用同级路径（`./user-list.html` 或直接 `user-list.html`）。

未生成的目标页面用 `onclick="alert('跳转到[目标功能]')"` 占位，不使用 `href`。

## 交互要求

- 所有页面跳转用 `<a href="相对路径">` 或 `location.href` 实现，可真实点击
- 页面进入淡入动效（已内置在 common.css）
- 按钮点击缩放反馈（scale 0.97，100ms）— 已内置在 `.btn-primary:active`
- 表单提交有加载态（按钮文字变"处理中..."，disabled）
- 弹窗用 `.modal-overlay` + `.modal`，JS 控制 `.show` class
- 未生成的目标页面用 `alert("跳转到[目标功能]")` 占位，不得留空

## 功能闭环

- 所有按钮和链接必须有明确去向
- 表单提交后必须有成功/失败反馈
- 列表空态必须有引导操作（使用 `.empty-state`）
