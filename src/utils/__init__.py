# utils/__init__.py
"""工具模块

提供通用工具:
- QueryCache: 查询缓存
- logger: 日志工具 (loguru)
- chat_logger: 会话日志
- error_handler: 错误处理工具
"""

from .cache import QueryCache
from .logger import logger, chat_logger, ChatLogger, AuditLogger, audit_logger
from .error_handler import (
    AgentError,
    ToolExecutionError,
    DataSourceError,
    IntentParseError,
    LLMError,
    with_error_handling,
    with_fallback,
    safe_execute
)

__all__ = [
    # Cache
    "QueryCache",
    # Logger - 保持与loguru一致的接口
    "logger",
    "chat_logger",
    "ChatLogger",
    "AuditLogger", 
    "audit_logger",
    # Error handling
    "AgentError",
    "ToolExecutionError", 
    "DataSourceError",
    "IntentParseError",
    "LLMError",
    "with_error_handling",
    "with_fallback",
    "safe_execute"
]
