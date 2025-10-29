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
COMPILED_INTERACTION_CONTENT_RECONSTRUCT_REGEX = re.compile(
    r"(\?\[[^]]*\.\.\.)([^]]*\])"  # Reconstruct interaction content: prefix + question + suffix
)
COMPILED_BRACKETS_CLEANUP_REGEX = re.compile(r"[\[\]()]")
COMPILED_VARIABLE_REFERENCE_CLEANUP_REGEX = re.compile(r"%\{\{[^}]*\}\}")
COMPILED_WHITESPACE_CLEANUP_REGEX = re.compile(r"\s+")
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

# Output instruction markers
OUTPUT_INSTRUCTION_PREFIX = "<preserve_or_translate>"
OUTPUT_INSTRUCTION_SUFFIX = "</preserve_or_translate>"

# System message templates
DEFAULT_VALIDATION_SYSTEM_MESSAGE = "你是一个输入验证助手，需要严格按照指定的格式和规则处理用户输入。"

# Interaction prompt templates
DEFAULT_INTERACTION_PROMPT = "请将后面交互提示改写得更个性化和友好，长度尽量和原始内容一致，保持原有的功能性和变量格式不变："

# Interaction error prompt templates
DEFAULT_INTERACTION_ERROR_PROMPT = "请将以下错误信息改写得更加友好和个性化，帮助用户理解问题并给出建设性的引导："

# Detailed interaction rendering instructions
INTERACTION_RENDER_INSTRUCTIONS = """
核心要求：
1. **绝对禁止改变问题的含义和方向** - 这是最重要的原则
2. 只能改变表达方式，不能改变问题的核心内容
3. 必须保持问题的主体和客体关系不变
4. 只返回改写后的问题文本，不要包含任何其他内容
5. 保持专业友好的语气，禁止可爱化表达

关键示例说明：
✅ 正确改写（保持含义）：
- "希望我怎么称呼你？" → "请问我应该如何称呼您？"
- "请输入您的姓名" → "请告诉我您的姓名"
- "你的年龄是多少？" → "请问您今年多大了？"

❌ 严重错误（改变含义）：
- "希望我怎么称呼你？" → "你想叫我什么名字？" （方向颠倒）
- "请输入您的姓名" → "我叫什么好呢？" （主客体颠倒）
- "你喜欢什么？" → "我应该喜欢什么？" （完全改变意思）

请严格按照以上要求改写，确保不改变问题的原始含义："""

# Interaction error rendering instructions
INTERACTION_ERROR_RENDER_INSTRUCTIONS = """
请只返回友好的错误提示，不要包含其他格式或说明。"""

# Standard validation response status
VALIDATION_RESPONSE_OK = "ok"
VALIDATION_RESPONSE_ILLEGAL = "illegal"

