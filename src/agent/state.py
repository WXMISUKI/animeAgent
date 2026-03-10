# agent/state.py
"""Agent 状态定义"""

from typing import TypedDict, Annotated, Optional
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """Agent 状态定义"""
    
    # 输入
    messages: Annotated[list, add_messages]    # 消息历史
    user_query: str                             # 用户查询
    
    # 意图解析结果
    intent: Optional[dict]                      # 解析后的意图
    query_params: Optional[dict]                # 查询参数
    
    # 数据源结果
    anime_results: Optional[list[dict]]        # 番剧数据
    
    # 输出
    final_response: Optional[str]               # 最终回复
    error: Optional[str]                        # 错误信息
    
    # 元数据
    needs_data_fetch: bool                     # 是否需要获取数据
    cache_hit: bool                            # 是否命中缓存
