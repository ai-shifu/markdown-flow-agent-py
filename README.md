# MarkdownFlow Agent (Python)

**Python backend parsing toolkit for transforming [MarkdownFlow](https://markdownflow.ai) documents into personalized, AI-powered interactive content.**

[MarkdownFlow](https://markdownflow.ai) (also known as MDFlow or markdown-flow) extends standard Markdown with AI to create personalized, interactive pages. Its tagline is **"Write Once, Deliver Personally"**.

<div align="center">

[![PyPI version](https://badge.fury.io/py/markdown-flow.svg)](https://badge.fury.io/py/markdown-flow)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Type Hints](https://img.shields.io/badge/Type_Hints-Enabled-green.svg)](https://docs.python.org/3/library/typing.html)

English | [简体中文](README_CN.md)

</div>

## 🚀 Quick Start

### Install

```bash
pip install markdown-flow
# or
pip install -e .  # For development
```

### Basic Usage

```python
from markdown_flow import MarkdownFlow, ProcessMode

# Simple content processing
document = """
Hello {{name}}! Let's explore your Python skills.

?[%{{level}} Beginner | Intermediate | Expert]

Based on your {{level}} level, here are some recommendations...
"""

mf = MarkdownFlow(document)
variables = mf.extract_variables()  # Returns: {'name', 'level'}
blocks = mf.get_all_blocks()        # Get parsed document blocks
```

### LLM Integration

```python
from markdown_flow import MarkdownFlow, ProcessMode
from your_llm_provider import YourLLMProvider

# Initialize with LLM provider
llm_provider = YourLLMProvider(api_key="your-key")
mf = MarkdownFlow(document, llm_provider=llm_provider)

# Process with different modes
result = mf.process(
    block_index=0,
    mode=ProcessMode.COMPLETE,
    variables={'name': 'Alice', 'level': 'Intermediate'}
)
```

### Streaming Response

```python
# Stream processing for real-time responses
for chunk in mf.process(
    block_index=0,
    mode=ProcessMode.STREAM,
    variables={'name': 'Bob'}
):
    print(chunk.content, end='')
```

### Interactive Elements

```python
# Handle user interactions
document = """
What's your preferred programming language?

?[%{{language}} Python | JavaScript | Go | Other...]

Select your skills (multi-select):

?[%{{skills}} Python||JavaScript||Go||Rust]

?[Continue | Skip]
"""

mf = MarkdownFlow(document)
blocks = mf.get_all_blocks()

for block in blocks:
    if block.block_type == BlockType.INTERACTION:
        # Process user interaction
        print(f"Interaction: {block.content}")

# Process user input
user_input = {
    'language': ['Python'],                    # Single selection
    'skills': ['Python', 'JavaScript', 'Go']  # Multi-selection
}

result = mf.process(
    block_index=1,  # Process skills interaction
    user_input=user_input,
    mode=ProcessMode.COMPLETE
)
```

## 📖 API Reference

### Core Classes

#### MarkdownFlow

Main class for parsing and processing MarkdownFlow documents.

```python
class MarkdownFlow:
    def __init__(
        self,
        content: str,
        llm_provider: Optional[LLMProvider] = None
    ) -> None: ...

    def get_all_blocks(self) -> List[Block]: ...
    def extract_variables(self) -> Set[str]: ...

    def process(
        self,
        block_index: int,
        mode: ProcessMode = ProcessMode.COMPLETE,
        variables: Optional[Dict[str, str]] = None,
        user_input: Optional[str] = None
    ) -> LLMResult | Generator[LLMResult, None, None]: ...
```

**Methods:**

- `get_all_blocks()` - Parse document into structured blocks
- `extract_variables()` - Extract all `{{variable}}` and `%{{variable}}` patterns
- `process()` - Process blocks with LLM using unified interface

**Example:**

```python
mf = MarkdownFlow("""
# Welcome {{name}}!

Choose your experience: ?[%{{exp}} Beginner | Expert]

Your experience level is {{exp}}.
""")

print("Variables:", mf.extract_variables())  # {'name', 'exp'}
print("Blocks:", len(mf.get_all_blocks()))   # 3
```

#### ProcessMode

Processing mode enumeration for different use cases.

```python
class ProcessMode(Enum):
    COMPLETE = "complete"  # Non-streaming LLM processing
    STREAM = "stream"      # Streaming LLM responses
```

**Usage:**

```python
# Complete response
complete_result = mf.process(0, ProcessMode.COMPLETE)
print(complete_result.content)  # Full LLM response

# Streaming response
for chunk in mf.process(0, ProcessMode.STREAM):
    print(chunk.content, end='')
```

#### LLMProvider

Abstract base class for implementing LLM providers.

```python
from abc import ABC, abstractmethod
from typing import Generator

class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[dict[str, str]]) -> str: ...

    @abstractmethod
    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]: ...
```

**Custom Implementation:**

```python
class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)

    def complete(self, messages: list[dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        return response.choices[0].message.content

    def stream(self, messages: list[dict[str, str]]):
        stream = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

### Block Types

#### BlockType

Enumeration of different block types in MarkdownFlow documents.

```python
class BlockType(Enum):
    CONTENT = "content"                    # Regular markdown content
    INTERACTION = "interaction"            # User interaction blocks (?[...])
    PRESERVED_CONTENT = "preserved_content" # Content wrapped in === (inline) or !=== (multiline) markers
```

**Block Structure:**

```python
# Content blocks - processed by LLM
"""
Hello {{name}}! Welcome to our platform.
"""

# Interaction blocks - user input required
"""
?[%{{choice}} Option A | Option B | Enter custom option...]
"""

# Preserved content - output as-is
"""
# Inline format (single line)
===Fixed title===

# Multiline fence with leading '!'
!===
This content is preserved exactly as written.
No LLM processing or variable replacement.
!===
"""
```

### Interaction Types

#### InteractionType

Parsed interaction format types.

```python
class InteractionType(NamedTuple):
    name: str                    # Type name
    variable: Optional[str]      # Variable to assign (%{{var}})
    buttons: List[str]          # Button options
    question: Optional[str]      # Text input question
    has_text_input: bool        # Whether text input is allowed
```

**Supported Formats:**

```python
# TEXT_ONLY: Text input with question
"?[%{{name}} What is your name?]"

# BUTTONS_ONLY: Button selection only
"?[%{{level}} Beginner | Intermediate | Expert]"

# BUTTONS_WITH_TEXT: Buttons with fallback text input
"?[%{{preference}} Option A | Option B | Please specify...]"

# BUTTONS_MULTI_SELECT: Multi-select buttons
"?[%{{skills}} Python||JavaScript||Go||Rust]"

# BUTTONS_MULTI_WITH_TEXT: Multi-select with text fallback
"?[%{{frameworks}} React||Vue||Angular||Please specify others...]"

# NON_ASSIGNMENT_BUTTON: Display buttons without variable assignment
"?[Continue | Cancel | Go Back]"
```

### Utility Functions

#### Variable Operations

```python
def extract_variables_from_text(text: str) -> Set[str]:
    """Extract all {{variable}} and %{{variable}} patterns."""

def replace_variables_in_text(text: str, variables: dict) -> str:
    """Replace {{variable}} patterns with values, preserve %{{variable}}."""

# Example
text = "Hello {{name}}! Choose: ?[%{{level}} Basic | Advanced]"
vars = extract_variables_from_text(text)  # {'name', 'level'}
result = replace_variables_in_text(text, {'name': 'Alice'})
# Returns: "Hello Alice! Choose: ?[%{{level}} Basic | Advanced]"
```

#### Interaction Processing

```python
def InteractionParser.parse(content: str) -> InteractionType:
    """Parse interaction block into structured format."""

def extract_interaction_question(content: str) -> str:
    """Extract question text from interaction block."""

def generate_smart_validation_template(interaction_type: InteractionType) -> str:
    """Generate validation template for interaction."""

# Example
parser_result = InteractionParser.parse("%{{choice}} A | B | Enter custom...")
print(parser_result.name)          # "BUTTONS_WITH_TEXT"
print(parser_result.variable)      # "choice"
print(parser_result.buttons)       # ["A", "B"]
print(parser_result.question)      # "Enter custom..."
```

### Types and Models

```python
# Core data structures
from dataclasses import dataclass
from typing import Optional, List, Dict, Set

@dataclass
class Block:
    content: str
    block_type: BlockType
    index: int

@dataclass
class LLMResult:
    content: str
    metadata: Optional[Dict] = None

# Variable system types
Variables = Dict[str, str]  # Variable name -> value mapping

# All types are exported for use
from markdown_flow import (
    Block, LLMResult, Variables,
    BlockType, InteractionType, ProcessMode
)
```

## 🔄 Migration Guide

### Parameter Format Upgrade

The new version introduces multi-select interaction support with improvements to the `user_input` parameter format.

#### Old Format

```python
# Single string input
user_input = "Python"

# Process interaction
result = mf.process(
    block_index=1,
    user_input=user_input,
    mode=ProcessMode.COMPLETE
)
```

#### New Format

```python
# Dictionary format with list values
user_input = {
    'language': ['Python'],                    # Single selection as list
    'skills': ['Python', 'JavaScript', 'Go']  # Multi-selection
}

# Process interaction
result = mf.process(
    block_index=1,
    user_input=user_input,
    mode=ProcessMode.COMPLETE
)
```

#### New Multi-Select Syntax

```markdown
<!-- Single select (traditional) -->
?[%{{language}} Python|JavaScript|Go]

<!-- Multi-select (new) -->
?[%{{skills}} Python||JavaScript||Go||Rust]

<!-- Multi-select with text fallback -->
?[%{{frameworks}} React||Vue||Angular||Please specify others...]
```

#### Variable Types

```python
# Variables now support both string and list values
variables = {
    'name': 'John',                           # str (traditional)
    'skills': ['Python', 'JavaScript'],      # list[str] (new)
    'experience': 'Senior'                    # str (traditional)
}
```

## 🧩 Advanced Examples

### Custom LLM Provider Integration

```python
from markdown_flow import MarkdownFlow, LLMProvider, LLMResult
import httpx

class CustomAPIProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.Client()

    def complete(self, prompt: str) -> LLMResult:
        response = self.client.post(
            f"{self.base_url}/complete",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"prompt": prompt, "max_tokens": 1000}
        )
        data = response.json()
        return LLMResult(content=data["text"])

    def stream(self, prompt: str):
        with self.client.stream(
            "POST",
            f"{self.base_url}/stream",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"prompt": prompt}
        ) as response:
            for chunk in response.iter_text():
                if chunk.strip():
                    yield chunk

# Usage
provider = CustomAPIProvider("https://api.example.com", "your-key")
mf = MarkdownFlow(document, llm_provider=provider)
```

### Multi-Block Document Processing

```python
def process_conversation():
    conversation = """
# AI Assistant

Hello {{user_name}}! I'm here to help you learn Python.

---

What's your current experience level?

?[%{{experience}} Complete Beginner | Some Experience | Experienced]

---

Based on your {{experience}} level, let me create a personalized learning plan.

This plan will include {{topics}} that match your background.

---

Would you like to start with the basics?

?[Start Learning | Customize Plan | Ask Questions]
"""

    mf = MarkdownFlow(conversation, llm_provider=your_provider)
    blocks = mf.get_all_blocks()

    variables = {
        'user_name': 'Alice',
        'experience': 'Some Experience',
        'topics': 'intermediate concepts and practical projects'
    }

    for i, block in enumerate(blocks):
        if block.block_type == BlockType.CONTENT:
            print(f"\n--- Processing Block {i} ---")
            result = mf.process(
                block_index=i,
                mode=ProcessMode.COMPLETE,
                variables=variables
            )
            print(result.content)
        elif block.block_type == BlockType.INTERACTION:
            print(f"\n--- User Interaction Block {i} ---")
            print(block.content)
```

### Streaming with Progress Tracking

```python
from markdown_flow import MarkdownFlow, ProcessMode

def stream_with_progress():
    document = """
Generate a comprehensive Python tutorial for {{user_name}}
focusing on {{topic}} with practical examples.

Include code samples, explanations, and practice exercises.
"""

    mf = MarkdownFlow(document, llm_provider=your_provider)

    print("Starting stream processing...")
    content = ""
    chunk_count = 0

    for chunk in mf.process(
        block_index=0,
        mode=ProcessMode.STREAM,
        variables={
            'user_name': 'developer',
            'topic': 'synchronous programming'
        }
    ):
        content += chunk.content
        chunk_count += 1

        # Show progress
        if chunk_count % 10 == 0:
            print(f"Received {chunk_count} chunks, {len(content)} characters")

        # Real-time processing
        if chunk.content.endswith('\n'):
            # Process complete line
            lines = content.strip().split('\n')
            if lines:
                latest_line = lines[-1]
                # Do something with complete line
                pass

    print(f"\nStreaming complete! Total: {chunk_count} chunks, {len(content)} characters")
    return content
```

### Interactive Document Builder

```python
from markdown_flow import MarkdownFlow, BlockType, InteractionType

class InteractiveDocumentBuilder:
    def __init__(self, template: str, llm_provider):
        self.mf = MarkdownFlow(template, llm_provider)
        self.user_responses = {}
        self.current_block = 0

    def start_interaction(self):
        blocks = self.mf.get_all_blocks()

        for i, block in enumerate(blocks):
            if block.block_type == BlockType.CONTENT:
                # Process content block with current variables
                result = self.mf.process(
                    block_index=i,
                    mode=ProcessMode.COMPLETE,
                    variables=self.user_responses
                )
                print(f"\nContent: {result.content}")

            elif block.block_type == BlockType.INTERACTION:
                # Handle user interaction
                response = self.handle_interaction(block.content)
                if response:
                    self.user_responses.update(response)

    def handle_interaction(self, interaction_content: str):
        from markdown_flow.parser import InteractionParser

        interaction = InteractionParser().parse(interaction_content)
        print(f"\n{interaction_content}")

        if interaction.name == "BUTTONS_ONLY":
            print("Choose an option:")
            for i, button in enumerate(interaction.buttons, 1):
                print(f"{i}. {button}")

            choice = input("Enter choice number: ")
            try:
                selected = interaction.buttons[int(choice) - 1]
                return {interaction.variable: selected}
            except (ValueError, IndexError):
                print("Invalid choice")
                return self.handle_interaction(interaction_content)

        elif interaction.name == "TEXT_ONLY":
            response = input(f"{interaction.question}: ")
            return {interaction.variable: response}

        return {}

# Usage
template = """
Welcome! Let's create a personalized learning plan.

What's your name?
?[%{{name}} Enter your name]

Hi {{name}}! What would you like to learn?
?[%{{subject}} Python | JavaScript | Data Science | Machine Learning]

Great choice, {{name}}! {{subject}} is an excellent field to study.
"""

builder = InteractiveDocumentBuilder(template, your_llm_provider)
builder.start_interaction()
```

### Variable System Deep Dive

```python
from markdown_flow import extract_variables_from_text, replace_variables_in_text

def demonstrate_variable_system():
    # Complex document with both variable types
    document = """
    Welcome {{user_name}} to the {{course_title}} course!

    Please rate your experience: ?[%{{rating}} 1 | 2 | 3 | 4 | 5]

    Current progress: {{progress_percent}}%
    Assignment due: {{due_date}}

    Your rating of %{{rating}} helps us improve the course content.
    """

    # Extract all variables
    all_vars = extract_variables_from_text(document)
    print(f"All variables found: {all_vars}")
    # Output: {'user_name', 'course_title', 'rating', 'progress_percent', 'due_date'}

    # Replace only {{variable}} patterns, preserve %{{variable}}
    replacements = {
        'user_name': 'Alice',
        'course_title': 'Python Advanced',
        'progress_percent': '75',
        'due_date': '2024-12-15',
        'rating': '4'  # This won't be replaced due to %{{}} format
    }

    result = replace_variables_in_text(document, replacements)
    print("\nAfter replacement:")
    print(result)

    # The %{{rating}} remains unchanged for LLM processing,
    # while {{user_name}}, {{course_title}}, etc. are replaced

demonstrate_variable_system()
```

## 🌐 MarkdownFlow Ecosystem

markdown-flow-agent-py is part of the MarkdownFlow ecosystem for creating personalized, AI-driven interactive documents:

- **[markdown-flow](https://github.com/ai-shifu/markdown-flow)** - Main repository with homepage, documentation, and interactive playground
- **[markdown-flow-ui](https://github.com/ai-shifu/markdown-flow-ui)** - React component library for rendering interactive MarkdownFlow documents
- **[markdown-it-flow](https://github.com/ai-shifu/markdown-it-flow)** - markdown-it plugin to parse and render MarkdownFlow syntax
- **[remark-flow](https://github.com/ai-shifu/remark-flow)** - Remark plugin to parse and process MarkdownFlow syntax in React applications

## 💖 Sponsors

<div align="center">
  <a href="https://ai-shifu.com">
    <img src="https://raw.githubusercontent.com/ai-shifu/ai-shifu/main/assets/logo_en.png" alt="AI-Shifu" width="150" />
  </a>
  <p><strong><a href="https://ai-shifu.com">AI-Shifu.com</a></strong></p>
  <p>AI-powered personalized learning platform</p>
</div>

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Python](https://www.python.org/) for the robust programming language
- [Ruff](https://docs.astral.sh/ruff/) for lightning-fast Python linting and formatting
- [MyPy](https://mypy.readthedocs.io/) for static type checking
- [Commitizen](https://commitizen-tools.github.io/commitizen/) for standardized commit messages
- [Pre-commit](https://pre-commit.com/) for automated code quality checks

## 📞 Support

- 📖 [Documentation](https://github.com/ai-shifu/markdown-flow-agent-py#readme)
- 🐛 [Issue Tracker](https://github.com/ai-shifu/markdown-flow-agent-py/issues)
- 💬 [Discussions](https://github.com/ai-shifu/markdown-flow-agent-py/discussions)
