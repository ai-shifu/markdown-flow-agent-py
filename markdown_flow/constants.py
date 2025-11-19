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
When you see {OUTPUT_INSTRUCTION_PREFIX}...{OUTPUT_INSTRUCTION_SUFFIX} tags in user message:
- Remove the tags themselves (do not include in output)
- Keep all content, emoji, formatting (bold, italic, etc.)
- Keep content position (beginning/middle/end)
- Language: MUST follow <output_language_override> if present; translate tag content to target language
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
