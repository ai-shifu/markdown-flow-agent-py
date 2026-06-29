# MarkdownFlow Agent (Python)

**用于将 [MarkdownFlow](https://markdownflow.ai) 文档转换为个性化、AI 驱动交互式内容的 Python 后端解析工具包。**

MarkdownFlow（也称为 MDFlow 或 markdown-flow）通过 AI 扩展了标准 Markdown，用于创建个性化的交互式页面。我们的口号是：**"一次创作，千人千面"**。

<div align="center">

[![PyPI version](https://badge.fury.io/py/markdown-flow.svg)](https://badge.fury.io/py/markdown-flow)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Type Hints](https://img.shields.io/badge/Type_Hints-Enabled-green.svg)](https://docs.python.org/3/library/typing.html)

[English](README.md) | 简体中文

</div>

## 🚀 快速开始

### 安装

```bash
pip install markdown-flow
# 或
pip install -e .  # 用于开发
```

### 基础用法

```python
from markdown_flow import MarkdownFlow, ProcessMode

# 简单的内容处理
document = """
你好 {{name}}！让我们探索一下你的 Python 技能。

?[%{{level}} 初学者 | 中级 | 高级]

根据你的 {{level}} 水平，这里有一些建议...
"""

mf = MarkdownFlow(document)
variables = mf.extract_variables()  # 返回：{'name', 'level'}
blocks = mf.get_all_blocks()        # 获取解析的文档块
```

### LLM 集成

```python
from markdown_flow import MarkdownFlow, ProcessMode
from your_llm_provider import YourLLMProvider

# 用 LLM 提供程序初始化
llm_provider = YourLLMProvider(api_key="your-key")
mf = MarkdownFlow(document, llm_provider=llm_provider)

# 使用不同模式处理
result = mf.process(
    block_index=0,
    mode=ProcessMode.COMPLETE,
    variables={'name': 'Alice', 'level': '中级'}
)
```

### 流式响应

```python
# 实时响应的流处理
for chunk in mf.process(
    block_index=0,
    mode=ProcessMode.STREAM,
    variables={'name': 'Bob'}
):
    print(chunk.content, end='')
```

### 交互式元素

```python
# 处理用户交互
document = """
你偏爱的编程语言是什么？

?[%{{language}} Python | JavaScript | Go | 其他...]

选择你的技能（多选）：

?[%{{skills}} Python||JavaScript||Go||Rust]

?[继续 | 跳过]
"""

mf = MarkdownFlow(document)
blocks = mf.get_all_blocks()

for block in blocks:
    if block.block_type == BlockType.INTERACTION:
        # 处理用户交互
        print(f"交互：{block.content}")

# 处理用户输入
user_input = {
    'language': ['Python'],                    # 单选
    'skills': ['Python', 'JavaScript', 'Go']  # 多选
}

result = mf.process(
    block_index=1,  # 处理技能交互
    user_input=user_input,
    mode=ProcessMode.COMPLETE
)
```

## 📖 API 参考

### 核心类

#### MarkdownFlow

用于解析和处理 MarkdownFlow 文档的主要类。

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

**方法：**

- `get_all_blocks()` - 将文档解析为结构化块
- `extract_variables()` - 提取所有 `{{variable}}` 和 `%{{variable}}` 模式
- `process()` - 使用统一接口通过 LLM 处理块

**示例：**

```python
mf = MarkdownFlow("""
# 欢迎 {{name}}！

选择你的经验：?[%{{exp}} 初学者 | 专家]

你的经验水平是 {{exp}}。
""")

print("变量：", mf.extract_variables())  # {'name', 'exp'}
print("块数：", len(mf.get_all_blocks()))   # 3
```

#### ProcessMode

不同用例的处理模式枚举。

```python
class ProcessMode(Enum):
    COMPLETE = "complete"  # 非流式 LLM 处理
    STREAM = "stream"      # 流式 LLM 响应
```

**用法：**

```python
# 完整响应
complete_result = mf.process(0, ProcessMode.COMPLETE)
print(complete_result.content)  # 完整的 LLM 响应

# 流式响应
for chunk in mf.process(0, ProcessMode.STREAM):
    print(chunk.content, end='')
```

#### LLMProvider

用于实现 LLM 提供程序的抽象基类。

```python
from abc import ABC, abstractmethod
from typing import Generator

class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[dict[str, str]]) -> str: ...

    @abstractmethod
    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]: ...
```

**自定义实现：**

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

### 块类型

#### BlockType

MarkdownFlow 文档中不同块类型的枚举。

```python
class BlockType(Enum):
    CONTENT = "content"                    # 常规 markdown 内容
    INTERACTION = "interaction"            # 用户交互块 (?[...])
    PRESERVED_CONTENT = "preserved_content" # 用 === (单行) 或 !=== (多行) 标记的内容
```

**块结构：**

```python
# 内容块 - 由 LLM 处理
"""
你好 {{name}}！欢迎来到我们的平台。
"""

# 交互块 - 需要用户输入
"""
?[%{{choice}} 选项 A | 选项 B | 输入自定义选项...]
"""

# 保留内容 - 原样输出
"""
# 单行格式
===固定标题===

# 多行格式 - 以感叹号开头并至少 3 个等号作为分隔线
!===
此内容完全按原样保留。
没有 LLM 处理或变量替换。
!===
"""
```

### 交互类型

#### InteractionType

解析后的交互格式类型。

```python
class InteractionType(NamedTuple):
    name: str                    # 类型名称
    variable: Optional[str]      # 要分配的变量 (%{{var}})
    buttons: List[str]          # 按钮选项
    question: Optional[str]      # 文本输入问题
    has_text_input: bool        # 是否允许文本输入
```

**支持的格式：**

```python
# TEXT_ONLY：带问题的文本输入
"?[%{{name}} 你的名字是什么？]"

# BUTTONS_ONLY：仅按钮选择
"?[%{{level}} 初学者 | 中级 | 高级]"

# BUTTONS_WITH_TEXT：按钮与备用文本输入
"?[%{{preference}} 选项 A | 选项 B | 请指定...]"

# BUTTONS_MULTI_SELECT：多选按钮
"?[%{{skills}} Python||JavaScript||Go||Rust]"

# BUTTONS_MULTI_WITH_TEXT：多选带文本备选
"?[%{{frameworks}} React||Vue||Angular||请指定其他...]"

# NON_ASSIGNMENT_BUTTON：显示按钮但不分配变量
"?[继续 | 取消 | 返回]"
```

### 实用函数

#### 变量操作

```python
def extract_variables_from_text(text: str) -> Set[str]:
    """提取所有 {{variable}} 和 %{{variable}} 模式。"""

def replace_variables_in_text(text: str, variables: dict) -> str:
    """替换 {{variable}} 模式的值，保留 %{{variable}}。"""

# 示例
text = "你好 {{name}}！选择：?[%{{level}} 基础 | 高级]"
vars = extract_variables_from_text(text)  # {'name', 'level'}
result = replace_variables_in_text(text, {'name': 'Alice'})
# 返回："你好 Alice！选择：?[%{{level}} 基础 | 高级]"
```

#### 交互处理

```python
def InteractionParser.parse(content: str) -> InteractionType:
    """将交互块解析为结构化格式。"""

def extract_interaction_question(content: str) -> str:
    """从交互块中提取问题文本。"""

def generate_smart_validation_template(interaction_type: InteractionType) -> str:
    """为交互生成验证模板。"""

# 示例
parser_result = InteractionParser.parse("%{{choice}} A | B | 输入自定义...")
print(parser_result.name)          # "BUTTONS_WITH_TEXT"
print(parser_result.variable)      # "choice"
print(parser_result.buttons)       # ["A", "B"]
print(parser_result.question)      # "输入自定义..."
```

### 类型和模型

```python
# 核心数据结构
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

# 变量系统类型
Variables = Dict[str, str]  # 变量名 -> 值映射

# 所有类型都已导出供使用
from markdown_flow import (
    Block, LLMResult, Variables,
    BlockType, InteractionType, ProcessMode
)
```

## 🔄 迁移指南

### 参数格式升级

新版本引入了多选交互支持，对 `user_input` 参数格式进行了改进。

#### 旧格式

```python
# 单个字符串输入
user_input = "Python"

# 处理交互
result = mf.process(
    block_index=1,
    user_input=user_input,
    mode=ProcessMode.COMPLETE
)
```

#### 新格式

```python
# 字典格式，值为列表
user_input = {
    'language': ['Python'],                    # 单选作为列表
    'skills': ['Python', 'JavaScript', 'Go']  # 多选
}

# 处理交互
result = mf.process(
    block_index=1,
    user_input=user_input,
    mode=ProcessMode.COMPLETE
)
```

#### 新的多选语法

```markdown
<!-- 单选（传统） -->
?[%{{language}} Python|JavaScript|Go]

<!-- 多选（新增） -->
?[%{{skills}} Python||JavaScript||Go||Rust]

<!-- 多选带文本备选 -->
?[%{{frameworks}} React||Vue||Angular||请指定其他...]
```

#### 变量类型

```python
# 变量现在同时支持字符串和列表值
variables = {
    'name': 'John',                           # str（传统）
    'skills': ['Python', 'JavaScript'],      # list[str]（新增）
    'experience': 'Senior'                    # str（传统）
}
```

## 🧩 高级示例

### 自定义 LLM 提供程序集成

```python
from markdown_flow import MarkdownFlow, LLMProvider
import httpx

class CustomAPIProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.Client()

    def complete(self, messages: list[dict[str, str]]) -> str:
        # Convert messages to your API format
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

        response = self.client.post(
            f"{self.base_url}/complete",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"prompt": prompt, "max_tokens": 1000}
        )
        data = response.json()
        return data["text"]

    def stream(self, messages: list[dict[str, str]]):
        # Convert messages to your API format
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

        with self.client.stream(
            "POST",
            f"{self.base_url}/stream",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"prompt": prompt}
        ) as response:
            for chunk in response.iter_text():
                if chunk.strip():
                    yield chunk

# 用法
provider = CustomAPIProvider("https://api.example.com", "your-key")
mf = MarkdownFlow(document, llm_provider=provider)
```

### 多块文档处理

```python
def process_conversation():
    conversation = """
# AI 助手

你好 {{user_name}}！我在这里帮助你学习 Python。

---

你当前的经验水平如何？

?[%{{experience}} 完全初学者 | 有一些经验 | 有经验]

---

根据你的 {{experience}} 水平，让我创建一个个性化的学习计划。

该计划将包括符合你背景的 {{topics}}。

---

你想从基础开始吗？

?[开始学习 | 自定义计划 | 提问]
"""

    mf = MarkdownFlow(conversation, llm_provider=your_provider)
    blocks = mf.get_all_blocks()

    variables = {
        'user_name': 'Alice',
        'experience': '有一些经验',
        'topics': '中级概念和实际项目'
    }

    for i, block in enumerate(blocks):
        if block.block_type == BlockType.CONTENT:
            print(f"\n--- 处理块 {i} ---")
            result = mf.process(
                block_index=i,
                mode=ProcessMode.COMPLETE,
                variables=variables
            )
            print(result.content)
        elif block.block_type == BlockType.INTERACTION:
            print(f"\n--- 用户交互块 {i} ---")
            print(block.content)
```

### 带进度跟踪的流式处理

```python
from markdown_flow import MarkdownFlow, ProcessMode

def stream_with_progress():
    document = """
为 {{user_name}} 生成一个全面的 Python 教程，
专注于 {{topic}}，包含实际示例。

包括代码样例、解释和练习。
"""

    mf = MarkdownFlow(document, llm_provider=your_provider)

    print("开始流处理...")
    content = ""
    chunk_count = 0

    for chunk in mf.process(
        block_index=0,
        mode=ProcessMode.STREAM,
        variables={
            'user_name': '开发者',
            'topic': '同步编程'
        }
    ):
        content += chunk.content
        chunk_count += 1

        # 显示进度
        if chunk_count % 10 == 0:
            print(f"已接收 {chunk_count} 个块，{len(content)} 个字符")

        # 实时处理
        if chunk.content.endswith('\n'):
            # 处理完整行
            lines = content.strip().split('\n')
            if lines:
                latest_line = lines[-1]
                # 对完整行做一些操作
                pass

    print(f"\n流处理完成！总计：{chunk_count} 个块，{len(content)} 个字符")
    return content
```

### 交互式文档生成器

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
                # 使用当前变量处理内容块
                result = self.mf.process(
                    block_index=i,
                    mode=ProcessMode.COMPLETE,
                    variables=self.user_responses
                )
                print(f"\n内容：{result.content}")

            elif block.block_type == BlockType.INTERACTION:
                # 处理用户交互
                response = self.handle_interaction(block.content)
                if response:
                    self.user_responses.update(response)

    def handle_interaction(self, interaction_content: str):
        from markdown_flow.parser import InteractionParser

        interaction = InteractionParser().parse(interaction_content)
        print(f"\n{interaction_content}")

        if interaction.name == "BUTTONS_ONLY":
            print("选择一个选项：")
            for i, button in enumerate(interaction.buttons, 1):
                print(f"{i}. {button}")

            choice = input("输入选择编号：")
            try:
                selected = interaction.buttons[int(choice) - 1]
                return {interaction.variable: selected}
            except (ValueError, IndexError):
                print("无效选择")
                return self.handle_interaction(interaction_content)

        elif interaction.name == "TEXT_ONLY":
            response = input(f"{interaction.question}：")
            return {interaction.variable: response}

        return {}

# 用法
template = """
欢迎！让我们创建一个个性化的学习计划。

你的名字是什么？
?[%{{name}} 输入你的名字]

你好 {{name}}！你想学什么？
?[%{{subject}} Python | JavaScript | 数据科学 | 机器学习]

很好的选择，{{name}}！{{subject}} 是一个绝佳的学习领域。
"""

builder = InteractiveDocumentBuilder(template, your_llm_provider)
builder.start_interaction()
```

### 变量系统深入了解

```python
from markdown_flow import extract_variables_from_text, replace_variables_in_text

def demonstrate_variable_system():
    # 包含两种变量类型的复杂文档
    document = """
    欢迎 {{user_name}} 来到 {{course_title}} 课程！

    请为你的体验评分：?[%{{rating}} 1 | 2 | 3 | 4 | 5]

    当前进度：{{progress_percent}}%
    作业截止：{{due_date}}

    你的 %{{rating}} 评分帮助我们改进课程内容。
    """

    # 提取所有变量
    all_vars = extract_variables_from_text(document)
    print(f"找到的所有变量：{all_vars}")
    # 输出：{'user_name', 'course_title', 'rating', 'progress_percent', 'due_date'}

    # 仅替换 {{variable}} 模式，保留 %{{variable}}
    replacements = {
        'user_name': 'Alice',
        'course_title': 'Python 高级',
        'progress_percent': '75',
        'due_date': '2024-12-15',
        'rating': '4'  # 由于 %{{}} 格式，这个不会被替换
    }

    result = replace_variables_in_text(document, replacements)
    print("\n替换后：")
    print(result)

    # %{{rating}} 保持不变供 LLM 处理，
    # 而 {{user_name}}、{{course_title}} 等被替换

demonstrate_variable_system()
```

## 🌐 MarkdownFlow 生态系统

markdown-flow-agent-py 是 MarkdownFlow 生态系统的一部分，用于创建个性化、AI 驱动的交互式文档：

- **[markdown-flow](https://github.com/ai-shifu/markdown-flow)** - 包含主页、文档和交互式 playground 的主仓库
- **[markdown-flow-ui](https://github.com/ai-shifu/markdown-flow-ui)** - 用于渲染交互式 MarkdownFlow 文档的 React 组件库
- **[markdown-it-flow](https://github.com/ai-shifu/markdown-it-flow)** - 用于解析和渲染 MarkdownFlow 语法的 markdown-it 插件
- **[remark-flow](https://github.com/ai-shifu/remark-flow)** - 用于在 React 应用中解析和处理 MarkdownFlow 语法的 Remark 插件

## 💖 赞助商

<div align="center">
  <a href="https://ai-shifu.cn">
    <img src="https://raw.githubusercontent.com/ai-shifu/ai-shifu/main/assets/logo_zh.png" alt="AI 师傅" width="150" />
  </a>
  <p><strong><a href="https://ai-shifu.cn">AI-Shifu.cn</a></strong></p>
  <p>AI 驱动的个性化学习平台</p>
</div>

## 📄 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [Python](https://www.python.org/) 提供强大的编程语言
- [Ruff](https://docs.astral.sh/ruff/) 提供闪电般快速的 Python 代码检查和格式化
- [MyPy](https://mypy.readthedocs.io/) 提供静态类型检查
- [Commitizen](https://commitizen-tools.github.io/commitizen/) 提供标准化提交消息
- [Lefthook](https://lefthook.dev/) 提供自动化代码质量检查(git 钩子 + CI)

## 📞 支持

- 📖 [文档](https://github.com/ai-shifu/markdown-flow-agent-py#readme)
- 🐛 [问题跟踪](https://github.com/ai-shifu/markdown-flow-agent-py/issues)
- 💬 [讨论](https://github.com/ai-shifu/markdown-flow-agent-py/discussions)