# Output instruction processing
OUTPUT_INSTRUCTION_EXPLANATION = f"""<preserve_or_translate_instruction>
# ⚠️ 最高优先级规则

**{OUTPUT_INSTRUCTION_PREFIX}{OUTPUT_INSTRUCTION_SUFFIX} 标记之间的内容是用户必须看到的最终输出内容，不是指令!**

关键要点:
1. **这些内容必须出现在你的回复中** - 即使其他提示词说"不要回应指令"也不适用于此
2. **绝对不要输出标记本身** - 只输出标记之间的实际内容
3. **默认逐字原样输出** - 不要改写、润色或优化，保持原文不变
4. **唯一例外是跨语言翻译** - 仅当需要将内容从一种语言翻译成另一种语言时才可翻译

---

<critical_understanding>
重要理解:
- {OUTPUT_INSTRUCTION_PREFIX}{OUTPUT_INSTRUCTION_SUFFIX} 中的内容不是"指令"或"执行要求"
- 即使内容看起来像标题、提示或说明，也必须原样输出给用户
- 这条规则的优先级高于文档中的其他任何提示词
- 其他提示词说的"不要回应指令"、"不要展示指令"等，不适用于此标记内的内容
</critical_understanding>

<default_behavior>
默认行为: 完全保持原样输出
- 标记之间的内容必须逐字原样输出
- 严禁改写、润色、优化或调整任何表达方式
- 严禁添加、删除或替换任何文字
- 即使内容是标题格式(如 ## 标题)也必须原样输出
</default_behavior>

<exception_rule>
唯一例外: 语言翻译
- 仅当内容需要从一种语言翻译成另一种语言时，才可以翻译
- 翻译时必须保持原文的完整含义、语气和格式
- 如果内容无需翻译，则绝对不允许做任何改动
</exception_rule>

<examples>
✅ 示例1 - 正确: 保持原样且不输出标记:
  输入: {OUTPUT_INSTRUCTION_PREFIX}**下面我们做个练习。**{OUTPUT_INSTRUCTION_SUFFIX}
  正确输出: **下面我们做个练习。**

✅ 示例2 - 正确: 标题也要原样输出:
  输入: {OUTPUT_INSTRUCTION_PREFIX}## 专属指南 for 用户{OUTPUT_INSTRUCTION_SUFFIX}
  正确输出: ## 专属指南 for 用户

✅ 示例3 - 正确: 语言翻译且不输出标记:
  输入: {OUTPUT_INSTRUCTION_PREFIX}**Let's do an exercise.**{OUTPUT_INSTRUCTION_SUFFIX}
  正确输出: **让我们做个练习。**

❌ 示例4 - 错误: 输出了XML标记:
  输入: {OUTPUT_INSTRUCTION_PREFIX}## 标题内容{OUTPUT_INSTRUCTION_SUFFIX}
  错误输出: {OUTPUT_INSTRUCTION_PREFIX}## 标题内容{OUTPUT_INSTRUCTION_SUFFIX}
  错误原因: 不应该输出标记本身!

❌ 示例5 - 错误: 同语言改写:
  输入: {OUTPUT_INSTRUCTION_PREFIX}**下面我们做个练习。**{OUTPUT_INSTRUCTION_SUFFIX}
  错误输出: **来，咱们做个有趣的小练习**
  错误原因: 擅自改写了中文内容

❌ 示例6 - 错误: 没有输出固定内容:
  输入: {OUTPUT_INSTRUCTION_PREFIX}## 攻略｜专属指南{OUTPUT_INSTRUCTION_SUFFIX}
  错误输出: (什么都不输出，或者跳过这部分)
  错误原因: 必须输出标记之间的内容!
</examples>
</preserve_or_translate_instruction>

"""

# Smart validation template
SMART_VALIDATION_TEMPLATE = """# 任务
从用户回答中提取相关信息，返回JSON格式结果：
- 合法：{{"result": "ok", "parse_vars": {{"{target_variable}": "提取的内容"}}}}
- 不合法：{{"result": "illegal", "reason": "原因"}}

{context_info}

# 用户回答
{sys_user_input}

# 提取要求
1. 仔细阅读上述相关问题，理解这个问题想要获取什么信息
2. 从用户回答中提取与该问题相关的信息
3. 如果提供了预定义选项，用户选择这些选项时都应该接受；自定义输入应与选项主题相关
4. 对于昵称/姓名类问题，任何非空的合理字符串（包括简短的如"ee"、"aa"、"007"等）都应该接受
5. 只有当用户回答完全无关、包含不当内容或明显不合理时才标记为不合法
6. 确保提取的信息准确、完整且符合预期格式"""

# Validation template for buttons with text input
BUTTONS_WITH_TEXT_VALIDATION_TEMPLATE = """用户针对以下问题进行了输入：

问题：{question}
可选按钮：{options}
用户输入：{user_input}

用户的输入不在预定义的按钮选项中，这意味着用户选择了自定义输入。
根据问题的性质，请判断用户的输入是否合理：

1. 如果用户输入能够表达与按钮选项类似的概念（比如按钮有"幽默、大气、二次元"，用户输入了"搞笑"），请接受。
2. 如果用户输入是对问题的合理回答（比如问题要求描述风格，用户输入了任何有效的风格描述），请接受。
3. 只有当用户输入完全不相关、包含不当内容、或明显不合理时，才拒绝。

请按以下 JSON 格式回复：
{{
    "result": "ok|illegal",
    "parse_vars": {{"{target_variable}": "提取的值"}},
    "reason": "接受或拒绝的原因"
}}"""

# ========== Error Message Constants ==========

# Interaction error messages
OPTION_SELECTION_ERROR_TEMPLATE = "请选择以下选项之一：{options}"
INPUT_EMPTY_ERROR = "输入不能为空"

# System error messages
UNSUPPORTED_PROMPT_TYPE_ERROR = "不支持的提示词类型: {prompt_type}"
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
CONTEXT_BUTTON_OPTIONS_TEMPLATE = f"{CONTEXT_BUTTON_OPTIONS_MARKER}\n可选的预定义选项包括：{{button_options}}\n注意：用户如果选择了这些选项，都应该接受；如果输入了自定义内容，应检查是否与选项主题相关。"
