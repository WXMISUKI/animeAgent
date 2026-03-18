"""统一错误处理模块"""

from typing import Optional, Callable, Any
from functools import wraps
import logging

# 创建专用logger
logger = logging.getLogger("anime_agent.errors")


class AgentError(Exception):
    """Agent基础异常"""
    
    def __init__(self, message: str, code: str = "AGENT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ToolExecutionError(AgentError):
    """工具执行失败异常"""
    
    def __init__(self, tool_name: str, message: str):
        super().__init__(
            message=f"工具 '{tool_name}' 执行失败: {message}",
            code="TOOL_EXECUTION_ERROR"
        )
        self.tool_name = tool_name


class DataSourceError(AgentError):
    """数据源错误异常"""
    
    def __init__(self, source_name: str, message: str):
        super().__init__(
            message=f"数据源 '{source_name}' 错误: {message}",
            code="DATA_SOURCE_ERROR"
        )
        self.source_name = source_name


class IntentParseError(AgentError):
    """意图解析错误异常"""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"意图解析失败: {message}",
            code="INTENT_PARSE_ERROR"
        )


class LLMError(AgentError):
    """LLM调用错误异常"""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"LLM调用失败: {message}",
            code="LLM_ERROR"
        )


def with_error_handling(
    default_return: Any = None,
    log_errors: bool = True,
    reraise: bool = False
):
    """错误处理装饰器
    
    Args:
        default_return: 错误时的默认返回值
        log_errors: 是否记录错误日志
        reraise: 是否重新抛出异常
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AgentError as e:
                if log_errors:
                    logger.error(f"[{e.code}] {e.message}")
                if reraise:
                    raise
                return default_return
            except Exception as e:
                error_msg = f"未预期的错误: {type(e).__name__}: {str(e)}"
                if log_errors:
                    logger.error(error_msg)
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator


def with_fallback(fallback_func: Callable):
    """降级处理装饰器
    
    当主函数执行失败时，自动调用降级函数
    
    Args:
        fallback_func: 降级函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"执行失败，使用降级方案: {e}")
                return fallback_func(*args, **kwargs)
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    *args,
    default: Any = None,
    error_callback: Optional[Callable] = None,
    **kwargs
) -> Any:
    """安全执行函数
    
    Args:
        func: 要执行的函数
        *args: 位置参数
        default: 执行失败时的默认返回值
        error_callback: 错误回调函数
        **kwargs: 关键字参数
    
    Returns:
        函数执行结果或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_msg = f"执行 {func.__name__} 失败: {e}"
        logger.error(error_msg)
        
        if error_callback:
            try:
                return error_callback(e)
            except Exception:
                pass
        
        return default
