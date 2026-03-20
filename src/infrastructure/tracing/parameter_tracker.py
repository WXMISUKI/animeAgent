"""参数追踪器 - 记录参数在各个阶段的流动"""

import logging
import time
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ParamSource(Enum):
    """参数来源枚举"""
    LLM = "llm"           # LLM 提取
    RULE = "rule"         # 规则兜底
    DEFAULT = "default"   # 默认值
    USER = "user"         # 用户输入
    CONTEXT = "context"   # 上下文推断
    PLANNER = "planner"  # Planner 生成
    EXECUTOR = "executor" # Executor 生成


class ParamStage(Enum):
    """参数所在的阶段"""
    INPUT = "input"           # 输入阶段
    INTENT_PARSER = "intent_parser"  # 意图解析
    PARAM_EXTRACTION = "param_extraction"  # 参数提取
    RULE_BASED = "rule_based"  # 规则兜底
    VALIDATION = "validation"  # 参数校验
    PLANNING = "planning"     # 计划生成
    EXECUTION = "execution"   # 工具执行
    OUTPUT = "output"         # 输出阶段


@dataclass
class ParameterSnapshot:
    """参数快照 - 记录参数在某个时刻的状态"""
    
    stage: str  # 阶段名称
    operation: str  # 操作名称
    timestamp: float  # 时间戳
    params: Dict[str, Any]  # 参数快照
    source: str  # 参数来源
    trace_id: str = ""  # 追踪 ID
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "operation": self.operation,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "params": self.params,
            "source": self.source,
            "trace_id": self.trace_id,
        }


@dataclass
class ParameterChange:
    """参数变更记录"""
    
    param_name: str  # 参数名称
    old_value: Any  # 旧值
    new_value: Any  # 新值
    stage: str  # 变更发生的阶段
    operation: str  # 变更发生的操作
    timestamp: float  # 时间戳
    source: str  # 变更来源
    reason: str = ""  # 变更原因
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "param_name": self.param_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "stage": self.stage,
            "operation": self.operation,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "source": self.source,
            "reason": self.reason,
        }


