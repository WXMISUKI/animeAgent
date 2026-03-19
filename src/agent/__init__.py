# agent/__init__.py
"""Agent 模块"""

# 意图解析模块
from .intent import IntentParser, IntentType, SlotDefinition

# 计划生成器
from .planner import Planner

# 执行器
from .executor import Executor

# 响应生成器
from .response import ResponseGenerator, ResponseStyle

# 延迟导入，避免因依赖问题导致整个模块无法使用
try:
    from .graph import agent, create_agent_graph
    __all__ = ["agent", "create_agent_graph", "IntentParser", "IntentType", "SlotDefinition", "Planner", "Executor", "ResponseGenerator", "ResponseStyle"]
except ImportError as e:
    __all__ = ["IntentParser", "IntentType", "SlotDefinition", "Planner", "Executor", "ResponseGenerator", "ResponseStyle"]
    import logging
    logging.warning(f"Agent graph module import failed: {e}")
