# AGENTS.md

This file provides comprehensive guidance to all Coding Agents such as Claude Code (claude.ai/code), GitHub Copilot, and other AI coding assistants when working with code in this repository.

## Quick Start

### Most Common Tasks

| Task | Command | Location |
|------|---------|----------|
| Install package (dev) | `pip install -e .` | Root directory |
| Run code formatting | `ruff format` | Root directory |
| Run linting | `ruff check --fix` | Root directory |
| Run pre-commit hooks | `pre-commit run --all-files` | Root directory |
| Build package | `python -m build` | Root directory |
| Run Python tests | `pytest` | Root directory (when tests exist) |
| Check installed version | `python -c "import markdown_flow; print(markdown_flow.__version__)"` | Any directory |

### Essential Dependencies

```bash
# Core dependencies (none for runtime)
# Development dependencies
pip install -e .[dev]  # When dev dependencies are configured
pip install pre-commit ruff mypy pytest  # Manual installation
```

## Critical Warnings ⚠️

### MUST DO Before Any Commit

1. **Run pre-commit hooks**: `pre-commit run --all-files` (MANDATORY)
2. **Test your changes**: Verify core functionality with test scripts
3. **Use English for all code**: Comments, variables, docstrings, commit messages
4. **Follow Conventional Commits**: `type: description` (lowercase type, imperative mood)
5. **Validate package integrity**: Ensure imports work after installation

### Common Pitfalls to Avoid

- **Don't skip pre-commit** - It catches formatting and style issues automatically
- **Don't use Chinese in code** - English only (except example data)
- **Don't hardcode API keys** - Use environment variables or config files
- **Don't modify installed packages** - Always work with editable installation (`pip install -e .`)
- **Don't commit without testing** - Verify basic functionality works
- **Don't break backward compatibility** - Ensure existing API contracts are maintained
- **Don't add unnecessary dependencies** - Keep the package lightweight

## Project Overview

MarkdownFlow Agent (Python) is a specialized library designed to parse and process MarkdownFlow documents with AI-powered intelligence to create personalized, interactive content. The tagline: **"Write Once, Deliver Personally"**.

### Key Features

- **Three-Layer Parsing Architecture**: Document → Block → Interaction level parsing
- **Variable System**: Support for `{{variable}}` (replaceable) and `%{{variable}}` (preserved) formats
- **LLM Integration**: Abstract provider interface with multiple processing modes
- **Interactive Elements**: Parse and handle `?[]` syntax for user interactions
- **Stream Processing**: Support for real-time streaming responses
- **Type Safety**: Full TypeScript-style type hints for Python development
- **Block Metadata**: Automatic `block_type` and `block_index` in all LLMResult metadata
- **Instance-Level Config**: Per-instance model and temperature configuration with chainable API
- **Built-in Provider**: Production-ready OpenAI-compatible provider with debug mode and token tracking
- **Modular Architecture**: Clean `parser/` module structure replacing monolithic `utils.py`

## Architecture

The project follows a clean, modular architecture with clear separation of concerns:

### Core Components

**MarkdownFlow (`core.py`)** - Main processing engine

- Parses MarkdownFlow documents into structured blocks
- Handles LLM interactions through unified `process()` interface
- Manages variable substitution and preservation

**Three-Layer Parsing Architecture:**

1. **Document Level**: Splits content using `---` separators and `?[]` interaction patterns
2. **Block Level**: Categorizes blocks as CONTENT, INTERACTION, or PRESERVED_CONTENT
3. **Interaction Level**: Parses `?[]` formats into TEXT_ONLY, BUTTONS_ONLY, BUTTONS_WITH_TEXT, BUTTONS_MULTI_SELECT, BUTTONS_MULTI_WITH_TEXT, or NON_ASSIGNMENT_BUTTON types

**LLM Integration (`llm.py`)** - Abstract provider interface

- `COMPLETE`: Non-streaming LLM processing
- `STREAM`: Streaming LLM responses

**Parser Modules (`parser/`)** - Modular parsing utilities

- `variable.py` - Variable extraction and replacement
- `interaction.py` - Interaction parsing (6 types) and validation
- `output.py` - Output instructions and preserved content processing
- `validation.py` - Template generation and response parsing
- `json_parser.py` - JSON parsing with code block support
- `code_fence_utils.py` - CommonMark-compliant code fence parsing utilities
- `preprocessor.py` - Code block preprocessor for syntax protection

**Providers (`providers/`)** - Built-in LLM provider implementations

- `openai.py` - Production-ready OpenAI-compatible provider
- `config.py` - Provider configuration with environment variable support

### Module Structure

```text
markdown_flow/
├── __init__.py              # Public API exports and version
├── core.py                  # MarkdownFlow main class with instance-level config
├── enums.py                 # Type definitions (BlockType, InputType)
├── exceptions.py            # Custom exception classes
├── llm.py                   # LLM provider abstract interface
├── models.py                # Data classes and models
├── constants.py             # Pre-compiled regex patterns and constants
├── parser/                  # Modular parsing components
│   ├── __init__.py         # Parser module exports
│   ├── variable.py         # Variable extraction and replacement
│   ├── interaction.py      # Interaction parsing (6 types)
│   ├── output.py           # Output instructions and preserved content
│   ├── validation.py       # Validation templates and parsing
│   └── json_parser.py      # JSON parsing utilities
└── providers/               # Built-in provider implementations
    ├── __init__.py         # Provider module exports
    ├── config.py           # ProviderConfig class
    └── openai.py           # OpenAIProvider implementation
```

## Development Commands

### Package Management

```bash
# Development installation (editable)
pip install -e .

# Build package for distribution
python -m build

# Install from built package (for testing)
pip install dist/markdown_flow-*.whl

# Uninstall package
pip uninstall markdown-flow

# Check package structure
python -c "import markdown_flow; print(dir(markdown_flow))"

# Verify imports work correctly
python -c "from markdown_flow import MarkdownFlow, ProcessMode; print('Import successful')"
```

