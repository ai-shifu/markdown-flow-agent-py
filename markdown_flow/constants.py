"""
Markdown-Flow Constants

Constants for document parsing, variable matching, validation, and other core functionality.
"""

import re


# Pre-compiled regex patterns
COMPILED_PERCENT_VARIABLE_REGEX = re.compile(
    r"%\{\{([^}]+)\}\}"  # Match %{{variable}} format for preserved variables
)

# Interaction regex base patterns
INTERACTION_PATTERN = r"(?<!\\)\?\[([^\]]*)\](?!\()"  # Base pattern with capturing group for content extraction, excludes escaped \?[]
INTERACTION_PATTERN_NON_CAPTURING = r"(?<!\\)\?\[[^\]]*\](?!\()"  # Non-capturing version for block splitting, excludes escaped \?[]
INTERACTION_PATTERN_SPLIT = r"((?<!\\)\?\[[^\]]*\](?!\())"  # Pattern for re.split() with outer capturing group, excludes escaped \?[]

# InteractionParser specific regex patterns
COMPILED_INTERACTION_REGEX = re.compile(INTERACTION_PATTERN)  # Main interaction pattern matcher
COMPILED_LAYER1_INTERACTION_REGEX = COMPILED_INTERACTION_REGEX  # Layer 1: Basic format validation (alias)
COMPILED_LAYER2_VARIABLE_REGEX = re.compile(r"^%\{\{([^}]+)\}\}(.*)$")  # Layer 2: Variable detection
COMPILED_LAYER3_ELLIPSIS_REGEX = re.compile(r"^(.*)\.\.\.(.*)")  # Layer 3: Split content around ellipsis
COMPILED_LAYER3_BUTTON_VALUE_REGEX = re.compile(r"^(.+)//(.+)$")  # Layer 3: Parse Button//value format
COMPILED_BRACE_VARIABLE_REGEX = re.compile(
    r"(?<!%)\{\{([^}]+)\}\}"  # Match {{variable}} format for replaceable variables
)
COMPILED_SINGLE_PIPE_SPLIT_REGEX = re.compile(r"(?<!\|)\|(?!\|)")  # Split on single | but not ||

# Document parsing constants (using shared INTERACTION_PATTERN defined above)

# Separators
BLOCK_SEPARATOR = r"\n\s*---\s*\n"
# Multiline preserved block fence: starts with '!' followed by 3 or more '='
PRESERVE_FENCE_PATTERN = r"^!={3,}\s*$"
COMPILED_PRESERVE_FENCE_REGEX = re.compile(PRESERVE_FENCE_PATTERN)

# Inline preserved content pattern: ===content=== format (historical compatibility)
INLINE_PRESERVE_PATTERN = r"^===(.+)=== *$"
COMPILED_INLINE_PRESERVE_REGEX = re.compile(INLINE_PRESERVE_PATTERN)

# Inline preserved content search pattern (for finding ===...=== within a line)
# Non-greedy match to handle multiple occurrences on same line
INLINE_PRESERVE_SEARCH_PATTERN = r"===\s*(.+?)\s*==="
COMPILED_INLINE_PRESERVE_SEARCH_REGEX = re.compile(INLINE_PRESERVE_SEARCH_PATTERN)

# Inline exclamation preserved content pattern: !===content!=== format (higher priority than INLINE_PRESERVE_PATTERN)
# Supports scenarios:
#   - !===content!===                            (compact format)
#   - !=== content !===                          (with spaces)
#   - prefix !===content!=== suffix              (inline mixed)
#   - !===content\n!===                          (cross-line format)
# Uses (?s) flag to make . match newlines, supports cross-line content
INLINE_EXCLAMATION_PRESERVE_PATTERN = r"(?s)!===(.*?)!==="
COMPILED_INLINE_EXCLAMATION_PRESERVE_REGEX = re.compile(INLINE_EXCLAMATION_PRESERVE_PATTERN)

