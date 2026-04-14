"""
原样输出 标签过滤器

LLM 有时不遵守 system prompt 中的指令，会在输出中保留这些标签。
本模块提供硬过滤，确保返回给调用方的内容中不包含这些标签。
"""

from .constants import OUTPUT_INSTRUCTION_PREFIX, OUTPUT_INSTRUCTION_SUFFIX


_PRESERVE_TAGS = [
    OUTPUT_INSTRUCTION_PREFIX,  # <原样输出>
    OUTPUT_INSTRUCTION_SUFFIX,  # </原样输出>
]

_MAX_TAG_LEN = max(len(tag) for tag in _PRESERVE_TAGS)


def strip_preserve_tags(content: str) -> str:
    """从完整文本中移除所有 原样输出 标签。

    用于 Complete 模式，此时拿到的是完整文本。
    """
    for tag in _PRESERVE_TAGS:
        content = content.replace(tag, "")
    return content


def _is_tag_prefix(s: str) -> bool:
    """检查 s 是否是任意一个标签的前缀（非空且不等于完整标签）。"""
    if not s:
        return False
    return any(len(s) < len(tag) and tag.startswith(s) for tag in _PRESERVE_TAGS)


class StreamTagFilter:
    """流式模式下的标签过滤器。

    处理标签可能跨 chunk 分割的情况（如 chunk1="<mandatory_"，chunk2="output>"）。
    维护一个最多 _MAX_TAG_LEN-1 字符的缓冲区，保存可能是标签前缀的尾部内容。
    """

    def __init__(self) -> None:
        self._buf = ""

    def process(self, chunk: str) -> str:
        """处理一个 chunk，返回可以安全输出的内容。

        可能返回空字符串（当所有内容都在缓冲区中等待确认时）。
        """
        # 将缓冲区和新 chunk 合并
        combined = self._buf + chunk
        self._buf = ""

        # 移除所有完整标签
        combined = strip_preserve_tags(combined)

        # 检查尾部是否是某个标签的前缀
        buf_start = len(combined)
        for i in range(len(combined) - 1, -1, -1):
            if len(combined) - i >= _MAX_TAG_LEN:
                break
            tail = combined[i:]
            if _is_tag_prefix(tail):
                buf_start = i

        # 分离安全输出和缓冲区
        self._buf = combined[buf_start:]
        return combined[:buf_start]

    def flush(self) -> str:
        """流结束时释放缓冲区中未匹配为标签的内容。

        此时不可能再有后续 chunk 完成标签匹配，所以直接输出缓冲区。
        """
        remaining = self._buf
        self._buf = ""
        # 最后一次清理，以防缓冲区中恰好包含完整标签
        return strip_preserve_tags(remaining)
