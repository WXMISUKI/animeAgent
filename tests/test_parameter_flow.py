"""参数追踪测试 - 参数流动追踪"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.tracing.parameter_tracker import (
    ParameterTracker,
    get_parameter_tracker,
    ParamSource,
    ParamStage,
)


class TestParameterTracker:
    """测试参数追踪器"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清理状态"""
        self.tracker = get_parameter_tracker()
        self.tracker._snapshots.clear()
        self.tracker._changes.clear()
        yield
        self.tracker._snapshots.clear()
        self.tracker._changes.clear()

    def test_start_tracking(self):
        """测试开始追踪"""
        trace_id = "test-trace-123"
        
        self.tracker.start_tracking(
            trace_id=trace_id,
            initial_params={"query": "推荐几部国漫"}
        )
        
        # 验证快照已创建
        snapshots = self.tracker.get_snapshots(trace_id)
        assert len(snapshots) == 1
        assert snapshots[0]["stage"] == "input"
        assert snapshots[0]["params"]["query"] == "推荐几部国漫"

    def test_record_snapshot(self):
        """测试记录快照"""
        trace_id = "test-trace-123"
        
        # 记录多个快照
        self.tracker.record_snapshot(
            stage=ParamStage.INTENT_PARSER.value,
            operation="intent_recognition",
            params={"intent": "query"},
            source="llm",
            trace_id=trace_id
        )
        
        self.tracker.record_snapshot(
            stage=ParamStage.PARAM_EXTRACTION.value,
            operation="param_extraction",
            params={"anime_type": "国漫"},
            source="llm",
            trace_id=trace_id
        )
        
        # 验证快照记录
        snapshots = self.tracker.get_snapshots(trace_id)
        assert len(snapshots) == 2
        assert snapshots[0]["stage"] == "intent_parser"
        assert snapshots[1]["params"]["anime_type"] == "国漫"

    def test_record_change(self):
        """测试记录变更"""
        trace_id = "test-trace-123"
        
        # 记录参数变更
        self.tracker.record_change(
            param_name="anime_type",
            old_value=None,
            new_value="国漫",
            stage=ParamStage.PARAM_EXTRACTION.value,
            operation="param_extraction",
            source="llm",
            reason="LLM参数提取",
            trace_id=trace_id
        )
        
        self.tracker.record_change(
            param_name="anime_type",
            old_value="国漫",
            new_value="日漫",
            stage=ParamStage.RULE_BASED.value,
            operation="rule_fallback",
            source="rule",
            reason="规则兜底补充",
            trace_id=trace_id
        )
        
        # 验证变更记录
        changes = self.tracker.get_changes(trace_id)
        assert len(changes) == 2
        assert changes[0]["param_name"] == "anime_type"
        assert changes[0]["old_value"] is None
        assert changes[0]["new_value"] == "国漫"
        assert changes[1]["new_value"] == "日漫"
        assert changes[1]["source"] == "rule"

    def test_ignore_same_value_change(self):
        """测试忽略相同值的变更"""
        trace_id = "test-trace-123"
        
        # 记录相同值的变更
        self.tracker.record_change(
            param_name="anime_type",
            old_value="国漫",
            new_value="国漫",  # 相同值
            stage=ParamStage.PARAM_EXTRACTION.value,
            operation="param_extraction",
            source="llm",
            trace_id=trace_id
        )
        
        # 验证变更被忽略
        changes = self.tracker.get_changes(trace_id)
        assert len(changes) == 0

    def test_get_parameter_flow(self):
        """测试获取参数流动"""
        trace_id = "test-trace-123"
        
        # 模拟完整的参数流动
        self.tracker.start_tracking(trace_id, {"query": "推荐几部国漫"})
        
        self.tracker.record_snapshot(
            stage=ParamStage.INTENT_PARSER.value,
            operation="intent_recognition",
            params={"intent": "query"},
            source="llm",
            trace_id=trace_id
        )
        
        self.tracker.record_change(
            param_name="anime_type",
            old_value=None,
            new_value="国漫",
            stage=ParamStage.PARAM_EXTRACTION.value,
            operation="param_extraction",
            source="llm",
            trace_id=trace_id
        )
        
        self.tracker.record_change(
            param_name="sort_by",
            old_value=None,
            new_value="rating",
            stage=ParamStage.PARAM_EXTRACTION.value,
            operation="param_extraction",
            source="default",
            trace_id=trace_id
        )
        
        self.tracker.record_snapshot(
            stage=ParamStage.PLANNING.value,
            operation="plan_generation",
            params={"anime_type": "国漫", "sort_by": "rating"},
            source="planner",
            trace_id=trace_id
        )
        
        # 获取参数流动
        flow = self.tracker.get_parameter_flow(trace_id)
        
        assert flow["trace_id"] == trace_id
        assert flow["snapshot_count"] == 2
        assert flow["change_count"] == 2
        assert "anime_type" in flow["parameter_flows"]
        assert "sort_by" in flow["parameter_flows"]

    def test_get_param_history(self):
        """测试获取特定参数的历史"""
        trace_id = "test-trace-123"
        
        # 记录多次变更
        self.tracker.record_change(
            param_name="anime_type",
            old_value=None,
            new_value="国漫",
            stage=ParamStage.PARAM_EXTRACTION.value,
            source="llm",
            trace_id=trace_id
        )
        
        self.tracker.record_change(
            param_name="anime_type",
            old_value="国漫",
            new_value="日漫",
            stage=ParamStage.RULE_BASED.value,
            source="rule",
            trace_id=trace_id
        )
        
        # 获取 anime_type 的历史
        history = self.tracker.get_param_history("anime_type", trace_id)
        
        assert len(history) == 2
        assert history[0]["new_value"] == "国漫"
        assert history[1]["new_value"] == "日漫"

    def test_track_intent_parser_params(self):
        """测试追踪意图解析参数"""
        trace_id = "test-trace-123"
        
        self.tracker.start_tracking(trace_id)
        
        # 追踪意图解析
        self.tracker.track_intent_parser_params(
            raw_input="推荐几部国漫",
            extracted_params={"intent": "query", "anime_type": "国漫"},
            source="llm"
        )
        
        # 验证快照
        snapshots = self.tracker.get_snapshots(trace_id)
        assert len(snapshots) == 1
        assert snapshots[0]["operation"] == "intent_recognition"
        assert snapshots[0]["params"]["anime_type"] == "国漫"

    def test_track_rule_based_params(self):
        """测试追踪规则兜底参数"""
        trace_id = "test-trace-123"
        
        self.tracker.start_tracking(trace_id)
        
        # 追踪规则兜底
        self.tracker.track_rule_based_params(
            input_params={"anime_type": "国漫"},
            rule_params={"anime_type": "国漫", "sort_by": "rating"}
        )
        
        # 验证快照
        snapshots = self.tracker.get_snapshots(trace_id)
        assert len(snapshots) == 1
        assert snapshots[0]["operation"] == "rule_fallback"
        
        # 验证变更记录
        changes = self.tracker.get_changes(trace_id)
        # sort_by 是新增的参数，应该被记录
        assert any(c["param_name"] == "sort_by" for c in changes)

    def test_track_planner_params(self):
        """测试追踪 Planner 参数"""
        trace_id = "test-trace-123"
        
        self.tracker.start_tracking(trace_id)
        
        # 追踪 Planner
        self.tracker.track_planner_params(
            input_params={"anime_type": "国漫"},
            output_params={
                "tool": "query_anime",
                "params": {"anime_type": "国漫", "sort_by": "rating"}
            }
        )
        
        # 验证快照
        snapshots = self.tracker.get_snapshots(trace_id)
        assert len(snapshots) == 1
        assert snapshots[0]["operation"] == "plan_generation"
        assert snapshots[0]["params"]["tool"] == "query_anime"

    def test_track_executor_params(self):
        """测试追踪 Executor 参数"""
        trace_id = "test-trace-123"
        
        self.tracker.start_tracking(trace_id)
        
        # 追踪 Executor
        self.tracker.track_executor_params(
            tool_name="query_anime",
            input_params={"anime_type": "国漫"},
            output_result=[{"title": "国漫1"}, {"title": "国漫2"}]
        )
        
        # 验证快照
        snapshots = self.tracker.get_snapshots(trace_id)
        assert len(snapshots) == 1
        assert "tool_execution_query_anime" in snapshots[0]["operation"]
        assert snapshots[0]["params"]["result"] is not None


