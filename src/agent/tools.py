# agent/tools.py
"""LangChain Tools 定义 - 让 LLM 自主调用 Skills"""

import json
import asyncio
from typing import Any
from langchain_core.tools import BaseTool
from pydantic import Field
from ..skills.query import AnimeQuerySkill
from ..skills.detail import AnimeDetailSkill
from ..skills.ranking import RankingSkill


class QueryAnimeInput(BaseTool):
    """query_anime 工具的参数 schema"""
    time_range: str = Field(default="", description="时间范围，如 '2026-02'、'2024年7月'、'本月'、'最新'、'2024夏'")
    platform: str = Field(default="all", description="平台，如 'jikan'、'bangumi'、'all'（默认 all）")
    anime_type: str = Field(default="all", description="类型，如 '日漫'、'国漫'、'all'")
    sort_by: str = Field(default="latest", description="排序方式，如 'latest'（最新）、'hot'（热门）、'rating'（评分）")
    keyword: str = Field(default="", description="关键词搜索，如番剧名称 '違国日記'、'葬送的芙莉莲' 等")


def _run_skill_sync(skill_instance, params: dict) -> str:
    """同步执行 Skill（包装异步为同步）"""
    try:
        # 获取事件循环
        try:
            loop = asyncio.get_running_loop()
            # 已有事件循环，在新线程中执行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, skill_instance.execute({
                    "query_params": params,
                    "context": {}
                }))
                result = future.result()
        except RuntimeError:
            # 没有运行中的事件循环
            result = asyncio.run(skill_instance.execute({
                "query_params": params,
                "context": {}
            }))

        if result.get("success"):
            return json.dumps(result.get("data", []), ensure_ascii=False, indent=2)
        else:
            return f"查询失败: {result.get('error', '未知错误')}"
    except Exception as e:
        return f"执行错误: {str(e)}"


class QueryAnimeTool(BaseTool):
    """番剧查询工具"""

    name: str = "query_anime"
    description: str = """查询番剧列表。当用户想了解番剧列表、搜索番剧、了解某个类型/时间段的番剧时使用。
    
可以回答以下问题：
- "有什么番剧推荐？"
- "2026年2月有什么新番？"
- "最近有哪些日漫？"
- "推荐几部热血类型的番剧"
- "《違国日記》讲了什么？" - 使用 keyword 参数搜索具体番剧

**重要**：当用户询问特定番剧的详情时（如"《xxx》讲了什么"），应优先使用 keyword 参数搜索！

参数：
- time_range: 时间范围（可选），如 "2026-02"、"2024年7月"、"2024夏"、"本月"、"最新"
- platform: 平台（可选），如 "jikan"（MyAnimeList）、"bangumi"、"all"（默认 all）
- anime_type: 类型（可选），如 "日漫"、"国漫"、"all"（默认 all）
- sort_by: 排序（可选），如 "latest"（最新）、"hot"（热门）、"rating"（评分，默认 rating）
- keyword: 关键词（可选），如番剧名称 "違国日記"、"葬送的芙莉莲"、"Spy x Family" """

    args_schema: type[BaseTool] = QueryAnimeInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._skill = AnimeQuerySkill()

    def _run(self, time_range: str = "", platform: str = "all", anime_type: str = "all", sort_by: str = "latest", keyword: str = "") -> str:
        params = {
            "time_range": time_range if time_range else None,
            "platform": platform,
            "anime_type": anime_type,
            "sort_by": sort_by,
            "keyword": keyword if keyword else None
        }
        return _run_skill_sync(self._skill, params)

    async def _arun(self, time_range: str = "", platform: str = "all", anime_type: str = "all", sort_by: str = "latest", keyword: str = "") -> str:
        params = {
            "time_range": time_range if time_range else None,
            "platform": platform,
            "anime_type": anime_type,
            "sort_by": sort_by,
            "keyword": keyword if keyword else None
        }
        result = await self._skill.execute({"query_params": params, "context": {}})
        if result.get("success"):
            return json.dumps(result.get("data", []), ensure_ascii=False, indent=2)
        else:
            return f"查询失败: {result.get('error', '未知错误')}"


class GetAnimeDetailInput(BaseTool):
    """get_anime_detail 工具的参数 schema"""
    anime_id: str = Field(default="", description="番剧ID，如 '12345'")


class GetAnimeDetailTool(BaseTool):
    """番剧详情查询工具"""

    name: str = "get_anime_detail"
    description: str = """获取特定番剧的详细信息。当用户询问某个具体番剧的详细信息、剧情介绍、评分、演员等时使用。

可以回答以下问题：
- "《葬送的芙莉莲》怎么样？"
- "这部番剧的剧情是什么？"
- "间谍过家人的评分是多少？"
- "帮我查一下这部动漫的详细信息"

参数：
- anime_id: 番剧ID（必填），可以从查询结果中获取，或者用户提供番剧名称时需要先查询获取ID"""

    args_schema: type[BaseTool] = GetAnimeDetailInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._skill = AnimeDetailSkill()

    def _run(self, anime_id: str = "") -> str:
        params = {"anime_id": anime_id}
        return _run_skill_sync(self._skill, params)

    async def _arun(self, anime_id: str = "") -> str:
        params = {"anime_id": anime_id}
        result = await self._skill.execute({"query_params": params, "context": {}})
        if result.get("success"):
            return json.dumps(result.get("data"), ensure_ascii=False, indent=2)
        else:
            return f"查询失败: {result.get('error', '未知错误')}"


