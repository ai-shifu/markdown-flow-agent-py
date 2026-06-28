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
OUTPUT_INSTRUCTION_PREFIX = "<原样输出>"
OUTPUT_INSTRUCTION_SUFFIX = "</原样输出>"

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
INTERACTION_PROMPT_BASE = """# JSON Interaction Translation Task

You will receive a JSON object containing interaction elements (`buttons` and/or `question` fields), and you need to translate the text in it into the target language.

## Output Format Requirements

- Return pure JSON only; do not add any explanations or Markdown code blocks
- The JSON structure must be exactly the same as the input: do not add or remove fields, do not modify key names, and do not change the order
- Preserve the original spaces, punctuation, and quotation marks"""

INTERACTION_PROMPT_NO_TRANSLATION = """
## Processing Rules

Return the input JSON exactly as-is, character for character:

- Do not translate any text
- Do not modify any formatting
- Do not add any content (such as display//value separation)
- Do not delete any content
- Do not change any order

## Example

- Input `{"buttons": ["Product Manager", "Developer"], "question": "Other role"}`
- Output `{"buttons": ["Product Manager", "Developer"], "question": "Other role"}`"""

INTERACTION_PROMPT_WITH_TRANSLATION = """
## Translation Rules

- Translate the text in `buttons` and `question` into the target language
- Translate only the display text (the Display part); do not change the JSON structure
- If `display//value` separation exists (for example `Yes//1`), translate only the Display part before `//` and keep value unchanged
- Use the target language 100%; language mixing is not allowed. Translate all non-target-language words before outputting
- If a text segment's original language is already the same as the target language, return that text unchanged (for example, when the target language is English and the original text is also English, do not rewrite it)

## Examples

- Input `{"buttons": ["Yes//1", "No//0"]}`, target language Spanish -> `{"buttons": ["Sí//1", "No//0"]}`
- Input `{"buttons": ["Débutant", "Avancé"], "question": "Autre"}`, target language English -> `{"buttons": ["Beginner", "Advanced"], "question": "Other"}`"""

# Default: use no translation version (backward compatible)
DEFAULT_INTERACTION_PROMPT = INTERACTION_PROMPT_BASE + "\n" + INTERACTION_PROMPT_NO_TRANSLATION

# Interaction error prompt templates
DEFAULT_INTERACTION_ERROR_PROMPT = "Please rewrite the following error message to be friendlier and more personalized, helping the user understand the problem and providing constructive guidance:"

# Interaction error rendering instructions
INTERACTION_ERROR_RENDER_INSTRUCTIONS = """
Return only the friendly error message; do not include any other format or explanation."""

# Standard validation response status
VALIDATION_RESPONSE_OK = "ok"
VALIDATION_RESPONSE_ILLEGAL = "illegal"

# Validation task template (Modular design)
VALIDATION_TASK_BASE = """You are a string validation program, not a conversational assistant.

Your only task: check the input according to the following rules and output exactly one of these JSON objects:
{{"result": "ok", "parse_vars": {{"{target_variable}": "<exact user input>"}}}} or {{"result": "illegal", "reason": "<reason>"}}

It is strictly forbidden to output any natural-language explanation."""

VALIDATION_TASK_WITH_LANGUAGE = """

# reason Language Rule
reason must use the language specified in the <output_language_override> tag."""

VALIDATION_TASK_NO_LANGUAGE = """

# reason Language Rule
reason uses the primary language of the user input or question (auto-detect)."""

# Default: use no language version (backward compatible)
VALIDATION_TASK_TEMPLATE = VALIDATION_TASK_BASE + VALIDATION_TASK_NO_LANGUAGE