class TestParameterTrackerEdgeCases:
    """测试参数追踪器边界情况"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前清理状态"""
        self.tracker = get_parameter_tracker()
        self.tracker._snapshots.clear()
        self.tracker._changes.clear()
        yield
        self.tracker._snapshots.clear()
        self.tracker._changes.clear()

    def test_no_active_trace(self):
        """测试没有活动追踪时的行为"""
        # 应该不抛出异常，只是警告
        self.tracker.record_snapshot(
            stage="test",
            operation="test",
            params={"key": "value"}
        )
        
        # 验证没有记录
        snapshots = self.tracker.get_snapshots()
        assert len(snapshots) == 0

    def test_empty_params(self):
        """测试空参数"""
        trace_id = "test-trace-123"
        
        self.tracker.start_tracking(trace_id)
        
        self.tracker.record_snapshot(
            stage=ParamStage.INPUT.value,
            operation="test",
            params={},
            source="user"
        )
        
        snapshots = self.tracker.get_snapshots(trace_id)
        assert len(snapshots) == 1
        assert snapshots[0]["params"] == {}

    def test_complex_nested_params(self):
        """测试复杂的嵌套参数"""
        trace_id = "test-trace-123"
        
        complex_params = {
            "query": "推荐几部国漫",
            "filters": {
                "anime_type": "国漫",
                "year": 2024,
                "tags": ["热血", "冒险"]
            },
            "pagination": {
                "page": 1,
                "page_size": 10
            }
        }
        
        self.tracker.record_snapshot(
            stage=ParamStage.INPUT.value,
            operation="test",
            params=complex_params,
            source="user",
            trace_id=trace_id
        )
        
        snapshots = self.tracker.get_snapshots(trace_id)
        assert snapshots[0]["params"]["filters"]["anime_type"] == "国漫"
        assert snapshots[0]["params"]["pagination"]["page"] == 1

    def test_clear_trace(self):
        """测试清除追踪"""
        trace_id = "test-trace-123"
        
        self.tracker.start_tracking(trace_id, {"key": "value"})
        self.tracker.record_snapshot("test", "test", {"key": "value"})
        
        # 清除追踪
        self.tracker.clear_trace(trace_id)
        
        # 验证已清除
        snapshots = self.tracker.get_snapshots(trace_id)
        changes = self.tracker.get_changes(trace_id)
        assert len(snapshots) == 0
        assert len(changes) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
