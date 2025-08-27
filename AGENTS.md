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

- `PROMPT_ONLY`: Generate prompts without LLM calls
- `COMPLETE`: Non-streaming LLM processing
- `STREAM`: Streaming LLM responses

**Utilities (`utils.py`)** - Core processing utilities

- Variable extraction and replacement
- Interaction parsing and validation
- Template generation for smart validation

### Module Structure

```text
markdown_flow/
├── __init__.py              # Public API exports and version
├── core.py                  # MarkdownFlow main class (30KB+)
├── enums.py                 # Type definitions (BlockType, InputType)
├── exceptions.py            # Custom exception classes
├── llm.py                   # LLM provider abstract interface
├── models.py                # Data classes and models
├── utils.py                 # Utility functions (24KB+)
└── constants.py             # Pre-compiled regex patterns and constants (7KB+)
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

## API Reference

### Core Classes

**MarkdownFlow** - Main processing class

- `__init__(content: str, llm_provider: LLMProvider = None)`
- `get_all_blocks() -> List[Block]`
- `extract_variables() -> Set[str]`
- `process(block_index: int, mode: ProcessMode, variables: dict[str, str | list[str]] = None, user_input: dict[str, list[str]] = None)`

**ProcessMode** - Processing mode enumeration

- `PROMPT_ONLY`: Generate prompts without LLM calls
- `COMPLETE`: Non-streaming LLM processing
- `STREAM`: Streaming LLM responses

**BlockType** - Block type enumeration

- `CONTENT`: Regular markdown content processed by LLM
- `INTERACTION`: User input blocks with `?[]` syntax requiring validation
- `PRESERVED_CONTENT`: Output-as-is blocks using inline `!===content!===` or multiline fences `!===` ... `!===` (3+ `=`)

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

## Testing Guidelines

### Test File Structure

```text
tests/                          # When test suite is added
├── conftest.py                # Shared fixtures
├── test_core.py              # Core MarkdownFlow functionality tests
├── test_models.py            # Data model tests
├── test_utils.py             # Utility function tests
├── test_llm.py               # LLM integration tests
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

    @pytest.mark.asyncio
    async def test_process_with_mock_llm(self, sample_document, mock_llm_provider):
        """Test processing with mocked LLM"""
        # Arrange
        mf = MarkdownFlow(sample_document, llm_provider=mock_llm_provider)
        variables = {"name": "John", "level": "Beginner"}

        # Act
        result = await mf.process(0, mode=ProcessMode.COMPLETE, variables=variables)

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

- ✅ Correct: `markdown_flow/`, `core.py`, `utils.py`
- ❌ Wrong: `MarkdownFlow/`, `Core.py`, `utilsHelper.py`

**Test Files**: Use `test_` prefix

- ✅ Correct: `test_core.py`, `test_utils.py`
- ❌ Wrong: `core_test.py`, `CoreTests.py`

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

**Async/await**: Use async patterns for LLM calls and I/O operations

```python
# Good: Async processing
async def process_with_llm(content):
    result = await llm_provider.complete(content)
    return result

# Bad: Synchronous blocking call
def process_with_llm(content):
    result = llm_provider.complete(content)  # Blocks execution
    return result
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
import asyncio
import random

async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(wait_time)
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
async def process_stream(self, block_index: int):
    async for chunk in self.llm_provider.stream(prompt):
        yield chunk

# Bad: Loading full response into memory
async def process_complete(self, block_index: int):
    full_response = await self.llm_provider.complete(prompt)
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
# Optional: For testing with actual LLM providers
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
print('ProcessMode.PROMPT_ONLY:', ProcessMode.PROMPT_ONLY)
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
from unittest.mock import AsyncMock
import asyncio

async def test():
    doc = '''Hello {{name}}!

---

?[%{{level}} Beginner|Expert]

---

You selected {{level}}.'''

    mock_llm = AsyncMock()
    mock_llm.complete.return_value = 'Mock LLM response'

    mf = MarkdownFlow(doc, llm_provider=mock_llm)
    print('Variables:', mf.extract_variables())
    print('Blocks:', len(mf.get_all_blocks()))

    result = await mf.process(0, ProcessMode.COMPLETE, {'name': 'John'})
    print('Process result:', result)

asyncio.run(test())
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
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.2f}s")
        return result
    return wrapper
```

## Advanced Usage Patterns

### Custom LLM Provider Implementation

```python
from markdown_flow.llm import LLMProvider, LLMResult, ProcessMode
from collections.abc import AsyncGenerator

class CustomLLMProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def complete(self, prompt: str) -> LLMResult:
        # Implement your LLM completion logic
        response = await your_llm_api.complete(prompt)
        return LLMResult(content=response.text)

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        # Implement streaming logic
        async for chunk in your_llm_api.stream(prompt):
            yield chunk.text

# Usage
provider = CustomLLMProvider("your-api-key")
mf = MarkdownFlow(document, llm_provider=provider)
```

### Batch Processing Multiple Documents

```python
import asyncio
from markdown_flow import MarkdownFlow, ProcessMode

async def process_documents(documents: list, llm_provider):
    """Process multiple documents concurrently"""
    tasks = []

    for i, doc in enumerate(documents):
        mf = MarkdownFlow(doc, llm_provider=llm_provider)
        task = mf.process(0, ProcessMode.COMPLETE)
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    return results

# Usage
documents = ["Document 1", "Document 2", "Document 3"]
results = await process_documents(documents, your_llm_provider)
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

    async def process(self, block_index: int, mode: ProcessMode,
                     variables: dict = None, user_input: str = None):
        if variables:
            variables = self.validate_variables(variables)
        return await super().process(block_index, mode, variables, user_input)

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
- Three processing modes support different use cases
- Async/await pattern throughout for non-blocking operations
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
