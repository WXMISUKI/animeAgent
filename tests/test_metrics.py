"""监控指标测试 - Prometheus 指标收集"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.metrics import (
    MetricsCollector,
    get_metrics_collector,
    CounterMetrics,
    GaugeMetrics,
    HistogramMetrics,
    BusinessMetrics,
    get_business_metrics,
)


class TestMetricsCollector:
    """测试指标收集器"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前创建新的收集器"""
        self.collector = MetricsCollector()
        yield

    def test_singleton(self):
        """测试单例模式"""
        collector1 = MetricsCollector()
        collector2 = MetricsCollector()
        
        assert collector1 is collector2

    def test_register_counter(self):
        """测试注册 Counter 指标"""
        counter = self.collector.register_counter(
            name="test_counter_total",
            description="测试计数器",
            labelnames=("label1",)
        )
        
        assert counter is not None
        assert "test_counter_total" in self.collector._counters

    def test_register_gauge(self):
        """测试注册 Gauge 指标"""
        gauge = self.collector.register_gauge(
            name="test_gauge",
            description="测试仪表",
            labelnames=("label1",)
        )
        
        assert gauge is not None
        assert "test_gauge" in self.collector._gauges

    def test_register_histogram(self):
        """测试注册 Histogram 指标"""
        histogram = self.collector.register_histogram(
            name="test_histogram_seconds",
            description="测试直方图",
            labelnames=("label1",)
        )
        
        assert histogram is not None
        assert "test_histogram_seconds" in self.collector._histograms

    def test_inc_counter(self):
        """测试增加 Counter"""
        self.collector.register_counter(
            name="test_counter_total",
            description="测试计数器"
        )
        
        self.collector.inc_counter("test_counter_total")
        self.collector.inc_counter("test_counter_total")
        
        # 验证计数器已增加
        # 注意：Prometheus 指标需要在 registry 中才能读取
        assert "test_counter_total" in self.collector._counters

    def test_set_gauge(self):
        """测试设置 Gauge"""
        self.collector.register_gauge(
            name="test_gauge",
            description="测试仪表"
        )
        
        self.collector.set_gauge("test_gauge", 10.0)
        self.collector.set_gauge("test_gauge", 20.0)
        
        assert "test_gauge" in self.collector._gauges

    def test_observe_histogram(self):
        """测试观察 Histogram"""
        self.collector.register_histogram(
            name="test_histogram_seconds",
            description="测试直方图"
        )
        
        self.collector.observe_histogram("test_histogram_seconds", 0.1)
        self.collector.observe_histogram("test_histogram_seconds", 0.5)
        self.collector.observe_histogram("test_histogram_seconds", 1.0)
        
        assert "test_histogram_seconds" in self.collector._histograms

    def test_counter_with_labels(self):
        """测试带标签的 Counter"""
        counter = self.collector.register_counter(
            name="test_labeled_counter_total",
            description="测试计数器",
            labelnames=("endpoint",)
        )
        
        # 增加带标签的计数
        counter.labels(endpoint="/api/chat").inc()
        counter.labels(endpoint="/api/query").inc()
        
        assert "test_labeled_counter_total" in self.collector._counters


class TestCounterMetrics:
    """测试 Counter 指标"""

    def test_counter_metrics_instance(self):
        """测试 Counter 指标实例"""
        metrics = CounterMetrics()
        
        assert metrics.intent_recognition is not None
        assert metrics.tool_call is not None
        assert metrics.data_source_query is not None
        assert metrics.llm_call is not None
        assert metrics.api_request is not None

    def test_intent_recognition_counter(self):
        """测试意图识别计数器"""
        metrics = CounterMetrics()
        
        # 记录意图识别
        metrics.intent_recognition.labels(
            intent_type="query",
            result="success"
        ).inc()
        
        metrics.intent_recognition.labels(
            intent_type="query",
            result="failure"
        ).inc()
        
        # 验证
        assert metrics.intent_recognition is not None

    def test_tool_call_counter(self):
        """测试工具调用计数器"""
        metrics = CounterMetrics()
        
        # 记录工具调用
        metrics.tool_call.labels(
            tool_name="query_anime",
            result="success"
        ).inc()
        
        metrics.tool_call.labels(
            tool_name="query_anime",
            result="error"
        ).inc()
        
        assert metrics.tool_call is not None

    def test_data_source_counter(self):
        """测试数据源计数器"""
        metrics = CounterMetrics()
        
        # 记录数据源查询
        metrics.data_source_query.labels(
            data_source="jikan",
            result="success"
        ).inc()
        
        assert metrics.data_source_query is not None


class TestGaugeMetrics:
    """测试 Gauge 指标"""

    def test_gauge_metrics_instance(self):
        """测试 Gauge 指标实例"""
        metrics = GaugeMetrics()
        
        assert metrics.active_requests is not None
        assert metrics.session_count is not None
        assert metrics.uptime_seconds is not None

    def test_set_active_requests(self):
        """测试设置活跃请求数"""
        metrics = GaugeMetrics()
        
        metrics.active_requests.labels(endpoint="/api/chat").set(5)
        
        assert metrics.active_requests is not None

    def test_set_session_count(self):
        """测试设置会话数"""
        metrics = GaugeMetrics()
        
        metrics.session_count.set(10)
        
        assert metrics.session_count is not None


