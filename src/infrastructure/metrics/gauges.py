"""Gauge 指标定义 - 当前值仪表盘"""

import logging
from typing import Optional
from prometheus_client import Gauge as PrometheusGauge

logger = logging.getLogger(__name__)


class GaugeMetrics:
    """Gauge 指标管理器
    
    提供预定义的业务 Gauge 指标：
    - active_requests: 当前活跃请求数
    - session_count: 当前会话数
    """
    
    def __init__(self):
        # 当前活跃请求数
        self._active_requests: Optional[PrometheusGauge] = None
        
        # 当前会话数
        self._session_count: Optional[PrometheusGauge] = None
        
        # 系统运行时间（秒）
        self._uptime_seconds: Optional[PrometheusGauge] = None
        
        # 当前在线用户数
        self._online_users: Optional[PrometheusGauge] = None
        
        self._register_gauges()
    
    def _register_gauges(self):
        """注册所有 Gauge 指标"""
        
        # 当前活跃请求数
        self._active_requests = PrometheusGauge(
            "anime_agent_active_requests",
            "当前活跃的请求数",
            labelnames=("endpoint",),  # endpoint: API 端点
            registry=None
        )
        
        # 当前会话数
        self._session_count = PrometheusGauge(
            "anime_agent_session_count",
            "当前活跃的会话数",
            registry=None
        )
        
        # 系统运行时间
        self._uptime_seconds = PrometheusGauge(
            "anime_agent_uptime_seconds",
            "系统运行时间（秒）",
            registry=None
        )
        
        # 当前在线用户数
        self._online_users = PrometheusGauge(
            "anime_agent_online_users",
            "当前在线用户数",
            registry=None
        )
        
        logger.info("✅ Gauge 指标注册完成")
    
    @property
    def active_requests(self) -> PrometheusGauge:
        return self._active_requests
    
    @property
    def session_count(self) -> PrometheusGauge:
        return self._session_count
    
    @property
    def uptime_seconds(self) -> PrometheusGauge:
        return self._uptime_seconds
    
    @property
    def online_users(self) -> PrometheusGauge:
        return self._online_users


# 全局 Gauge 指标实例
_gauge_metrics: Optional[GaugeMetrics] = None


def get_gauge_metrics() -> GaugeMetrics:
    """获取全局 Gauge 指标实例"""
    global _gauge_metrics
    if _gauge_metrics is None:
        _gauge_metrics = GaugeMetrics()
    return _gauge_metrics


# 预定义的 Gauge 实例（用于直接引用）
active_requests = get_gauge_metrics().active_requests
session_count = get_gauge_metrics().session_count
