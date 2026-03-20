"""追踪器 - Trace ID 生成和追踪管理"""

import uuid
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextvars import ContextVar
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# 追踪上下文变量
_current_trace_id: ContextVar[Optional[str]] = ContextVar("current_trace_id", default=None)
_trace_start_time: ContextVar[Optional[float]] = ContextVar("trace_start_time", default=None)


def generate_trace_id() -> str:
    """生成唯一的 Trace ID
    
    格式：{时间戳}-{UUID前8位}
    例如：20260320123456-a1b2c3d4
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{timestamp}-{unique_id}"


@dataclass
class TraceSpan:
    """追踪跨度 - 表示请求处理中的一个阶段"""
    
    span_id: str
    trace_id: str
    operation_name: str  # 操作名称（如：intent_parsing, tool_execution）
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    
    # 标签和元数据
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    # 阶段信息
    stage: str = ""  # 阶段名称（如：intent, plan, execution, response）
    input_params: Dict[str, Any] = field(default_factory=dict)  # 输入参数
    output_params: Dict[str, Any] = field(default_factory=dict)  # 输出参数
    result: Any = None  # 执行结果
    
    # 状态
    success: bool = True
    error: Optional[str] = None
    
    def finish(self, success: bool = True, error: str = None):
        """完成跨度"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        if error:
            self.error = error
    
    def add_tag(self, key: str, value: Any):
        """添加标签"""
        self.tags[key] = value
    
    def add_log(self, message: str, **kwargs):
        """添加日志"""
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            **kwargs
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "operation_name": self.operation_name,
            "stage": self.stage,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "tags": self.tags,
            "logs": self.logs,
            "input_params": self.input_params,
            "output_params": self.output_params,
            "success": self.success,
            "error": self.error,
        }


class Tracer:
    """追踪器 - 管理请求的全链路追踪
    
    功能：
    - 生成和管理 Trace ID
    - 创建和管理追踪跨度（Span）
    - 记录各阶段的输入输出参数
    - 记录执行时间和状态
    """
    
    def __init__(self):
        self._spans: Dict[str, List[TraceSpan]] = {}  # trace_id -> spans
        self._current_span: Optional[TraceSpan] = None
    
    def start_trace(self, trace_id: str = None) -> str:
        """开始一个新的追踪
        
        Args:
            trace_id: 指定的 Trace ID（可选，默认自动生成）
            
        Returns:
            Trace ID
        """
        if trace_id is None:
            trace_id = generate_trace_id()
        
        # 设置上下文变量
        _current_trace_id.set(trace_id)
        _trace_start_time.set(time.time())
        
        # 初始化追踪记录
        if trace_id not in self._spans:
            self._spans[trace_id] = []
        
        logger.debug(f"🆔 开始追踪: {trace_id}")
        return trace_id
    
    def end_trace(self, trace_id: str = None):
        """结束追踪"""
        if trace_id is None:
            trace_id = _current_trace_id.get()
        
        # 清除上下文变量
        _current_trace_id.set(None)
        _trace_start_time.set(None)
        
        logger.debug(f"🏁 结束追踪: {trace_id}")
    
    def get_current_trace_id(self) -> Optional[str]:
        """获取当前追踪的 Trace ID"""
        return _current_trace_id.get()
    
    def get_trace_start_time(self) -> Optional[float]:
        """获取追踪开始时间"""
        return _trace_start_time.get()
    
    def start_span(
        self,
        operation_name: str,
        stage: str = "",
        trace_id: str = None,
        input_params: Dict[str, Any] = None
    ) -> TraceSpan:
        """开始一个新的跨度
        
        Args:
            operation_name: 操作名称
            stage: 阶段名称
            trace_id: Trace ID（可选，默认使用当前追踪）
            input_params: 输入参数
            
        Returns:
            TraceSpan 对象
        """
        if trace_id is None:
            trace_id = _current_trace_id.get()
            if trace_id is None:
                trace_id = self.start_trace()
        
        span_id = uuid.uuid4().hex[:8]
        
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            operation_name=operation_name,
            stage=stage,
            start_time=time.time(),
            input_params=input_params or {}
        )
        
        # 添加到追踪记录
        if trace_id not in self._spans:
            self._spans[trace_id] = []
        self._spans[trace_id].append(span)
        
        self._current_span = span
        
        logger.debug(f"📍 开始跨度: {operation_name} (trace_id={trace_id}, span_id={span_id})")
        return span
    
    def end_span(
        self,
        output_params: Dict[str, Any] = None,
        result: Any = None,
        success: bool = True,
        error: str = None
    ):
        """结束当前跨度"""
        if self._current_span is None:
            logger.warning("没有活动的跨度")
            return
        
        span = self._current_span
        span.output_params = output_params or {}
        span.result = result
        span.finish(success=success, error=error)
        
        logger.debug(
            f"📍 结束跨度: {span.operation_name} "
            f"(duration={span.duration:.3f}s, success={span.success})"
        )
        
        self._current_span = None
    
    def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """获取指定追踪的所有跨度"""
        return self._spans.get(trace_id, [])
    
    def get_current_trace(self) -> List[TraceSpan]:
        """获取当前追踪的所有跨度"""
        trace_id = _current_trace_id.get()
        if trace_id is None:
            return []
        return self._spans.get(trace_id, [])
    
    def add_span_tag(self, key: str, value: Any):
        """为当前跨度添加标签"""
        if self._current_span:
            self._current_span.add_tag(key, value)
    
    def add_span_log(self, message: str, **kwargs):
        """为当前跨度添加日志"""
        if self._current_span:
            self._current_span.add_log(message, **kwargs)
    
    def get_trace_summary(self, trace_id: str = None) -> Dict[str, Any]:
        """获取追踪摘要"""
        if trace_id is None:
            trace_id = _current_trace_id.get()
        
        if trace_id is None:
            return {}
        
        spans = self._spans.get(trace_id, [])
        
        total_duration = 0
        success_count = 0
        failure_count = 0
        
        for span in spans:
            if span.duration:
                total_duration += span.duration
            if span.success:
                success_count += 1
            else:
                failure_count += 1
        
        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "total_duration": total_duration,
            "success_count": success_count,
            "failure_count": failure_count,
            "stages": [s.stage for s in spans]
        }
    
    def clear_trace(self, trace_id: str = None):
        """清除追踪记录"""
        if trace_id:
            self._spans.pop(trace_id, None)
        else:
            self._spans.clear()


# 全局追踪器实例
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """获取全局追踪器实例"""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
