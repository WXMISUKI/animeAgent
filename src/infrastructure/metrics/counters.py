"""Counter 指标定义 - 累积计数器"""

import logging
from typing import Optional
from prometheus_client import Counter as PrometheusCounter

logger = logging.getLogger(__name__)


class CounterMetrics:
    """Counter 指标管理器
    
    提供预定义的业务 Counter 指标：
    - intent_recognition_total: 意图识别总次数
    - tool_call_total: 工具调用总次数
    - data_source_query_total: 数据源查询总次数
    - llm_call_total: LLM 调用总次数
    - api_request_total: API 请求总次数
    """
    
    def __init__(self):
        # 意图识别计数器（按意图类型和结果分组）
        self._intent_recognition: Optional[PrometheusCounter] = None
        
        # 工具调用计数器（按工具名称和结果分组）
        self._tool_call: Optional[PrometheusCounter] = None
        
        # 数据源查询计数器（按数据源和结果分组）
        self._data_source_query: Optional[PrometheusCounter] = None
        
        # LLM 调用计数器（按调用类型分组）
        self._llm_call: Optional[PrometheusCounter] = None
        
        # API 请求计数器（按端点和状态分组）
        self._api_request: Optional[PrometheusCounter] = None
        
        self._register_counters()
    
    def _register_counters(self):
        """注册所有 Counter 指标"""
        
        # 意图识别计数器
        self._intent_recognition = PrometheusCounter(
            "anime_agent_intent_recognition_total",
            "意图识别总次数",
            labelnames=("intent_type", "result"),  # intent_type: 意图类型, result: success/failure
            registry=None  # 会在 get_metrics_collector 中注册
        )
        
        # 工具调用计数器
        self._tool_call = PrometheusCounter(
            "anime_agent_tool_call_total",
            "工具调用总次数",
            labelnames=("tool_name", "result"),  # tool_name: 工具名称, result: success/error
            registry=None
        )
        
        # 数据源查询计数器
        self._data_source_query = PrometheusCounter(
            "anime_agent_data_source_query_total",
            "数据源查询总次数",
            labelnames=("data_source", "result"),  # data_source: 数据源名称, result: success/error
            registry=None
        )
        
        # LLM 调用计数器
        self._llm_call = PrometheusCounter(
            "anime_agent_llm_call_total",
            "LLM 调用总次数",
            labelnames=("call_type", "result"),  # call_type: 调用类型(意图识别/参数提取/响应生成), result: success/error
            registry=None
        )
        
        # API 请求计数器
        self._api_request = PrometheusCounter(
            "anime_agent_api_request_total",
            "API 请求总次数",
            labelnames=("endpoint", "method", "status"),  # endpoint: API 端点, method: HTTP 方法, status: 状态码
            registry=None
        )
        
        logger.info("✅ Counter 指标注册完成")
    
    @property
    def intent_recognition(self) -> PrometheusCounter:
        return self._intent_recognition
    
    @property
    def tool_call(self) -> PrometheusCounter:
        return self._tool_call
    
    @property
    def data_source_query(self) -> PrometheusCounter:
        return self._data_source_query
    
    @property
    def llm_call(self) -> PrometheusCounter:
        return self._llm_call
    
    @property
    def api_request(self) -> PrometheusCounter:
        return self._api_request


# 全局 Counter 指标实例
_counter_metrics: Optional[CounterMetrics] = None


def get_counter_metrics() -> CounterMetrics:
    """获取全局 Counter 指标实例"""
    global _counter_metrics
    if _counter_metrics is None:
        _counter_metrics = CounterMetrics()
    return _counter_metrics


# 便捷函数：预定义的计数器实例
def get_intent_recognition_counter() -> PrometheusCounter:
    """获取意图识别计数器"""
    return get_counter_metrics().intent_recognition


def get_tool_call_counter() -> PrometheusCounter:
    """获取工具调用计数器"""
    return get_counter_metrics().tool_call


def get_data_source_query_counter() -> PrometheusCounter:
    """获取数据源查询计数器"""
    return get_counter_metrics().data_source_query


def get_llm_call_counter() -> PrometheusCounter:
    """获取 LLM 调用计数器"""
    return get_counter_metrics().llm_call


def get_api_request_counter() -> PrometheusCounter:
    """获取 API 请求计数器"""
    return get_counter_metrics().api_request


# 预定义的计数器实例（用于直接引用）
intent_recognition_total = get_intent_recognition_counter()
tool_call_total = get_tool_call_counter()
data_source_query_total = get_data_source_query_counter()
llm_call_total = get_llm_call_counter()
api_request_total = get_api_request_counter()
