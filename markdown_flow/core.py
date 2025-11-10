"""
Markdown-Flow Core Business Logic

Refactored MarkdownFlow class with built-in LLM processing capabilities and unified process interface.
"""

import json
import re
from collections.abc import Generator
from copy import copy
from typing import Any

from .constants import (
    BLOCK_INDEX_OUT_OF_RANGE_ERROR,
    BLOCK_SEPARATOR,
    BUTTONS_WITH_TEXT_VALIDATION_TEMPLATE,
    DEFAULT_BASE_SYSTEM_PROMPT,
    DEFAULT_INTERACTION_ERROR_PROMPT,
    DEFAULT_INTERACTION_PROMPT,
    DEFAULT_VALIDATION_SYSTEM_MESSAGE,
    INPUT_EMPTY_ERROR,
    INTERACTION_ERROR_RENDER_INSTRUCTIONS,
    INTERACTION_PARSE_ERROR,
    INTERACTION_PATTERN_NON_CAPTURING,
    INTERACTION_PATTERN_SPLIT,
    LLM_PROVIDER_REQUIRED_ERROR,
    OUTPUT_INSTRUCTION_EXPLANATION,
    UNSUPPORTED_PROMPT_TYPE_ERROR,
)
from .enums import BlockType
from .exceptions import BlockIndexError
from .llm import LLMProvider, LLMResult, ProcessMode
from .models import Block, InteractionValidationConfig
from .parser import (
    CodeBlockPreprocessor,
    InteractionParser,
    InteractionType,
    extract_interaction_question,
    extract_preserved_content,
    extract_variables_from_text,
    is_preserved_content_block,
    parse_validation_response,
    process_output_instructions,
    replace_variables_in_text,
)


