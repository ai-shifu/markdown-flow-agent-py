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
    OUTPUT_INSTRUCTION_EXPLANATION,
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
    _max_context_length: int
    _blocks: list[Block] | None
    _interaction_configs: dict[int, InteractionValidationConfig]

    def __init__(
        self,
        document: str,
        llm_provider: LLMProvider | None = None,
        document_prompt: str | None = None,
        interaction_prompt: str | None = None,
        interaction_error_prompt: str | None = None,
        max_context_length: int = 0,
    ):
        """
        Initialize MarkdownFlow instance.

        Args:
            document: Markdown document content
            llm_provider: LLM provider, if None only PROMPT_ONLY mode is available
            document_prompt: Document-level system prompt
            interaction_prompt: Interaction content rendering prompt
            interaction_error_prompt: Interaction error rendering prompt
            max_context_length: Maximum number of context messages to keep (0 = unlimited)
        """
        self._document = document
        self._llm_provider = llm_provider
        self._document_prompt = document_prompt
        self._interaction_prompt = interaction_prompt or DEFAULT_INTERACTION_PROMPT
        self._interaction_error_prompt = interaction_error_prompt or DEFAULT_INTERACTION_ERROR_PROMPT
        self._max_context_length = max_context_length
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

        if mode == ProcessMode.PROMPT_ONLY:
            return LLMResult(prompt=messages[-1]["content"], metadata={"messages": messages})

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                raise ValueError(LLM_PROVIDER_REQUIRED_ERROR)

            content = self._llm_provider.complete(messages)
            return LLMResult(content=content, prompt=messages[-1]["content"])

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                raise ValueError(LLM_PROVIDER_REQUIRED_ERROR)

            def stream_generator():
                for chunk in self._llm_provider.stream(messages):  # type: ignore[attr-defined]
                    yield LLMResult(content=chunk, prompt=messages[-1]["content"])

            return stream_generator()

    def _process_preserved_content(self, block_index: int, variables: dict[str, str | list[str]] | None) -> LLMResult:
        """Process preserved content block, output as-is without LLM call."""
        block = self.get_block(block_index)

        # Extract preserved content (remove !=== markers)
        content = extract_preserved_content(block.content)

        # Replace variables
        content = replace_variables_in_text(content, variables or {})

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

        # Extract question text from processed content
        question_text = extract_interaction_question(processed_block.content)
        if not question_text:
            # Unable to extract, return processed content
            return LLMResult(content=processed_block.content)

        # Truncate context to configured maximum length
        truncated_context = self._truncate_context(context)

        # Build render messages with context
        messages = self._build_interaction_render_messages(question_text, truncated_context)

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

            rendered_question = self._llm_provider.complete(messages)
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

                def stream_generator():
                    yield LLMResult(
                        content=rendered_content,
                        prompt=messages[-1]["content"],
                    )

                return stream_generator()

            # With LLM provider, collect full response then return once
            def stream_generator():
                full_response = ""
                for chunk in self._llm_provider.stream(messages):  # type: ignore[attr-defined]
                    full_response += chunk

                # Reconstruct final interaction content
                rendered_content = self._reconstruct_interaction_content(processed_block.content, full_response)

                # Return complete content at once, not incrementally
                yield LLMResult(
                    content=rendered_content,
                    prompt=messages[-1]["content"],
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
                if mode == ProcessMode.PROMPT_ONLY:
                    # Return validation prompt
                    return validation_result

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
                    else:
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

            llm_response = self._llm_provider.complete(messages)

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
                for chunk in self._llm_provider.stream(messages):  # type: ignore[attr-defined]
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

            llm_response = self._llm_provider.complete(messages)

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
                for chunk in self._llm_provider.stream(messages):  # type: ignore[attr-defined]
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

        if mode == ProcessMode.PROMPT_ONLY:
            return LLMResult(
                prompt=messages[-1]["content"],
                metadata={"original_error": error_message},
            )

        if mode == ProcessMode.COMPLETE:
            if not self._llm_provider:
                return LLMResult(content=error_message)  # Fallback processing

            friendly_error = self._llm_provider.complete(messages)
            return LLMResult(content=friendly_error, prompt=messages[-1]["content"])

        if mode == ProcessMode.STREAM:
            if not self._llm_provider:
                return LLMResult(content=error_message)

            def stream_generator():
                for chunk in self._llm_provider.stream(messages):  # type: ignore[attr-defined]
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

        # Build message array
        messages = []

        # Conditionally add system prompts
        if self._document_prompt:
            system_msg = self._document_prompt
            # Only add output instruction explanation when preserved content detected
            if has_preserved_content:
                system_msg += "\n\n" + OUTPUT_INSTRUCTION_EXPLANATION.strip()
            messages.append({"role": "system", "content": system_msg})
        elif has_preserved_content:
            # No document prompt but has preserved content, add explanation alone
            messages.append({"role": "system", "content": OUTPUT_INSTRUCTION_EXPLANATION.strip()})

        # Add conversation history context if provided
        # Context is inserted after system message and before current user message
        truncated_context = self._truncate_context(context)
        if truncated_context:
            messages.extend(truncated_context)

        # Add processed content as user message (as instruction to LLM)
        messages.append({"role": "user", "content": block_content})

        return messages

    def _build_interaction_render_messages(
        self,
        question_text: str,
        context: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
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

        # NOTE: Context is temporarily disabled for interaction rendering
        # Mixing conversation history with interaction content rewriting can cause issues
        # The context parameter is kept in the signature for future use
        # truncated_context = self._truncate_context(context)
        # if truncated_context:
        #     messages.extend(truncated_context)

        messages.append({"role": "user", "content": question_text})

        return messages

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
            from .utils import (
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
