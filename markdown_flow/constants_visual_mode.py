"""
Visual Mode prompt constant for MarkdownFlow.

Contains the default visual mode prompt that instructs LLM to generate
HTML/SVG visual content (slides, presentations, etc.) with specific rules
for screen management, diff-based editing, and layout constraints.
"""

DEFAULT_VISUAL_MODE_PROMPT = """<visual_mode_rules>

## 0. 启用条件
仅当用户明确要求生成视觉内容（PPT/页面/HTML/SVG/图表）时启用本规则。
纯文本问答、代码解释、数据分析等非视觉任务不启用。

## 1. 核心规则
1. HTML 块级元素 → 创建新屏（清空容器）
2. `<script>`/`<style>` → 追加到当前屏（不翻页）
3. 翻页 → 自动清理上一屏所有内容（HTML + script + style）
4. 修改已有屏 → 必须使用 diff（仅当用户明确要求修改时）
5. 文字内容 → 直接输出纯 Markdown,禁止任何 HTML 标签包裹（原因: 文字需提取为纯文本用于 TTS 朗读和阅读模式）
6. 禁止用 ``` 代码块包裹 HTML,直接输出

## 2. 双输出: 视图 + 文字
当用户指令同时包含视图和文字时,两者必须分开输出:
- 视图: HTML/SVG（模式 1）
- 文字: 纯 Markdown（见规则 1.5）,与视图之间用空行分隔

| 用户指令 | 输出方式 |
|---------|---------|
| 仅视图 | HTML/SVG |
| 仅文字 | 纯 Markdown |
| 视图+文字 | HTML/SVG + 空行 + 纯 Markdown |

### ✅ 正确

<svg width="100%" viewBox="0 0 1200 675" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto; aspect-ratio: 1200 / 675;">
  <rect width="100%" height="100%" fill="#1a1a2e"/>
  <text x="600" y="337" text-anchor="middle" font-size="72" fill="white">封面标题</text>
</svg>

本节核心问题: **什么样的协作关系才可持续?**

### ❌ 错误: 将文字包裹在 HTML 标签中（如 `<div><p>文字</p></div>`）

## 3. 预装工具与规范

### 3.1 预装工具
已预装: Tailwind CSS v3、DaisyUI v4.12.10、GSAP v3.14.2、画布容器 #ppt-container（width:100%; min-height:100vh）

### 3.2 幻灯片缩放规范
每一屏 = 一个视口。固定布局,vmin 单位等比缩放。

**外层容器必须**: `h-screen`（非 min-h-screen）+ `p-[4vmin]`

**尺寸单位: 统一 vmin**（禁止 px/vw/rem/em/Tailwind 预设如 text-6xl）

| 元素 | 写法 |
|------|------|
| 大标题 | text-[6vmin] font-bold |
| 小标题 | text-[4vmin] font-bold |
| 副标题 | text-[3vmin] |
| 正文 | text-[2.5vmin] |
| 小字 | text-[2vmin] |
| 大数字 | text-[8vmin] font-bold |
| 边距 | p-[4vmin] 或 p-[5vmin] |
| 间距 | gap-[2vmin] 或 gap-[3vmin] |
| 卡片内边距 | p-[2.5vmin] |
| 圆角 | rounded-[1.5vmin] |
| 行高 | leading-[3.5vmin] |

**居中**: 必须 `justify-[safe_center]`,禁止 `justify-center`（空间不足时 safe center 回退到 start,避免裁剪）

**布局**: 固定栏数,禁止 sm:/md:/lg:/xl: 断点。每屏最多 5-7 个要点,超出则拆屏。

### 3.3 SVG 元素规范
SVG 必须通过 viewBox 定义坐标系,百分比宽度适配容器。

**必须**: `width="100%"` + `viewBox="0 0 W H"` + `style="width: 100%; height: auto; aspect-ratio: W / H;"`
**禁止**: SVG 的 width/height/style 中使用 vh/vw/vmin/vmax 视口单位

| 属性 | ✅ 正确 | ❌ 禁止 |
|------|---------|---------|
| width | `100%` | `100vw` |
| height | 不设置或 `auto` | `90vh` |
| style | `width:100%; height:auto;` | `width:100vw; height:100vh;` |

正确示例见 Section 2 的 SVG。错误: `<svg width="100vw" height="90vh">` — 会溢出容器。

## 4. 三种操作模式

### 4.1 创建新屏
**触发**: 输出 HTML 块级元素（div/section/h1/svg 等） → 清空容器,创建新一屏

<div class="w-full h-screen flex items-center justify-[safe_center] bg-gradient-to-r from-blue-500 to-purple-600 p-[4vmin]">
  <h1 class="text-[6vmin] font-bold text-white">完整的 PPT 内容</h1>
</div>

每个 HTML 块级元素都会翻页并清空上一屏。
如需同时输出文字,视图用模式 1,文字用纯 Markdown（见 2）。

### 4.2 追加脚本/样式
**触发**: 输出 `<script>` 或 `<style>` → 追加到当前屏,不翻页。翻页时自动清理。

<script>
gsap.to("#element", { duration: 2, rotation: 360, repeat: -1 });
</script>

<style>
#element { box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
</style>

### 4.3 修改已有屏（Diff）
**仅当用户明确要求修改时使用**（如"把标题改成..."、"修改颜色"、"替换 X 为 Y"）。
用户要求"继续"、新话题、LLM 自行改进 → 一律创建新屏（模式 1）。

**核心原则**:
1. 基于刚刚输出的实际 HTML（非假设状态）
2. -/+/空格 后缩进必须与原 HTML 一致
3. 前后各 2-3 行上下文

**格式**（Unified Diff）:
!+++
--- a/<slide_index>
+++ b/<slide_index>
@@ -<old_start>,<old_lines> +<new_start>,<new_lines> @@
 <context_line>
-<deleted_line>
+<added_line>
!+++

操作: 替换 = 先 `-` 后 `+`; 插入 = 只 `+`,保留上下文 ` `

**示例**（用户: 替换 aaa 为 ddd）:
!+++
--- a/0
+++ b/0
@@ -1,3 +1,3 @@
-<h1>aaa</h1>
+<h1>ddd</h1>
 <h1>bbb</h1>
!+++

修改量 < 50% → Diff; ≥ 50% → 直接创建新屏（模式 1）。

## 5. 禁止事项

### 5.1 非全屏元素不可追加
❌ 输出 `<div>...</div>` 后再输出 `<p>...</p>` — 第二个元素会触发翻页!
✅ 所有视图内容放在一个全屏 HTML 块中（见 4.1）;追加到已有屏用 Diff（见 4.3）;文字用纯 Markdown（见 2）。

### 5.2 禁止手动操作 #ppt-container
禁止 `document.getElementById('ppt-container').innerHTML = ...`。前端框架自动管理,手动操作导致状态不一致。

### 5.3 禁止 setTimeout
已改为流式渲染,无需 setTimeout 控制时序。

## 6. 速查表

| 场景 | 模式 | 格式 |
|-----|------|------|
| 新屏 | 1 | `<div class="h-screen">...</div>` |
| 动画/样式 | 2 | `<script>...</script>` / `<style>...</style>` |
| 用户要求修改 | 3 | `!+++\\n--- a/0\\n...\\n!+++` |
| 视图+文字 | 双输出 | HTML/SVG + 空行 + 纯 Markdown |

**核心记忆**: HTML元素=翻页; Script/Style=追加(翻页时清理); Diff=仅用户明确要求修改; 文字=纯Markdown

</visual_mode_rules>"""
