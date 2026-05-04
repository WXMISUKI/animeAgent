# agent/nodes.py
"""Agent 节点实现"""

import asyncio
import concurrent.futures
from .state import AgentState
from ..llm.client import LLMClient
from ..llm.prompts import DIRECT_RESPONSE_TEMPLATES
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


def classify_intent(state: AgentState) -> AgentState:
    """节点1：简单意图预判（快速路径）

    优化：只做简单的快速判断，复杂情况交给LLM自主决定
    - 明显打招呼：直接回复
    - 感谢：直接回复
    - 其他：交给LLM判断
    """

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

    # 快速路径：明显的打招呼/寒暄直接返回
    # 使用更宽松的匹配
    query_lower = user_query.lower().strip()

    # 打招呼关键词（更全面）
    greeting_keywords = ["你好", "在吗", "嗨", "hi", "hello", "早上好", "晚安",
                        "您好", "哈喽", "hey", "yo", "你好呀", "你好啊", "晚上好"]

    # 感谢关键词
    thanks_keywords = ["谢谢", "感谢", "好的", "明白了", "知道了", "感谢你", "谢谢啦", "thanks", "thx"]

    # 检查是否是打招呼
    is_greeting = any(kw in query_lower for kw in greeting_keywords)

    # 检查是否是感谢
    is_thanks = any(kw in query_lower for kw in thanks_keywords)

    # 如果只是简单的打招呼（没有其他内容）
    if is_greeting and len(user_query.strip()) < 10:
        return {
            **state,
            "intent_type": "greeting",
            "response_mode": "direct",
            "needs_data_fetch": False,
            "final_response": DIRECT_RESPONSE_TEMPLATES["greeting"]
        }

    # 如果只是感谢
    if is_thanks and len(user_query.strip()) < 15:
        return {
            **state,
            "intent_type": "thanks",
            "response_mode": "direct",
            "needs_data_fetch": False,
            "final_response": DIRECT_RESPONSE_TEMPLATES["thanks"]
        }

    # 其他情况：交给LLM判断
    # 调用 LLM 进行意图分类
    client = LLMClient()
    classify_result = client.classify_intent(user_query)

    intent_type = classify_result.get("intent_type", "query")  # 默认是查询
    needs_fetch = classify_result.get("needs_fetch", True)
    response_mode = classify_result.get("response_mode", "skill")

    # 根据响应模式决定后续流程
    if response_mode == "direct":
        # 直接回复类型，使用预设模板
        direct_response = client.get_direct_response(intent_type)
        return {
            **state,
            "intent_type": intent_type,
            "response_mode": response_mode,
            "needs_data_fetch": needs_fetch,
            "final_response": direct_response
        }
    else:
        # 需要调用数据源或进一步解析
        return {
            **state,
            "intent_type": intent_type,
            "response_mode": response_mode,
            "needs_data_fetch": needs_fetch,
            "query_params": classify_result.get("params", {})
        }


def parse_intent(state: AgentState) -> AgentState:
    """节点2：解析查询参数（当需要调用数据源时）"""

    # 如果不需要获取数据，直接返回
    if not state.get("needs_data_fetch"):
        return state

    user_query = state["user_query"]
    messages = state.get("messages", [])

    # 调用 LLM 解析意图参数
    client = LLMClient()
    intent_result = client.parse_intent(user_query, messages)

    intent = intent_result.get("intent", {})

    # 如果 LLM 已经直接回答（不需要数据源）
    if not intent_result.get("needs_fetch", True):
        response = intent_result.get("response", "")
        if response:
            return {
                **state,
                "intent": intent,
                "query_params": intent,
                "needs_data_fetch": False,
                "final_response": response
            }

    return {
        **state,
        "intent": intent,
        "query_params": intent,
        "needs_data_fetch": True
    }


async def execute_skill_async(state: AgentState) -> AgentState:
    """节点3：执行 Skill 获取数据（异步版本）"""

    if state.get("cache_hit"):
        return state

    # 如果不需要获取数据，直接返回
    if not state.get("needs_data_fetch"):
        return state

    # 如果已经有最终回复，也直接返回
    if state.get("final_response"):
        return state

    # 根据意图选择 Skill
    intent = state.get("intent", {})
    intent_type = state.get("intent_type", "query")

    # 根据 intent_type 确定 action
    if intent_type == "detail":
        action = "detail"
    elif intent_type == "ranking":
        action = "rank"
    else:
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
    """节点3：执行 Skill 获取数据"""

    if state.get("cache_hit"):
        return state

    # 如果不需要获取数据，直接返回
    if not state.get("needs_data_fetch"):
        return state

    # 如果已经有最终回复，也直接返回
    if state.get("final_response"):
        return state

    # 根据意图选择 Skill
    intent = state.get("intent", {})
    intent_type = state.get("intent_type", "query")

    # 根据 intent_type 确定 action
    if intent_type == "detail":
        action = "detail"
    elif intent_type == "ranking":
        action = "rank"
    else:
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
    """节点4：格式化响应"""

    if state.get("cache_hit"):
        return state

    # 如果已经有最终回复，直接返回
    if state.get("final_response"):
        return state

    client = LLMClient()
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


def direct_reply(state: AgentState) -> AgentState:
    """节点：处理直接回复（打招呼、身份询问等）"""

    # 如果已经有最终回复，直接返回
    if state.get("final_response"):
        return state

    # 获取意图类型并生成对应回复
    intent_type = state.get("intent_type", "chat")
    client = LLMClient()

    response = client.get_direct_response(intent_type)

    return {
        **state,
        "final_response": response
    }
