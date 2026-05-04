# agent/graph.py
"""LangGraph 流程定义 - 支持 Checkpoint 短期记忆"""

import logging
from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from .state import AgentState
from .nodes import (
    classify_intent,
    parse_intent,
    execute_skill,
    format_response,
    direct_reply
)

logger = logging.getLogger(__name__)


def create_agent_graph(checkpointer: Optional[BaseCheckpointSaver] = None) -> StateGraph:
    """创建改进后的 Agent 流程图

    工作流程：
    1. classify_intent - 意图分类（打招呼、身份询问、能力询问、查询等）
    2. 根据响应模式分支：
       - direct: 直接回复（打招呼等）
       - skill: 继续解析参数并执行 Skill
    3. execute_skill - 执行 Skill 获取数据
    4. format_response - 格式化输出

    Args:
        checkpointer: LangGraph Checkpoint Saver，用于多轮对话状态持久化
                     传入后将支持通过 thread_id 恢复对话状态
    """

    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("classify_intent", classify_intent)      # 意图分类
    graph.add_node("parse_intent", parse_intent)            # 参数解析
    graph.add_node("execute_skill", execute_skill)          # 执行 Skill
    graph.add_node("format_response", format_response)      # 格式化输出
    graph.add_node("direct_reply", direct_reply)            # 直接回复

    # 定义流程：从开始到意图分类
    graph.add_edge(START, "classify_intent")

    # 条件分支：根据响应模式决定后续流程
    graph.add_conditional_edges(
        "classify_intent",
        _get_response_mode,
        {
            "direct": "direct_reply",
            "skill": "parse_intent"
        }
    )

    # 参数解析后执行 Skill
    graph.add_edge("parse_intent", "execute_skill")
    graph.add_edge("execute_skill", "format_response")

    # 直接回复或格式化后结束
    graph.add_edge("direct_reply", END)
    graph.add_edge("format_response", END)

    # 编译图，支持 Checkpoint
    if checkpointer:
        logger.info("✅ Agent 图已编译，启用 Checkpoint 短期记忆")
        return graph.compile(checkpointer=checkpointer)
    else:
        logger.info("⚠️ Agent 图已编译，未启用 Checkpoint（单轮对话模式）")
        return graph.compile()


def _get_response_mode(state: AgentState) -> str:
    """根据状态获取响应模式"""
    # 如果命中缓存，跳过
    if state.get("cache_hit"):
        return "skip"

    # 如果已经有最终回复（在意图分类阶段已确定直接回复）
    if state.get("final_response"):
        return "direct"

    # 根据 response_mode 决定
    return state.get("response_mode", "skill")


def _should_fetch_data(state: AgentState) -> str:
    """判断是否需要获取数据（保留用于兼容）"""
    if state.get("cache_hit"):
        return "skip_fetch"
    if not state.get("needs_data_fetch", True):
        return "skip_fetch"
    return "fetch_data"


# 全局 Agent 实例（无 Checkpoint，用于兼容旧接口）
agent = create_agent_graph()


# 带 Checkpoint 的 Agent 图（支持多轮对话）
_checkpoint_agent_graph: Optional[StateGraph] = None


def get_agent_graph(checkpointer: Optional[BaseCheckpointSaver] = None) -> StateGraph:
    """获取 Agent 图（支持 Checkpoint）
    
    Args:
        checkpointer: LangGraph Checkpoint Saver
        
    Returns:
        编译后的 StateGraph
    """
    global _checkpoint_agent_graph
    
    if checkpointer is not None:
        # 每次创建新的图实例（因为 checkpointer 不同）
        _checkpoint_agent_graph = create_agent_graph(checkpointer)
        return _checkpoint_agent_graph
    else:
        # 返回全局无 checkpointer 的图
        return agent


def create_checkpoint_agent_graph() -> StateGraph:
    """创建带 Checkpoint 的 Agent 图（使用默认配置）"""
    from ..infrastructure.checkpoint import get_checkpoint_config, get_memory_saver
    
    config = get_checkpoint_config()
    
    if not config.enable_checkpoint:
        logger.info("Checkpoint 功能未启用，使用无状态模式")
        return create_agent_graph()
    
    if config.backend.value == "redis":
        # 尝试使用 Redis
        try:
            from ..infrastructure.checkpoint import get_redis_checkpointer
            redis_checkpointer = get_redis_checkpointer(
                redis_url=config.redis_url,
                key_prefix=config.redis_key_prefix,
                ttl=config.redis_ttl
            )
            checkpointer = redis_checkpointer.saver
            logger.info("✅ 使用 Redis Checkpoint 存储")
        except Exception as e:
            logger.warning(f"Redis Checkpoint 初始化失败: {e}，回退到内存存储")
            checkpointer = get_memory_saver()
    else:
        # 使用内存存储
        checkpointer = get_memory_saver()
        logger.info("✅ 使用内存 Checkpoint 存储")
    
    return create_agent_graph(checkpointer)
