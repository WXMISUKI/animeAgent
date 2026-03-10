# agent/graph.py
"""LangGraph 流程定义"""

from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .nodes import parse_intent, execute_skill, format_response


def create_agent_graph() -> StateGraph:
    """创建 Agent 流程图"""
    
    graph = StateGraph(AgentState)
    
    # 添加节点
    graph.add_node("parse_intent", parse_intent)
    graph.add_node("execute_skill", execute_skill)
    graph.add_node("format_response", format_response)
    
    # 定义流程
    graph.add_edge(START, "parse_intent")
    
    # 条件分支：根据是否需要获取数据
    graph.add_conditional_edges(
        "parse_intent",
        _should_fetch_data,
        {
            "skip_fetch": "format_response",
            "fetch_data": "execute_skill"
        }
    )
    
    graph.add_edge("execute_skill", "format_response")
    graph.add_edge("format_response", END)
    
    return graph.compile()


def _should_fetch_data(state: AgentState) -> str:
    """判断是否需要获取数据"""
    if state.get("cache_hit"):
        return "skip_fetch"
    if not state.get("needs_data_fetch", True):
        return "skip_fetch"
    return "fetch_data"


# 全局 Agent 实例
agent = create_agent_graph()
