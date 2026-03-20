"""追踪模块测试 - Trace ID 生成和传递"""

import pytest
import time
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.tracing import (
    generate_trace_id,
    Tracer,
    get_tracer,
    TracingContext,
    create_tracing_context,
    get_tracing_context,
    clear_tracing_context,
)


class TestGenerateTraceId:
    """测试 Trace ID 生成"""

    def test_generate_trace_id_format(self):
        """测试 Trace ID 格式"""
        trace_id = generate_trace_id()
        
        # 格式应该是: YYYYMMDDHHMMSS-xxxxxxxx
        assert len(trace_id) > 15
        assert "-" in trace_id
        
        # 验证时间戳部分
        parts = trace_id.split("-")
        timestamp_part = parts[0]
        assert len(timestamp_part) == 14  # YYYYMMDDHHMMSS
        assert timestamp_part.isdigit()
    
    def test_generate_trace_id_unique(self):
        """测试生成的 Trace ID 唯一性"""
        trace_ids = [generate_trace_id() for _ in range(100)]
        
        # 所有 ID 应该唯一
        assert len(set(trace_ids)) == 100
    
    def test_generate_trace_id_not_empty(self):
        """测试生成的 Trace ID 不为空"""
        trace_id = generate_trace_id()
        assert trace_id is not None
        assert len(trace_id) > 0


class TestTracer:
    """测试追踪器"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清理状态"""
        clear_tracing_context()
        self.tracer = get_tracer()
        self.tracer._spans.clear()
        yield
        clear_tracing_context()
        self.tracer._spans.clear()

    def test_start_trace(self):
        """测试开始追踪"""
        trace_id = self.tracer.start_trace()
        
        assert trace_id is not None
        assert self.tracer.get_current_trace_id() == trace_id
    
    def test_start_trace_with_custom_id(self):
        """测试使用自定义 ID 开始追踪"""
        custom_id = "test-trace-123"
        trace_id = self.tracer.start_trace(custom_id)
        
        assert trace_id == custom_id
        assert self.tracer.get_current_trace_id() == custom_id
    
    def test_end_trace(self):
        """测试结束追踪"""
        trace_id = self.tracer.start_trace()
        self.tracer.end_trace()
        
        assert self.tracer.get_current_trace_id() is None
    
    def test_start_and_end_span(self):
        """测试跨度的开始和结束"""
        trace_id = self.tracer.start_trace()
        
        # 开始意图解析跨度
        span = self.tracer.start_span(
            operation_name="intent_recognition",
            stage="intent",
            input_params={"query": "推荐几部国漫"}
        )
        
        assert span.trace_id == trace_id
        assert span.operation_name == "intent_recognition"
        assert span.stage == "intent"
        
        # 结束跨度
        time.sleep(0.01)  # 模拟处理
        self.tracer.end_span(
            output_params={"anime_type": "国漫"},
            success=True
        )
        
        # 验证跨度已记录
        spans = self.tracer.get_trace(trace_id)
        assert len(spans) == 1
        assert spans[0].duration is not None
        assert spans[0].duration > 0
    
    def test_multiple_spans(self):
        """测试多个跨度"""
        trace_id = self.tracer.start_trace()
        
        # 意图解析
        self.tracer.start_span(
            operation_name="intent_recognition",
            stage="intent",
            input_params={"query": "推荐几部国漫"}
        )
        self.tracer.end_span(
            output_params={"intent": "query", "anime_type": "国漫"}
        )
        
        # 参数提取
        self.tracer.start_span(
            operation_name="param_extraction",
            stage="intent",
            input_params={"query": "推荐几部国漫"}
        )
        self.tracer.end_span(
            output_params={"anime_type": "国漫", "sort_by": "rating"}
        )
        
        # 计划生成
        self.tracer.start_span(
            operation_name="plan_generation",
            stage="plan",
            input_params={"intent": "query"}
        )
        self.tracer.end_span(
            output_params={"tool": "query_anime", "params": {...}}
        )
        
        # 验证三个跨度都已记录
        spans = self.tracer.get_trace(trace_id)
        assert len(spans) == 3
    
    def test_span_with_tags_and_logs(self):
        """测试跨度的标签和日志"""
        trace_id = self.tracer.start_trace()
        
        span = self.tracer.start_span(
            operation_name="test_operation",
            stage="test"
        )
        
        # 添加标签
        span.add_tag("user_id", "test_user")
        span.add_tag("session_id", "test_session")
        
        # 添加日志
        span.add_log("开始处理")
        span.add_log("处理中", progress=50)
        span.add_log("处理完成")
        
        self.tracer.end_span()
        
        # 验证标签
        assert span.tags["user_id"] == "test_user"
        assert span.tags["session_id"] == "test_session"
        
        # 验证日志
        assert len(span.logs) == 3
    
    def test_trace_summary(self):
        """测试追踪摘要"""
        trace_id = self.tracer.start_trace()
        
        # 添加一些跨度
        self.tracer.start_span("intent_recognition", "intent")
        time.sleep(0.01)
        self.tracer.end_span(success=True)
        
        self.tracer.start_span("param_extraction", "intent")
        time.sleep(0.01)
        self.tracer.end_span(success=True)
        
        self.tracer.start_span("tool_execution", "execution")
        time.sleep(0.01)
        self.tracer.end_span(success=False, error="Test error")
        
        # 获取摘要
        summary = self.tracer.get_trace_summary(trace_id)
        
        assert summary["trace_id"] == trace_id
        assert summary["span_count"] == 3
        assert summary["success_count"] == 2
        assert summary["failure_count"] == 1
        assert "intent" in summary["stages"]
        assert "execution" in summary["stages"]