class MarkdownFlow:
    """
    Refactored Markdown-Flow core class.

    Integrates all document processing and LLM interaction capabilities with a unified process interface.
    """

    _llm_provider: LLMProvider | None
    _document: str
    _processed_document: str
    _document_prompt: str | None
    _interaction_prompt: str | None
    _interaction_error_prompt: str | None
    _max_context_length: int
    _blocks: list[Block] | None
    _interaction_configs: dict[int, InteractionValidationConfig]
    _model: str | None
    _temperature: float | None
    _preprocessor: CodeBlockPreprocessor

    def __init__(
        self,
        document: str,
        llm_provider: LLMProvider | None = None,
        base_system_prompt: str | None = None,
        document_prompt: str | None = None,
        interaction_prompt: str | None = None,
        interaction_error_prompt: str | None = None,
        max_context_length: int = 0,
    ):
        """
        Initialize MarkdownFlow instance.

        Args:
            document: Markdown document content
            llm_provider: LLM provider (required for COMPLETE and STREAM modes)
            base_system_prompt: MarkdownFlow base system prompt (framework-level, content blocks only)
            document_prompt: Document-level system prompt
            interaction_prompt: Interaction content rendering prompt
            interaction_error_prompt: Interaction error rendering prompt
            max_context_length: Maximum number of context messages to keep (0 = unlimited)
        """
        self._document = document
        self._llm_provider = llm_provider
        self._base_system_prompt = base_system_prompt or DEFAULT_BASE_SYSTEM_PROMPT
        self._document_prompt = document_prompt
        self._interaction_prompt = interaction_prompt or DEFAULT_INTERACTION_PROMPT
        self._interaction_error_prompt = interaction_error_prompt or DEFAULT_INTERACTION_ERROR_PROMPT
        self._max_context_length = max_context_length
        self._blocks = None
        self._interaction_configs: dict[int, InteractionValidationConfig] = {}
        self._model: str | None = None
        self._temperature: float | None = None

        # Preprocess document: extract code blocks and replace with placeholders
        # This is done once during initialization, similar to Go implementation
        self._preprocessor = CodeBlockPreprocessor()
        self._processed_document = self._preprocessor.extract_code_blocks(document)

    def set_llm_provider(self, provider: LLMProvider) -> None:
        """Set LLM provider."""
        self._llm_provider = provider

    def get_processed_document(self) -> str:
        """
        Get preprocessed document (for debugging and testing).

        Returns the document content after code blocks have been replaced with placeholders.

        Use cases:
            - Verify that code block preprocessing was executed correctly
            - Check placeholder format (__MDFLOW_CODE_BLOCK_N__)
            - Debug preprocessing stage issues

        Returns:
            Preprocessed document string
        """
        return self._processed_document

    def get_content_messages(
        self,
        block_index: int,
        variables: dict[str, str | list[str]] | None,
        context: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """
        Get content messages (for debugging and inspection).

        Builds and returns the complete message list that will be sent to LLM.

        Use cases:
            - Debug: View actual content sent to LLM
            - Verify: Check if code blocks are correctly restored
            - Inspect: Verify variable replacement and prompt building logic
            - Review: Confirm system/user message assembly results

        Args:
            block_index: Block index
            variables: Variable mapping
            context: Context message list

        Returns:
            List of message dictionaries
        """
        return self._build_content_messages(block_index, variables, context)

    def set_model(self, model: str) -> "MarkdownFlow":
        """
        Set model name for this instance.

        Args:
            model: Model name to use

        Returns:
            Self for method chaining
        """
        self._model = model
        return self

    def set_temperature(self, temperature: float) -> "MarkdownFlow":
        """
        Set temperature for this instance.

        Args:
            temperature: Temperature value (typically 0.0-2.0)

        Returns:
            Self for method chaining
        """
        self._temperature = temperature
        return self

    def get_model(self) -> str | None:
        """
        Get model name for this instance.

        Returns:
            Model name if set, None otherwise
        """
        return self._model

    def get_temperature(self) -> float | None:
        """
        Get temperature for this instance.

        Returns:
            Temperature value if set, None otherwise
        """
        return self._temperature

    def set_prompt(self, prompt_type: str, value: str | None) -> None:
        """
        Set prompt template.

        Args:
            prompt_type: Prompt type ('base_system', 'document', 'interaction', 'interaction_error')
            value: Prompt content
        """
        if prompt_type == "base_system":
            self._base_system_prompt = value or DEFAULT_BASE_SYSTEM_PROMPT
        elif prompt_type == "document":
            self._document_prompt = value
        elif prompt_type == "interaction":
            self._interaction_prompt = value or DEFAULT_INTERACTION_PROMPT
        elif prompt_type == "interaction_error":
            self._interaction_error_prompt = value or DEFAULT_INTERACTION_ERROR_PROMPT
        else:
            raise ValueError(UNSUPPORTED_PROMPT_TYPE_ERROR.format(prompt_type=prompt_type))

    def _truncate_context(
        self,
        context: list[dict[str, str]] | None,
    ) -> list[dict[str, str]] | None:
        """
        Filter and truncate context to specified maximum length.

        Processing steps:
        1. Filter out messages with empty content (empty string or whitespace only)
        2. Truncate to max_context_length if configured (0 = unlimited)

        Args:
            context: Original context list

        Returns:
            Filtered and truncated context. Returns None if no valid messages remain.
        """
        if not context:
            return None

        # Step 1: Filter out messages with empty or whitespace-only content
        filtered_context = [msg for msg in context if msg.get("content", "").strip()]

        # Return None if no valid messages remain after filtering
        if not filtered_context:
            return None

        # Step 2: Truncate to max_context_length if configured
        if self._max_context_length == 0:
            # No limit, return all filtered messages
            return filtered_context

        # Keep the most recent N messages
        if len(filtered_context) > self._max_context_length:
            return filtered_context[-self._max_context_length :]

        return filtered_context

    @property
    def document(self) -> str:
        """Get document content."""
        return self._document

    @property
    def block_count(self) -> int:
        """Get total number of blocks."""
        return len(self.get_all_blocks())

    def get_all_blocks(self) -> list[Block]:
        """Parse document and get all blocks."""
        if self._blocks is not None:
            return self._blocks

        # Parse the preprocessed document (code blocks already replaced with placeholders)
        # The preprocessing was done once during initialization
        segments = re.split(BLOCK_SEPARATOR, self._processed_document)
        final_blocks: list[Block] = []

        for segment in segments:
            # Use dedicated split pattern to avoid duplicate blocks from capturing groups
            parts = re.split(INTERACTION_PATTERN_SPLIT, segment)

            for part in parts:
                part = part.strip()
                if part:
                    # Use non-capturing pattern for matching
                    if re.match(INTERACTION_PATTERN_NON_CAPTURING, part):
                        block = Block(
                            content=part,
                            block_type=BlockType.INTERACTION,
                            index=len(final_blocks),
                        )
                        final_blocks.append(block)
                    else:
                        if is_preserved_content_block(part):  # type: ignore[unreachable]
                            block_type = BlockType.PRESERVED_CONTENT
                        else:
                            block_type = BlockType.CONTENT

                        block = Block(content=part, block_type=block_type, index=len(final_blocks))
                        final_blocks.append(block)

        self._blocks = final_blocks
        return self._blocks

    def get_block(self, index: int) -> Block:
        """Get block at specified index."""
        blocks = self.get_all_blocks()
        if index < 0 or index >= len(blocks):
            raise BlockIndexError(BLOCK_INDEX_OUT_OF_RANGE_ERROR.format(index=index, total=len(blocks)))
        return blocks[index]

    def extract_variables(self) -> list[str]:
        """Extract all variable names from the document."""
        return extract_variables_from_text(self._document)

    def set_interaction_validation_config(self, block_index: int, config: InteractionValidationConfig) -> None:
        """Set validation config for specified interaction block."""
        self._interaction_configs[block_index] = config

    def get_interaction_validation_config(self, block_index: int) -> InteractionValidationConfig | None:
        """Get validation config for specified interaction block."""
        return self._interaction_configs.get(block_index)

    # Core unified interface

    def process(
        self,
        block_index: int,
        mode: ProcessMode = ProcessMode.COMPLETE,
        context: list[dict[str, str]] | None = None,
        variables: dict[str, str | list[str]] | None = None,
        user_input: dict[str, list[str]] | None = None,
    ):
        """
        Unified block processing interface.

        Args:
            block_index: Block index
            mode: Processing mode
            context: Context message list
            variables: Variable mappings
            user_input: User input (for interaction blocks)

        Returns:
            LLMResult or Generator[LLMResult, None, None]
        """
        # Process base_system_prompt variable replacement
        if self._base_system_prompt:
            self._base_system_prompt = replace_variables_in_text(self._base_system_prompt, variables or {})

        # Process document_prompt variable replacement
        if self._document_prompt:
            self._document_prompt = replace_variables_in_text(self._document_prompt, variables or {})

        block = self.get_block(block_index)

        if block.block_type == BlockType.CONTENT:
            return self._process_content(block_index, mode, context, variables)

        if block.block_type == BlockType.INTERACTION:
            if user_input is None:
                # Render interaction content
                return self._process_interaction_render(block_index, mode, context, variables)
            # Process user input
            return self._process_interaction_input(block_index, user_input, mode, context, variables)

        if block.block_type == BlockType.PRESERVED_CONTENT:
            # Preserved content output as-is, no LLM call
            return self._process_preserved_content(block_index, variables)

        # Handle other types as content
        return self._process_content(block_index, mode, context, variables)

    # Internal processing methods

    def _process_content(
        self,
        block_index: int,
        mode: ProcessMode,
        context: list[dict[str, str]] | None,
        variables: dict[str, str | list[str]] | None,
    ):
        """Process content block."""
        # Truncate context to configured maximum length
        truncated_context = self._truncate_context(context)

        # Build messages with context
        messages = self._build_content_messages(block_index, variables, truncated_context)

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                raise ValueError(LLM_PROVIDER_REQUIRED_ERROR)

            content = self._llm_provider.complete(messages, model=self._model, temperature=self._temperature)
            return LLMResult(content=content, prompt=messages[-1]["content"])

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                raise ValueError(LLM_PROVIDER_REQUIRED_ERROR)

            def stream_generator():
                for chunk in self._llm_provider.stream(messages, model=self._model, temperature=self._temperature):  # type: ignore[attr-defined]
                    yield LLMResult(content=chunk, prompt=messages[-1]["content"])

            return stream_generator()

    def _process_preserved_content(self, block_index: int, variables: dict[str, str | list[str]] | None) -> LLMResult:
        """Process preserved content block, output as-is without LLM call."""
        block = self.get_block(block_index)

        # Extract preserved content (remove !=== markers)
        content = extract_preserved_content(block.content)

        # Replace variables
        content = replace_variables_in_text(content, variables or {})

        # Restore code blocks (replace placeholders with original code blocks)
        content = self._preprocessor.restore_code_blocks(content)

        return LLMResult(content=content)

    def _process_interaction_render(
        self,
        block_index: int,
        mode: ProcessMode,
        context: list[dict[str, str]] | None = None,
        variables: dict[str, str | list[str]] | None = None,
    ):
        """Process interaction content rendering."""
        block = self.get_block(block_index)

        # Apply variable replacement to interaction content
        processed_content = replace_variables_in_text(block.content, variables or {})

        # Create temporary block object to avoid modifying original data
        processed_block = copy(block)
        processed_block.content = processed_content

        # 提取可翻译内容（JSON 格式）
        translatable_json, interaction_info = self._extract_translatable_content(processed_block.content)
        if not interaction_info:
            # 解析失败，返回原始内容
            return LLMResult(
                content=processed_block.content,
                metadata={
                    "block_type": "interaction",
                    "block_index": block_index,
                },
            )

        # 如果没有可翻译内容，直接返回
        if not translatable_json or translatable_json == "{}":
            return LLMResult(
                content=processed_block.content,
                metadata={
                    "block_type": "interaction",
                    "block_index": block_index,
                },
            )

        # 构建翻译消息
        messages = self._build_translation_messages(translatable_json)

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                return LLMResult(
                    content=processed_block.content,
                    metadata={
                        "block_type": "interaction",
                        "block_index": block_index,
                    },
                )

            # 调用 LLM 进行翻译
            translated_json = self._llm_provider.complete(messages, model=self._model, temperature=self._temperature)

            # 使用翻译结果重构交互内容
            translated_content = self._reconstruct_with_translation(
                processed_block.content, translatable_json, translated_json, interaction_info
            )

            return LLMResult(
                content=translated_content,
                prompt=messages[-1]["content"],
                metadata={
                    "block_type": "interaction",
                    "block_index": block_index,
                    "original_content": translatable_json,
                    "translated_content": translated_json,
                },
            )

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                # 降级处理，返回处理后的内容
                def stream_generator():
                    yield LLMResult(
                        content=processed_block.content,
                        prompt=messages[-1]["content"],
                        metadata={
                            "block_type": "interaction",
                            "block_index": block_index,
                        },
                    )

                return stream_generator()

            # 有 LLM 提供者，收集完整响应后返回一次
            def stream_generator():
                full_response = ""
                for chunk in self._llm_provider.stream(messages, model=self._model, temperature=self._temperature):  # type: ignore[attr-defined]
                    full_response += chunk

                # 使用翻译结果重构交互内容
                translated_content = self._reconstruct_with_translation(
                    processed_block.content, translatable_json, full_response, interaction_info
                )

                # 一次性返回完整内容（不是增量）
                yield LLMResult(
                    content=translated_content,
                    prompt=messages[-1]["content"],
                    metadata={
                        "block_type": "interaction",
                        "block_index": block_index,
                        "original_content": translatable_json,
                        "translated_content": full_response,
                    },
                )

            return stream_generator()

    def _process_interaction_input(
        self,
        block_index: int,
        user_input: dict[str, list[str]],
        mode: ProcessMode,
        context: list[dict[str, str]] | None,
        variables: dict[str, str | list[str]] | None = None,
    ) -> LLMResult | Generator[LLMResult, None, None]:
        """Process interaction user input."""
        block = self.get_block(block_index)
        target_variable = block.variables[0] if block.variables else "user_input"

        # Basic validation
        if not user_input or not any(values for values in user_input.values()):
            error_msg = INPUT_EMPTY_ERROR
            return self._render_error(error_msg, mode, context)

        # Get the target variable value from user_input
        target_values = user_input.get(target_variable, [])

        # Apply variable replacement to interaction content
        processed_content = replace_variables_in_text(block.content, variables or {})

        # Parse interaction format using processed content
        parser = InteractionParser()
        parse_result = parser.parse(processed_content)

        if "error" in parse_result:
            error_msg = INTERACTION_PARSE_ERROR.format(error=parse_result["error"])
            return self._render_error(error_msg, mode, context)

        interaction_type = parse_result.get("type")

        # Process user input based on interaction type
        if interaction_type in [
            InteractionType.BUTTONS_WITH_TEXT,
            InteractionType.BUTTONS_MULTI_WITH_TEXT,
        ]:
            # Buttons with text input: smart validation (match buttons first, then LLM validate custom text)
            buttons = parse_result.get("buttons", [])

            # Step 1: Match button values
            matched_values, unmatched_values = self._match_button_values(buttons, target_values)

            # Step 2: If there are unmatched values (custom text), validate with LLM
            if unmatched_values:
                # Create user_input for LLM validation (only custom text)
                custom_input = {target_variable: unmatched_values}

                validation_result = self._process_llm_validation(
                    block_index=block_index,
                    user_input=custom_input,
                    target_variable=target_variable,
                    mode=mode,
                    context=context,
                )

                # Handle validation result based on mode
                if mode == ProcessMode.COMPLETE:
                    # Check if validation passed
                    if isinstance(validation_result, LLMResult) and validation_result.variables:
                        validated_values = validation_result.variables.get(target_variable, [])
                        # Merge matched button values + validated custom text
                        all_values = matched_values + validated_values
                        return LLMResult(
                            content="",
                            variables={target_variable: all_values},
                            metadata={
                                "interaction_type": str(interaction_type),
                                "matched_button_values": matched_values,
                                "validated_custom_values": validated_values,
                            },
                        )
                    # Validation failed, return error
                    return validation_result

                if mode == ProcessMode.STREAM:
                    # For stream mode, collect validation result
                    def stream_merge_generator():
                        # Consume the validation stream
                        for result in validation_result:  # type: ignore[attr-defined]
                            if isinstance(result, LLMResult) and result.variables:
                                validated_values = result.variables.get(target_variable, [])
                                all_values = matched_values + validated_values
                                yield LLMResult(
                                    content="",
                                    variables={target_variable: all_values},
                                    metadata={
                                        "interaction_type": str(interaction_type),
                                        "matched_button_values": matched_values,
                                        "validated_custom_values": validated_values,
                                    },
                                )
                            else:
                                # Validation failed
                                yield result

                    return stream_merge_generator()
            else:
                # All values matched buttons, return directly
                return LLMResult(
                    content="",
                    variables={target_variable: matched_values},
                    metadata={
                        "interaction_type": str(interaction_type),
                        "all_matched_buttons": True,
                    },
                )

        if interaction_type in [
            InteractionType.BUTTONS_ONLY,
            InteractionType.BUTTONS_MULTI_SELECT,
        ]:
            # Pure button types: only basic button validation (no LLM)
            return self._process_button_validation(
                parse_result,
                target_values,
                target_variable,
                mode,
                interaction_type,
                context,
            )

        if interaction_type == InteractionType.NON_ASSIGNMENT_BUTTON:
            # Non-assignment buttons: ?[Continue] or ?[Continue|Cancel]
            # These buttons don't assign variables, any input completes the interaction
            return LLMResult(
                content="",  # Empty content indicates interaction complete
                variables={},  # Non-assignment buttons don't set variables
                metadata={
                    "interaction_type": "non_assignment_button",
                    "user_input": user_input,
                },
            )

        # Text-only input type: ?[%{{sys_user_nickname}}...question]
        # Use LLM validation to check if input is relevant to the question
        if target_values:
            return self._process_llm_validation(
                block_index=block_index,
                user_input=user_input,
                target_variable=target_variable,
                mode=mode,
                context=context,
            )
        error_msg = f"No input provided for variable '{target_variable}'"
        return self._render_error(error_msg, mode, context)

    def _match_button_values(
        self,
        buttons: list[dict[str, str]],
        target_values: list[str],
    ) -> tuple[list[str], list[str]]:
        """
        Match user input values against button options.

        Args:
            buttons: List of button dictionaries with 'display' and 'value' keys
            target_values: User input values to match

        Returns:
            Tuple of (matched_values, unmatched_values)
            - matched_values: Values that match button options (using button value)
            - unmatched_values: Values that don't match any button
        """
        matched_values = []
        unmatched_values = []

        for value in target_values:
            matched = False
            for button in buttons:
                if value in [button["display"], button["value"]]:
                    matched_values.append(button["value"])  # Use button value
                    matched = True
                    break

            if not matched:
                unmatched_values.append(value)

        return matched_values, unmatched_values

    def _process_button_validation(
        self,
        parse_result: dict[str, Any],
        target_values: list[str],
        target_variable: str,
        mode: ProcessMode,
        interaction_type: InteractionType,
        context: list[dict[str, str]] | None = None,
    ) -> LLMResult | Generator[LLMResult, None, None]:
        """
        Simplified button validation with new input format.

        Args:
            parse_result: InteractionParser result containing buttons list
            target_values: User input values for the target variable
            target_variable: Target variable name
            mode: Processing mode
            interaction_type: Type of interaction
            context: Conversation history context (optional)
        """
        buttons = parse_result.get("buttons", [])
        is_multi_select = interaction_type in [
            InteractionType.BUTTONS_MULTI_SELECT,
            InteractionType.BUTTONS_MULTI_WITH_TEXT,
        ]
        allow_text_input = interaction_type in [
            InteractionType.BUTTONS_WITH_TEXT,
            InteractionType.BUTTONS_MULTI_WITH_TEXT,
        ]

        if not target_values:
            if allow_text_input:
                # Allow empty input for buttons+text mode
                return LLMResult(
                    content="",
                    variables={target_variable: []},
                    metadata={
                        "interaction_type": str(interaction_type),
                        "empty_input": True,
                    },
                )
            # Pure button mode requires input
            button_displays = [btn["display"] for btn in buttons]
            error_msg = f"Please select from: {', '.join(button_displays)}"
            return self._render_error(error_msg, mode, context)

        # Validate input values against available buttons
        valid_values = []
        invalid_values = []

        for value in target_values:
            matched = False
            for button in buttons:
                if value in [button["display"], button["value"]]:
                    valid_values.append(button["value"])  # Use actual value
                    matched = True
                    break

            if not matched:
                if allow_text_input:
                    # Allow custom text in buttons+text mode
                    valid_values.append(value)
                else:
                    invalid_values.append(value)

        # Check for validation errors
        if invalid_values and not allow_text_input:
            button_displays = [btn["display"] for btn in buttons]
            error_msg = f"Invalid options: {', '.join(invalid_values)}. Please select from: {', '.join(button_displays)}"
            return self._render_error(error_msg, mode, context)

        # Success: return validated values
        return LLMResult(
            content="",
            variables={target_variable: valid_values},
            metadata={
                "interaction_type": str(interaction_type),
                "is_multi_select": is_multi_select,
                "valid_values": valid_values,
                "invalid_values": invalid_values,
                "total_input_count": len(target_values),
            },
        )

    def _process_llm_validation(
        self,
        block_index: int,
        user_input: dict[str, list[str]],
        target_variable: str,
        mode: ProcessMode,
        context: list[dict[str, str]] | None = None,
    ) -> LLMResult | Generator[LLMResult, None, None]:
        """Process LLM validation."""
        # Build validation messages
        messages = self._build_validation_messages(block_index, user_input, target_variable, context)

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                # Fallback processing, return variables directly
                return LLMResult(content="", variables=user_input)  # type: ignore[arg-type]

            llm_response = self._llm_provider.complete(messages, model=self._model, temperature=self._temperature)

            # Parse validation response and convert to LLMResult
            # Use joined target values for fallback; avoids JSON string injection
            orig_input_str = ", ".join(user_input.get(target_variable, []))
            parsed_result = parse_validation_response(llm_response, orig_input_str, target_variable)
            return LLMResult(content=parsed_result["content"], variables=parsed_result["variables"])

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                return LLMResult(content="", variables=user_input)  # type: ignore[arg-type]

            def stream_generator():
                full_response = ""
                for chunk in self._llm_provider.stream(messages, model=self._model, temperature=self._temperature):  # type: ignore[attr-defined]
                    full_response += chunk

                # Parse complete response and convert to LLMResult
                # Use joined target values for fallback; avoids JSON string injection
                orig_input_str = ", ".join(user_input.get(target_variable, []))
                parsed_result = parse_validation_response(full_response, orig_input_str, target_variable)
                yield LLMResult(
                    content=parsed_result["content"],
                    variables=parsed_result["variables"],
                )

            return stream_generator()

    def _process_llm_validation_with_options(
        self,
        block_index: int,
        user_input: dict[str, list[str]],
        target_variable: str,
        options: list[str],
        question: str,
        mode: ProcessMode,
    ) -> LLMResult | Generator[LLMResult, None, None]:
        """Process LLM validation with button options (third case)."""
        # Build special validation messages containing button option information
        messages = self._build_validation_messages_with_options(user_input, target_variable, options, question)

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                # Fallback processing, return variables directly
                return LLMResult(content="", variables=user_input)  # type: ignore[arg-type]

            llm_response = self._llm_provider.complete(messages, model=self._model, temperature=self._temperature)

            # Parse validation response and convert to LLMResult
            # Use joined target values for fallback; avoids JSON string injection
            orig_input_str = ", ".join(user_input.get(target_variable, []))
            parsed_result = parse_validation_response(llm_response, orig_input_str, target_variable)
            return LLMResult(content=parsed_result["content"], variables=parsed_result["variables"])

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                return LLMResult(content="", variables=user_input)  # type: ignore[arg-type]

            def stream_generator():
                full_response = ""
                for chunk in self._llm_provider.stream(messages, model=self._model, temperature=self._temperature):  # type: ignore[attr-defined]
                    full_response += chunk
                    # For validation scenario, don't output chunks in real-time, only final result

                # Process final response
                # Use joined target values for fallback; avoids JSON string injection
                orig_input_str = ", ".join(user_input.get(target_variable, []))
                parsed_result = parse_validation_response(full_response, orig_input_str, target_variable)

                # Return only final parsing result
                yield LLMResult(
                    content=parsed_result["content"],
                    variables=parsed_result["variables"],
                )

            return stream_generator()

    def _render_error(
        self,
        error_message: str,
        mode: ProcessMode,
        context: list[dict[str, str]] | None = None,
    ) -> LLMResult | Generator[LLMResult, None, None]:
        """Render user-friendly error message."""
        # Truncate context to configured maximum length
        truncated_context = self._truncate_context(context)

        # Build error messages with context
        messages = self._build_error_render_messages(error_message, truncated_context)

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                return LLMResult(content=error_message)  # Fallback processing

            friendly_error = self._llm_provider.complete(messages, model=self._model, temperature=self._temperature)
            return LLMResult(content=friendly_error, prompt=messages[-1]["content"])

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                return LLMResult(content=error_message)

            def stream_generator():
                for chunk in self._llm_provider.stream(messages, model=self._model, temperature=self._temperature):  # type: ignore[attr-defined]
                    yield LLMResult(content=chunk, prompt=messages[-1]["content"])

            return stream_generator()

    # Message building helpers

    def _build_content_messages(
        self,
        block_index: int,
        variables: dict[str, str | list[str]] | None,
        context: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Build content block messages."""
        block = self.get_block(block_index)
        block_content = block.content

        # Process output instructions and detect if preserved content exists
        # Returns: (processed_content, has_preserved_content)
        block_content, has_preserved_content = process_output_instructions(block_content)

        # Replace variables
        block_content = replace_variables_in_text(block_content, variables or {})

        # Restore code blocks (让 LLM 看到真实的代码块内容)
        # Code block preprocessing is to prevent the parser from misinterpreting
        # MarkdownFlow syntax inside code blocks, but the LLM needs to see
        # the real content to correctly understand and generate responses
        block_content = self._preprocessor.restore_code_blocks(block_content)

        # Build message array
        messages = []

        # Build system message with XML tags
        # Priority order: preserve_or_translate_instruction > base_system > document_prompt
        system_parts = []

        # 1. Output instruction (highest priority - if preserved content exists)
        # Note: OUTPUT_INSTRUCTION_EXPLANATION already contains <preserve_or_translate_instruction> tags
        if has_preserved_content:
            system_parts.append(OUTPUT_INSTRUCTION_EXPLANATION.strip())

        # 2. Base system prompt (if exists and non-empty)
        if self._base_system_prompt:
            system_parts.append(f"<base_system>\n{self._base_system_prompt}\n</base_system>")

        # 3. Document prompt (if exists and non-empty)
        if self._document_prompt:
            system_parts.append(f"<document_prompt>\n{self._document_prompt}\n</document_prompt>")

        # Combine all parts and add as system message
        if system_parts:
            system_msg = "\n\n".join(system_parts)
            messages.append({"role": "system", "content": system_msg})

        # Add conversation history context if provided
        # Context is inserted after system message and before current user message
        truncated_context = self._truncate_context(context)
        if truncated_context:
            messages.extend(truncated_context)

        # Add processed content as user message (as instruction to LLM)
        messages.append({"role": "user", "content": block_content})

        return messages

    def _extract_translatable_content(
        self, interaction_content: str
    ) -> tuple[str, dict[str, Any] | None]:
        """提取交互内容中需要翻译的部分为 JSON 格式

        Args:
            interaction_content: 交互内容字符串

        Returns:
            tuple: (JSON 字符串, InteractionInfo 字典)
        """
        # 解析交互内容
        interaction_parser = InteractionParser()
        interaction_info = interaction_parser.parse(interaction_content)
        if not interaction_info:
            return "{}", None

        translatable = {}

        # 提取按钮的 Display 文本
        if interaction_info.get("buttons"):
            button_texts = [btn["display"] for btn in interaction_info["buttons"]]
            translatable["buttons"] = button_texts

        # 提取问题文本
        if interaction_info.get("question"):
            translatable["question"] = interaction_info["question"]

        # 转换为 JSON
        import json
        json_str = json.dumps(translatable, ensure_ascii=False)

        return json_str, interaction_info

    def _build_translation_messages(
        self, translatable_json: str
    ) -> list[dict[str, str]]:
        """构建翻译用的消息列表

        Args:
            translatable_json: 可翻译内容的 JSON 字符串

        Returns:
            list: 消息列表
        """
        messages = []

        # 构建 system message：交互翻译提示词 + 文档提示词（XML 格式）
        # interaction_prompt: 定义翻译规则和 JSON 格式要求（包含 <interaction_translation_rules> 标签）
        # document_prompt: 提供语言指令（如"使用英语输出"），包装在 <document_context> 标签中供 LLM 检测
        system_content = self._interaction_prompt
        if self._document_prompt:
            # 将文档提示词包装在 <document_context> 标签中
            system_content = f"{self._interaction_prompt}\n\n<document_context>\n{self._document_prompt}\n</document_context>"

        messages.append({"role": "system", "content": system_content})

        # 添加可翻译内容作为 user message
        messages.append({"role": "user", "content": translatable_json})

        return messages

    def _reconstruct_with_translation(
        self,
        original_content: str,
        original_json: str,
        translated_json: str,
        interaction_info: dict[str, Any],
    ) -> str:
        """使用翻译后的内容重构交互块

        Args:
            original_content: 原始交互内容
            original_json: 原始的可翻译 JSON（翻译前）
            translated_json: 翻译后的 JSON 字符串
            interaction_info: 交互信息字典

        Returns:
            str: 重构后的交互内容
        """
        import json

        # 解析原始 JSON
        try:
            original = json.loads(original_json)
        except json.JSONDecodeError:
            return original_content

        # 解析翻译后的 JSON
        try:
            translated = json.loads(translated_json)
        except json.JSONDecodeError:
            return original_content

        reconstructed = original_content

        # 替换按钮 Display 文本（智能处理 Value）
        if "buttons" in translated and interaction_info.get("buttons"):
            for i, button in enumerate(interaction_info["buttons"]):
                if i < len(translated["buttons"]):
                    old_display = button["display"]
                    new_display = translated["buttons"][i]

                    # 检测是否发生了翻译
                    translation_happened = False
                    if "buttons" in original and i < len(original["buttons"]):
                        if original["buttons"][i] != new_display:
                            translation_happened = True

                    # 如果有 Value 分离（display//value 格式），保留 value
                    if button["display"] != button["value"]:
                        # 已有 value 分离，按原逻辑处理
                        # 替换格式：oldDisplay//value -> newDisplay//value
                        old_pattern = f"{old_display}//{button['value']}"
                        new_pattern = f"{new_display}//{button['value']}"
                        reconstructed = reconstructed.replace(old_pattern, new_pattern, 1)
                    elif translation_happened:
                        # 没有 value 分离，但发生了翻译
                        # 自动添加 value：翻译后//原始
                        old_pattern = old_display
                        new_pattern = f"{new_display}//{old_display}"
                        reconstructed = reconstructed.replace(old_pattern, new_pattern, 1)
                    else:
                        # 没有翻译，保持原样
                        reconstructed = reconstructed.replace(old_display, new_display, 1)

        # 替换问题文本
        if "question" in translated and interaction_info.get("question"):
            old_question = interaction_info["question"]
            new_question = translated["question"]
            reconstructed = reconstructed.replace(f"...{old_question}", f"...{new_question}", 1)

        return reconstructed

    def _build_validation_messages(
        self,
        block_index: int,
        user_input: dict[str, list[str]],
        target_variable: str,
        context: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Build validation messages."""
        block = self.get_block(block_index)
        config = self.get_interaction_validation_config(block_index)

        # Truncate context to configured maximum length
        truncated_context = self._truncate_context(context)

        if config and config.validation_template:
            # Use custom validation template
            validation_prompt = config.validation_template
            user_input_str = json.dumps(user_input, ensure_ascii=False)
            validation_prompt = validation_prompt.replace("{sys_user_input}", user_input_str)
            validation_prompt = validation_prompt.replace("{block_content}", block.content)
            validation_prompt = validation_prompt.replace("{target_variable}", target_variable)
            system_message = DEFAULT_VALIDATION_SYSTEM_MESSAGE
        else:
            # Use smart default validation template
            from .parser import (
                InteractionParser,
                extract_interaction_question,
                generate_smart_validation_template,
            )

            # Extract interaction question
            interaction_question = extract_interaction_question(block.content)

            # Parse interaction to extract button information
            parser = InteractionParser()
            parse_result = parser.parse(block.content)
            buttons = parse_result.get("buttons") if "buttons" in parse_result else None

            # Generate smart validation template with context and buttons
            validation_template = generate_smart_validation_template(
                target_variable,
                context=truncated_context,
                interaction_question=interaction_question,
                buttons=buttons,
            )

            # Replace template variables
            user_input_str = json.dumps(user_input, ensure_ascii=False)
            validation_prompt = validation_template.replace("{sys_user_input}", user_input_str)
            validation_prompt = validation_prompt.replace("{block_content}", block.content)
            validation_prompt = validation_prompt.replace("{target_variable}", target_variable)
            system_message = DEFAULT_VALIDATION_SYSTEM_MESSAGE

        messages = []

        messages.append({"role": "system", "content": system_message})

        # Add conversation history context if provided (only if not using custom template)
        if truncated_context and not (config and config.validation_template):
            messages.extend(truncated_context)

        messages.append({"role": "user", "content": validation_prompt})

        return messages

    def _build_validation_messages_with_options(
        self,
        user_input: dict[str, list[str]],
        target_variable: str,
        options: list[str],
        question: str,
    ) -> list[dict[str, str]]:
        """Build validation messages with button options (third case)."""
        # Use validation template from constants
        user_input_str = json.dumps(user_input, ensure_ascii=False)
        validation_prompt = BUTTONS_WITH_TEXT_VALIDATION_TEMPLATE.format(
            question=question,
            options=", ".join(options),
            user_input=user_input_str,
            target_variable=target_variable,
        )

        messages = []
        if self._document_prompt:
            messages.append({"role": "system", "content": self._document_prompt})

        messages.append({"role": "system", "content": DEFAULT_VALIDATION_SYSTEM_MESSAGE})
        messages.append({"role": "user", "content": validation_prompt})

        return messages

    def _build_error_render_messages(
        self,
        error_message: str,
        context: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Build error rendering messages."""
        render_prompt = f"""{self._interaction_error_prompt}

Original Error: {error_message}

{INTERACTION_ERROR_RENDER_INSTRUCTIONS}"""

        messages = []
        if self._document_prompt:
            messages.append({"role": "system", "content": self._document_prompt})

        messages.append({"role": "system", "content": render_prompt})

        # Add conversation history context if provided
        truncated_context = self._truncate_context(context)
        if truncated_context:
            messages.extend(truncated_context)

        messages.append({"role": "user", "content": error_message})

        return messages

    # Helper methods