class ParameterTracker:
    """参数追踪器 - 追踪参数在整个请求生命周期中的流动
    
    功能：
    - 记录参数在每个阶段的快照
    - 追踪参数的变更历史
    - 记录参数的来源
    - 提供参数流动的可视化
    """
    
    def __init__(self):
        # 快照存储 {trace_id: [snapshots]}
        self._snapshots: Dict[str, List[ParameterSnapshot]] = {}
        
        # 变更记录 {trace_id: [changes]}
        self._changes: Dict[str, List[ParameterChange]] = {}
        
        # 当前追踪的 trace_id
        self._current_trace_id: Optional[str] = None
    
    def start_tracking(self, trace_id: str, initial_params: Dict[str, Any] = None, source: str = "user"):
        """开始追踪参数
        
        Args:
            trace_id: 追踪 ID
            initial_params: 初始参数
            source: 参数来源
        """
        self._current_trace_id = trace_id
        
        if trace_id not in self._snapshots:
            self._snapshots[trace_id] = []
            self._changes[trace_id] = []
        
        # 记录初始快照
        if initial_params:
            self.record_snapshot(
                stage=ParamStage.INPUT.value,
                operation="initial_input",
                params=initial_params,
                source=source
            )
        
        logger.debug(f"📊 参数追踪开始: trace_id={trace_id}")
    
    def stop_tracking(self):
        """停止追踪"""
        self._current_trace_id = None
    
    def record_snapshot(
        self,
        stage: str,
        operation: str,
        params: Dict[str, Any],
        source: str = "unknown",
        trace_id: str = None
    ):
        """记录参数快照
        
        Args:
            stage: 阶段名称
            operation: 操作名称
            params: 当前参数
            source: 参数来源
            trace_id: 追踪 ID
        """
        if trace_id is None:
            trace_id = self._current_trace_id
        
        if trace_id is None:
            logger.warning("没有活动的追踪，无法记录快照")
            return
        
        snapshot = ParameterSnapshot(
            stage=stage,
            operation=operation,
            timestamp=time.time(),
            params=self._serialize_params(params),
            source=source,
            trace_id=trace_id
        )
        
        if trace_id not in self._snapshots:
            self._snapshots[trace_id] = []
        
        self._snapshots[trace_id].append(snapshot)
        
        logger.debug(f"📸 参数快照: trace_id={trace_id}, stage={stage}, operation={operation}")
    
    def record_change(
        self,
        param_name: str,
        old_value: Any,
        new_value: Any,
        stage: str,
        operation: str,
        source: str = "unknown",
        reason: str = "",
        trace_id: str = None
    ):
        """记录参数变更
        
        Args:
            param_name: 参数名称
            old_value: 旧值
            new_value: 新值
            stage: 变更发生的阶段
            operation: 变更发生的操作
            source: 变更来源
            reason: 变更原因
            trace_id: 追踪 ID
        """
        if trace_id is None:
            trace_id = self._current_trace_id
        
        if trace_id is None:
            logger.warning("没有活动的追踪，无法记录变更")
            return
        
        # 忽略没有实际变化的变更
        if old_value == new_value:
            return
        
        change = ParameterChange(
            param_name=param_name,
            old_value=self._serialize_value(old_value),
            new_value=self._serialize_value(new_value),
            stage=stage,
            operation=operation,
            timestamp=time.time(),
            source=source,
            reason=reason
        )
        
        if trace_id not in self._changes:
            self._changes[trace_id] = []
        
        self._changes[trace_id].append(change)
        
        logger.debug(
            f"🔄 参数变更: trace_id={trace_id}, param={param_name}, "
            f"stage={stage}, source={source}"
        )
    
    def get_snapshots(self, trace_id: str = None) -> List[Dict[str, Any]]:
        """获取指定追踪的所有快照"""
        if trace_id is None:
            trace_id = self._current_trace_id
        
        if trace_id is None:
            return []
        
        return [s.to_dict() for s in self._snapshots.get(trace_id, [])]
    
    def get_changes(self, trace_id: str = None) -> List[Dict[str, Any]]:
        """获取指定追踪的所有变更"""
        if trace_id is None:
            trace_id = self._current_trace_id
        
        if trace_id is None:
            return []
        
        return [c.to_dict() for c in self._changes.get(trace_id, [])]
    
    def get_parameter_flow(self, trace_id: str = None) -> Dict[str, Any]:
        """获取参数流动的完整视图
        
        Returns:
            包含快照和变更的完整流动视图
        """
        if trace_id is None:
            trace_id = self._current_trace_id
        
        if trace_id is None:
            return {}
        
        snapshots = self.get_snapshots(trace_id)
        changes = self.get_changes(trace_id)
        
        # 分析每个参数的变化路径
        param_paths = {}
        for change in changes:
            param_name = change["param_name"]
            if param_name not in param_paths:
                param_paths[param_name] = []
            param_paths[param_name].append(change)
        
        return {
            "trace_id": trace_id,
            "snapshots": snapshots,
            "changes": changes,
            "parameter_flows": param_paths,
            "snapshot_count": len(snapshots),
            "change_count": len(changes),
        }
    
    def get_param_history(self, param_name: str, trace_id: str = None) -> List[Dict[str, Any]]:
        """获取特定参数的历史变更"""
        if trace_id is None:
            trace_id = self._current_trace_id
        
        if trace_id is None:
            return []
        
        return [
            c.to_dict() for c in self._changes.get(trace_id, [])
            if c.param_name == param_name
        ]
    
    def clear_trace(self, trace_id: str = None):
        """清除追踪记录"""
        if trace_id:
            self._snapshots.pop(trace_id, None)
            self._changes.pop(trace_id, None)
        else:
            self._snapshots.clear()
            self._changes.clear()
    
    def _serialize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """序列化参数字典"""
        result = {}
        for key, value in params.items():
            result[key] = self._serialize_value(value)
        return result
    
    def _serialize_value(self, value: Any) -> Any:
        """序列化单个值"""
        try:
            # 尝试序列化为 JSON
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            # 如果无法序列化，转换为字符串
            return str(value)
    
    # ==================== 便捷方法 ====================
    
    def track_intent_parser_params(
        self,
        raw_input: str,
        extracted_params: Dict[str, Any],
        source: str = "llm"
    ):
        """追踪意图解析阶段的参数"""
        self.record_snapshot(
            stage=ParamStage.INTENT_PARSER.value,
            operation="intent_recognition",
            params=extracted_params,
            source=source
        )
    
    def track_param_extraction(
        self,
        input_params: Dict[str, Any],
        output_params: Dict[str, Any],
        source: str = "llm"
    ):
        """追踪参数提取阶段的参数变化"""
        # 记录输入快照
        self.record_snapshot(
            stage=ParamStage.PARAM_EXTRACTION.value,
            operation="param_input",
            params=input_params,
            source=source
        )
        
        # 记录输出快照
        self.record_snapshot(
            stage=ParamStage.PARAM_EXTRACTION.value,
            operation="param_output",
            params=output_params,
            source=source
        )
        
        # 记录变更
        for key, new_value in output_params.items():
            old_value = input_params.get(key)
            self.record_change(
                param_name=key,
                old_value=old_value,
                new_value=new_value,
                stage=ParamStage.PARAM_EXTRACTION.value,
                operation="param_extraction",
                source=source,
                reason="LLM参数提取"
            )
    
    def track_rule_based_params(
        self,
        input_params: Dict[str, Any],
        rule_params: Dict[str, Any]
    ):
        """追踪规则兜底的参数"""
        merged_params = {**input_params, **rule_params}
        
        self.record_snapshot(
            stage=ParamStage.RULE_BASED.value,
            operation="rule_fallback",
            params=rule_params,
            source="rule"
        )
        
        # 记录规则兜底带来的变更
        for key, new_value in rule_params.items():
            if input_params.get(key) != new_value:
                self.record_change(
                    param_name=key,
                    old_value=input_params.get(key),
                    new_value=new_value,
                    stage=ParamStage.RULE_BASED.value,
                    operation="rule_fallback",
                    source="rule",
                    reason="规则兜底补充"
                )
    
    def track_planner_params(
        self,
        input_params: Dict[str, Any],
        output_params: Dict[str, Any]
    ):
        """追踪 Planner 阶段的参数"""
        self.record_snapshot(
            stage=ParamStage.PLANNING.value,
            operation="plan_generation",
            params=output_params,
            source="planner"
        )
        
        # 记录参数变更
        for key, new_value in output_params.items():
            old_value = input_params.get(key)
            self.record_change(
                param_name=key,
                old_value=old_value,
                new_value=new_value,
                stage=ParamStage.PLANNING.value,
                operation="plan_generation",
                source="planner",
                reason="Planner生成执行计划"
            )
    
    def track_executor_params(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        output_result: Any = None
    ):
        """追踪 Executor 阶段的参数"""
        result_params = {"result": str(output_result)[:200] if output_result else None}
        
        self.record_snapshot(
            stage=ParamStage.EXECUTION.value,
            operation=f"tool_execution_{tool_name}",
            params={**input_params, **result_params},
            source="executor"
        )


# 全局参数追踪器实例
_parameter_tracker: Optional[ParameterTracker] = None


def get_parameter_tracker() -> ParameterTracker:
    """获取全局参数追踪器实例"""
    global _parameter_tracker
    if _parameter_tracker is None:
        _parameter_tracker = ParameterTracker()
    return _parameter_tracker
