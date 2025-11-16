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

# Inline preserved content pattern: ===content=== format
INLINE_PRESERVE_PATTERN = r"^===(.+)=== *$"
COMPILED_INLINE_PRESERVE_REGEX = re.compile(INLINE_PRESERVE_PATTERN)

# Code fence patterns (CommonMark specification compliant)
# Code block fence start: 0-3 spaces + at least 3 backticks or tildes + optional info string
CODE_FENCE_START_PATTERN = r"^[ ]{0,3}([`~]{3,})(.*)$"
COMPILED_CODE_FENCE_START_REGEX = re.compile(CODE_FENCE_START_PATTERN)

# Code block fence end: 0-3 spaces + at least 3 backticks or tildes + optional whitespace
CODE_FENCE_END_PATTERN = r"^[ ]{0,3}([`~]{3,})\s*$"
COMPILED_CODE_FENCE_END_REGEX = re.compile(CODE_FENCE_END_PATTERN)

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

# Interaction prompt templates (条件翻译)
DEFAULT_INTERACTION_PROMPT = """<interaction_translation_rules>
⚠️⚠️⚠️ 这是一个 JSON 原样输出任务 - 默认不翻译！⚠️⚠️⚠️

## 默认行为（最高优先级）

**除非明确检测到语言指令，否则必须逐字符原样返回输入的 JSON**
- 不翻译任何文本
- 不修改任何格式
- 不添加任何内容（如 display//value 分离）
- 不删除任何内容
- 不调整任何顺序

## 语言指令检测规则

**仅在以下情况才翻译：**

1. **检测范围**：仅在 <document_context> 标签内检测
2. **必须包含明确的语言转换关键词**：
   - 中文："使用英语"、"用英文"、"英语输出"、"翻译成英语"、"Translate to English"
   - 英文："use English"、"in English"、"respond in English"、"translate to"
   - 其他语言：类似的明确转换指令
3. **不算语言指令的情况**：
   - ❌ 风格要求："用emoji"、"讲故事"、"友好"、"简洁"
   - ❌ 任务描述："内容营销"、"吸引用户"、"引人入胜"
   - ❌ 输出要求："内容简洁"、"使用吸引人的语言"

## 处理逻辑

步骤1：在 <document_context> 中搜索语言转换关键词
步骤2：
- 如果找到 → 将 buttons 和 question 翻译成指定语言（仅翻译文本，不改格式）
- 如果未找到 → 逐字符原样返回输入的 JSON

## 输出格式要求

- **必须返回纯 JSON**，不要添加任何解释或 markdown 代码块
- **格式必须与输入完全一致**，包括空格、标点、引号

## 示例

### 示例 1：无语言指令（默认情况）

输入：{"buttons": ["产品经理", "开发者", "大学生"], "question": "其他身份"}

<document_context>
你是一个内容营销，擅长结合用户特点，给到引人入胜的内容。
任务说明：认真理解给定的内容，站在用户角度...
输出要求：内容简洁有力，使用吸引用户的语言...
</document_context>

✅ 正确输出：{"buttons": ["产品经理", "开发者", "大学生"], "question": "其他身份"}
❌ 错误输出：{"buttons": ["Product Manager//产品经理", ...], ...}  ← 不要添加翻译！

### 示例 2：有明确语言指令

输入：{"buttons": ["苹果", "香蕉"], "question": "其他水果"}

<document_context>
请使用英语输出所有内容。
</document_context>

✅ 正确输出：{"buttons": ["Apple", "Banana"], "question": "Other fruit"}

### 示例 3：仅有风格指令（不算语言指令）

输入：{"buttons": ["选项A", "选项B"], "question": "其他"}

<document_context>
请用emoji和故事化的方式呈现内容。
</document_context>

✅ 正确输出：{"buttons": ["选项A", "选项B"], "question": "其他"}  ← 保持原样！

⚠️⚠️⚠️ 最终强调 ⚠️⚠️⚠️

- 默认行为：原样输出，不做任何改动
- 只有在 <document_context> 中明确看到"使用XX语言"、"translate to"等关键词时才翻译
- 如有任何疑问，必须原样输出
</interaction_translation_rules>"""

# Interaction error prompt templates
DEFAULT_INTERACTION_ERROR_PROMPT = "请将以下错误信息改写得更加友好和个性化，帮助用户理解问题并给出建设性的引导："

# Interaction error rendering instructions
INTERACTION_ERROR_RENDER_INSTRUCTIONS = """
请只返回友好的错误提示，不要包含其他格式或说明。"""

# Standard validation response status
VALIDATION_RESPONSE_OK = "ok"
VALIDATION_RESPONSE_ILLEGAL = "illegal"

