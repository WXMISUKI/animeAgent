# agent/nodes.py
"""Agent 节点实现"""

import asyncio
import concurrent.futures
from .state import AgentState
from ..llm.client import MiniMaxClient
from ..skills.query import AnimeQuerySkill
from ..skills.detail import AnimeDetailSkill
from ..skills.ranking import RankingSkill
from ..utils.cache import QueryCache

# 全局缓存实例
query_cache = QueryCache(ttl=3600)

# 线程池执行器
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def run_async(coro):
    """安全地运行异步代码"""
    try:
        loop = asyncio.get_running_loop()
        # 已有事件循环，在新线程中执行
        future = _executor.submit(asyncio.run, coro)
        return future.result()
    except RuntimeError:
        # 没有运行中的事件循环
        return asyncio.run(coro)


def parse_intent(state: AgentState) -> AgentState:
    """节点1：解析用户意图"""
    
    user_query = state["user_query"]
    messages = state.get("messages", [])
    
    # 检查缓存
    cached = query_cache.get(user_query, {})
    if cached:
        return {
            **state,
            "final_response": cached,
            "cache_hit": True
        }
    
    # 调用 LLM 解析意图
    client = MiniMaxClient()
    intent_result = client.parse_intent(user_query, messages)
    
    intent = intent_result.get("intent", {})
    
    return {
        **state,
        "intent": intent,
        "query_params": intent,
        "needs_data_fetch": intent_result.get("needs_fetch", True)
    }


async def execute_skill_async(state: AgentState) -> AgentState:
    """节点2：执行 Skill 获取数据（异步版本）"""
    
    if state.get("cache_hit"):
        return state
    
    if not state.get("needs_data_fetch"):
        # LLM 已直接回答
        return {
            **state,
            "final_response": state.get("intent", {}).get("response", "")
        }
    
    # 根据意图选择 Skill
    intent = state.get("intent", {})
    action = intent.get("action", "query")
    
    try:
        if action == "detail":
            skill = AnimeDetailSkill()
        elif action == "rank":
            skill = RankingSkill()
        else:
            skill = AnimeQuerySkill()
        
        # 异步执行 Skill
        result = await skill.execute({
            "query_params": state.get("query_params", {}),
            "context": {}
        })
        
        if result.get("success"):
            return {
                **state,
                "anime_results": result.get("data", [])
            }
        else:
            return {
                **state,
                "error": result.get("error", "Skill 执行失败"),
                "anime_results": []
            }
            
    except Exception as e:
        return {
            **state,
            "error": str(e),
            "anime_results": []
        }


def execute_skill(state: AgentState) -> AgentState:
    """节点2：执行 Skill 获取数据"""
    
    if state.get("cache_hit"):
        return state
    
    if not state.get("needs_data_fetch"):
        # LLM 已直接回答
        return {
            **state,
            "final_response": state.get("intent", {}).get("response", "")
        }
    
    # 根据意图选择 Skill
    intent = state.get("intent", {})
    action = intent.get("action", "query")
    
    try:
        if action == "detail":
            skill = AnimeDetailSkill()
        elif action == "rank":
            skill = RankingSkill()
        else:
            skill = AnimeQuerySkill()
        
        # 使用安全的异步执行方式
        result = run_async(skill.execute({
            "query_params": state.get("query_params", {}),
            "context": {}
        }))
        
        if result.get("success"):
            return {
                **state,
                "anime_results": result.get("data", [])
            }
        else:
            return {
                **state,
                "error": result.get("error", "Skill 执行失败"),
                "anime_results": []
            }
            
    except Exception as e:
        return {
            **state,
            "error": str(e),
            "anime_results": []
        }


def format_response(state: AgentState) -> AgentState:
    """节点3：格式化响应"""
    
    if state.get("cache_hit"):
        return state
    
    if state.get("final_response"):
        return state
    
    client = MiniMaxClient()
    anime_results = state.get("anime_results", [])
    user_query = state["user_query"]
    
    # 如果有数据，调用 LLM 格式化
    if anime_results:
        response = client.format_response(user_query, anime_results)
    else:
        # 无数据时的默认回复
        response = "抱歉，暂未找到符合条件的番剧。请问换个关键词试试？"
    
    # 缓存结果
    if not state.get("error"):
        query_cache.set(user_query, {}, response)
    
    return {
        **state,
        "final_response": response
    }