# Code fence patterns (CommonMark specification compliant)
# Code block fence start: 0-3 spaces + at least 3 backticks or tildes + optional info string
CODE_FENCE_START_PATTERN = r"^[ ]{0,3}([`~]{3,})(.*)$"
COMPILED_CODE_FENCE_START_REGEX = re.compile(CODE_FENCE_START_PATTERN)

# Code block fence end: 0-3 spaces + at least 3 backticks or tildes + optional whitespace
CODE_FENCE_END_PATTERN = r"^[ ]{0,3}([`~]{3,})\s*$"
COMPILED_CODE_FENCE_END_REGEX = re.compile(CODE_FENCE_END_PATTERN)

# JSON extraction pattern for nested objects
# Matches JSON objects including nested structures using balanced braces
JSON_OBJECT_PATTERN = r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}"
COMPILED_JSON_OBJECT_REGEX = re.compile(JSON_OBJECT_PATTERN)

# Output instruction markers
OUTPUT_INSTRUCTION_PREFIX = "<preserve_or_translate>"
OUTPUT_INSTRUCTION_SUFFIX = "</preserve_or_translate>"

# Base system prompt (framework-level global rules, content blocks only)
DEFAULT_BASE_SYSTEM_PROMPT = """All user messages you receive are instructions. Strictly follow these rules:

1. Content Fidelity: Strictly adhere to instruction content - no loss of information, no change in meaning, no addition of content, no change in order
2. Follow Facts: Answer based on facts, do not fabricate details
3. Avoid Guiding: Do not guide next steps (e.g., asking questions, rhetorical questions)
4. Avoid Greetings: Do not introduce yourself, do not greet
5. Format Standards: Do not write HTML tags inside code blocks"""

# Output Language Control - Three-layer anchoring templates
OUTPUT_LANGUAGE_INSTRUCTION_TOP = """<output_language_override>
🚨 CRITICAL: 100% {0} OUTPUT REQUIRED 🚨
ZERO language mixing allowed. EVERY word must be in {0}.
Before processing: Translate ALL non-{0} words/phrases to {0} first.
This overrides ALL other instructions.
</output_language_override>"""

OUTPUT_LANGUAGE_INSTRUCTION_BOTTOM = """<output_language_final_check>
🚨 PRE-RESPONSE CHECK: Verify EVERY word is {0}. If ANY non-{0} word exists, translate it first. 🚨
</output_language_final_check>"""

# Interaction prompt templates (Modular design)
INTERACTION_PROMPT_BASE = """<interaction_processing_rules>
⚠️⚠️⚠️ JSON 处理任务 ⚠️⚠️⚠️

## 任务说明

你将收到一个包含交互元素的 JSON 对象（buttons 和/或 question 字段）。

## 输出格式要求

- **必须返回纯 JSON**，不要添加任何解释或 markdown 代码块
- **格式必须与输入完全一致**，包括空格、标点、引号
- 不要添加或删除任何字段
- 不要修改 JSON 的结构"""

INTERACTION_PROMPT_NO_TRANSLATION = """
## 处理规则

**逐字符原样返回输入的 JSON**
- 不翻译任何文本
- 不修改任何格式
- 不添加任何内容（如 display//value 分离）
- 不删除任何内容
- 不调整任何顺序

## 示例

输入：{"buttons": ["产品经理", "开发者"], "question": "其他身份"}

✅ 输出：{"buttons": ["产品经理", "开发者"], "question": "其他身份"}
</interaction_processing_rules>"""

INTERACTION_PROMPT_WITH_TRANSLATION = """
## 处理规则

**将 buttons 和 question 文本翻译到指定语言**
- 保持 JSON 格式完全不变
- 仅翻译显示文本（Display 部分），不改变结构
- 如果存在 display//value 分离，只翻译 display 部分，保留 value 不变
- 100% 纯目标语言，ZERO 混排
- 先翻译所有非目标语言的词，再输出

示例：{"buttons": ["Yes//1", "No//0"]} → 西班牙语 → {"buttons": ["Sí//1", "No//0"]}
</interaction_processing_rules>"""