### Code Quality

```bash
# Install pre-commit hooks (first time)
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files

# Run pre-commit on modified files only
pre-commit run

# Ruff linting with auto-fix (replaces Flake8 + isort + more)
ruff check --fix

# Ruff formatting (replaces Black)
ruff format

# All-in-one linting and formatting
ruff check --fix && ruff format

# MyPy type checking (when configured)
mypy markdown_flow/
```

### Commitizen (Version Management)

```bash
# Install commitizen (first time)
pip install commitizen

# Check current version
cz version

# Bump version and create changelog (automatically follows semver)
cz bump --increment PATCH    # Bug fixes (0.1.5 -> 0.1.6)
cz bump --increment MINOR    # New features (0.1.5 -> 0.2.0)
cz bump --increment MAJOR    # Breaking changes (0.1.5 -> 1.0.0)

# Automatic version bump based on commit messages
cz bump                      # Auto-detect increment level

# Generate/update changelog
cz changelog

# Validate commit message format
cz check --rev-range HEAD~1..HEAD

# Interactive commit with conventional format
cz commit
```

### Testing

```bash
# Run tests (when test suite exists)
pytest

# Run tests with coverage
pytest --cov=markdown_flow --cov-report=html

# Run specific test file
pytest tests/test_core.py

# Run tests with verbose output
pytest -v

# Run tests and stop on first failure
pytest -x

# Run tests for specific functionality
pytest -k "test_extract_variables"
```

### Development Utilities

```bash
# Check version info
python -c "import markdown_flow; print(f'Version: {markdown_flow.__version__}')"

# Test core functionality
python -c "
from markdown_flow import MarkdownFlow, ProcessMode
doc = 'Hello {{name}}!\n\n?[%{{response}} Yes|No]'
mf = MarkdownFlow(doc)
print('Blocks:', len(mf.get_all_blocks()))
print('Variables:', mf.extract_variables())
"

# Validate package build
python -c "
import subprocess
import sys
result = subprocess.run([sys.executable, '-m', 'build'], capture_output=True, text=True)
print('Build result:', 'SUCCESS' if result.returncode == 0 else 'FAILED')
if result.stderr: print('Errors:', result.stderr)
"
```

## Key Features 🎉

### 1. Block Type Metadata

All `LLMResult` objects now automatically include block metadata:

```python
result = mf.process(0, mode=ProcessMode.COMPLETE, variables=vars)

# result.metadata automatically contains:
# - block_type: "content" | "interaction" | "preserved_content"
# - block_index: 0-based index of the block
```

**Use Case**: Build custom output formatters based on block type.

### 2. Instance-Level Model Configuration

Configure model and temperature per-instance with chainable API:

```python
from markdown_flow import MarkdownFlow

# Create instances with different configs
mf_creative = MarkdownFlow(creative_doc, provider)
mf_creative.set_model("gpt-4").set_temperature(0.9)

mf_factual = MarkdownFlow(factual_doc, provider)
mf_factual.set_model("gpt-3.5-turbo").set_temperature(0.1)

# Override per-instance
result = mf_creative.process(0, mode=ProcessMode.COMPLETE, variables=vars)
# Uses: model="gpt-4", temperature=0.9
```

**Priority**: Instance config > Provider default

### 3. Built-in OpenAI Provider

Production-ready provider with comprehensive features:

```python
from markdown_flow.providers import create_provider, create_default_provider, ProviderConfig

# Option 1: Environment variables (LLM_API_KEY, LLM_MODEL, etc.)
provider = create_default_provider()

# Option 2: Explicit configuration
provider = create_provider(ProviderConfig(
    api_key="sk-...",
    base_url="https://api.openai.com/v1",
    model="gpt-4",
    temperature=0.7,
    debug=True,  # Enable colorized console output
    timeout=None  # No timeout (recommended for streaming), or set to seconds (e.g., 300.0)
))

# Use with MarkdownFlow
mf = MarkdownFlow(document, provider)
result = mf.process(0, mode=ProcessMode.COMPLETE)

# Access provider metadata
print(f"Tokens used: {result.metadata['total_tokens']}")
print(f"Processing time: {result.metadata['processing_time']}ms")
```

**Features**:

- ✅ Debug mode with colorized request/response output
- ✅ Automatic token tracking (prompt/output/total)
- ✅ Processing time measurement
- ✅ Comprehensive metadata
- ✅ Environment variable defaults
- ✅ Streaming and non-streaming modes

### 4. Modular Parser Architecture

Clean separation of parsing concerns:

```python
# Import from parser module
from markdown_flow.parser import (
    extract_variables_from_text,
    replace_variables_in_text,
    InteractionParser,
    InteractionType,
    process_output_instructions,
    generate_smart_validation_template,
    parse_validation_response,
    parse_json_response
)

# Each parser module is focused and maintainable
parser = InteractionParser()
result = parser.parse("?[%{{choice}} Yes|No]")
```

**Migration Note**: Replace `from markdown_flow.utils import ...` with `from markdown_flow.parser import ...`

### 5. Provider Metadata Propagation

LLM provider metadata automatically merged into results:

```python
result = mf.process(0, mode=ProcessMode.COMPLETE, variables=vars)

# Available in result.metadata:
{
    "block_type": "content",
    "block_index": 0,
    "model": "gpt-4",
    "temperature": 0.7,
    "provider": "openai-compatible",
    "prompt_tokens": 150,
    "output_tokens": 45,
    "total_tokens": 195,
    "processing_time": 1234,  # milliseconds
    "timestamp": 1730851200
}
```

## API Reference

### Core Classes

**MarkdownFlow** - Main processing class

- `__init__(content: str, llm_provider: LLMProvider = None)`
- `get_all_blocks() -> List[Block]`
- `extract_variables() -> Set[str]`
- `process(block_index: int, mode: ProcessMode, variables: dict[str, str | list[str]] = None, user_input: dict[str, list[str]] = None)`

