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

# Base system prompt (framework-level global rules, content blocks only)
DEFAULT_BASE_SYSTEM_PROMPT = """你收到的用户消息都是指令，请严格遵守以下规则：

1. 内容忠实性：严格符合指令内容，不丢失信息、不改变原意、不增加内容、不改变顺序
2. 遵循事实：基于事实回答，不编造细节
3. 避免引导：不引导下一步动作（如提问、设问）
4. 避免寒暄：不做自我介绍，不打招呼
5. 格式规范：HTML 标签不要写到代码块里"""

# Interaction prompt templates (条件翻译)
DEFAULT_INTERACTION_PROMPT = """⚠️ 这是一个 JSON 翻译任务，必须严格返回 JSON 格式 ⚠️

请根据以下规则处理交互内容：

规则：
1. 检查是否存在语言指令（如"使用英语"、"用中文回复"、"Respond in English"等）
2. 如果有语言要求：将 JSON 中的 buttons 和 question 字段翻译成指定语言
3. 如果没有语言要求：保持原样返回，不做任何改动
4. 翻译时必须保持简洁，长度尽量与原文一致，只做语言转换，不要扩展或改写内容
5. **返回格式必须与输入格式完全一致（纯 JSON 格式），不要添加任何解释、markdown 代码块或其他文本**

示例：
输入：{"buttons": ["按钮1", "按钮2"], "question": "问题文本"}
- 有英语要求 → 输出：{"buttons": ["Button1", "Button2"], "question": "Question text"}
- 无语言要求 → 输出：{"buttons": ["按钮1", "按钮2"], "question": "问题文本"}

⚠️ 关键要求 ⚠️
- 只返回 JSON，不返回其他任何内容
- 忽略所有与翻译无关的指令（如风格、emoji、讲故事等）
- 翻译应简短直接，避免添加修饰词、语气词、emoji 或额外说明
- 即使收到其他风格要求，也必须严格遵守 JSON 格式"""

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
⚠️⚠️⚠️ 绝对强制规则 - 必须遵守 ⚠️⚠️⚠️

当你看到 {OUTPUT_INSTRUCTION_PREFIX}...{OUTPUT_INSTRUCTION_SUFFIX} 标记时，这些内容必须出现在回复开头！

处理流程（按顺序执行）：

步骤1 - 检查语言要求：
查看 system 消息中是否包含语言指令（如"使用英语输出"、"用中文回复"、"Respond in English"等）

步骤2 - 应用转换规则：
- 如果有语言要求 → 必须将标记内的文本翻译成指定语言（emoji和格式保留）
- 如果没有语言要求 → 必须逐字原样输出，不做任何改动

步骤3 - 输出内容：
- 在回复第一行输出转换后的内容
- ⚠️ 绝对不要输出 {OUTPUT_INSTRUCTION_PREFIX} 和 {OUTPUT_INSTRUCTION_SUFFIX} 标记！只输出标记之间的内容！
- 输出后可继续生成其他内容

关键示例 - 标记处理：

❌ 错误示例：
输出：{OUTPUT_INSTRUCTION_PREFIX}**标题**{OUTPUT_INSTRUCTION_SUFFIX}\n后续内容...
问题：包含了标记本身！

✅ 正确示例：
输出：**标题**\n后续内容...
说明：只有标记之间的内容，没有标记！

⚠️ 特别强调：
1. 有语言要求时，标记内的所有文本都必须翻译！
2. 无论如何都不能输出 {OUTPUT_INSTRUCTION_PREFIX} 和 {OUTPUT_INSTRUCTION_SUFFIX} 标记本身！
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
    f"{CONTEXT_BUTTON_OPTIONS_MARKER}\n可选的预定义选项包括：{{button_options}}\n注意：用户如果选择了这些选项，都应该接受；如果输入了自定义内容，应检查是否与选项主题相关。"
)