# Validation requirements template (extremely lenient version)
VALIDATION_REQUIREMENTS_TEMPLATE = """# Validation Algorithm (execute in order)

Step 1: Empty-value check (string length check)

Check rule: input.trim().length == 0 ?
- YES -> empty
- NO  -> non-empty

Important: as long as the number of characters after trimming leading and trailing spaces is > 0, it is non-empty.
Important: do not judge semantics. All visible characters (a, 1, @, CJK characters) count toward length.
Examples:
  - ""      -> length 0 -> empty
  - "  "    -> length 0 -> empty
  - "aa"    -> length 2 -> non-empty
  - "@_@"   -> length 3 -> non-empty
  - "abc"   -> length 3 -> non-empty

Step 2: Vague-answer check

Reject these vague-answer intents and their equivalents in the input language: "I don't know", "I'm not sure", "No/none", "I won't tell you"

Step 3: Religious/political check

Reject only explicit religious or political position statements (religious doctrines, political slogans, etc.).
Place names, regions, etc. (Beijing, Shanghai, etc.) and ordinary vocabulary do not count.

Step 4: Output result (the reason language follows the language requirement in <document_context>)

Pseudocode logic:
  if empty:
      output {{"result": "illegal", "reason": "input is empty (or its translation into the corresponding language)"}}
  else if vague answer:
      output {{"result": "illegal", "reason": "please provide specific content (or its translation into the corresponding language)"}}
  else if religious/political:
      output {{"result": "illegal", "reason": "contains sensitive content (or its translation into the corresponding language)"}}
  else:
      output {{"result": "ok", "parse_vars": {{"{target_variable}": "<exact user input>"}}}}

Extremely important:
- len(input after trimming leading and trailing spaces) > 0 -> it must be regarded as non-empty
- Symbols, numbers, brand names, place names, etc. are neither "empty" nor "invalid"
- Pass by default; reject only when there is an explicit violation
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
CONTEXT_QUESTION_MARKER = "# Related Question"
CONTEXT_CONVERSATION_MARKER = "# Conversation Context"
CONTEXT_BUTTON_OPTIONS_MARKER = "## Predefined Options"

# Context generation templates
CONTEXT_QUESTION_TEMPLATE = f"{CONTEXT_QUESTION_MARKER}\n{{question}}"
CONTEXT_CONVERSATION_TEMPLATE = f"{CONTEXT_CONVERSATION_MARKER}\n{{content}}"
CONTEXT_BUTTON_OPTIONS_TEMPLATE = (
    f"{CONTEXT_BUTTON_OPTIONS_MARKER}\n"
    "Available predefined options include: {button_options}\n"
    "Note: If the user selected one of these options, it should be accepted; if the user entered custom content, accept it as long as it is a reasonable answer to the question."
)

# Next interaction context prompt templates
NEXT_INTERACTION_CONTEXT_INTRO = (
    "The next interaction will appear immediately after this content. When generating the current content, connect to it naturally. "
    "You may briefly restate, explain, or set up the available choices so the user understands what they will decide next, but do not output the interaction syntax or answer on the user's behalf."
)
NEXT_INTERACTION_TEXT_INPUT_TEMPLATE = "The next interaction asks the user to answer in text: {question}"
NEXT_INTERACTION_SINGLE_CHOICE_TEMPLATE = "The next interaction is a single-choice question. The user will choose one option from: {options}"
NEXT_INTERACTION_MULTIPLE_CHOICE_TEMPLATE = "The next interaction is a multiple-choice question. The user can choose one or more options from: {options}"
NEXT_INTERACTION_SINGLE_CHOICE_WITH_TEXT_INTRO = "The next interaction is a single-choice question with an optional custom text answer."
NEXT_INTERACTION_MULTIPLE_CHOICE_WITH_TEXT_INTRO = "The next interaction is a multiple-choice question with an optional custom text answer."
NEXT_INTERACTION_PREDEFINED_OPTIONS_TEMPLATE = "The predefined options are: {options}."
NEXT_INTERACTION_CUSTOM_TEXT_PROMPT_TEMPLATE = "The custom text prompt is: {question}"