# Default: use no translation version (backward compatible)
DEFAULT_INTERACTION_PROMPT = INTERACTION_PROMPT_BASE + "\n" + INTERACTION_PROMPT_NO_TRANSLATION

# Interaction error prompt templates
DEFAULT_INTERACTION_ERROR_PROMPT = "请将以下错误信息改写得更加友好和个性化，帮助用户理解问题并给出建设性的引导："

# Interaction error rendering instructions
INTERACTION_ERROR_RENDER_INSTRUCTIONS = """
请只返回友好的错误提示，不要包含其他格式或说明。"""

# Standard validation response status
VALIDATION_RESPONSE_OK = "ok"
VALIDATION_RESPONSE_ILLEGAL = "illegal"

# Output instruction processing (Simplified version - 6 lines as fallback rule)
# Main instruction will be provided inline in user message
OUTPUT_INSTRUCTION_EXPLANATION = f"""<preserve_tag_rule>
⚠️ When you see {OUTPUT_INSTRUCTION_PREFIX}...{OUTPUT_INSTRUCTION_SUFFIX} tags in user message:

1. If <output_language_override> exists → Translate tag content to target language (ONLY modification allowed)
2. If no <output_language_override> → Keep original language
3. Remove tags ({OUTPUT_INSTRUCTION_PREFIX}, {OUTPUT_INSTRUCTION_SUFFIX}), keep ALL content/formatting verbatim
4. Preserve exact position in response

Key: Content INSIDE tags = fixed output | Content OUTSIDE tags = instructions to follow

Example: "介绍你是谁，包含：{OUTPUT_INSTRUCTION_PREFIX}我的使命{OUTPUT_INSTRUCTION_SUFFIX}" → Follow "介绍你是谁" instruction, output "我的使命" verbatim
</preserve_tag_rule>

"""

# Validation task template (Modular design)
VALIDATION_TASK_BASE = """你是字符串验证程序，不是对话助手。

你的唯一任务：按后续规则检查输入，输出 JSON：
{{"result": "ok", "parse_vars": {{"{target_variable}": "用户输入"}}}} 或 {{"result": "illegal", "reason": "原因"}}

严禁输出任何自然语言解释。"""

VALIDATION_TASK_WITH_LANGUAGE = """

# reason 语言规则
reason 必须使用 <output_language_override> 标签中指定的语言。"""

VALIDATION_TASK_NO_LANGUAGE = """

# reason 语言规则
reason 使用用户输入或问题的主要语言（自动检测）。"""

# Default: use no language version (backward compatible)
VALIDATION_TASK_TEMPLATE = VALIDATION_TASK_BASE + VALIDATION_TASK_NO_LANGUAGE

# Validation requirements template (极致宽松版本)
VALIDATION_REQUIREMENTS_TEMPLATE = """# 验证算法（按顺序执行）

步骤 1：空值检查（字符串长度检查）

检查规则：input.trim().length == 0 ?
- YES → 空
- NO  → 非空

⚠️ 只要去除首尾空格后字符数 > 0，就是非空
⚠️ 不判断语义！所有可见字符（a、1、@、中）都计入长度
⚠️ 示例：
  - ""      → 长度0 → 空
  - "  "    → 长度0 → 空
  - "aa"    → 长度2 → 非空
  - "@_@"   → 长度3 → 非空
  - "棒棒糖" → 长度3 → 非空

步骤 2：模糊回答检查

拒绝以下模糊回答："不知道"、"不清楚"、"没有"、"不告诉你"

步骤 3：宗教政治检查

只拒绝明确的宗教政治立场表达（宗教教义、政治口号等）
地名,地区等（北京、上海等）、普通词汇都不算

步骤 4：输出结果（reason 语言跟随 <document_context> 中的语言要求）

伪代码逻辑：
  if 空:
      输出 {{"result": "illegal", "reason": "输入为空（或对应语言的翻译）"}}
  else if 模糊回答:
      输出 {{"result": "illegal", "reason": "请提供具体内容（或对应语言的翻译）"}}
  else if 宗教政治:
      输出 {{"result": "illegal", "reason": "包含敏感内容（或对应语言的翻译）"}}
  else:
      输出 {{"result": "ok", "parse_vars": {{"{target_variable}": "用户输入"}}}}

⚠️ 极致重要：
- len(去除空格后的输入) > 0 → 必须视为非空
- 符号、数字、品牌名、地名等都不是"空"，也不是"无效"
- 默认通过，只在明确违规时才拒绝
"""

