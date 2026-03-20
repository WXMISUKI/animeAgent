"""追踪上下文 - 管理请求级别的追踪状态"""

import logging
from typing import Optional, Dict, Any
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TracingContext:
    """追踪上下文
    
    在单个请求的生命周期内保持追踪状态，
    包括 Trace ID、当前阶段、参数快照等。
    """
    
    trace_id: str
    user_query: str = ""
    user_id: str = "default"
    session_id: str = ""
    
    # 当前阶段
    current_stage: str = ""  # intent, plan, execution, response
    current_operation: str = ""  # intent_recognition, param_extraction, etc.
    
    # 参数快照
    raw_input: str = ""  # 原始用户输入
    intent_type: str = ""  # 识别的意图类型
    query_params: Dict[str, Any] = field(default_factory=dict)  # 查询参数
    
    # 参数来源追踪
    param_sources: Dict[str, str] = field(default_factory=dict)  # 参数名 -> 来源 (llm/rule/default)
    param_changes: Dict[str, list] = field(default_factory=dict)  # 参数名 -> 变更历史
    
    # 阶段时间记录
    stage_timings: Dict[str, float] = field(default_factory=dict)  # 阶段名 -> 耗时
    
    # 状态
    started_at: datetime = field(default_factory=datetime.now)
    completed: bool = False
    error: Optional[str] = None
    
    def update_param(self, param_name: str, value: Any, source: str = "unknown"):
        """更新参数并记录来源
        
        Args:
            param_name: 参数名称
            value: 参数值
            source: 参数来源 (llm/rule/default/intent_parser/planner/executor)
        """
        # 记录参数来源
        if param_name in self.query_params:
            # 参数已存在，记录变更
            if param_name not in self.param_changes:
                self.param_changes[param_name] = []
            self.param_changes[param_name].append({
                "old_value": self.query_params[param_name],
                "new_value": value,
                "source": source,
                "timestamp": datetime.now().isoformat()
            })
        
        self.query_params[param_name] = value
        self.param_sources[param_name] = source
    
    def set_stage(self, stage: str, operation: str = ""):
        """设置当前阶段"""
        self.current_stage = stage
        self.current_operation = operation
        logger.debug(f"📍 追踪上下文 - 阶段: {stage}, 操作: {operation}")
    
    def record_timing(self, stage: str, duration: float):
        """记录阶段耗时"""
        self.stage_timings[stage] = duration
    
    def get_param_source(self, param_name: str) -> str:
        """获取参数来源"""
        return self.param_sources.get(param_name, "unknown")
    
    def get_param_history(self, param_name: str) -> list:
        """获取参数变更历史"""
        return self.param_changes.get(param_name, [])
    
    def mark_completed(self, error: str = None):
        """标记完成"""
        self.completed = True
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "user_query": self.user_query,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "current_stage": self.current_stage,
            "current_operation": self.current_operation,
            "raw_input": self.raw_input,
            "intent_type": self.intent_type,
            "query_params": self.query_params,
            "param_sources": self.param_sources,
            "param_changes": self.param_changes,
            "stage_timings": self.stage_timings,
            "started_at": self.started_at.isoformat(),
            "completed": self.completed,
            "error": self.error,
        }


# 追踪上下文 ContextVar
_tracing_context: ContextVar[Optional[TracingContext]] = ContextVar(
    "tracing_context", 
    default=None
)


def create_tracing_context(
    trace_id: str,
    user_query: str = "",
    user_id: str = "default",
    session_id: str = ""
) -> TracingContext:
    """创建追踪上下文"""
    context = TracingContext(
        trace_id=trace_id,
        user_query=user_query,
        user_id=user_id,
        session_id=session_id,
        raw_input=user_query
    )
    _tracing_context.set(context)
    return context


def get_tracing_context() -> Optional[TracingContext]:
    """获取当前追踪上下文"""
    return _tracing_context.get()


def clear_tracing_context():
    """清除追踪上下文"""
    _tracing_context.set(None)


def update_tracing_context_param(param_name: str, value: Any, source: str = "unknown"):
    """便捷函数：更新追踪上下文的参数"""
    context = get_tracing_context()
    if context:
        context.update_param(param_name, value, source)


def set_tracing_context_stage(stage: str, operation: str = ""):
    """便捷函数：设置追踪上下文的阶段"""
    context = get_tracing_context()
    if context:
        context.set_stage(stage, operation)