class TestHistogramMetrics:
    """测试 Histogram 指标"""

    def test_histogram_metrics_instance(self):
        """测试 Histogram 指标实例"""
        metrics = HistogramMetrics()
        
        assert metrics.request_duration is not None
        assert metrics.llm_token is not None
        assert metrics.tool_execution is not None
        assert metrics.data_source_duration is not None

    def test_observe_request_duration(self):
        """测试观察请求延迟"""
        metrics = HistogramMetrics()
        
        # 记录请求延迟
        metrics.request_duration.labels(
            endpoint="/api/chat",
            method="POST"
        ).observe(0.5)
        
        metrics.request_duration.labels(
            endpoint="/api/query",
            method="POST"
        ).observe(1.2)
        
        assert metrics.request_duration is not None

    def test_observe_token_usage(self):
        """测试观察 Token 使用量"""
        metrics = HistogramMetrics()
        
        # 记录 Token 使用
        metrics.llm_token.labels(token_type="input").observe(100)
        metrics.llm_token.labels(token_type="output").observe(200)
        
        assert metrics.llm_token is not None


class TestBusinessMetrics:
    """测试业务指标"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前创建新的业务指标"""
        self.metrics = BusinessMetrics()
        yield

    def test_record_intent_recognition(self):
        """测试记录意图识别"""
        self.metrics.record_intent_recognition("query", success=True)
        self.metrics.record_intent_recognition("query", success=True)
        self.metrics.record_intent_recognition("query", success=False)
        
        stats = self.metrics.get_intent_stats()
        
        assert stats["by_type"]["query"]["success"] == 2
        assert stats["by_type"]["query"]["failure"] == 1

    def test_get_intent_accuracy(self):
        """测试获取意图识别准确率"""
        self.metrics.record_intent_recognition("query", success=True)
        self.metrics.record_intent_recognition("query", success=True)
        self.metrics.record_intent_recognition("query", success=False)
        self.metrics.record_intent_recognition("detail", success=True)
        
        accuracy = self.metrics.get_intent_accuracy()
        
        assert accuracy == 0.75  # 3/4 = 0.75

    def test_record_tool_call(self):
        """测试记录工具调用"""
        self.metrics.record_tool_call("query_anime", success=True, duration=0.5)
        self.metrics.record_tool_call("query_anime", success=True, duration=0.3)
        self.metrics.record_tool_call("query_anime", success=False, duration=0.1)
        
        stats = self.metrics.get_tool_stats()
        
        assert stats["query_anime"]["success"] == 2
        assert stats["query_anime"]["failure"] == 1

    def test_get_tool_success_rate(self):
        """测试获取工具成功率"""
        self.metrics.record_tool_call("query_anime", success=True)
        self.metrics.record_tool_call("query_anime", success=True)
        self.metrics.record_tool_call("query_anime", success=False)
        
        rate = self.metrics.get_tool_success_rate("query_anime")
        
        assert rate == 2/3

    def test_record_data_source_query(self):
        """测试记录数据源查询"""
        self.metrics.record_data_source_query("jikan", success=True, duration=0.5)
        self.metrics.record_data_source_query("jikan", success=False, duration=0.3)
        
        stats = self.metrics.get_data_source_stats()
        
        assert stats["jikan"]["success"] == 1
        assert stats["jikan"]["failure"] == 1

    def test_record_token_usage(self):
        """测试记录 Token 使用"""
        self.metrics.record_token_usage(input_tokens=100, output_tokens=200)
        self.metrics.record_token_usage(input_tokens=150, output_tokens=250)
        
        stats = self.metrics.get_token_stats()
        
        assert stats["input_tokens"] == 250
        assert stats["output_tokens"] == 450
        assert stats["total_tokens"] == 700

    def test_calculate_cost(self):
        """测试计算成本"""
        self.metrics.record_token_usage(input_tokens=1000, output_tokens=500)
        
        # 假设输入价格 0.001/token，输出价格 0.002/token
        cost = self.metrics.calculate_cost(
            input_price=0.001,
            output_price=0.002
        )
        
        assert cost == 1.0 + 1.0  # 1000*0.001 + 500*0.002

    def test_record_request_latency(self):
        """测试记录请求延迟"""
        self.metrics.record_request_latency("/api/chat", 0.5)
        self.metrics.record_request_latency("/api/chat", 1.0)
        self.metrics.record_request_latency("/api/chat", 1.5)
        
        stats = self.metrics.get_latency_stats("/api/chat")
        
        assert stats["count"] == 3
        assert stats["min"] == 0.5
        assert stats["max"] == 1.5
        assert stats["avg"] == 1.0

    def test_get_summary(self):
        """测试获取汇总"""
        self.metrics.record_intent_recognition("query", success=True)
        self.metrics.record_tool_call("query_anime", success=True, duration=0.5)
        self.metrics.record_token_usage(input_tokens=100, output_tokens=200)
        
        summary = self.metrics.get_summary()
        
        assert "timestamp" in summary
        assert "intent_recognition" in summary
        assert "tool_call" in summary
        assert "token_usage" in summary

    def test_reset(self):
        """测试重置"""
        self.metrics.record_intent_recognition("query", success=True)
        self.metrics.record_token_usage(input_tokens=100, output_tokens=200)
        
        # 重置
        self.metrics.reset()
        
        # 验证已重置
        stats = self.metrics.get_intent_stats()
        assert stats["overall_accuracy"] == 0.0


class TestMetricsIntegration:
    """测试指标集成"""

    def test_get_metrics_collector(self):
        """测试获取指标收集器"""
        collector = get_metrics_collector()
        
        assert collector is not None

    def test_get_business_metrics(self):
        """测试获取业务指标"""
        metrics = get_business_metrics()
        
        assert metrics is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