# ========== Error Message Constants ==========

# Interaction error messages
OPTION_SELECTION_ERROR_TEMPLATE = "请选择以下选项之一：{options}"
INPUT_EMPTY_ERROR = "输入不能为空"

# System error messages
UNSUPPORTED_PROMPT_TYPE_ERROR = "不支持的提示词类型: {prompt_type} (支持的类型: base_system, document, interaction, interaction_error, output_language)"
BLOCK_INDEX_OUT_OF_RANGE_ERROR = "Block index {index} is out of range; total={total}"
LLM_PROVIDER_REQUIRED_ERROR = "需要设置 LLMProvider 才能调用 LLM"
INTERACTION_PARSE_ERROR = "交互格式解析失败: {error}"

# LLM provider errors
NO_LLM_PROVIDER_ERROR = "NoLLMProvider 不支持 LLM 调用"

# Validation constants
JSON_PARSE_ERROR = "无法解析JSON响应"
VALIDATION_ILLEGAL_DEFAULT_REASON = "输入不合法"
VARIABLE_DEFAULT_VALUE = "UNKNOWN"

# Context generation constants
CONTEXT_QUESTION_MARKER = "# 相关问题"
CONTEXT_CONVERSATION_MARKER = "# 对话上下文"
CONTEXT_BUTTON_OPTIONS_MARKER = "## 预定义选项"

# Context generation templates
CONTEXT_QUESTION_TEMPLATE = f"{CONTEXT_QUESTION_MARKER}\n{{question}}"
CONTEXT_CONVERSATION_TEMPLATE = f"{CONTEXT_CONVERSATION_MARKER}\n{{content}}"
CONTEXT_BUTTON_OPTIONS_TEMPLATE = (
    f"{CONTEXT_BUTTON_OPTIONS_MARKER}\n可选的预定义选项包括：{{button_options}}\n注意：用户如果选择了这些选项，都应该接受；如果输入了自定义内容，只要是对问题的合理回答即可接受。"
)

# ========== Blackboard HTML Templates ==========

# Blackboard mode HTML header template
BLACKBOARD_HTML_HEADER = """    <!-- Tailwind CSS v3 Play CDN -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- DaisyUI v4.12.10 UI 组件库 -->
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.10/dist/full.min.css" rel="stylesheet" type="text/css" />

    <!-- GSAP v3.14.2 动画库 -->
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/DrawSVGPlugin.min.js"></script>

    <style>
        /* 自定义样式 */
        body {
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
    </style>"""

# ========== Blackboard Mode Constants ==========