**ProcessMode** - Processing mode enumeration

- `COMPLETE`: Non-streaming LLM processing
- `STREAM`: Streaming LLM responses

**BlockType** - Block type enumeration

- `CONTENT`: Regular markdown content processed by LLM
- `INTERACTION`: User input blocks with `?[]` syntax requiring validation
- `PRESERVED_CONTENT`: Output-as-is blocks using inline `===content===` or multiline fences `!===` ... `!===` (3+ `=`)

**InteractionType** - Interaction format enumeration

- `TEXT_ONLY`: `?[%{{var}}...question]` - Text input with question
- `BUTTONS_ONLY`: `?[%{{var}} A|B]` - Button selection only
- `BUTTONS_WITH_TEXT`: `?[%{{var}} A|B|...question]` - Buttons with fallback text input
- `BUTTONS_MULTI_SELECT`: `?[%{{var}} A||B||C]` - Multi-select buttons using `||` separator
- `BUTTONS_MULTI_WITH_TEXT`: `?[%{{var}} A||B||...question]` - Multi-select buttons with text fallback
- `NON_ASSIGNMENT_BUTTON`: `?[Continue|Cancel]` - Display buttons without variable assignment

### Utility Functions

**Variable Management**

- `extract_variables_from_text(text: str) -> Set[str]`
- `replace_variables_in_text(text: str, variables: dict) -> str`

**Interaction Processing**

- `InteractionParser.parse(content: str) -> InteractionType`
- `extract_interaction_question(content: str) -> str`
- `generate_smart_validation_template(interaction_type: InteractionType) -> str`

## Variable System

### Two Variable Formats

**Replaceable Variables: `{{variable}}`**

- Get substituted with actual values during processing
- Used for content personalization
- Example: `Hello {{name}}!` → `Hello John!`

**Preserved Variables: `%{{variable}}`**

- Kept in original format for LLM understanding
- Used in interaction blocks for assignment
- Example: `?[%{{level}} Beginner|Expert]` stays as-is

### Variable Extraction

```python
from markdown_flow import extract_variables_from_text

text = "Hello {{name}}! Your level: ?[%{{level}} Beginner|Expert]"
variables = extract_variables_from_text(text)
# Returns: {'name', 'level'}
```

### Variable Replacement

```python
from markdown_flow import replace_variables_in_text

text = "Hello {{name}}! You are {{age}} years old."
result = replace_variables_in_text(text, {'name': 'John', 'age': '25'})
# Returns: "Hello John! You are 25 years old."
```

### Multi-Select Variable Values

Multi-select interactions support list values for variables:

```python
# Single value (traditional)
variables = {'level': 'Beginner'}

# Multiple values (multi-select)
variables = {'skills': ['Python', 'JavaScript', 'Go']}

# Mixed types supported
variables = {
    'name': 'John',                    # str
    'skills': ['Python', 'JavaScript'], # list[str]
    'experience': 'Senior'             # str
}
```

**User Input Format**

Multi-select user input uses `dict[str, list[str]]` format:

```python
# Traditional single selection
user_input = {'level': ['Beginner']}

# Multi-select
user_input = {'skills': ['Python', 'JavaScript', 'Go']}

# Multiple variables
user_input = {
    'skills': ['Python', 'JavaScript'],
    'experience': ['Senior']
}
```

## Interaction Formats

### Supported Patterns

**Text Input Only**

```markdown
?[%{{variable}} What is your question?]
```

**Button Selection Only**

```markdown
?[%{{level}} Beginner|Intermediate|Expert]
```

**Buttons with Text Fallback**

```markdown
?[%{{preference}} Option A|Option B|Please specify your preference]
```

**Multi-Select Buttons**

```markdown
?[%{{skills}} Python||JavaScript||Go||Rust]
```

**Multi-Select with Text Fallback**

```markdown
?[%{{frameworks}} React||Vue||Angular||Please specify other frameworks]
```

**Display-Only Buttons**

```markdown
?[Continue|Cancel|Go Back]
```

### Button Value Separation

Support for display text different from stored value:

```markdown
?[%{{choice}} Yes//1|No//0|Maybe//2]
```

### Button Translation Best Practices ⭐

**Problem Scenario:** When interaction blocks need translation, button text changes, causing validation failures.

```markdown
Original interaction: ?[%{{fruit}} 苹果|香蕉|橙子]
Translated (English): ?[%{{fruit}} Apple|Banana|Orange]

User sees "Apple" in frontend and selects it
Returns user_input: {"fruit": ["Apple"]}
Validation compares against original document "苹果" → ❌ Validation fails
```

**Solution 1: Automatic Value Conversion ⚡**

MarkdownFlow supports **automatic translation detection and value addition**, no manual document format modification needed:

```markdown
# Original document (unchanged)
?[%{{fruit}} 苹果|香蕉|橙子]

# After translation (automatic value addition)
?[%{{fruit}} Apple//苹果|Banana//香蕉|Orange//橙子]
```

**How It Works:**
1. Detects translation occurred (苹果 → Apple)
2. Automatically adds value separation: `Apple//苹果`
3. Display = Translated text (Apple), Value = Original text (苹果)
4. User selects "Apple", frontend extracts value = "苹果"
5. Validation compares against original document: 苹果 is in [苹果, 香蕉, 橙子] ✅
6. Business layer receives stable original Chinese values

**Key Advantages:**
- ✅ Zero configuration: No need to modify existing documents
- ✅ Smart detection: Only adds when translation occurs
- ✅ Backward compatible: Existing display//value format remains unchanged
- ✅ Business layer stability: Always receives original Chinese values

**Solution 2: Manual display//value Separation Format**

Manually specify stable values (for scenarios requiring custom values):

