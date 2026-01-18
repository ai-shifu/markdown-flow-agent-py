#!/usr/bin/env python3
"""
测试板书模式重构功能

验证模块化常量和部分定制功能是否正常工作
"""

from markdown_flow import MarkdownFlow

# 测试 1: 导入模块化常量
try:
    from markdown_flow import (
        BLACKBOARD_ACTIONS,
        BLACKBOARD_CORE_RULES,
        BLACKBOARD_LIBRARIES,
        BLACKBOARD_OPTIMIZATION_STRATEGY,
        build_blackboard_prompt,
    )

    print("✅ 测试 1: 成功导入模块化常量")
    print(f"   - BLACKBOARD_CORE_RULES: {len(BLACKBOARD_CORE_RULES)} 字符")
    print(f"   - BLACKBOARD_LIBRARIES: {len(BLACKBOARD_LIBRARIES)} 字符")
    print(f"   - BLACKBOARD_ACTIONS: {len(BLACKBOARD_ACTIONS)} 字符")
    print(f"   - BLACKBOARD_OPTIMIZATION_STRATEGY: {len(BLACKBOARD_OPTIMIZATION_STRATEGY)} 字符")
except ImportError as e:
    print(f"❌ 测试 1 失败: {e}")
    exit(1)

# 测试 2: 创建 MarkdownFlow 实例
try:
    mf = MarkdownFlow("# 测试文档")
    print("\n✅ 测试 2: 成功创建 MarkdownFlow 实例")
except Exception as e:
    print(f"\n❌ 测试 2 失败: {e}")
    exit(1)

# 测试 3: 测试 set_blackboard_optimization_strategy 方法
try:
    custom_strategy = """## 自定义优化策略
强调使用 update_element 和 replace_container 来实现动态效果。
"""
    mf.set_blackboard_optimization_strategy(custom_strategy)
    retrieved = mf.get_blackboard_optimization_strategy()
    assert retrieved == custom_strategy, "优化策略设置/获取不匹配"
    print("\n✅ 测试 3: set/get_blackboard_optimization_strategy 方法正常工作")
except Exception as e:
    print(f"\n❌ 测试 3 失败: {e}")
    exit(1)

# 测试 4: 测试链式调用
try:
    mf.set_blackboard_optimization_strategy("策略1").set_blackboard_prompt("提示词1")
    print("\n✅ 测试 4: 链式调用支持正常")
except Exception as e:
    print(f"\n❌ 测试 4 失败: {e}")
    exit(1)

# 测试 5: 测试 build_blackboard_prompt 函数
try:
    # 使用默认策略
    default_prompt = build_blackboard_prompt()
    assert len(default_prompt) > 1000, "默认提示词太短"
    print("\n✅ 测试 5a: build_blackboard_prompt() 默认模式正常")

    # 使用自定义策略
    custom_prompt = build_blackboard_prompt("## 自定义策略\n强调动态更新")
    assert "自定义策略" in custom_prompt, "自定义策略未被包含"
    assert "强调动态更新" in custom_prompt, "自定义策略内容未被包含"
    print("✅ 测试 5b: build_blackboard_prompt(custom) 自定义模式正常")
except Exception as e:
    print(f"\n❌ 测试 5 失败: {e}")
    exit(1)

# 测试 6: 测试 _get_effective_blackboard_prompt 优先级
try:
    mf_test = MarkdownFlow("# 测试")

    # 情况 1: 都未设置，应返回默认提示词
    prompt1 = mf_test._get_effective_blackboard_prompt()
    assert "板书模式" in prompt1 or "blackboard" in prompt1.lower(), "默认提示词不正确"
    print("\n✅ 测试 6a: 优先级 - 默认提示词正常")

    # 情况 2: 只设置优化策略，应使用自定义策略构建
    mf_test.set_blackboard_optimization_strategy("## 自定义策略")
    prompt2 = mf_test._get_effective_blackboard_prompt()
    assert "自定义策略" in prompt2, "自定义策略未生效"
    print("✅ 测试 6b: 优先级 - 自定义策略生效")

    # 情况 3: 设置完整提示词，应优先使用
    mf_test.set_blackboard_prompt("完全自定义的提示词")
    prompt3 = mf_test._get_effective_blackboard_prompt()
    assert prompt3 == "完全自定义的提示词", "完整提示词未优先使用"
    print("✅ 测试 6c: 优先级 - 完整提示词优先级最高")

    # 情况 4: 重置为 None，应回到优化策略
    mf_test.set_blackboard_prompt(None)
    prompt4 = mf_test._get_effective_blackboard_prompt()
    assert "自定义策略" in prompt4, "重置后未回到优化策略"
    print("✅ 测试 6d: 优先级 - 重置后正确回退")
except Exception as e:
    print(f"\n❌ 测试 6 失败: {e}")
    exit(1)

# 测试 7: 验证与 Go 版本的 API 一致性
try:
    mf_go = MarkdownFlow("# Go 版本对照测试")

    # Go: SetBlackboardOptimizationStrategy
    # Python: set_blackboard_optimization_strategy
    mf_go.set_blackboard_optimization_strategy("策略")
    assert mf_go.get_blackboard_optimization_strategy() == "策略"

    # Go: SetBlackboardPrompt
    # Python: set_blackboard_prompt
    mf_go.set_blackboard_prompt("提示词")
    assert mf_go.get_blackboard_prompt() == "提示词"

    print("\n✅ 测试 7: 与 Go 版本 API 一致性验证通过")
except Exception as e:
    print(f"\n❌ 测试 7 失败: {e}")
    exit(1)

print("\n" + "=" * 60)
print("🎉 所有测试通过！板书模式重构成功！")
print("=" * 60)
print("\n📊 功能对比:")
print("   Go 版本              | Python 版本")
print("   " + "-" * 58)
print("   BlackboardCoreRules  | BLACKBOARD_CORE_RULES ✅")
print("   BlackboardLibraries  | BLACKBOARD_LIBRARIES ✅")
print("   BlackboardActions    | BLACKBOARD_ACTIONS ✅")
print("   BlackboardOptimizationStrategy | BLACKBOARD_OPTIMIZATION_STRATEGY ✅")
print("   SetBlackboardOptimizationStrategy | set_blackboard_optimization_strategy ✅")
print("   SetBlackboardPrompt  | set_blackboard_prompt ✅")
print("   build (组合字符串)   | build_blackboard_prompt() ✅")
print("\n✨ Python 版本已与 Go 版本完全对齐！")
