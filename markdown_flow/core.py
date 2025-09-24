"""
Markdown-Flow Core Business Logic

Refactored MarkdownFlow class with built-in LLM processing capabilities and unified process interface.
"""

import json
import re
from collections.abc import AsyncGenerator
from copy import copy
from typing import Any

from .constants import (
    BLOCK_INDEX_OUT_OF_RANGE_ERROR,
    BLOCK_SEPARATOR,
    BUTTONS_WITH_TEXT_VALIDATION_TEMPLATE,
    COMPILED_BRACKETS_CLEANUP_REGEX,
    COMPILED_INTERACTION_CONTENT_RECONSTRUCT_REGEX,
    COMPILED_VARIABLE_REFERENCE_CLEANUP_REGEX,
    COMPILED_WHITESPACE_CLEANUP_REGEX,
    DEFAULT_INTERACTION_ERROR_PROMPT,
    DEFAULT_INTERACTION_PROMPT,
    DEFAULT_VALIDATION_SYSTEM_MESSAGE,
    INPUT_EMPTY_ERROR,
    INTERACTION_ERROR_RENDER_INSTRUCTIONS,
    INTERACTION_PARSE_ERROR,
    INTERACTION_PATTERN_NON_CAPTURING,
    INTERACTION_PATTERN_SPLIT,
    INTERACTION_RENDER_INSTRUCTIONS,
    LLM_PROVIDER_REQUIRED_ERROR,
    UNSUPPORTED_PROMPT_TYPE_ERROR,
)
from .enums import BlockType
from .exceptions import BlockIndexError
from .llm import LLMProvider, LLMResult, ProcessMode
from .models import Block, InteractionValidationConfig
from .utils import (
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
    _document_prompt: str | None
    _interaction_prompt: str | None
    _interaction_error_prompt: str | None
    _blocks: list[Block] | None
    _interaction_configs: dict[int, InteractionValidationConfig]

    def __init__(
        self,
        document: str,
        llm_provider: LLMProvider | None = None,
        document_prompt: str | None = None,
        interaction_prompt: str | None = None,
        interaction_error_prompt: str | None = None,
        enable_dynamic_interaction: bool = False,
    ):
        """
        Initialize MarkdownFlow instance.

        Args:
            document: Markdown document content
            llm_provider: LLM provider, if None only PROMPT_ONLY mode is available
            document_prompt: Document-level system prompt
            interaction_prompt: Interaction content rendering prompt
            interaction_error_prompt: Interaction error rendering prompt
            enable_dynamic_interaction: Enable dynamic content to interaction conversion
        """
        self._document = document
        self._llm_provider = llm_provider
        self._document_prompt = document_prompt
        self._interaction_prompt = interaction_prompt or DEFAULT_INTERACTION_PROMPT
        self._interaction_error_prompt = interaction_error_prompt or DEFAULT_INTERACTION_ERROR_PROMPT
        self._enable_dynamic_interaction = enable_dynamic_interaction
        self._blocks = None
        self._interaction_configs: dict[int, InteractionValidationConfig] = {}

    def set_llm_provider(self, provider: LLMProvider) -> None:
        """Set LLM provider."""
        self._llm_provider = provider

    def set_prompt(self, prompt_type: str, value: str | None) -> None:
        """
        Set prompt template.

        Args:
            prompt_type: Prompt type ('document', 'interaction', 'interaction_error')
            value: Prompt content
        """
        if prompt_type == "document":
            self._document_prompt = value
        elif prompt_type == "interaction":
            self._interaction_prompt = value or DEFAULT_INTERACTION_PROMPT
        elif prompt_type == "interaction_error":
            self._interaction_error_prompt = value or DEFAULT_INTERACTION_ERROR_PROMPT
        else:
            raise ValueError(UNSUPPORTED_PROMPT_TYPE_ERROR.format(prompt_type=prompt_type))

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

        content = self._document.strip()
        segments = re.split(BLOCK_SEPARATOR, content)
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

    async def process(
        self,
        block_index: int,
        mode: ProcessMode = ProcessMode.COMPLETE,
        context: list[dict[str, str]] | None = None,
        variables: dict[str, str | list[str]] | None = None,
        user_input: dict[str, list[str]] | None = None,
        dynamic_interaction_format: str | None = None,
    ) -> LLMResult | AsyncGenerator[LLMResult, None]:
        """
        Unified block processing interface.

        Args:
            block_index: Block index
            mode: Processing mode
            context: Context message list
            variables: Variable mappings
            user_input: User input (for interaction blocks)
            dynamic_interaction_format: Dynamic interaction format for validation

        Returns:
            LLMResult or AsyncGenerator[LLMResult, None]
        """
        # Process document_prompt variable replacement
        if self._document_prompt:
            self._document_prompt = replace_variables_in_text(self._document_prompt, variables or {})

        block = self.get_block(block_index)

        if block.block_type == BlockType.CONTENT:
            # Check if this is dynamic interaction validation
            if dynamic_interaction_format and user_input:
                return await self._process_dynamic_interaction_validation(
                    block_index, dynamic_interaction_format, user_input, mode, context, variables
                )
            # Normal content processing (possibly with dynamic conversion)
            return await self._process_content(block_index, mode, context, variables)

        if block.block_type == BlockType.INTERACTION:
            if user_input is None:
                # Render interaction content
                return await self._process_interaction_render(block_index, mode, variables)
            # Process user input
            return await self._process_interaction_input(block_index, user_input, mode, context, variables)

        if block.block_type == BlockType.PRESERVED_CONTENT:
            # Preserved content output as-is, no LLM call
            return await self._process_preserved_content(block_index, variables)

        # Handle other types as content
        return await self._process_content(block_index, mode, context, variables)

    # Internal processing methods

    async def _process_content(
        self,
        block_index: int,
        mode: ProcessMode,
        context: list[dict[str, str]] | None,
        variables: dict[str, str | list[str]] | None,
    ) -> LLMResult | AsyncGenerator[LLMResult, None]:
        """Process content block."""

        # Check if dynamic interaction is enabled and should be attempted
        if self._enable_dynamic_interaction and mode != ProcessMode.PROMPT_ONLY:
            return await self._process_with_dynamic_check(block_index, mode, context, variables)

        # Original logic: Build messages
        messages = self._build_content_messages(block_index, variables)

        if mode == ProcessMode.PROMPT_ONLY:
            return LLMResult(prompt=messages[-1]["content"], metadata={"messages": messages})

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                raise ValueError(LLM_PROVIDER_REQUIRED_ERROR)

            content = await self._llm_provider.complete(messages)
            return LLMResult(content=content, prompt=messages[-1]["content"])

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                raise ValueError(LLM_PROVIDER_REQUIRED_ERROR)

            async def stream_generator():
                async for chunk in self._llm_provider.stream(messages):  # type: ignore[attr-defined]
                    yield LLMResult(content=chunk, prompt=messages[-1]["content"])

            return stream_generator()

    async def _process_preserved_content(self, block_index: int, variables: dict[str, str | list[str]] | None) -> LLMResult:
        """Process preserved content block, output as-is without LLM call."""
        block = self.get_block(block_index)

        # Extract preserved content (remove !=== markers)
        content = extract_preserved_content(block.content)

        # Replace variables
        content = replace_variables_in_text(content, variables or {})

        return LLMResult(content=content)

    async def _process_interaction_render(self, block_index: int, mode: ProcessMode, variables: dict[str, str | list[str]] | None = None) -> LLMResult | AsyncGenerator[LLMResult, None]:
        """Process interaction content rendering."""
        block = self.get_block(block_index)

        # Apply variable replacement to interaction content
        processed_content = replace_variables_in_text(block.content, variables or {})

        # Create temporary block object to avoid modifying original data
        processed_block = copy(block)
        processed_block.content = processed_content

        # Extract question text from processed content
        question_text = extract_interaction_question(processed_block.content)
        if not question_text:
            # Unable to extract, return processed content
            return LLMResult(content=processed_block.content)

        # Build render messages
        messages = self._build_interaction_render_messages(question_text)

        if mode == ProcessMode.PROMPT_ONLY:
            return LLMResult(
                prompt=messages[-1]["content"],
                metadata={
                    "original_content": processed_block.content,
                    "question_text": question_text,
                },
            )

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                return LLMResult(content=processed_block.content)  # Fallback processing

            rendered_question = await self._llm_provider.complete(messages)
            rendered_content = self._reconstruct_interaction_content(processed_block.content, rendered_question)

            return LLMResult(
                content=rendered_content,
                prompt=messages[-1]["content"],
                metadata={
                    "original_question": question_text,
                    "rendered_question": rendered_question,
                },
            )

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                # For interaction blocks, return reconstructed content (one-time output)
                rendered_content = self._reconstruct_interaction_content(processed_block.content, question_text or "")

                async def stream_generator():
                    yield LLMResult(
                        content=rendered_content,
                        prompt=messages[-1]["content"],
                    )

                return stream_generator()

            # With LLM provider, collect full response then return once
            async def stream_generator():
                full_response = ""
                async for chunk in self._llm_provider.stream(messages):  # type: ignore[attr-defined]
                    full_response += chunk

                # Reconstruct final interaction content
                rendered_content = self._reconstruct_interaction_content(processed_block.content, full_response)

                # Return complete content at once, not incrementally
                yield LLMResult(
                    content=rendered_content,
                    prompt=messages[-1]["content"],
                )

            return stream_generator()

    async def _process_interaction_input(
        self,
        block_index: int,
        user_input: dict[str, list[str]],
        mode: ProcessMode,
        context: list[dict[str, str]] | None,
        variables: dict[str, str | list[str]] | None = None,
    ) -> LLMResult | AsyncGenerator[LLMResult, None]:
        """Process interaction user input."""
        block = self.get_block(block_index)
        target_variable = block.variables[0] if block.variables else "user_input"

        # Basic validation
        if not user_input or not any(values for values in user_input.values()):
            error_msg = INPUT_EMPTY_ERROR
            return await self._render_error(error_msg, mode)

        # Get the target variable value from user_input
        target_values = user_input.get(target_variable, [])

        # Apply variable replacement to interaction content
        processed_content = replace_variables_in_text(block.content, variables or {})

        # Parse interaction format using processed content
        parser = InteractionParser()
        parse_result = parser.parse(processed_content)

        if "error" in parse_result:
            error_msg = INTERACTION_PARSE_ERROR.format(error=parse_result["error"])
            return await self._render_error(error_msg, mode)

        interaction_type = parse_result.get("type")

        # Process user input based on interaction type
        if interaction_type in [
            InteractionType.BUTTONS_ONLY,
            InteractionType.BUTTONS_WITH_TEXT,
            InteractionType.BUTTONS_MULTI_SELECT,
            InteractionType.BUTTONS_MULTI_WITH_TEXT,
        ]:
            # All button types: validate user input against available buttons
            return await self._process_button_validation(
                parse_result,
                target_values,
                target_variable,
                mode,
                interaction_type,
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
        # For text-only inputs, directly use the target variable values
        if target_values:
            return LLMResult(
                content="",
                variables={target_variable: target_values},
                metadata={
                    "interaction_type": "text_only",
                    "target_variable": target_variable,
                    "values": target_values,
                },
            )
        error_msg = f"No input provided for variable '{target_variable}'"
        return await self._render_error(error_msg, mode)

    async def _process_button_validation(
        self,
        parse_result: dict[str, Any],
        target_values: list[str],
        target_variable: str,
        mode: ProcessMode,
        interaction_type: InteractionType,
    ) -> LLMResult | AsyncGenerator[LLMResult, None]:
        """
        Simplified button validation with new input format.

        Args:
            parse_result: InteractionParser result containing buttons list
            target_values: User input values for the target variable
            target_variable: Target variable name
            mode: Processing mode
            interaction_type: Type of interaction
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
            return await self._render_error(error_msg, mode)

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
            return await self._render_error(error_msg, mode)

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

    async def _process_llm_validation(
        self,
        block_index: int,
        user_input: dict[str, list[str]],
        target_variable: str,
        mode: ProcessMode,
    ) -> LLMResult | AsyncGenerator[LLMResult, None]:
        """Process LLM validation."""
        # Build validation messages
        messages = self._build_validation_messages(block_index, user_input, target_variable)

        if mode == ProcessMode.PROMPT_ONLY:
            return LLMResult(
                prompt=messages[-1]["content"],
                metadata={
                    "validation_target": user_input,
                    "target_variable": target_variable,
                },
            )

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                # Fallback processing, return variables directly
                return LLMResult(content="", variables=user_input)  # type: ignore[arg-type]

            llm_response = await self._llm_provider.complete(messages)

            # Parse validation response and convert to LLMResult
            # Use joined target values for fallback; avoids JSON string injection
            orig_input_str = ", ".join(user_input.get(target_variable, []))
            parsed_result = parse_validation_response(llm_response, orig_input_str, target_variable)
            return LLMResult(content=parsed_result["content"], variables=parsed_result["variables"])

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                return LLMResult(content="", variables=user_input)  # type: ignore[arg-type]

            async def stream_generator():
                full_response = ""
                async for chunk in self._llm_provider.stream(messages):  # type: ignore[attr-defined]
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

    async def _process_llm_validation_with_options(
        self,
        block_index: int,
        user_input: dict[str, list[str]],
        target_variable: str,
        options: list[str],
        question: str,
        mode: ProcessMode,
    ) -> LLMResult | AsyncGenerator[LLMResult, None]:
        """Process LLM validation with button options (third case)."""
        # Build special validation messages containing button option information
        messages = self._build_validation_messages_with_options(user_input, target_variable, options, question)

        if mode == ProcessMode.PROMPT_ONLY:
            return LLMResult(
                prompt=messages[-1]["content"],
                metadata={
                    "validation_target": user_input,
                    "target_variable": target_variable,
                    "options": options,
                    "question": question,
                },
            )

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                # Fallback processing, return variables directly
                return LLMResult(content="", variables=user_input)  # type: ignore[arg-type]

            llm_response = await self._llm_provider.complete(messages)

            # Parse validation response and convert to LLMResult
            # Use joined target values for fallback; avoids JSON string injection
            orig_input_str = ", ".join(user_input.get(target_variable, []))
            parsed_result = parse_validation_response(llm_response, orig_input_str, target_variable)
            return LLMResult(content=parsed_result["content"], variables=parsed_result["variables"])

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                return LLMResult(content="", variables=user_input)  # type: ignore[arg-type]

            async def stream_generator():
                full_response = ""
                async for chunk in self._llm_provider.stream(messages):  # type: ignore[attr-defined]
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

    async def _render_error(self, error_message: str, mode: ProcessMode) -> LLMResult | AsyncGenerator[LLMResult, None]:
        """Render user-friendly error message."""
        messages = self._build_error_render_messages(error_message)

        if mode == ProcessMode.PROMPT_ONLY:
            return LLMResult(
                prompt=messages[-1]["content"],
                metadata={"original_error": error_message},
            )

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                return LLMResult(content=error_message)  # Fallback processing

            friendly_error = await self._llm_provider.complete(messages)
            return LLMResult(content=friendly_error, prompt=messages[-1]["content"])

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                return LLMResult(content=error_message)

            async def stream_generator():
                async for chunk in self._llm_provider.stream(messages):  # type: ignore[attr-defined]
                    yield LLMResult(content=chunk, prompt=messages[-1]["content"])

            return stream_generator()

    # Message building helpers

    def _build_content_messages(
        self,
        block_index: int,
        variables: dict[str, str | list[str]] | None,
    ) -> list[dict[str, str]]:
        """Build content block messages."""
        block = self.get_block(block_index)
        block_content = block.content

        # Process output instructions
        block_content = process_output_instructions(block_content)

        # Replace variables
        block_content = replace_variables_in_text(block_content, variables or {})

        # Build message array
        messages = []

        # Add document prompt
        if self._document_prompt:
            messages.append({"role": "system", "content": self._document_prompt})

        # For most content blocks, historical conversation context is not needed
        # because each document block is an independent instruction
        # If future specific scenarios need context, logic can be added here
        # if context:
        #     messages.extend(context)

        # Add processed content as user message (as instruction to LLM)
        messages.append({"role": "user", "content": block_content})

        return messages

    def _build_interaction_render_messages(self, question_text: str) -> list[dict[str, str]]:
        """Build interaction rendering messages."""
        # Check if using custom interaction prompt
        if self._interaction_prompt != DEFAULT_INTERACTION_PROMPT:
            # User custom prompt + mandatory direction protection
            render_prompt = f"""{self._interaction_prompt}"""
        else:
            # Use default prompt and instructions
            render_prompt = f"""{self._interaction_prompt}
{INTERACTION_RENDER_INSTRUCTIONS}"""

        messages = []

        messages.append({"role": "system", "content": render_prompt})
        messages.append({"role": "user", "content": question_text})

        return messages

    def _build_validation_messages(self, block_index: int, user_input: dict[str, list[str]], target_variable: str) -> list[dict[str, str]]:
        """Build validation messages."""
        block = self.get_block(block_index)
        config = self.get_interaction_validation_config(block_index)

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
            from .utils import (
                extract_interaction_question,
                generate_smart_validation_template,
            )

            # Extract interaction question
            interaction_question = extract_interaction_question(block.content)

            # Generate smart validation template
            validation_template = generate_smart_validation_template(
                target_variable,
                context=None,  # Could consider passing context here
                interaction_question=interaction_question,
            )

            # Replace template variables
            user_input_str = json.dumps(user_input, ensure_ascii=False)
            validation_prompt = validation_template.replace("{sys_user_input}", user_input_str)
            validation_prompt = validation_prompt.replace("{block_content}", block.content)
            validation_prompt = validation_prompt.replace("{target_variable}", target_variable)
            system_message = DEFAULT_VALIDATION_SYSTEM_MESSAGE

        messages = []

        messages.append({"role": "system", "content": system_message})
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

    def _build_error_render_messages(self, error_message: str) -> list[dict[str, str]]:
        """Build error rendering messages."""
        render_prompt = f"""{self._interaction_error_prompt}

Original Error: {error_message}

{INTERACTION_ERROR_RENDER_INSTRUCTIONS}"""

        messages = []
        if self._document_prompt:
            messages.append({"role": "system", "content": self._document_prompt})

        messages.append({"role": "system", "content": render_prompt})
        messages.append({"role": "user", "content": error_message})

        return messages

    # Helper methods

    def _reconstruct_interaction_content(self, original_content: str, rendered_question: str) -> str:
        """Reconstruct interaction content."""
        cleaned_question = rendered_question.strip()
        # Use pre-compiled regex for improved performance
        cleaned_question = COMPILED_BRACKETS_CLEANUP_REGEX.sub("", cleaned_question)
        cleaned_question = COMPILED_VARIABLE_REFERENCE_CLEANUP_REGEX.sub("", cleaned_question)
        cleaned_question = COMPILED_WHITESPACE_CLEANUP_REGEX.sub(" ", cleaned_question).strip()

        match = COMPILED_INTERACTION_CONTENT_RECONSTRUCT_REGEX.search(original_content)

        if match:
            prefix = match.group(1)
            suffix = match.group(2)
            return f"{prefix}{cleaned_question}{suffix}"
        return original_content  # type: ignore[unreachable]

    # Dynamic Interaction Methods

    async def _process_with_dynamic_check(
        self,
        block_index: int,
        mode: ProcessMode,
        context: list[dict[str, str]] | None,
        variables: dict[str, str | list[str]] | None,
    ) -> LLMResult | AsyncGenerator[LLMResult, None]:
        """Process content with dynamic interaction detection and conversion."""

        block = self.get_block(block_index)
        messages = self._build_dynamic_check_messages(block, context, variables)

        # Define Function Calling tools
        tools = [{
            "type": "function",
            "function": {
                "name": "create_interaction_block",
                "description": "Convert content to interaction block format with specific options when it needs to collect user input",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "needs_interaction": {
                            "type": "boolean",
                            "description": "Whether this content needs to be converted to interaction block"
                        },
                        "interaction_content": {
                            "type": "string",
                            "description": "Complete interaction block format following MarkdownFlow syntax. MUST use '...' for text input. Examples: ?[%{{dish}} 宫保鸡丁|麻婆豆腐|...其他请输入] or ?[%{{skills}} Python||JavaScript||...其他请输入] or ?[%{{name}} ...请输入姓名]"
                        }
                    },
                    "required": ["needs_interaction"]
                }
            }
        }]

        if not self._llm_provider:
            raise ValueError(LLM_PROVIDER_REQUIRED_ERROR)

        # Call LLM with tools
        result = await self._llm_provider.complete_with_tools(messages, tools)

        # If transformed to interaction, return as is
        if result.transformed_to_interaction:
            return result

        # If not transformed, continue with normal processing
        if mode == ProcessMode.STREAM:
            async def stream_wrapper():
                async for chunk in self._llm_provider.stream(messages):
                    yield LLMResult(content=chunk)
            return stream_wrapper()

        # Complete mode - already handled by complete_with_tools
        return result

    def _build_dynamic_check_messages(
        self,
        block: "Block",
        context: list[dict[str, str]] | None,
        variables: dict[str, str | list[str]] | None,
    ) -> list[dict[str, str]]:
        """Build messages for dynamic interaction detection."""

        import json

        # System prompt for detection
        system_prompt = """You are an intelligent document processing assistant specializing in creating interactive forms.

Task: Analyze the given content block and determine if it needs to be converted to an interaction block to collect user information.

Judgment criteria:
1. Does the content imply the need to ask users for information?
2. Does it need to collect detailed information based on previous variable values?
3. Does it mention "recording" or "saving" information to variables?

If conversion is needed, generate a STANDARD interaction block format with SPECIFIC options based on the document-level instructions and context.

REQUIRED FORMATS (MarkdownFlow Standard Syntax):
- Buttons only: ?[%{{variable_name}} Option1|Option2|Option3]
- Multi-select only: ?[%{{variable_name}} Option1||Option2||Option3]
- Text input only: ?[%{{variable_name}} ...Text input prompt]
- Buttons + text: ?[%{{variable_name}} Option1|Option2|...Text input prompt]
- Multi-select + text: ?[%{{variable_name}} Option1||Option2||...Text input prompt]

CRITICAL SYNTAX RULES:
1. Text input MUST have "..." prefix (e.g., "...enter your name" not "enter your name")
2. Use %{{variable_name}} format to protect variables from replacement
3. Use single | for single choice, double || for multiple choice
4. For buttons+text combo, text option MUST start with "..."
5. ALWAYS provide specific options based on document context and existing variables
6. You can reference existing variables in the content: "You chose {{food_type}}"
7. Follow the language and domain specified in the document-level instructions

IMPORTANT: The document-level instructions will specify the language, domain, and specific requirements. Follow them precisely for option generation."""

        # User message with content and context
        # Build user prompt with document context
        user_prompt_parts = []

        # Add document-level prompt context if exists
        if self._document_prompt:
            user_prompt_parts.append(f"""Document-level instructions:
{self._document_prompt}

(Note: The above are the user's document-level instructions that provide context and requirements for processing.)
""")

        # Prepare content analysis with both original and resolved versions
        original_content = block.content

        # Create resolved content with variable substitution for better context
        resolved_content = original_content
        if variables:
            from .utils import replace_variables_in_text
            resolved_content = replace_variables_in_text(original_content, variables)

        content_analysis = f"""Current content block to analyze:

**Original content (shows variable structure):**
{original_content}

**Resolved content (with current variable values):**
{resolved_content}

**Existing variable values:**
{json.dumps(variables, ensure_ascii=False) if variables else "None"}"""

        # Add different analysis based on whether content has variables
        if "{{" in original_content and "}}" in original_content:
            from .utils import extract_variables_from_text
            content_variables = set(extract_variables_from_text(original_content))

            # Find new variables (not yet collected)
            new_variables = content_variables - (set(variables.keys()) if variables else set())
            existing_used_variables = content_variables & (set(variables.keys()) if variables else set())

            content_analysis += f"""

**Variable analysis:**
- Variables used from previous steps: {list(existing_used_variables) if existing_used_variables else "None"}
- New variables to collect: {list(new_variables) if new_variables else "None"}

**Context guidance:**
- Use the resolved content to understand the actual context and requirements
- Generate options based on the real variable values shown in the resolved content
- Collect user input for the new variables identified above"""

        user_prompt_parts.append(content_analysis)

        # Add analysis requirements
        user_prompt_parts.append("""Analysis requirements:
1. Consider BOTH the document-level instructions AND the current content block
2. If this content asks for user information or mentions recording to variables, convert it to interaction format
3. **IMPORTANT: Use the resolved content for context, generate options for new variables:**
   - Pay attention to the "Resolved content" which shows actual variable values
   - Generate specific options based on the resolved context (e.g., if resolved content shows "川菜", generate Sichuan dishes)
   - Create interaction format to collect the "New variables to collect" identified above
   - Use the format: ?[%{{new_variable_name}} option1|option2|...] where new_variable_name is from the analysis above
5. Follow ALL requirements specified in the document-level instructions, including:
   - Language requirements (use the exact language specified)
   - Domain-specific options and terminology
   - Formatting preferences
   - Any other specific requirements

6. **CRITICAL: Choose appropriate selection type based on business logic:**

   **Use MULTIPLE CHOICE (||) when:**
   - Users can logically select multiple items simultaneously
   - Items are additive/complementary, not mutually exclusive
   - Examples:
     * Food dishes: "宫保鸡丁||麻婆豆腐||水煮鱼" (can order multiple dishes)
     * Skills/Technologies: "Python||JavaScript||Java" (can know multiple languages)
     * Interests/Hobbies: "读书||运动||旅游" (can have multiple interests)
     * Features/Requirements: "定制颜色||个性化logo||特殊尺寸" (can want multiple features)
     * Exercise types: "跑步||游泳||瑜伽" (can do multiple exercises)

   **Use SINGLE CHOICE (|) when:**
   - Only one option makes logical sense
   - Options are mutually exclusive or represent a single decision
   - Examples:
     * Job positions: "软件工程师|数据科学家|产品经理" (usually apply for one position)
     * Education levels: "Beginner|Intermediate|Advanced" (have one current level)
     * Budget ranges: "5-10万|10-20万|20-30万" (have one budget range)
     * Travel destinations: "北京|上海|深圳" (usually choose one main destination)
     * Experience levels: "初级|中级|高级" (have one current experience level)

7. **Selection logic analysis:**
   - Ask yourself: "Can a user realistically want/choose multiple of these options at the same time?"
   - If YES → Use multiple choice (||)
   - If NO → Use single choice (|)

8. Always include 3-4 realistic options plus appropriate fallback text option when suitable

Please determine if conversion is needed, analyze the selection logic carefully, and generate the proper interaction format with concrete options using the appropriate selection type (| or ||).""")

        user_prompt = "\n\n".join(user_prompt_parts)

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add context if provided
        if context:
            messages.extend(context)

        messages.append({"role": "user", "content": user_prompt})

        return messages

    async def _process_dynamic_interaction_validation(
        self,
        block_index: int,
        interaction_format: str,
        user_input: dict[str, list[str]],
        mode: ProcessMode,
        context: list[dict[str, str]] | None,
        variables: dict[str, str | list[str]] | None,
    ) -> LLMResult:
        """Validate user input for dynamically generated interaction blocks."""

        from .utils import InteractionParser

        # Parse the interaction format
        parser = InteractionParser()
        interaction = parser.parse(interaction_format)

        if interaction is None:
            raise ValueError(f"Invalid interaction format: {interaction_format}")

        # Extract variable name from the interaction format
        # This is a simplified extraction - in real implementation you'd use the parser result
        import re
        var_match = re.search(r'%\{\{([^}]+)\}\}', interaction_format)
        if not var_match:
            raise ValueError(f"No variable found in interaction format: {interaction_format}")

        variable_name = var_match.group(1)

        # Validate the user input
        user_values = user_input.get(variable_name, [])
        if not user_values:
            raise ValueError(f"No input provided for variable: {variable_name}")

        # Process the validation result
        updated_variables = dict(variables or {})

        # Handle single vs multiple values
        if len(user_values) == 1:
            updated_variables[variable_name] = user_values[0]
        else:
            updated_variables[variable_name] = user_values

        # Return successful validation result
        return LLMResult(
            content=f"Successfully collected {variable_name}: {user_values}",
            variables=updated_variables,
            metadata={
                "validation_success": True,
                "variable_collected": variable_name,
                "values_collected": user_values
            }
        )