# Output instruction processing
OUTPUT_INSTRUCTION_EXPLANATION = f"""<preserve_or_translate_instruction>
⚠️⚠️⚠️ 保留内容输出任务 - 默认原样输出！⚠️⚠️⚠️

## 默认行为（最高优先级）

**看到 {OUTPUT_INSTRUCTION_PREFIX}...{OUTPUT_INSTRUCTION_SUFFIX} 标记时，必须将标记内的内容输出到回复中（保持原位置）**
- 默认：逐字符原样输出，不做任何改动
- 绝对不要输出 {OUTPUT_INSTRUCTION_PREFIX} 和 {OUTPUT_INSTRUCTION_SUFFIX} 标记本身
- 始终保留 emoji、格式、特殊字符

## 语言指令检测规则

**仅在以下情况才翻译：**

1. **检测范围**：仅在 <document_prompt> 标签内检测
2. **必须包含明确的语言转换关键词**：
   - 中文："使用英语"、"用韩文"、"英语输出"、"翻译成英语"、"Translate to English"
   - 英文："use English"、"in English"、"respond in English"、"translate to"
   - 其他语言：类似的明确转换指令
3. **不算语言指令的情况**：
   - ❌ 风格要求："用emoji"、"讲故事"、"友好"、"简洁"
   - ❌ 任务描述："内容营销"、"吸引用户"、"引人入胜"
   - ❌ 输出要求："内容简洁"、"使用吸引人的语言"

## 处理逻辑

步骤1：在 <document_prompt> 中搜索语言转换关键词
步骤2：
- 如果找到 → 保持原意与风格，翻译成指定语言
- 如果未找到 → 逐字符原样输出，不做任何改动

## 输出位置规则

- 保持内容在原文档中的位置（开头/中间/结尾）
- 不要强制移到开头或其他位置

## 示例

### 示例 1：无语言指令（默认情况）

输入: {OUTPUT_INSTRUCTION_PREFIX}🌟 欢迎冒险！{OUTPUT_INSTRUCTION_SUFFIX}

询问小朋友的名字：

<document_prompt>
你是一个故事大王，擅长讲故事。
用一些语气词，多用emoji。
</document_prompt>

✅ 正确输出: 🌟 欢迎冒险！

询问小朋友的名字：...（保留内容在开头，原样输出）

❌ 错误输出: 询问小朋友的名字：...（完全不输出保留内容 ← 绝对禁止！）

### 示例 2：有明确语言指令

输入: {OUTPUT_INSTRUCTION_PREFIX}🌟 欢迎冒险！{OUTPUT_INSTRUCTION_SUFFIX}

询问小朋友的名字：

<document_prompt>
请使用韩语输出所有内容。
</document_prompt>

✅ 正确输出: 🌟 모험에 오신 것을 환영합니다!

아이의 이름을 물어보세요：...（保留内容翻译为韩语）

### 示例 3：仅有风格指令（不算语言指令）

输入: {OUTPUT_INSTRUCTION_PREFIX}**重要提示**{OUTPUT_INSTRUCTION_SUFFIX}

后续内容...

<document_prompt>
请用emoji和故事化的方式呈现内容。
</document_prompt>

✅ 正确输出: **重要提示**

后续内容...（保持原样！）

### 示例 4：标记剥离错误

输入: {OUTPUT_INSTRUCTION_PREFIX}**Title**{OUTPUT_INSTRUCTION_SUFFIX}

❌ 绝对不要: {OUTPUT_INSTRUCTION_PREFIX}**Title**{OUTPUT_INSTRUCTION_SUFFIX}（包含了标记）
✅ 正确输出: **Title**（排除了标记）

⚠️⚠️⚠️ 最终强调 ⚠️⚠️⚠️

- 默认行为：原样输出保留内容，不做任何改动
- 只有在 <document_prompt> 中明确看到"使用XX语言"、"translate to"等关键词时才翻译
- 如有任何疑问，必须原样输出
- 此规则优先级最高，覆盖所有其他指令
</preserve_or_translate_instruction>

"""

# Validation task template (merged with system message)
VALIDATION_TASK_TEMPLATE = """你是字符串验证程序，不是对话助手。

你的唯一任务：按后续规则检查输入，输出 JSON：
{{"result": "ok", "parse_vars": {{"{target_variable}": "用户输入"}}}} 或 {{"result": "illegal", "reason": "原因"}}

严禁输出任何自然语言解释。

# reason 语言
从 <document_context> 中仅提取语言要求（如"使用英文"、"use English"）
- 如果有明确语言要求 → reason 使用该语言
- 否则 → reason 使用用户输入或问题的语言
"""

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
UNSUPPORTED_PROMPT_TYPE_ERROR = "不支持的提示词类型: {prompt_type} (支持的类型: base_system, document, interaction, interaction_error)"
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