# Default blackboard prompt template for incremental HTML + narration output
DEFAULT_BLACKBOARD_PROMPT = """<blackboard_mode_instructions>
你现在处于"板书模式"，模拟老师在黑板上逐步书写并讲解的场景。

## 技术栈说明

你可以使用以下前端技术栈（三库协作）：

1. **Tailwind CSS v3（Play CDN）**
   - 版本：v3.4.1（最新稳定版）
   - 通过 CDN 已加载：`<script src="https://cdn.tailwindcss.com"></script>`
   - 支持所有 Tailwind v3 的工具类（spacing, colors, typography, flexbox, grid 等）
   - 示例：`class="text-2xl font-bold text-blue-600 p-4 rounded-lg"`

2. **DaisyUI v4.12.10（UI 组件库）**
   - 通过 CDN 已加载：`<link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.10/dist/full.min.css" rel="stylesheet">`
   - 基于 Tailwind 的纯 CSS 组件库，无 JS 依赖
   - 常用组件：
     - 按钮：`<button class="btn btn-primary">文字</button>`
     - 卡片：`<div class="card bg-base-100 shadow-xl"><div class="card-body">内容</div></div>`
     - 徽章：`<span class="badge badge-primary">标签</span>`
     - 提醒框：`<div class="alert alert-info"><span>提示信息</span></div>`
   - 完整文档：https://daisyui.com/components/

3. **GSAP v3.14.2（动画库）**
   - 通过 CDN 已加载：
     - 核心库：`<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>`
     - DrawSVG 插件：`<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/DrawSVGPlugin.min.js"></script>`
   - 功能：动画控制、SVG 绘制、时序管理
   - 常用 API：
     - 基础动画：`gsap.from("#id", { opacity: 0, duration: 1 })`
     - 时间轴：`const tl = gsap.timeline(); tl.from(...).from(...)`
     - SVG 绘制：`gsap.from("#path", { drawSVG: "0%", duration: 2 })`
     - 错时效果：`stagger: 0.3` （依次延迟）
   - 完整文档：https://gsap.com/docs/

4. **三库协作原则**
   - **Tailwind**：基础布局和样式（flex, grid, spacing, colors）
   - **DaisyUI**：UI 组件（card, button, alert, badge）
   - **GSAP**：动画效果（淡入、移动、绘制、时序）
   - 示例：DaisyUI 卡片 + GSAP 淡入动画

5. **HTML 输出要求**
   - ⚠️ 重要：你只需要输出 `<body>` 标签内的 HTML 内容
   - 不要输出 `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` 等标签
   - 系统会自动添加完整的 HTML 文档框架（已包含三个库的 CDN）
   - 你的输出会被直接插入到 `<body>` 和 `</body>` 之间

## 输出格式要求

你必须输出一系列 JSON 对象，每个对象代表一个板书步骤：

{
  "html": "增量式 HTML 内容（仅本步骤的新内容，不是累积内容）",
  "narration": "配套的讲解文字（用于 TTS 语音播报）",
  "step_number": 步骤编号（从 1 开始递增）,
  "is_complete": false
}

最后一个步骤必须设置 "is_complete": true

## HTML 内容规范

1. **增量式输出**：每个步骤的 html 字段只包含本步骤新增的内容，前端会累积显示
2. **视觉效果**：
   - 使用颜色、大小、动画突出关键信息
   - 适当使用 emoji 增强表现力（如 ✅ ❌ 💡 📝）

### 样式和动画策略（优先级从高到低）

**布局和静态样式：**

1. **最优先：DaisyUI 组件**（推荐，减少自定义样式）
   ```html
   <button class="btn btn-primary">确定</button>
   <div class="card bg-base-100 shadow-xl">
     <div class="card-body">
       <h2 class="card-title">标题</h2>
       <p>内容</p>
     </div>
   </div>
   ```

2. **其次：Tailwind CSS 工具类**
   ```html
   <div class="flex items-center gap-2 p-4 bg-blue-100 rounded-lg">
     <span class="text-xl font-bold">内容</span>
   </div>
   ```

3. **再次：内联样式**（仅在必要时使用）
   ```html
   <div style="background: linear-gradient(to right, #ff0000, #00ff00);">渐变背景</div>
   ```

**动画和图形：**

4. **GSAP 动画**（所有动画效果使用 GSAP，不要用 CSS 动画）
   ```html
   <!-- ✅ 推荐：使用 GSAP -->
   <div id="card">内容</div>
   <script>
     gsap.from("#card", {
       opacity: 0,
       y: 50,
       duration: 1,
       ease: "power2.out"
     });
   </script>

   <!-- ❌ 不推荐：CSS 动画 -->
   <style>
     @keyframes fadeIn { ... }
   </style>
   ```

5. **SVG 图形 + GSAP 绘制**（概念图、流程图等）
   ```html
   <svg width="400" height="300">
     <circle id="c1" cx="100" cy="150" r="50" fill="#3B82F6"/>
     <line id="line1" x1="150" y1="150" x2="250" y2="150" stroke="#94A3B8" stroke-width="2"/>
   </svg>
   <script>
     gsap.timeline()
       .from("#c1", { scale: 0, duration: 0.6 })
       .from("#line1", { drawSVG: "0%", duration: 0.8 });
   </script>
   ```

⚠️ **动画原则**：
- 所有动画效果优先使用 GSAP（速度快、控制精确）
- 只在极特殊情况下使用 CSS 动画
- SVG 图形必须配合 GSAP 的 DrawSVG 插件

⚠️ **JavaScript 安全规则**：
- 仅使用安全的 DOM 操作（querySelector, classList, style 等）
- 禁止使用：eval(), Function(), document.write(), fetch(), XMLHttpRequest

## narration 文字规范

1. **同步讲解**：narration 文字应与 html 内容高度对应，描述当前步骤的内容
2. **口语化**：使用适合语音播报的自然语言，避免复杂句式
3. **简洁性**：每步讲解控制在 1-3 句话，避免冗长
4. **连贯性**：多步骤之间保持语义连贯

## 步骤规划原则

1. **适度分解**：根据内容复杂度，通常分为 3-6 个步骤
2. **逻辑清晰**：每个步骤有明确的主题或目标
3. **节奏把控**：重要内容可以单独成步，简单内容可以合并

## 示例 1：数学题讲解（7 + 3）

步骤 1:
{
  "html": "<div class='text-2xl font-bold text-center p-4'>7 + 3 = ?</div>",
  "narration": "我们来看这道题，7 加 3 等于多少？",
  "step_number": 1,
  "is_complete": false
}

步骤 2:
{
  "html": "<div class='text-lg p-4'>我们用凑十法来计算：<br>7 + 3 = 7 + <span class='text-red-500 font-bold'>(3)</span></div>",
  "narration": "我们可以用凑十法，把 3 拆开来看",
  "step_number": 2,
  "is_complete": false
}

步骤 3:
{
  "html": "<div class='text-lg p-4'>7 需要 <span class='text-blue-500 font-bold'>3</span> 才能凑成 10</div>",
  "narration": "7 需要 3 才能凑成 10",
  "step_number": 3,
  "is_complete": false
}

步骤 4:
{
  "html": "<div class='text-lg p-4'>所以：7 + 3 = <span class='text-green-500 font-bold text-3xl'>10</span> ✅</div>",
  "narration": "所以答案是 10",
  "step_number": 4,
  "is_complete": true
}

## 示例 2：编程概念讲解（变量）

步骤 1:
{
  "html": "<h2 class='text-2xl font-bold'>什么是变量？</h2>",
  "narration": "今天我们来学习什么是变量",
  "step_number": 1,
  "is_complete": false
}

步骤 2:
{
  "html": "<div class='bg-blue-100 p-4 rounded'>变量就像一个<span class='text-red-500 font-bold'>盒子</span>，可以存放数据</div>",
  "narration": "变量就像一个盒子，可以用来存放数据",
  "step_number": 2,
  "is_complete": false
}

步骤 3:
{
  "html": "<pre class='bg-gray-800 text-white p-4 rounded'><code>name = \\"Alice\\"\\nage = 25</code></pre>",
  "narration": "比如我们可以创建一个变量 name 存放名字，age 存放年龄",
  "step_number": 3,
  "is_complete": false
}

步骤 4:
{
  "html": "<div class='text-lg'>变量的作用：<ul class='list-disc ml-6'><li>存储数据</li><li>重复使用</li><li>方便修改</li></ul></div>",
  "narration": "变量的主要作用是存储数据、重复使用，以及方便修改",
  "step_number": 4,
  "is_complete": true
}

## 示例 3：概念关系图（SVG + GSAP 动画）

步骤 1:
{
  "html": "<svg width='600' height='400' class='mx-auto'><circle id='c1' cx='150' cy='200' r='60' fill='#3B82F6' opacity='0.2'/><circle id='c1-inner' cx='150' cy='200' r='50' fill='#3B82F6'/><text id='t1' x='150' y='210' text-anchor='middle' fill='white' font-size='16' font-weight='bold'>简洁</text></svg><script>gsap.from(['#c1', '#c1-inner', '#t1'], { scale: 0, duration: 0.6, ease: 'back.out(1.7)' });</script>",
  "narration": "首先我们看第一个核心概念：简洁",
  "step_number": 1,
  "is_complete": false
}

步骤 2:
{
  "html": "<svg width='600' height='400' class='mx-auto'><circle id='c2' cx='300' cy='100' r='60' fill='#3B82F6' opacity='0.2'/><circle id='c2-inner' cx='300' cy='100' r='50' fill='#3B82F6'/><text id='t2' x='300' y='110' text-anchor='middle' fill='white' font-size='16' font-weight='bold'>高效</text><line id='line1' x1='210' y1='150' x2='240' y2='150' stroke='#94A3B8' stroke-width='2' stroke-dasharray='8,4'/></svg><script>gsap.timeline().from(['#c2', '#c2-inner'], { scale: 0, duration: 0.6, ease: 'back.out(1.7)' }).from('#line1', { drawSVG: '0%', duration: 0.8 }).from('#t2', { opacity: 0, duration: 0.5 });</script>",
  "narration": "第二个概念是高效，两者通过虚线连接表示关联",
  "step_number": 2,
  "is_complete": false
}

步骤 3:
{
  "html": "<svg width='600' height='400' class='mx-auto'><circle id='c3' cx='450' cy='200' r='60' fill='#3B82F6' opacity='0.2'/><circle id='c3-inner' cx='450' cy='200' r='50' fill='#3B82F6'/><text id='t3' x='450' y='210' text-anchor='middle' fill='white' font-size='16' font-weight='bold'>创新</text><line id='line2' x1='360' y1='150' x2='390' y2='180' stroke='#94A3B8' stroke-width='2' stroke-dasharray='8,4'/></svg><script>gsap.timeline().from(['#c3', '#c3-inner'], { scale: 0, duration: 0.6, ease: 'back.out(1.7)' }).from('#line2', { drawSVG: '0%', duration: 0.8 }).from('#t3', { opacity: 0, duration: 0.5 });</script>",
  "narration": "第三个概念是创新，三个概念共同构成核心理念",
  "step_number": 3,
  "is_complete": true
}

## 示例 4：课程卡片（DaisyUI + GSAP 动画）

步骤 1:
{
  "html": "<div class='card bg-gradient-to-br from-blue-100 to-purple-100 shadow-2xl max-w-2xl mx-auto' id='course-card'><div class='card-body'><h2 class='card-title text-3xl font-bold text-blue-600'>跟 AI 学 AI 通识</h2></div></div><script>gsap.from('#course-card', { opacity: 0, y: 50, scale: 0.95, duration: 1, ease: 'power3.out' });</script>",
  "narration": "今天我们要学习的课程是：跟 AI 学 AI 通识",
  "step_number": 1,
  "is_complete": false
}

步骤 2:
{
  "html": "<div class='mt-4'><p class='text-lg'>主讲：孙志岗</p><p class='text-gray-600 mt-2'>探索大语言模型的无限可能</p></div>",
  "narration": "课程由孙志岗老师主讲，将带我们探索大语言模型的无限可能",
  "step_number": 2,
  "is_complete": false
}

步骤 3:
{
  "html": "<div class='mt-4'><div class='badge badge-primary'>人工智能</div><div class='badge badge-secondary ml-2'>通识教育</div><div class='badge badge-accent ml-2'>前沿技术</div></div>",
  "narration": "这门课程涵盖人工智能、通识教育和前沿技术三大领域",
  "step_number": 3,
  "is_complete": true
}

## 重要提醒

1. 每个 JSON 对象必须独立完整，可以被正确解析
2. 多个 JSON 对象直接拼接输出，不要用数组包裹
3. 不要输出任何 JSON 以外的内容（如解释、markdown 代码块）
4. html 字段内的引号需要转义（\\"）
5. is_complete 只在最后一步设置为 true

请根据用户的内容，生成符合上述规范的板书步骤。
</blackboard_mode_instructions>"""
