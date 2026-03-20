"""Prometheus 指标收集器 - 统一管理所有指标"""

import logging
from typing import Optional, Dict, Any
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry, REGISTRY

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Prometheus 指标收集器
    
    统一管理所有 Prometheus 指标，提供：
    - 指标注册和管理
    - 指标数据收集
    - 指标导出
    """
    
    _instance: Optional["MetricsCollector"] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化指标收集器"""
        if self._initialized:
            return
        
        # 创建独立的注册表（避免与全局 REGISTRY 冲突）
        self.registry = CollectorRegistry()
        
        # 预定义的指标字典
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        
        # 注册预定义的指标
        self._register_default_metrics()
        
        self._initialized = True
        logger.info("📊 MetricsCollector 初始化完成")
    
    def _register_default_metrics(self):
        """注册默认的业务指标"""
        
        # 注册 Counter 指标
        self.register_counter(
            "anime_agent_intent_recognition_total",
            "意图识别总次数",
            labelnames=("intent_type", "result")
        )
        self.register_counter(
            "anime_agent_tool_call_total",
            "工具调用总次数",
            labelnames=("tool_name", "result")
        )
        self.register_counter(
            "anime_agent_data_source_query_total",
            "数据源查询总次数",
            labelnames=("data_source", "result")
        )
        self.register_counter(
            "anime_agent_llm_call_total",
            "LLM 调用总次数",
            labelnames=("call_type", "result")
        )
        self.register_counter(
            "anime_agent_api_request_total",
            "API 请求总次数",
            labelnames=("endpoint", "method", "status")
        )
        
        # 注册 Gauge 指标
        self.register_gauge(
            "anime_agent_active_requests",
            "当前活跃请求数",
            labelnames=("endpoint",)
        )
        self.register_gauge(
            "anime_agent_session_count",
            "当前会话数"
        )
        self.register_gauge(
            "anime_agent_uptime_seconds",
            "服务运行时间（秒）"
        )
        
        # 注册 Histogram 指标
        self.register_histogram(
            "anime_agent_request_duration_seconds",
            "请求处理时长（秒）",
            labelnames=("endpoint", "method")
        )
        self.register_histogram(
            "anime_agent_llm_token_usage",
            "LLM Token 使用量",
            labelnames=("token_type",)
        )
        self.register_histogram(
            "anime_agent_tool_execution_seconds",
            "工具执行时长（秒）",
            labelnames=("tool_name",)
        )
        self.register_histogram(
            "anime_agent_data_source_duration_seconds",
            "数据源查询时长（秒）",
            labelnames=("data_source",)
        )
        
        logger.info("✅ 默认指标注册完成")
    
    def register_counter(
        self,
        name: str,
        description: str,
        labelnames: tuple = ()
    ) -> Counter:
        """注册 Counter 指标"""
        if name in self._counters:
            return self._counters[name]
        
        counter = Counter(
            name=name,
            documentation=description,
            labelnames=labelnames,
            registry=self.registry
        )
        self._counters[name] = counter
        logger.debug(f"注册 Counter: {name}")
        return counter
    
    def register_gauge(
        self,
        name: str,
        description: str,
        labelnames: tuple = ()
    ) -> Gauge:
        """注册 Gauge 指标"""
        if name in self._gauges:
            return self._gauges[name]
        
        gauge = Gauge(
            name=name,
            documentation=description,
            labelnames=labelnames,
            registry=self.registry
        )
        self._gauges[name] = gauge
        logger.debug(f"注册 Gauge: {name}")
        return gauge
    
    def register_histogram(
        self,
        name: str,
        description: str,
        labelnames: tuple = (),
        buckets: tuple = None
    ) -> Histogram:
        """注册 Histogram 指标"""
        if name in self._histograms:
            return self._histograms[name]
        
        histogram = Histogram(
            name=name,
            documentation=description,
            labelnames=labelnames,
            buckets=buckets or Histogram.DEFAULT_BUCKETS,
            registry=self.registry
        )
        self._histograms[name] = histogram
        logger.debug(f"注册 Histogram: {name}")
        return histogram
    
    def inc_counter(self, name: str, labels: Dict[str, str] = None, value: float = 1):
        """增加 Counter 指标"""
        if name not in self._counters:
            logger.warning(f"Counter {name} 未注册")
            return
        
        counter = self._counters[name]
        if labels:
            counter.labels(**labels).inc(value)
        else:
            counter.inc(value)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """设置 Gauge 指标"""
        if name not in self._gauges:
            logger.warning(f"Gauge {name} 未注册")
            return
        
        gauge = self._gauges[name]
        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """观察 Histogram 指标"""
        if name not in self._histograms:
            logger.warning(f"Histogram {name} 未注册")
            return
        
        histogram = self._histograms[name]
        if labels:
            histogram.labels(**labels).observe(value)
        else:
            histogram.observe(value)
    
    def get_metrics(self) -> bytes:
        """获取所有指标的 Prometheus 格式"""
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """获取内容类型"""
        return CONTENT_TYPE_LATEST


# 全局指标收集器实例
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