class TestTracingContext:
    """测试追踪上下文"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清理状态"""
        clear_tracing_context()
        yield
        clear_tracing_context()

    def test_create_tracing_context(self):
        """测试创建追踪上下文"""
        context = create_tracing_context(
            trace_id="test-123",
            user_query="推荐几部国漫",
            user_id="user1",
            session_id="session1"
        )
        
        assert context.trace_id == "test-123"
        assert context.user_query == "推荐几部国漫"
        assert context.user_id == "user1"
        assert context.session_id == "session1"
        assert get_tracing_context() is not None
    
    def test_update_param(self):
        """测试更新参数"""
        context = create_tracing_context("test-123")
        
        # 首次设置参数
        context.update_param("anime_type", "国漫", source="llm")
        assert context.query_params["anime_type"] == "国漫"
        assert context.get_param_source("anime_type") == "llm"
        
        # 更新参数
        context.update_param("anime_type", "日漫", source="rule")
        assert context.query_params["anime_type"] == "日漫"
        
        # 验证变更历史
        history = context.get_param_history("anime_type")
        assert len(history) == 1
        assert history[0]["old_value"] == "国漫"
        assert history[0]["new_value"] == "日漫"
        assert history[0]["source"] == "rule"
    
    def test_set_stage(self):
        """测试设置阶段"""
        context = create_tracing_context("test-123")
        
        context.set_stage("intent", "intent_recognition")
        assert context.current_stage == "intent"
        assert context.current_operation == "intent_recognition"
    
    def test_record_timing(self):
        """测试记录耗时"""
        context = create_tracing_context("test-123")
        
        context.record_timing("intent_parsing", 0.5)
        context.record_timing("tool_execution", 1.2)
        
        assert context.stage_timings["intent_parsing"] == 0.5
        assert context.stage_timings["tool_execution"] == 1.2
    
    def test_to_dict(self):
        """测试转换为字典"""
        context = create_tracing_context(
            trace_id="test-123",
            user_query="推荐几部国漫"
        )
        context.update_param("anime_type", "国漫", source="llm")
        
        result = context.to_dict()
        
        assert result["trace_id"] == "test-123"
        assert result["user_query"] == "推荐几部国漫"
        assert result["query_params"]["anime_type"] == "国漫"
        assert result["param_sources"]["anime_type"] == "llm"


class TestTracerIntegration:
    """测试追踪器集成"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清理状态"""
        clear_tracing_context()
        self.tracer = get_tracer()
        self.tracer._spans.clear()
        yield
        clear_tracing_context()
        self.tracer._spans.clear()

    def test_full_request_tracking(self):
        """测试完整请求追踪流程"""
        
        # 1. 开始追踪
        trace_id = self.tracer.start_trace()
        
        # 2. 意图解析阶段
        self.tracer.start_span(
            operation_name="intent_recognition",
            stage="intent",
            input_params={"query": "推荐几部国漫"}
        )
        self.tracer.end_span(
            output_params={"intent": "query", "confidence": "high"}
        )
        
        # 3. 参数提取阶段
        self.tracer.start_span(
            operation_name="param_extraction",
            stage="intent",
            input_params={"query": "推荐几部国漫"}
        )
        self.tracer.end_span(
            output_params={"anime_type": "国漫", "sort_by": "rating"}
        )
        
        # 4. 工具执行阶段
        self.tracer.start_span(
            operation_name="query_anime",
            stage="execution",
            input_params={"anime_type": "国漫"}
        )
        self.tracer.end_span(
            output_params={"result_count": 10},
            success=True
        )
        
        # 5. 结束追踪
        self.tracer.end_trace()
        
        # 验证追踪摘要
        summary = self.tracer.get_trace_summary(trace_id)
        assert summary["span_count"] == 3
        assert summary["success_count"] == 3
        assert summary["failure_count"] == 0


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", "--tb=short", __file__]))
