"""
Code Block Preprocessor

Extracts code block content before parsing, implementing CommonMark-compliant fenced code blocks.
Also extracts HTML comments to prevent them from being sent to LLM.
"""

from .code_fence_utils import is_code_fence_end, parse_code_fence_start
from .html_comment_utils import is_html_comment_end, is_html_comment_start, remove_inline_comment


class CodeBlockPreprocessor:
    """
    Code block and HTML comment preprocessor

    Extracts code blocks and HTML comments from document and replaces them with placeholders,
    so that MarkdownFlow syntax inside code blocks/comments is ignored during subsequent parsing.

    Attributes:
        code_blocks: Mapping of placeholder → original code block content (including fence markers)
        html_comments: Mapping of placeholder → HTML comment content (multi-line only)
        counter: Unified placeholder counter (code blocks and comments share same counter)
    """

    # State machine states
    STATE_NORMAL = "NORMAL"
    STATE_IN_CODE_BLOCK = "IN_CODE_BLOCK"
    STATE_IN_HTML_COMMENT = "IN_HTML_COMMENT"

    def __init__(self):
        """Initialize preprocessor"""
        self.code_blocks: dict[str, str] = {}
        self.html_comments: dict[str, str] = {}
        self.counter: int = 0

    def extract_code_blocks(self, document: str) -> str:
        """
        Extract code blocks and HTML comments from document and replace with placeholders

        How it works:
          1. Scan document line by line using a state machine
          2. Detect CommonMark-compliant fenced code blocks
          3. Detect HTML multi-line comments
          4. Replace code blocks and comments with unique placeholders
          5. Store content in internal mappings

        Priority rules:
          - Code blocks have priority: HTML comments inside code blocks are not extracted
          - Single-line comments are removed inline: <!-- ... --> on same line
          - Multi-line comments are extracted with placeholders

        Args:
            document: Original markdown document

        Returns:
            Processed document (code blocks and comments replaced with placeholders)

        Examples:
            >>> preprocessor = CodeBlockPreprocessor()
            >>> doc = "```python\\nprint('hello')\\n```"
            >>> processed = preprocessor.extract_code_blocks(doc)
            >>> "__MDFLOW_CODE_BLOCK_1__" in processed
            True
        """
        lines = document.split("\n")
        result = []

        # State machine variables
        state = self.STATE_NORMAL
        current_fence = None
        code_buffer = []
        comment_buffer = []

        for line in lines:
            if state == self.STATE_NORMAL:
                # Priority: Check code blocks first (code block priority principle)
                fence_info = parse_code_fence_start(line)
                if fence_info is not None:
                    # Enter code block state
                    state = self.STATE_IN_CODE_BLOCK
                    current_fence = fence_info
                    code_buffer = [line]
                else:
                    # Check HTML comments (both single-line and multi-line need processing)
                    comment_info, is_single_line = is_html_comment_start(line)
                    if comment_info is not None:
                        if is_single_line:
                            # Single-line comment: remove comment part, preserve rest of line
                            cleaned_line = remove_inline_comment(line)
                            # Only add if cleaned content is non-empty
                            if cleaned_line.strip():
                                result.append(cleaned_line)
                            # Don't store single-line comments, already processed
                        else:
                            # Multi-line comment: enter comment state
                            state = self.STATE_IN_HTML_COMMENT
                            comment_buffer = [line]
                    else:
                        # Normal line, keep as-is
                        result.append(line)

            elif state == self.STATE_IN_CODE_BLOCK:
                # Don't check HTML comments inside code blocks
                code_buffer.append(line)

                # Detect fence closing
                if is_code_fence_end(line, current_fence):
                    # Generate code block placeholder
                    placeholder = self._generate_code_block_placeholder()

                    # Store code block
                    code_content = "\n".join(code_buffer)
                    self.code_blocks[placeholder] = code_content

                    # Output placeholder (as a separate line)
                    result.append(placeholder)

                    # Reset state
                    state = self.STATE_NORMAL
                    current_fence = None
                    code_buffer = []

            elif state == self.STATE_IN_HTML_COMMENT:
                # Accumulate comment lines
                comment_buffer.append(line)

                # Detect comment end
                if is_html_comment_end(line):
                    # Generate HTML comment placeholder
                    placeholder = self._generate_html_comment_placeholder()

                    # Store comment
                    comment_content = "\n".join(comment_buffer)
                    self.html_comments[placeholder] = comment_content

                    # Output placeholder
                    result.append(placeholder)

                    # Reset state
                    state = self.STATE_NORMAL
                    comment_buffer = []

        # Handle unclosed code blocks (keep as-is)
        if state == self.STATE_IN_CODE_BLOCK and code_buffer:
            # Restore unclosed code block content to result
            result.extend(code_buffer)

        # Handle unclosed comments (keep as-is)
        if state == self.STATE_IN_HTML_COMMENT and comment_buffer:
            result.extend(comment_buffer)

        return "\n".join(result)

    def restore_code_blocks(self, processed: str) -> str:
        """
        Restore all placeholders back to original content (code blocks + HTML comments)

        Used for preserved content blocks, needs complete restoration of all content.

        Args:
            processed: Processed document containing placeholders

        Returns:
            Restored document

        Examples:
            >>> preprocessor = CodeBlockPreprocessor()
            >>> doc = "```python\\nprint('hello')\\n```"
            >>> processed = preprocessor.extract_code_blocks(doc)
            >>> restored = preprocessor.restore_code_blocks(processed)
            >>> restored == doc
            True
        """
        result = processed

        # Restore code block placeholders
        for placeholder, original in self.code_blocks.items():
            result = result.replace(placeholder, original)

        # Restore HTML comment placeholders
        for placeholder, original in self.html_comments.items():
            result = result.replace(placeholder, original)

        return result

    def restore_code_blocks_only(self, processed: str) -> str:
        """
        Restore only code block placeholders, not HTML comments

        Used for content blocks sent to LLM, preserves code blocks but removes comments.

        Args:
            processed: Processed document containing placeholders

        Returns:
            Document with only code blocks restored (comment placeholders remain)
        """
        result = processed

        # Only restore code block placeholders
        for placeholder, original in self.code_blocks.items():
            result = result.replace(placeholder, original)

        return result

    def remove_html_comment_placeholders(self, processed: str) -> str:
        """
        Remove HTML comment placeholders and their lines

        Used to clean comment content before sending to LLM.

        Args:
            processed: Processed document containing placeholders

        Returns:
            Document with comment placeholders removed
        """
        lines = processed.split("\n")
        filtered_lines = []

        for line in lines:
            # Skip lines that only contain comment placeholders
            trimmed = line.strip()
            if not (trimmed.startswith("__MDFLOW_HTML_COMMENT_") and trimmed.endswith("__")):
                # Keep non-placeholder lines, or lines where placeholder has other content
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _generate_code_block_placeholder(self) -> str:
        """
        Generate code block placeholder

        Returns:
            Placeholder in format __MDFLOW_CODE_BLOCK_N__
        """
        self.counter += 1
        return f"__MDFLOW_CODE_BLOCK_{self.counter}__"

    def _generate_html_comment_placeholder(self) -> str:
        """
        Generate HTML comment placeholder

        Returns:
            Placeholder in format __MDFLOW_HTML_COMMENT_N__
        """
        self.counter += 1
        return f"__MDFLOW_HTML_COMMENT_{self.counter}__"

    def reset(self):
        """Reset preprocessor state (for processing new documents)"""
        self.code_blocks = {}
        self.html_comments = {}
        self.counter = 0

    def get_code_blocks(self) -> dict[str, str]:
        """
        Return all extracted code blocks (for debugging)

        Returns:
            Mapping of placeholder → original code block content
        """
        return self.code_blocks

    def get_html_comments(self) -> dict[str, str]:
        """
        Return all extracted HTML comments (for debugging)

        Returns:
            Mapping of placeholder → HTML comment content
        """
        return self.html_comments
