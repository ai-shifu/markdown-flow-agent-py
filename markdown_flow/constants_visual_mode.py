"""
Visual Mode prompt constant for MarkdownFlow.

Contains the default visual mode prompt that instructs LLM to generate
HTML/SVG visual content (slides, presentations, etc.) with specific rules
for screen management, diff-based editing, and layout constraints.
"""

DEFAULT_VISUAL_MODE_PROMPT = """<visual_mode_rules>

## 零、启用条件 ⚠️

**本规则仅在满足以下条件时启用**:

用户在 user 提示词中**明确要求**生成视觉内容,例如:
- ✅ "生成一个 PPT"
- ✅ "创建一个页面展示..."
- ✅ "用 HTML 展示..."
- ✅ "制作一个视图..."
- ✅ "画一个..."

**如果用户没有明确要求生成视图/PPT/页面,不要启用本规则**:
- ❌ 纯文本问答
- ❌ 代码解释
- ❌ 数据分析
- ❌ 其他非视觉内容任务

**判断标准**: 用户意图是否需要输出 HTML/SVG/视觉渲染内容。

---

## 一、核心规则

1. HTML 块级元素 → 创建新屏(清空容器)
2. Script/Style 标签 → 追加到当前屏(不翻页)
3. 翻页时 → 自动清理上一屏的所有内容(包括 HTML + script + style)
4. 修改已有屏 → 必须使用 diff 语法(仅当用户明确要求修改时)

**禁止使用代码块包裹**:
- ❌ 错误: 使用 ``` 符号包裹 HTML
- ✅ 正确: 直接输出 HTML,不使用任何代码块标记

## 二、预装工具

已预装: Tailwind CSS v3、DaisyUI v4.12.10、GSAP v3.14.2、画布容器 #ppt-container(width: 100%; min-height: 100vh)

## 二-A、幻灯片缩放规范

### 核心原则: 等比缩放,零滚动

每一屏 = 精确一个视口。内容固定布局,通过 vmin 单位等比缩放。**绝不允许出现滚动条。**

### 外层容器(每屏必须)

三个关键类缺一不可:
- `h-screen` — 精确填满视口高度(不是 min-h-screen)
- `overflow-hidden` — 裁剪溢出,保证零滚动
- `p-[4vmin]` — 安全边距,防止内容贴边

### 尺寸单位: 统一使用 vmin

vmin = min(视口宽, 视口高),同时响应宽度和高度变化。

**禁止**: px、vw、rem/em、Tailwind 预设尺寸(text-6xl 等)

| 元素 | 写法 |
|------|------|
| 大标题 | text-[6vmin] font-bold |
| 小标题 | text-[4vmin] font-bold |
| 副标题 | text-[3vmin] |
| 正文 | text-[2.5vmin] |
| 小字 | text-[2vmin] |
| 大数字 | text-[8vmin] font-bold |
| 外边距 | p-[4vmin] 或 p-[5vmin] |
| 间距 | gap-[2vmin] 或 gap-[3vmin] |
| 卡片内边距 | p-[2.5vmin] |
| 圆角 | rounded-[1.5vmin] |
| 行高 | leading-[3.5vmin] |

### 布局规则: 固定栏数,禁止重排

**禁止** sm:/md:/lg:/xl: 等断点前缀改变布局结构。
设计时确定栏数,所有屏幕保持同一布局。

### 内容量控制

每屏不超过 5-7 个要点,内容多则拆分为多屏。

## 三、三种操作模式

### 3.1 模式 1: 创建新屏

**触发条件**: 输出 HTML 块级元素(div/p/h1/svg 等)

**效果**: 清空容器,创建新的一屏

**输出格式**:
<div class="w-full h-screen overflow-hidden flex items-center justify-center bg-gradient-to-r from-blue-500 to-purple-600 p-[4vmin]">
  <h1 class="text-[6vmin] font-bold text-white">完整的 PPT 内容</h1>
</div>

**规则**: 每输出一个 HTML 块级元素,就创建新的一屏并清空上一屏。

---

### 3.2 模式 2: 追加脚本/样式

**触发条件**: 输出 <script> 或 <style> 标签

**效果**: 追加到当前屏,不触发翻页

**生命周期**: 翻页时自动清理(不会影响后续页面)

**输出格式**:
<script>
gsap.to("#element", { duration: 2, rotation: 360, repeat: -1 });
</script>

<style>
#element { box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
</style>

**规则**: script/style 仅对当前屏生效,翻页后会被自动清理。

---

### 3.3 模式 3: 修改已有屏(Diff)

**启用条件**: 仅当用户**明确要求修改**已有屏内容时才使用此模式。

用户在 user 提示词中**明确要求**修改已有内容,例如:
- ✅ "把标题改成..."
- ✅ "修改第二屏的颜色"
- ✅ "把 aaa 替换为 bbb"
- ✅ "调整一下上面的布局"
- ✅ "删除那个图表"

**如果用户没有明确要求修改,不要使用 Diff,应创建新屏(模式 1)**:
- ❌ 用户要求"继续"或"下一页" → 创建新屏
- ❌ 用户提出新话题或新内容 → 创建新屏
- ❌ LLM 自己觉得之前的内容需要改进 → 创建新屏

**判断标准**: 用户意图是否为修改已经生成的屏,而非生成新内容。

**核心原则**:
1. **必须基于刚刚输出的实际 HTML**(不能基于假设或理想状态)
2. **缩进规则**: -/+/ 标记后的内容缩进必须与原始 HTML 完全一致
3. **提供上下文**: 前后各 2-3 行上下文行

**Diff 格式**(标准: Unified Format, 1989):
!+++
--- a/<slide_index>
+++ b/<slide_index>
@@ -<old_start>,<old_lines> +<new_start>,<new_lines> @@
 <context_line>         # 上下文行(空格开头)
-<deleted_line>         # 删除的行(- 开头)
+<added_line>           # 添加的行(+ 开头)
!+++

**两种操作**:
- **替换行**(修改内容): 先删除(-),再添加(+)
- **添加行**(插入元素): 只添加(+),保留上下文( )

**完整示例**:
用户: 替换 aaa 为 ddd
你输出 diff(基于刚刚的实际 HTML):
!+++
--- a/0
+++ b/0
@@ -1,3 +1,3 @@
-<h1>aaa</h1>
+<h1>ddd</h1>
 <h1>bbb</h1>
 <h1>ccc</h1>
!+++

**修改量级判断**(前提: 用户已明确要求修改):
- 小范围修改(< 50% 内容): 使用 Diff(模式 3)
- 大范围修改(≥ 50% 内容): 直接创建新屏(模式 1) - `<div class="w-full h-screen overflow-hidden">...</div>`

**原则**: 只有当用户明确要求修改时才进入此判断。评估修改复杂度,量大时直接输出 HTML 块级元素比 Diff 更简单高效。

## 四、禁止事项

### 4.1 ❌ 直接输出非全屏元素期望追加

**错误示例**:
<div class="w-full h-screen overflow-hidden"><h1>标题</h1></div>
<p>想追加到上面的 div 中</p>  ❌ 这会触发翻页!

**正确做法**: 将所有内容包含在一个完整的全屏 HTML 块中输出
<div class="w-full h-screen overflow-hidden flex items-center justify-center bg-gradient-to-r from-blue-500 to-purple-600 p-[4vmin]">
  <h1 class="text-[6vmin] font-bold text-white">标题</h1>
  <p class="text-[2.5vmin] text-white">这段文字包含在同一个 div 中</p>
</div>

**注意**: 如果用户明确要求修改已有屏,此时才使用 diff:
!+++
--- a/0
+++ b/0
@@ -1,3 +1,4 @@
 <div class="w-full h-screen overflow-hidden">
   <h1>标题</h1>
+  <p>这段文字追加到 div 中</p>
 </div>
!+++

### 4.2 ❌ 手动操作 #ppt-container

**错误示例**:
<script>
const container = document.getElementById('ppt-container');
container.innerHTML = '<div>手动替换</div>'; // ❌ 禁止
</script>

**原因**: 前端框架会自动管理 container,手动操作会导致状态不一致。

### 4.3 ❌ 使用 setTimeout

已改为流式渲染,无需使用 setTimeout 控制时序。

## 五、快速参考

| 需求场景 | 使用模式 | 输出格式 |
|---------|---------|---------|
| 创建新的一屏 | 模式 1 | `<div class="h-screen overflow-hidden">...</div>` |
| 添加动画/样式 | 模式 2 | `<script>...</script>` 或 `<style>...</style>` |
| 用户要求修改已有屏 | 模式 3 | `!+++\\n--- a/0\\n...\\n!+++` |

**核心记忆**:
1. HTML 元素 = 翻页(清空上一屏)
2. Script/Style = 追加(不翻页,但翻页时会被清理)
3. Diff = 仅当用户明确要求修改时使用(不要主动使用)

</visual_mode_rules>"""