```markdown
# Recommended format
?[%{{fruit}} 苹果//apple|香蕉//banana|橙子//orange]

# After translation
?[%{{fruit}} Apple//apple|Banana//banana|Orange//orange]

# User selects "Apple", but returns stable value: "apple"
user_input: {"fruit": ["apple"]}  ✅ Validation succeeds
```

**Core Principles:**

1. **Display (Display Text)**: Will be translated, used for frontend presentation
2. **Value (Stored Value)**: Remains unchanged, used for validation and business logic
3. **Value Naming Suggestion**: Use lowercase English with underscore separation for stability

**Complete Examples:**

```python
# Python version - Automatic value conversion
from markdown_flow import MarkdownFlow
from markdown_flow.providers import create_provider, ProviderConfig

# Create Provider
provider = create_provider(ProviderConfig(
    api_key="your-api-key",
    base_url="https://api.siliconflow.cn/v1",
    model="deepseek-ai/DeepSeek-V3.1",
    temperature=0.3,
))

# Original document (no value separation)
document = "?[%{{fruit}} 苹果|香蕉|橙子]"
mf = MarkdownFlow(document, llm_provider=provider)
mf.set_prompt("document", "Please use English")

# Render phase: Automatically add value
render_result = mf.process(0)
# Result: ?[%{{fruit}} Apple//苹果|Banana//香蕉|Orange//橙子]
print(render_result.content)

# Input phase: User selects "Apple", frontend extracts value = "苹果"
user_input = {"fruit": ["苹果"]}
validation_result = mf.process(0, user_input=user_input)
# validation_result.variables["fruit"] = ["苹果"]  ✅
print(validation_result.variables["fruit"])  # Output: ['苹果']
```

```python
# Python version - Manual display//value format
document = "?[%{{level}} 初级//beginner|中级//intermediate|高级//advanced]"
mf = MarkdownFlow(document, llm_provider=provider)
mf.set_prompt("document", "Please use English")

# Render phase: Translate Display, keep Value
render_result = mf.process(0)
# Result: ?[%{{level}} Beginner//beginner|Intermediate//intermediate|Advanced//advanced]

# Input phase: User selects "Beginner", returns value: "beginner"
user_input = {"level": ["beginner"]}
validation_result = mf.process(0, user_input=user_input)
# validation_result.variables["level"] = ["beginner"]  ✅
```

**Value Naming Best Practices:**

| Scenario | Display (Chinese) | Value (Recommended) |
|----------|-------------------|---------------------|
| Difficulty Level | 初级/中级/高级 | beginner/intermediate/advanced |
| Yes/No Selection | 是/否 | yes/no or true/false or 1/0 |
| Fruit Selection | 苹果/香蕉/橙子 | apple/banana/orange |
| Role Selection | 小兔子/小松鼠 | rabbit/squirrel or role_rabbit/role_squirrel |

**Testing & Validation:**

```bash
# Test automatic value conversion
cd tests/demo && python test_auto_value_conversion.py

# Test manual display//value format (if exists)
cd tests/demo && python test_button_value_separation.py

# Run all interaction-related tests
pytest tests/ -k "interaction" -v
```

**Solution Comparison:**

| Feature | Automatic Conversion (v1.0+) | Manual display//value |
|---------|------------------------------|----------------------|
| Document Modification | Not required | Required |
| Value Type | Original Chinese | Custom (e.g., English, numbers) |
| Use Cases | General scenarios | Scenarios requiring stable English values |
| Business Layer Impact | Receives original Chinese values | Receives custom values |

**Recommended Approach:**
- ✅ New projects: Use original format directly, let automatic conversion handle it
- ✅ Existing projects: Keep existing display//value format unchanged (automatic detection skips)
- ✅ Need English values: Manually specify display//value format

## Code Block Processing

### Overview

MarkdownFlow supports syntax-ignoring functionality for Markdown code blocks. MarkdownFlow syntax (`===`, `?[]`, `---`) inside code blocks will not be parsed, allowing safe demonstration of code examples in documents.

### Supported Code Block Formats

**Fenced Code Blocks:**

Supports two standard Markdown fence formats:

1. **Backtick Fences** (`` ``` ``)
2. **Tilde Fences** (`~~~`)

**CommonMark Specification Compliant:**

- Fence Length: At least 3 characters (`` ``` `` or `~~~`), can be longer
- Indentation: Maximum 3 spaces
- Info String: Supports language identifiers (e.g., `` ```python ``、`~~~markdown`)
- Closing Fence: Must be same type, length ≥ opening fence

### How It Works

**Preprocessing Mechanism:**

```
Raw Document
  ↓
Code Block Preprocessor (CodeBlockPreprocessor)
  ↓ State machine scanning
  ↓ Extract code blocks → Replace with placeholders
  ↓
Preprocessed Document
  ↓
Block Parser (BlockParser)
  ↓ Normal parsing (code blocks protected by placeholders)
  ↓
Parsed Block Structure
```

**Core Flow:**

1. **Extract Phase**: Preprocessor runs automatically during `MarkdownFlow()` initialization
2. **Placeholder Replacement**: Code blocks replaced with `__MDFLOW_CODE_BLOCK_N__` format placeholders
3. **Normal Parsing**: Block parser processes preprocessed document
4. **Transparent Handling**: Completely transparent to users, no additional configuration needed

### Usage Examples

**Tutorial Document Example:**

```markdown
# MarkdownFlow Syntax Tutorial

?[%{{ready}} Ready|Need Help]

---

## Interaction Syntax Example

Below shows how to use interaction syntax:

` + "```markdown" + `
?[%{{choice}} Option A|Option B|Option C]
` + "```" + `

---

?[%{{next}} Continue Learning|Exit]
```

**Parse Results:**
- ✅ Recognizes 2 interaction blocks (outside code blocks)
- ✅ `?[%{{choice}}...]` inside code block not parsed
- ✅ Recognizes 2 block separators (`---` inside code blocks ignored)

**API Documentation Example:**

```markdown
# API Request Example

?[%{{format}} JSON|XML]

---

` + "```bash" + `
curl -X POST https://api.example.com/data \
  -d '{
    "filter": "=== active ===",
    "query": "?[Sample Content]"
  }'
