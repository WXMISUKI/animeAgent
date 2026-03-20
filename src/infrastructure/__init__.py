"""基础设施层初始化"""

from .cache.redis_cache import RedisCache
from .cache.session_manager import SessionManager

# 监控指标模块
from .metrics import (
    MetricsCollector,
    get_metrics_collector,
    CounterMetrics,
    GaugeMetrics,
    HistogramMetrics,
    BusinessMetrics,
    get_business_metrics,
    intent_recognition_total,
    tool_call_total,
    data_source_query_total,
    llm_call_total,
    api_request_total,
    active_requests,
    session_count,
    request_duration_seconds,
    llm_token_usage,
    tool_execution_seconds,
)

# 追踪模块
from .tracing import (
    Tracer,
    get_tracer,
    generate_trace_id,
    TracingContext,
    get_tracing_context,
    clear_tracing_context,
    ParameterTracker,
    get_parameter_tracker,
)
