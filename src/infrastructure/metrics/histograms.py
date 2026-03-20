"""Histogram 指标定义 - 分布统计"""

import logging
from typing import Optional
from prometheus_client import Histogram as PrometheusHistogram

# 自定义 buckets 配置
REQUEST_DURATION_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)  # 请求延迟 buckets
TOKEN_USAGE_BUCKETS = (10, 50, 100, 250, 500, 1000, 2500, 5000, 10000)  # Token 使用量 buckets
TOOL_EXECUTION_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)  # 工具执行时间 buckets

logger = logging.getLogger(__name__)


class HistogramMetrics:
    """Histogram 指标管理器
    
    提供预定义的业务 Histogram 指标：
    - request_duration_seconds: 请求持续时间
    - llm_token_usage: LLM Token 使用量
    - tool_execution_seconds: 工具执行时间
    """
    
    def __init__(self):
        # 请求持续时间
        self._request_duration: Optional[PrometheusHistogram] = None
        
        # LLM Token 使用量
        self._llm_token: Optional[PrometheusHistogram] = None
        
        # 工具执行时间
        self._tool_execution: Optional[PrometheusHistogram] = None
        
        # 数据源查询时间
        self._data_source_duration: Optional[PrometheusHistogram] = None
        
        self._register_histograms()
    
    def _register_histograms(self):
        """注册所有 Histogram 指标"""
        
        # 请求持续时间
        self._request_duration = PrometheusHistogram(
            "anime_agent_request_duration_seconds",
            "请求持续时间（秒）",
            labelnames=("endpoint", "method"),  # endpoint: API 端点, method: HTTP 方法
            buckets=REQUEST_DURATION_BUCKETS,
            registry=None
        )
        
        # LLM Token 使用量
        self._llm_token = PrometheusHistogram(
            "anime_agent_llm_token_usage",
            "LLM Token 使用量",
            labelnames=("token_type",),  # token_type: input/output
            buckets=TOKEN_USAGE_BUCKETS,
            registry=None
        )
        
        # 工具执行时间
        self._tool_execution = PrometheusHistogram(
            "anime_agent_tool_execution_seconds",
            "工具执行时间（秒）",
            labelnames=("tool_name",),  # tool_name: 工具名称
            buckets=TOOL_EXECUTION_BUCKETS,
            registry=None
        )
        
        # 数据源查询时间
        self._data_source_duration = PrometheusHistogram(
            "anime_agent_data_source_duration_seconds",
            "数据源查询时间（秒）",
            labelnames=("data_source",),  # data_source: 数据源名称
            buckets=TOOL_EXECUTION_BUCKETS,
            registry=None
        )
        
        logger.info("✅ Histogram 指标注册完成")
    
    @property
    def request_duration(self) -> PrometheusHistogram:
        return self._request_duration
    
    @property
    def llm_token(self) -> PrometheusHistogram:
        return self._llm_token
    
    @property
    def tool_execution(self) -> PrometheusHistogram:
        return self._tool_execution
    
    @property
    def data_source_duration(self) -> PrometheusHistogram:
        return self._data_source_duration


# 全局 Histogram 指标实例
_histogram_metrics: Optional[HistogramMetrics] = None


def get_histogram_metrics() -> HistogramMetrics:
    """获取全局 Histogram 指标实例"""
    global _histogram_metrics
    if _histogram_metrics is None:
        _histogram_metrics = HistogramMetrics()
    return _histogram_metrics


# 预定义的 Histogram 实例（用于直接引用）
request_duration_seconds = get_histogram_metrics().request_duration
llm_token_usage = get_histogram_metrics().llm_token
tool_execution_seconds = get_histogram_metrics().tool_execution