` + "```" + `
```

**Parse Results:**
- ✅ MarkdownFlow syntax in JSON strings not parsed
- ✅ Variable extraction excludes code block content

### Implementation Details

**State Machine Design:**

```python
STATE_NORMAL = "NORMAL"              # Normal content
STATE_IN_CODE_BLOCK = "IN_CODE_BLOCK"  # Inside code block

# Fence information
@dataclass
class FenceInfo:
    char: str      # '`' or '~'
    length: int    # Fence length (≥3)
    indent: int    # Indent spaces (≤3)
```

**Key Features:**

1. **Strict Fence Matching**
   - Closing fence must use same type character as opening fence
   - Closing fence length must be ≥ opening fence length
   - Mixed types (`` ``` `` opening, `~~~` closing) don't match

2. **Unclosed Code Block Handling**
   - Unclosed code blocks remain as-is
   - Won't be misidentified as fenced code blocks

3. **Performance Optimization**
   - Precompiled regular expressions
   - Single document traversal
   - Placeholder mechanism avoids re-parsing

### Testing & Validation

**Unit Tests (`tests/test_preprocessor.py`):**

```bash
# Run preprocessor unit tests
python -m pytest tests/test_preprocessor.py -v
```

**Test Coverage:**
- ✅ Basic backtick fences
- ✅ Tilde fences
- ✅ Code blocks with language identifiers
- ✅ Multiple code blocks
- ✅ Code blocks containing MarkdownFlow syntax
- ✅ Unclosed code blocks
- ✅ Empty code blocks
- ✅ Long fences (4+ characters)
- ✅ Indented code blocks (0-3 spaces)
- ✅ Mixed fence types (non-matching scenarios)

**Integration Tests:**

```python
from markdown_flow import MarkdownFlow

document = """
` + "```markdown" + `
?[%{{example}} Should not be parsed]
` + "```" + `

---

?[%{{real}} Will be parsed]
"""

mf = MarkdownFlow(document)
blocks = mf.get_all_blocks()

# Verify:
# - Code block content replaced with placeholder
# - Only outside ?[] parsed as interaction block
```

**Validation Content:**
- ✅ `?[]` syntax inside code blocks not parsed as interaction blocks
- ✅ `===` syntax inside code blocks not parsed as preserved content
- ✅ `---` inside code blocks not parsed as block separators
- ✅ Syntax outside code blocks works normally
- ✅ Variable extraction excludes code block content

### Notes

**Limitations:**

