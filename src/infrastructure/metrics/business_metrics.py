"""业务指标 - 高级指标封装"""

import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class BusinessMetrics:
    """业务指标管理器
    
    提供高级业务指标封装：
    - 意图识别准确率统计
    - 工具调用成功率统计
    - 数据源查询成功率统计
    - Token 消耗统计
    - 成本计算
    """
    
    def __init__(self):
        # 意图识别统计
        self._intent_stats: Dict[str, Dict[str, int]] = {}
        
        # 工具调用统计
        self._tool_stats: Dict[str, Dict[str, int]] = {}
        
        # 数据源查询统计
        self._data_source_stats: Dict[str, Dict[str, int]] = {}
        
        # Token 消耗统计
        self._token_stats: Dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        # 请求延迟统计
        self._request_latency_stats: Dict[str, list] = {}
        
        logger.info("✅ BusinessMetrics 初始化完成")
    
    # ==================== 意图识别统计 ====================
    
    def record_intent_recognition(self, intent_type: str, success: bool):
        """记录意图识别结果"""
        if intent_type not in self._intent_stats:
            self._intent_stats[intent_type] = {"success": 0, "failure": 0}
        
        if success:
            self._intent_stats[intent_type]["success"] += 1
        else:
            self._intent_stats[intent_type]["failure"] += 1
    
    def get_intent_accuracy(self) -> float:
        """获取意图识别准确率"""
        total = sum(s["success"] + s["failure"] for s in self._intent_stats.values())
        if total == 0:
            return 0.0
        success_count = sum(s["success"] for s in self._intent_stats.values())
        return success_count / total
    
    def get_intent_stats(self) -> Dict[str, Any]:
        """获取意图识别统计"""
        return {
            "by_type": self._intent_stats,
            "overall_accuracy": self.get_intent_accuracy()
        }
    
    # ==================== 工具调用统计 ====================
    
    def record_tool_call(self, tool_name: str, success: bool, duration: float = 0):
        """记录工具调用结果"""
        if tool_name not in self._tool_stats:
            self._tool_stats[tool_name] = {"success": 0, "failure": 0, "total_duration": 0.0}
        
        if success:
            self._tool_stats[tool_name]["success"] += 1
        else:
            self._tool_stats[tool_name]["failure"] += 1
        
        self._tool_stats[tool_name]["total_duration"] += duration
    
    def get_tool_success_rate(self, tool_name: str = None) -> float:
        """获取工具调用成功率"""
        if tool_name:
            stats = self._tool_stats.get(tool_name)
            if not stats:
                return 0.0
            total = stats["success"] + stats["failure"]
            if total == 0:
                return 0.0
            return stats["success"] / total
        else:
            # 总体成功率
            total = sum(s["success"] + s["failure"] for s in self._tool_stats.values())
            if total == 0:
                return 0.0
            success_count = sum(s["success"] for s in self._tool_stats.values())
            return success_count / total
    
    def get_tool_stats(self) -> Dict[str, Any]:
        """获取工具调用统计"""
        result = {}
        for tool_name, stats in self._tool_stats.items():
            total = stats["success"] + stats["failure"]
            result[tool_name] = {
                "success": stats["success"],
                "failure": stats["failure"],
                "total": total,
                "success_rate": stats["success"] / total if total > 0 else 0.0,
                "avg_duration": stats["total_duration"] / total if total > 0 else 0.0
            }
        return result
    
    # ==================== 数据源查询统计 ====================
    
    def record_data_source_query(self, data_source: str, success: bool, duration: float = 0):
        """记录数据源查询结果"""
        if data_source not in self._data_source_stats:
            self._data_source_stats[data_source] = {"success": 0, "failure": 0, "total_duration": 0.0}
        
        if success:
            self._data_source_stats[data_source]["success"] += 1
        else:
            self._data_source_stats[data_source]["failure"] += 1
        
        self._data_source_stats[data_source]["total_duration"] += duration
    
    def get_data_source_success_rate(self, data_source: str = None) -> float:
        """获取数据源查询成功率"""
        if data_source:
            stats = self._data_source_stats.get(data_source)
            if not stats:
                return 0.0
            total = stats["success"] + stats["failure"]
            if total == 0:
                return 0.0
            return stats["success"] / total
        else:
            total = sum(s["success"] + s["failure"] for s in self._data_source_stats.values())
            if total == 0:
                return 0.0
            success_count = sum(s["success"] for s in self._data_source_stats.values())
            return success_count / total
    
    def get_data_source_stats(self) -> Dict[str, Any]:
        """获取数据源查询统计"""
        result = {}
        for source, stats in self._data_source_stats.items():
            total = stats["success"] + stats["failure"]
            result[source] = {
                "success": stats["success"],
                "failure": stats["failure"],
                "total": total,
                "success_rate": stats["success"] / total if total > 0 else 0.0,
                "avg_duration": stats["total_duration"] / total if total > 0 else 0.0
            }
        return result
    
    # ==================== Token 消耗统计 ====================
    
    def record_token_usage(self, input_tokens: int = 0, output_tokens: int = 0):
        """记录 Token 消耗"""
        self._token_stats["input_tokens"] += input_tokens
        self._token_stats["output_tokens"] += output_tokens
        self._token_stats["total_tokens"] += input_tokens + output_tokens
    
    def get_token_stats(self) -> Dict[str, int]:
        """获取 Token 消耗统计"""
        return self._token_stats.copy()
    
    def calculate_cost(self, input_price: float = 0.0, output_price: float = 0.0) -> float:
        """计算成本（基于 Token 价格）"""
        return (
            self._token_stats["input_tokens"] * input_price +
            self._token_stats["output_tokens"] * output_price
        )
    
    # ==================== 请求延迟统计 ====================
    
    def record_request_latency(self, endpoint: str, latency: float):
        """记录请求延迟"""
        if endpoint not in self._request_latency_stats:
            self._request_latency_stats[endpoint] = []
        self._request_latency_stats[endpoint].append(latency)
    
    def get_latency_stats(self, endpoint: str = None) -> Dict[str, Any]:
        """获取延迟统计"""
        if endpoint:
            latencies = self._request_latency_stats.get(endpoint, [])
            if not latencies:
                return {}
            
            sorted_latencies = sorted(latencies)
            count = len(sorted_latencies)
            
            return {
                "count": count,
                "min": min(sorted_latencies),
                "max": max(sorted_latencies),
                "avg": sum(sorted_latencies) / count,
                "p50": sorted_latencies[int(count * 0.5)],
                "p95": sorted_latencies[int(count * 0.95)] if count > 1 else sorted_latencies[0],
                "p99": sorted_latencies[int(count * 0.99)] if count > 1 else sorted_latencies[0],
            }
        else:
            # 总体统计
            all_latencies = []
            for latencies in self._request_latency_stats.values():
                all_latencies.extend(latencies)
            
            if not all_latencies:
                return {}
            
            sorted_latencies = sorted(all_latencies)
            count = len(sorted_latencies)
            
            return {
                "count": count,
                "min": min(sorted_latencies),
                "max": max(sorted_latencies),
                "avg": sum(sorted_latencies) / count,
                "p50": sorted_latencies[int(count * 0.5)],
                "p95": sorted_latencies[int(count * 0.95)] if count > 1 else sorted_latencies[0],
                "p99": sorted_latencies[int(count * 0.99)] if count > 1 else sorted_latencies[0],
            }
    
    # ==================== 汇总统计 ====================
    
    def get_summary(self) -> Dict[str, Any]:
        """获取汇总统计"""
        return {
            "timestamp": datetime.now().isoformat(),
            "intent_recognition": self.get_intent_stats(),
            "tool_call": self.get_tool_stats(),
            "data_source": self.get_data_source_stats(),
            "token_usage": self.get_token_stats(),
            "latency": self.get_latency_stats()
        }
    
    def reset(self):
        """重置所有统计"""
        self._intent_stats.clear()
        self._tool_stats.clear()
        self._data_source_stats.clear()
        self._token_stats = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        self._request_latency_stats.clear()
        logger.info("✅ BusinessMetrics 已重置")


# 全局业务指标实例
_business_metrics: Optional[BusinessMetrics] = None


def get_business_metrics() -> BusinessMetrics:
    """获取全局业务指标实例"""
    global _business_metrics
    if _business_metrics is None:
        _business_metrics = BusinessMetrics()
    return _business_metrics