class GetAnimeRankingInput(BaseTool):
    """get_anime_ranking 工具的参数 schema"""
    time_range: str = Field(default="", description="时间范围，如 '本月'、'2026年'")
    platform: str = Field(default="all", description="平台，如 'bilibili'、'all'")
    anime_type: str = Field(default="all", description="类型，如 '日漫'、'国漫'、'all'")
    sort_by: str = Field(default="rating", description="排序方式，如 'rating'、'hot'")


class GetAnimeRankingTool(BaseTool):
    """番剧排行榜工具"""

    name: str = "get_anime_ranking"
    description: str = """获取番剧排行榜。当用户想了解热门番剧、评分最高的番剧、最受好评的番剧时使用。

可以回答以下问题：
- "有什么番剧排行榜？"
- "评分最高的番剧有哪些？"
- "最近最火的番剧是什么？"
- "推荐TOP10番剧"

参数：
- time_range: 时间范围（可选），如 "本月"、"2026年"
- platform: 平台（可选），如 "bilibili"、"all"（默认 all）
- anime_type: 类型（可选），如 "日漫"、"国漫"、"all"（默认 all）
- sort_by: 排序方式（可选），如 "rating"（评分）、"hot"（热度），默认 rating"""

    args_schema: type[BaseTool] = GetAnimeRankingInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._skill = RankingSkill()

    def _run(self, time_range: str = "", platform: str = "all", anime_type: str = "all", sort_by: str = "rating") -> str:
        params = {
            "time_range": time_range if time_range else None,
            "platform": platform,
            "anime_type": anime_type,
            "sort_by": sort_by
        }
        return _run_skill_sync(self._skill, params)

    async def _arun(self, time_range: str = "", platform: str = "all", anime_type: str = "all", sort_by: str = "rating") -> str:
        params = {
            "time_range": time_range if time_range else None,
            "platform": platform,
            "anime_type": anime_type,
            "sort_by": sort_by
        }
        result = await self._skill.execute({"query_params": params, "context": {}})
        if result.get("success"):
            return json.dumps(result.get("data", []), ensure_ascii=False, indent=2)
        else:
            return f"查询失败: {result.get('error', '未知错误')}"


class WebSearchInput(BaseTool):
    """web_search 工具的参数 schema"""
    query: str = Field(default="", description="搜索查询，如 '違国日記 剧情介绍'、'2024年7月新番推荐'")
    max_results: int = Field(default=10, description="最大结果数，默认10")


class WebSearchTool(BaseTool):
    """通用网页搜索工具
    
    当番剧数据库无法找到结果时，使用此工具进行通用搜索。
    """

    name: str = "web_search"
    description: str = """通用网页搜索工具。当用户询问的信息在番剧数据库中找不到时，使用此工具搜索互联网。
    
**重要**：这是最后的 fallback 手段！
- 首先应尝试使用 query_anime 工具查询数据库
- 只有当数据库查询失败或结果不满意时，才使用此工具

可以回答以下问题：
- "《違国日記》这部番剧讲了什么故事？"
- "《葬送的芙莉莲》剧情简介"
- "2024年7月有哪些热门新番"

参数：
- query: 搜索关键词，建议包含番剧名称和"剧情"、"介绍"等关键词
- max_results: 最大结果数，默认10"""

    args_schema: type[BaseTool] = WebSearchInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from ..data_sources.baidu_search import BaiduSearchAPI
        self._search_api = BaiduSearchAPI()

    def _run(self, query: str = "", max_results: int = 10) -> str:
        """同步搜索"""
        try:
            # 在新线程中运行异步函数
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self._search_api._search_web(query, max_results))
                results = future.result()
            
            # 解析结果
            parsed = self._search_api._parse_search_results(results, query)
            return json.dumps([a.to_dict() for a in parsed], ensure_ascii=False, indent=2)
        except Exception as e:
            return f"搜索失败: {str(e)}"

    async def _arun(self, query: str = "", max_results: int = 10) -> str:
        """异步搜索"""
        try:
            results = await self._search_api._search_web(query, max_results)
            parsed = self._search_api._parse_search_results(results, query)
            return json.dumps([a.to_dict() for a in parsed], ensure_ascii=False, indent=2)
        except Exception as e:
            return f"搜索失败: {str(e)}"


def create_tools() -> list[BaseTool]:
    """创建所有 LangChain Tools"""
    return [
        QueryAnimeTool(),
        GetAnimeDetailTool(),
        GetAnimeRankingTool(),
        WebSearchTool()
    ]