1. **Indented Code Blocks Not Supported**
   - Only supports fenced code blocks (`` ``` `` and `~~~`)
   - Traditional 4-space indent code blocks not supported

2. **Nested Code Blocks Not Supported**
   - Fence markers inside code blocks treated as plain text
   - To display nesting, use longer outer fence:

```markdown
` + "````markdown" + `
` + "```python" + `
print('nested')
` + "```" + `
` + "````" + `
```

3. **Automatic Processing**
   - Preprocessing happens automatically
   - No manual control over enable/disable
   - All fenced code blocks will be extracted

### Architecture Files

**Related Files:**

- `markdown_flow/constants.py` - Code fence regex patterns
- `markdown_flow/parser/code_fence_utils.py` - Fence parsing utilities
- `markdown_flow/parser/preprocessor.py` - Code block preprocessor
- `markdown_flow/core.py` - Integration point
- `tests/test_preprocessor.py` - Unit tests

## Testing Guidelines

### Test File Structure

```text
tests/                          # Test suite (46 unit tests)
├── conftest.py                # Shared fixtures
├── test_markdownflow_basic.py # MarkdownFlow core tests (21 tests)
├── test_parser_variable.py    # Variable parser tests (13 tests)
├── test_parser_interaction.py # Interaction parser tests (12 tests)
├── test_models.py            # Data model tests
├── test_llm.py               # Custom LLM provider for testing
├── test_enums.py             # Enumeration tests
└── fixtures/
    ├── test_documents.py     # Test document fixtures
    └── sample_documents/     # Sample MarkdownFlow files
```

### Test Patterns

```python
# Test file naming: test_[module].py
# Test function naming: test_[function]_[scenario]

import pytest
from unittest.mock import AsyncMock, MagicMock
from markdown_flow import MarkdownFlow, ProcessMode, BlockType

class TestMarkdownFlow:
    """Group related tests in classes"""

    @pytest.fixture
    def sample_document(self):
        """Provide test fixtures"""
        return """
        Ask {{name}} about their experience.

        ?[%{{level}} Beginner|Intermediate|Expert]

        The user chose {{level}} level.
        """

    @pytest.fixture
    def mock_llm_provider(self):
        """Mock LLM provider for testing"""
        mock = AsyncMock()
        mock.complete.return_value = "Mock response"
        return mock

    def test_extract_variables_success(self, sample_document):
        """Test successful variable extraction"""
        # Arrange
        mf = MarkdownFlow(sample_document)

        # Act
        variables = mf.extract_variables()

        # Assert
        assert "name" in variables
        assert "level" in variables
        assert len(variables) == 2

    def test_get_all_blocks_parsing(self, sample_document):
        """Test document parsing into blocks"""
        # Arrange
        mf = MarkdownFlow(sample_document)

        # Act
        blocks = mf.get_all_blocks()

        # Assert
        assert len(blocks) == 3
        assert blocks[0].block_type == BlockType.CONTENT
        assert blocks[1].block_type == BlockType.INTERACTION
        assert blocks[2].block_type == BlockType.CONTENT

    def test_process_with_mock_llm(self, sample_document, mock_llm_provider):
        """Test processing with mocked LLM"""
        # Arrange
        mf = MarkdownFlow(sample_document, llm_provider=mock_llm_provider)
        variables = {"name": "John", "level": "Beginner"}

        # Act
        result = mf.process(0, mode=ProcessMode.COMPLETE, variables=variables)

        # Assert
        assert result.content == "Mock response"
        mock_llm_provider.complete.assert_called_once()

    def test_interaction_parsing(self):
        """Test interaction format parsing"""
        # Arrange
        from markdown_flow.utils import InteractionParser
        content = "%{{level}} Beginner|Intermediate|Expert"

        # Act
        interaction_type = InteractionParser.parse(content)

        # Assert
        assert interaction_type.name == "BUTTONS_ONLY"
        assert len(interaction_type.buttons) == 3
        assert interaction_type.variable == "level"

    def test_variable_replacement(self):
        """Test variable replacement functionality"""
        # Arrange
        from markdown_flow import replace_variables_in_text
        text = "Hello {{name}}! You are {{age}} years old."
        variables = {"name": "Alice", "age": "30"}

        # Act
        result = replace_variables_in_text(text, variables)

        # Assert
        assert result == "Hello Alice! You are 30 years old."

    def test_preserved_variables_not_replaced(self):
        """Test that preserved variables are not replaced"""
        # Arrange
        from markdown_flow import replace_variables_in_text
        text = "Select: ?[%{{level}} High|Low] and name: {{name}}"
        variables = {"level": "High", "name": "Bob"}

        # Act
        result = replace_variables_in_text(text, variables)

        # Assert
        assert "%{{level}}" in result  # Preserved
        assert "{{name}}" not in result  # Replaced
        assert "Bob" in result
```

### Coverage Requirements

- Aim for >80% code coverage on new code
- Critical paths (core processing logic) must have 100% coverage
- Run coverage: `pytest --cov=markdown_flow --cov-report=html`

## Code Quality Guidelines

### English-Only Policy

**All code-related content MUST be written in English** to ensure consistency, maintainability, and international collaboration.

#### What MUST be in English

- **Code comments**: All inline comments, block comments, and docstrings
- **Variable and function names**: All identifiers in the code
- **Constants and enums**: All constant values and enumeration names
- **Log messages**: All logging statements and debug information
- **Error messages in code**: Internal error messages and exception messages
- **Git commit messages**: MUST use Conventional Commits format in English
- **Documentation**: README files, API documentation, code architecture docs

#### Exceptions

- **Test data**: Test data can be in any language for internationalization testing
- **Example content**: MarkdownFlow documents used as examples can contain non-English content

### Conventional Commits Format

**Required Format**: `<type>: <description>` (e.g., `feat: add stream processing support`)

**Common Types**:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `refactor:` - Code refactoring
- `test:` - Tests
- `chore:` - Maintenance
- `perf:` - Performance improvements
- `style:` - Formatting (no code change)
- `ci:` - CI configuration
- `build:` - Build system or dependencies

**Style Rules**:

- Type must be lowercase
- Use imperative mood ("add", not "added")
- Keep subject line ≤72 characters
- No trailing period
- English only

### File Naming Conventions

**Python Modules**: Use snake_case

- ✅ Correct: `markdown_flow/`, `core.py`, `parser/variable.py`
- ❌ Wrong: `MarkdownFlow/`, `Core.py`, `utilsHelper.py`

**Test Files**: Use `test_` prefix

- ✅ Correct: `test_markdownflow_basic.py`, `test_parser_variable.py`
- ❌ Wrong: `core_test.py`, `CoreTests.py`, `parserTests.py`

**Configuration Files**: Use lowercase with dots

- ✅ Correct: `.gitignore`, `pyproject.toml`, `.pre-commit-config.yaml`
- ❌ Wrong: `GitIgnore`, `PyProject.TOML`

**Documentation**: Use kebab-case

- ✅ Correct: `api-reference.md`, `user-guide.md`
- ❌ Wrong: `apiReference.md`, `user_guide.md`

### Pre-commit Hooks

The project uses comprehensive pre-commit hooks for code quality:

**Automatic Checks**:

- End-of-file fixer
- Trailing whitespace removal
- YAML syntax validation
- Python syntax validation
- JSON formatting
- Ruff linting and formatting
- MyPy type checking (when configured)

**Manual Execution**:

```bash
# Install hooks (first time)
pre-commit install

# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run
```

## Performance Guidelines

### Python-Specific Optimizations

**Pre-compiled Regex Patterns**: All regex patterns in `constants.py` are pre-compiled for performance

```python
# Good: Pre-compiled pattern (done in constants.py)
COMPILED_VARIABLE_PATTERN = re.compile(r'{{(.+?)}}')

# Bad: Compiling pattern repeatedly
result = re.findall(r'{{(.+?)}}', text)  # Compiles every time
```

**Lazy Evaluation**: Use generators and lazy evaluation for large document processing

```python
# Good: Generator for memory efficiency
def get_blocks():
    for block in document_parts:
        yield process_block(block)

# Bad: Loading everything into memory
blocks = [process_block(block) for block in document_parts]
```

**Memory Management**: Clear large objects when no longer needed

```python
# Good: Explicit cleanup
large_document = load_document()
result = process_document(large_document)
del large_document  # Free memory
return result
```

**Synchronous Processing**: The library uses synchronous patterns for simplicity and compatibility

```python
# Synchronous processing
def process_with_llm(content):
    result = llm_provider.complete(content)
    return result

# Streaming with generators
def process_stream(content):
    for chunk in llm_provider.stream(content):
        yield chunk
```

### LLM Integration Optimization

**Connection Reuse**: Reuse LLM connections across requests

```python
# Good: Reuse provider instance
class MarkdownFlow:
    def __init__(self, content, llm_provider=None):
        self.llm_provider = llm_provider  # Reuse connection
```

**Error Handling**: Implement retry logic with exponential backoff

```python
import time
import random

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait_time)
```

**Token Optimization**: Minimize prompt tokens while maintaining functionality

```python
# Good: Concise prompt with essential context
prompt = f"Process: {content[:500]}..."  # Truncate if too long

