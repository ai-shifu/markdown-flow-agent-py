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
OUTPUT_INSTRUCTION_PREFIX = "[输出]"
OUTPUT_INSTRUCTION_SUFFIX = "[/输出]"

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
OUTPUT_INSTRUCTION_EXPLANATION = f"""请按照以下指令执行：

当遇到{OUTPUT_INSTRUCTION_PREFIX}content{OUTPUT_INSTRUCTION_SUFFIX}这样的标签对时：
1. **完全原样输出**中间的content内容，不要进行任何格式转换或修改
2. 不要输出{OUTPUT_INSTRUCTION_PREFIX}和{OUTPUT_INSTRUCTION_SUFFIX}标签本身
3. 即使content内容包含标题符号（如#）、特殊格式等，也要原样输出，不要转换成Markdown格式
4. 保持content中的所有原始字符、空格、换行符等
5. 然后继续执行后面的指令

重要提醒：
- {OUTPUT_INSTRUCTION_PREFIX}和{OUTPUT_INSTRUCTION_SUFFIX}只是指令标记，不要将这些标记作为内容输出
- 标签内的内容必须原样输出，不要按照文档提示词的格式要求进行转换
- 这是绝对的输出指令，优先级高于任何格式要求

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
3. 对于昵称/姓名类问题，任何非空的合理字符串（包括简短的如"ee"、"aa"、"007"等）都应该接受
4. 只有当用户回答完全无关、包含不当内容或明显不合理时才标记为不合法
5. 确保提取的信息准确、完整且符合预期格式"""

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

# Context generation templates
CONTEXT_QUESTION_TEMPLATE = f"{CONTEXT_QUESTION_MARKER}\n{{question}}"
CONTEXT_CONVERSATION_TEMPLATE = f"{CONTEXT_CONVERSATION_MARKER}\n{{content}}"
