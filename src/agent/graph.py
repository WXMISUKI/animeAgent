# agent/graph.py
"""LangGraph 流程定义"""

from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .nodes import (
    classify_intent,
    parse_intent,
    execute_skill,
    format_response,
    direct_reply
)


def create_agent_graph() -> StateGraph:
    """创建改进后的 Agent 流程图

    工作流程：
    1. classify_intent - 意图分类（打招呼、身份询问、能力询问、查询等）
    2. 根据响应模式分支：
       - direct: 直接回复（打招呼等）
       - skill: 继续解析参数并执行 Skill
    3. execute_skill - 执行 Skill 获取数据
    4. format_response - 格式化输出
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


# 全局 Agent 实例
agent = create_agent_graph()