# Bad: Sending full context unnecessarily
prompt = f"Please process the following content: {full_content}"
```

### Document Processing

**Stream Processing**: Use streaming for large documents when possible

```python
# Good: Streaming response
def process_stream(self, block_index: int):
    for chunk in self.llm_provider.stream(prompt):
        yield chunk

# Bad: Loading full response into memory
def process_complete(self, block_index: int):
    full_response = self.llm_provider.complete(prompt)
    return full_response
```

**Caching**: Cache parsed blocks and variable extractions

```python
from functools import lru_cache

class MarkdownFlow:
    @lru_cache(maxsize=128)
    def extract_variables(self):
        # Expensive variable extraction
        return self._parse_variables()
```

## Development Workflow

### Branch Naming

**Feature Development**:

- `feat/description-of-feature` - New feature development
- `feat/add-streaming-support` - Adding streaming capabilities
- `feat/improve-variable-parsing` - Enhancing variable parsing

**Bug Fixes**:

- `fix/description-of-fix` - Bug fix
- `fix/interaction-parsing-error` - Fix interaction parsing issue
- `fix/memory-leak-in-processing` - Fix memory leak

**Refactoring**:

- `refactor/description` - Code refactoring
- `refactor/simplify-core-logic` - Simplify core processing logic
- `refactor/extract-utilities` - Extract utility functions

**Documentation**:

- `docs/description` - Documentation updates
- `docs/update-api-reference` - Update API documentation
- `docs/add-usage-examples` - Add usage examples

### Pull Request Checklist

**Before Creating PR**:

- [ ] Code follows project conventions
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)
- [ ] Tests added/updated and passing
- [ ] Version updated if needed (in `__init__.py`)
- [ ] Documentation updated if needed
- [ ] No hardcoded secrets or API keys
- [ ] Package builds successfully (`python -m build`)
- [ ] Imports work correctly after installation

**PR Title and Description**:

- [ ] Title follows Conventional Commits format
- [ ] Description explains what and why
- [ ] Breaking changes clearly documented
- [ ] Examples provided for new features

**Code Review Requirements**:

- [ ] All conversations resolved
- [ ] No merge conflicts
- [ ] CI/CD checks passing
- [ ] At least one approval from maintainer

### Release Process

1. **Version Update**: Update version in `markdown_flow/__init__.py`
2. **Changelog**: Update CHANGELOG.md with new features and fixes
3. **Testing**: Run comprehensive tests on multiple Python versions
4. **Build**: Create distribution packages (`python -m build`)
5. **Tag**: Create git tag with version number
6. **Release**: Publish to PyPI

```bash
# Example release workflow
git checkout main
git pull origin main
# Update version in __init__.py
python -m build
twine check dist/*
git add .
git commit -m "chore: bump version to 0.1.6"
git tag v0.1.6
git push origin main --tags
twine upload dist/*
```

## Environment Configuration

### Development Environment Setup

**Python Version**: Python 3.10+ required

- Project supports Python 3.10, 3.11, 3.12
- Use `pyproject.toml` for dependency management
- No runtime dependencies (lightweight package)

**Development Dependencies** (manual installation):

```bash
pip install pre-commit ruff mypy pytest pytest-cov
```

**Environment Variables** (for development):

```bash
# LLM Provider Configuration (using built-in OpenAI provider)
export LLM_API_KEY="sk-..."                          # Required: Your API key
export LLM_BASE_URL="https://api.openai.com/v1"     # Optional: API endpoint
export LLM_MODEL="gpt-4"                             # Optional: Model name (default: gpt-3.5-turbo)
export LLM_TEMPERATURE="0.7"                         # Optional: Temperature 0.0-2.0 (default: 0.7)
export LLM_DEBUG="true"                              # Optional: Enable debug output (default: false)
export LLM_TIMEOUT="300"                             # Optional: Timeout in seconds (default: None, no timeout)

# Legacy: For testing with other LLM providers
export OPENAI_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"

# Development flags
export PYTHONPATH="${PYTHONPATH}:."
export PYTHONDONTWRITEBYTECODE=1  # Prevent .pyc files
```

### IDE Configuration

**VS Code** (`settings.json`):

```json
{
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "none",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll": true,
            "source.organizeImports": true
        }
    },
    "python.testing.pytestEnabled": true
}
```

**PyCharm/IntelliJ**:

- Enable Ruff plugin for linting and formatting
- Configure pytest as test runner
- Enable pre-commit plugin

## Error Handling and Debugging

### Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| `ModuleNotFoundError: No module named 'markdown_flow'` | Import fails | Run `pip install -e .` in project root |
| Pre-commit hooks fail | Git commit rejected | Run `pre-commit install` then `pre-commit run --all-files` |
| Import errors during development | Module not found | Ensure editable install: `pip install -e .` |
| LLM provider errors | Processing fails | Check API keys and network connectivity |
| Variable replacement not working | Variables not substituted | Verify variable names match exactly (case-sensitive) |
| Interaction parsing fails | Syntax errors | Check `?[]` syntax is correctly formatted |
| Performance issues with large documents | Slow processing | Enable streaming mode and optimize batch sizes |
| Type checking errors | MyPy warnings | Add proper type hints to function signatures |
| Commitizen not found | `cz: command not found` | Install commitizen: `pip install commitizen` |
| Commit message validation fails | Pre-commit hook rejects commit | Use conventional format: `type: description` or run `cz commit` |
| Version bump fails | `cz bump` command errors | Check `cz.json` configuration and ensure clean git state |

### Debug Commands

```bash
# Check Python environment
python --version
pip list | grep markdown-flow
which python

# Validate package installation
python -c "import markdown_flow; print('Package imported successfully')"

# Check pre-commit status
pre-commit --version
git status

# Test document parsing
python -c "
from markdown_flow import MarkdownFlow
mf = MarkdownFlow('Hello {{name}}!\n\n?[%{{response}} Yes|No]')
print('Blocks:', len(mf.get_all_blocks()))
print('Variables:', mf.extract_variables())
"

# Verify LLM integration (with mock)
python -c "
from markdown_flow.llm import ProcessMode
print('ProcessMode.COMPLETE:', ProcessMode.COMPLETE)
print('ProcessMode.STREAM:', ProcessMode.STREAM)
"

# Check regex patterns compilation
python -c "
from markdown_flow.constants import *
print('Compiled patterns loaded successfully')
print('Pattern count:', len([var for var in dir() if 'COMPILED' in var]))
"

# Test core functionality end-to-end
python -c "
from markdown_flow import MarkdownFlow, ProcessMode
from unittest.mock import MagicMock

doc = '''Hello {{name}}!

---

?[%{{level}} Beginner|Expert]

---

You selected {{level}}.'''

mock_llm = MagicMock()
mock_llm.complete.return_value = 'Mock LLM response'

mf = MarkdownFlow(doc, llm_provider=mock_llm)
print('Variables:', mf.extract_variables())
print('Blocks:', len(mf.get_all_blocks()))

result = mf.process(0, ProcessMode.COMPLETE, {'name': 'John'})
print('Process result:', result)
"

# Check Commitizen configuration and version
cz version
cz check --rev-range HEAD~5..HEAD

# Test commitizen commit message validation
echo "test: example commit message" | cz check --commit-msg-file -
```

### Logging and Monitoring

**Enable Debug Logging**:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from markdown_flow import MarkdownFlow
# Now see detailed processing logs
```

**Performance Monitoring**:

```python
import time
from functools import wraps

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.2f}s")
        return result
    return wrapper
```

## Advanced Usage Patterns

### Custom LLM Provider Implementation

```python
from markdown_flow.llm import LLMProvider, LLMResult, ProcessMode
from typing import Generator

class CustomLLMProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def complete(self, messages: list[dict[str, str]]) -> str:
        # Implement your LLM completion logic
        response = your_llm_api.complete(messages)
        return response.text

    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        # Implement streaming logic
        for chunk in your_llm_api.stream(messages):
            yield chunk.text

# Usage
provider = CustomLLMProvider("your-api-key")
mf = MarkdownFlow(document, llm_provider=provider)
```

### Batch Processing Multiple Documents

```python
from markdown_flow import MarkdownFlow, ProcessMode
from concurrent.futures import ThreadPoolExecutor

def process_documents(documents: list, llm_provider):
    """Process multiple documents using thread pool"""
    def process_single(doc):
        mf = MarkdownFlow(doc, llm_provider=llm_provider)
        return mf.process(0, ProcessMode.COMPLETE)

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(process_single, documents))

    return results

# Usage
documents = ["Document 1", "Document 2", "Document 3"]
results = process_documents(documents, your_llm_provider)
```

### Variable Validation and Transformation

```python
from markdown_flow import MarkdownFlow

class ValidatedMarkdownFlow(MarkdownFlow):
    def __init__(self, content: str, llm_provider=None, variable_validators=None):
        super().__init__(content, llm_provider)
        self.validators = variable_validators or {}

    def validate_variables(self, variables: dict) -> dict:
        """Validate and transform variables before processing"""
        validated = {}
        for key, value in variables.items():
            if key in self.validators:
                validated[key] = self.validators[key](value)
            else:
                validated[key] = value
        return validated

    def process(self, block_index: int, mode: ProcessMode,
                     variables: dict = None, user_input: str = None):
        if variables:
            variables = self.validate_variables(variables)
        return super().process(block_index, mode, variables, user_input)

# Usage with validators
validators = {
    'age': lambda x: max(0, min(120, int(x))),  # Clamp age
    'name': lambda x: x.strip().title(),        # Clean name
}

mf = ValidatedMarkdownFlow(document, llm_provider, validators)
```

## Important Implementation Notes

### Regex Pattern Performance

- All regex patterns are pre-compiled in `constants.py` for maximum performance
- Pattern compilation happens once at import time, not during processing
- Use `COMPILED_*` constants instead of inline regex compilation

### Variable Handling Philosophy

- **Replaceable variables** (`{{var}}`) are meant for content personalization
- **Preserved variables** (`%{{var}}`) are meant for LLM understanding and assignment
- Variable extraction includes both types but processes them differently
- Default value for undefined variables is "UNKNOWN"

### Validation System

- Smart validation templates adapt based on interaction type
- Validation reduces unnecessary LLM calls through templating
- Button values support display//value separation (e.g., "Yes//1|No//0")

### Output Format Standards

- Output instructions use `!===` multiline fence format internally
- Gets converted to `[output]` format for external consumption
- Preserved content blocks maintain exact formatting

### LLM Provider Abstraction

- Providers are completely abstracted to support different AI services
- Two processing modes support different use cases (COMPLETE and STREAM)
- Synchronous processing with generator-based streaming
- Error handling and timeout management built into the interface

## Additional Resources

### Documentation Links

- **PyPI Package**: <https://pypi.org/project/markdown-flow/>
- **GitHub Repository**: <https://github.com/ai-shifu/markdown-flow-agent-py>
- **MarkdownFlow Specification**: <https://markdownflow.ai>
- **Python Documentation**: <https://docs.python.org/>
- **Pre-commit Documentation**: <https://pre-commit.com/>
- **Ruff Documentation**: <https://docs.astral.sh/ruff/>
- **Conventional Commits**: <https://www.conventionalcommits.org/>

### Community and Support

- **Issues**: Report bugs and feature requests on GitHub Issues
- **Discussions**: Join community discussions on GitHub Discussions
- **Contributing**: Read CONTRIBUTING.md for contribution guidelines
- **License**: MIT License - see LICENSE file for details

---

_This documentation is maintained by AI Shifu Team and the open source community._
