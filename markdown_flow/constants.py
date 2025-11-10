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
