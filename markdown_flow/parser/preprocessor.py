"""
Code Block Preprocessor

Extracts code block content before parsing, implementing CommonMark-compliant fenced code blocks.
"""

from .code_fence_utils import is_code_fence_end, parse_code_fence_start


class CodeBlockPreprocessor:
    """
    Code block preprocessor

    Extracts code blocks from document and replaces them with placeholders, so that MarkdownFlow
    syntax inside code blocks is ignored during subsequent parsing.

    Attributes:
        code_blocks: Mapping of placeholder → original code block content (including fence markers)
        counter: Placeholder counter
    """

    # State machine states
    STATE_NORMAL = "NORMAL"
    STATE_IN_CODE_BLOCK = "IN_CODE_BLOCK"

    def __init__(self):
        """Initialize preprocessor"""
        self.code_blocks: dict[str, str] = {}
        self.counter: int = 0

    def extract_code_blocks(self, document: str) -> str:
        """
        Extract code blocks from document and replace with placeholders

        How it works:
          1. Scan document line by line using a state machine
          2. Detect CommonMark-compliant fenced code blocks
          3. Replace code block content (including fences) with unique placeholders
          4. Store code block content in internal mapping

        Args:
            document: Original markdown document

        Returns:
            Processed document (code blocks replaced with placeholders)

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

        for line in lines:
            if state == self.STATE_NORMAL:
                # Detect code block opening fence
                fence_info = parse_code_fence_start(line)
                if fence_info is not None:
                    # Enter code block state
                    state = self.STATE_IN_CODE_BLOCK
                    current_fence = fence_info
                    code_buffer = [line]
                else:
                    # Normal line, keep as-is
                    result.append(line)

            elif state == self.STATE_IN_CODE_BLOCK:
                # Accumulate code lines
                code_buffer.append(line)

                # Detect fence closing
                if is_code_fence_end(line, current_fence):
                    # Generate placeholder
                    placeholder = self._generate_placeholder()

                    # Store code block
                    code_content = "\n".join(code_buffer)
                    self.code_blocks[placeholder] = code_content

                    # Output placeholder (as a separate line)
                    result.append(placeholder)

                    # Reset state
                    state = self.STATE_NORMAL
                    current_fence = None
                    code_buffer = []

        # Handle unclosed code blocks (keep as-is)
        if state == self.STATE_IN_CODE_BLOCK and code_buffer:
            # Restore unclosed code block content to result
            result.extend(code_buffer)

        return "\n".join(result)

    def restore_code_blocks(self, processed: str) -> str:
        """
        Restore placeholders back to original code block content

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

        # Replace all placeholders
        for placeholder, original in self.code_blocks.items():
            result = result.replace(placeholder, original)

        return result

    def _generate_placeholder(self) -> str:
        """
        Generate a unique placeholder

        Returns:
            Placeholder in format __MDFLOW_CODE_BLOCK_N__
        """
        self.counter += 1
        return f"__MDFLOW_CODE_BLOCK_{self.counter}__"

    def reset(self):
        """Reset preprocessor state (for processing new documents)"""
        self.code_blocks = {}
        self.counter = 0

    def get_code_blocks(self) -> dict[str, str]:
        """
        Return all extracted code blocks (for debugging)

        Returns:
            Mapping of placeholder → original code block content
        """
        return self.code_blocks
