"""LangChain Tools 定义 - 将 Skills 封装为 LLM 可调用的工具"""

from typing import TypeVar, Any
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import json
import asyncio
import concurrent.futures


class QueryAnimeInput(BaseModel):
    """番剧查询输入参数"""
    time_range: str = Field(default="", description="时间范围（如'2026-03'、'本周'、'最新'）")
    platform: str = Field(default="all", description="平台（bilibili/iqiyi/tencent/all）")
    anime_type: str = Field(default="all", description="类型（日漫/国漫/美漫/剧场版/all）")
    sort_by: str = Field(default="latest", description="排序（latest/hot/rating）")
    keyword: str = Field(default="", description="关键词（番剧名称或标签）")


class GetAnimeDetailInput(BaseModel):
    """番剧详情输入参数"""
    anime_id: str = Field(description="番剧 ID（可以从查询结果中获取）")


class GetRankingInput(BaseModel):
    """排行榜输入参数"""
    time_range: str = Field(default="本周", description="时间范围（本周/月/本季/本年）")
    platform: str = Field(default="all", description="平台（bilibili/iqiyi/tencent/all）")
    anime_type: str = Field(default="all", description="类型（日漫/国漫/美漫/all）")
    sort_by: str = Field(default="rating", description="排序方式（rating/hot）")
    limit: int = Field(default=10, description="返回数量限制")


def run_async(coro):
    """安全地运行异步代码"""
    try:
        loop = asyncio.get_running_loop()
        # 已有事件循环，在新线程中执行
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # 没有运行中的事件循环
        return asyncio.run(coro)


class QueryAnimeTool(BaseTool):
    """番剧查询工具"""
    name = "query_anime"
    description = """查询番剧信息列表。当用户想了解番剧列表、最新番剧、特定类型的番剧时使用。
    
    可以根据以下条件筛选：
    - 时间范围：最新、本周、本月、特定月份（如2026-03）
    - 平台：B站（bilibili）、爱奇艺（iqiyi）、腾讯（tencent）、全部（all）
    - 类型：日漫、国漫、美漫、剧场版、全部（all）
    - 排序方式：最新（latest）、热门（hot）、评分（rating）
    - 关键词：番剧名称或标签"""
    
    args_schema: Type[BaseModel] = QueryAnimeInput
    
    def _run(self, time_range: str = "", platform: str = "all", 
             anime_type: str = "all", sort_by: str = "latest", 
             keyword: str = "") -> str:
        """同步执行查询"""
        from ..skills.query import AnimeQuerySkill
        
        try:
            skill = AnimeQuerySkill()
            params = {
                "time_range": time_range,
                "platform": platform,
                "anime_type": anime_type,
                "sort_by": sort_by,
                "keyword": keyword
            }
            
            result = run_async(skill.execute({
                "query_params": params,
                "context": {}
            }))
            
            if result.get("success"):
                data = result.get("data", [])
                return self._format_result(data)
            else:
                return f"查询失败: {result.get('error')}"
                
        except Exception as e:
            return f"执行错误: {str(e)}"
    
    def _format_result(self, data: list) -> str:
        """格式化查询结果"""
        if not data:
            return "未找到符合条件的番剧"
        
        result_lines = [f"找到 {len(data)} 部番剧：\n"]
        
        for i, anime in enumerate(data[:10], 1):
            name = anime.get("名称") or anime.get("name_cn") or anime.get("name", "未知")
            rating = anime.get("rating") or anime.get("评分", "暂无")
            platform = anime.get("platform") or anime.get("平台", "未知")
            air_date = anime.get("air_date") or anime.get("播出时间", "未知")
            
            result_lines.append(
                f"{i}. {name} ★{rating}\n"
                f"   播出: {air_date} | 平台: {platform}"
            )
        
        return "\n\n".join(result_lines)


class GetAnimeDetailTool(BaseTool):
    """番剧详情查询工具"""
    name = "get_anime_detail"
    description = """获取特定番剧的详细信息。当用户询问某个具体番剧的详细信息、剧情介绍、评分、制作公司等时使用。
    
    输入参数：
    - anime_id: 番剧 ID（可以从查询结果中获取）"""
    
    args_schema: Type[BaseModel] = GetAnimeDetailInput
    
    def _run(self, anime_id: str) -> str:
        """同步执行详情查询"""
        from ..skills.detail import AnimeDetailSkill
        
        try:
            skill = AnimeDetailSkill()
            
            result = run_async(skill.execute({
                "query_params": {"anime_id": anime_id},
                "context": {}
            }))
            
            if result.get("success"):
                data = result.get("data")
                if data:
                    return self._format_detail(data[0] if isinstance(data, list) else data)
                return "未找到该番剧详情"
            else:
                return f"查询失败: {result.get('error')}"
                
        except Exception as e:
            return f"执行错误: {str(e)}"
    
    def _format_detail(self, anime: dict) -> str:
        """格式化详情结果"""
        name = anime.get("名称") or anime.get("name_cn") or anime.get("name", "未知")
        rating = anime.get("rating") or anime.get("评分", "暂无")
        summary = anime.get("summary") or anime.get("简介", "暂无简介")
        platform = anime.get("platform") or anime.get("平台", "未知")
        air_date = anime.get("air_date") or anime.get("播出时间", "未知")
        tags = anime.get("tags") or anime.get("标签", [])
        
        lines = [
            f"【{name}】",
            f"⭐ 评分: {rating}",
            f"📅 播出: {air_date}",
            f"📺 平台: {platform}",
            f"📖 简介: {summary}"
        ]
        
        if tags:
            lines.append(f"🏷️ 标签: {', '.join(tags)}")
        
        return "\n".join(lines)


class GetRankingTool(BaseTool):
    """番剧排行榜工具"""
    name = "get_anime_ranking"
    description = """获取番剧排行榜。当用户想了解热门番剧、评分最高的番剧、最受好评的番剧排行时使用。
    
    输入参数：
    - time_range: 时间范围（本周/月/本季/本年）
    - platform: 平台（bilibili/iqiyi/tencent/all）
    - anime_type: 类型（日漫/国漫/美漫/all）
    - sort_by: 排序方式（rating 评分排行 / hot 热门排行）
    - limit: 返回数量（默认10）"""
    
    args_schema: Type[BaseModel] = GetRankingInput
    
    def _run(self, time_range: str = "本周", platform: str = "all",
             anime_type: str = "all", sort_by: str = "rating",
             limit: int = 10) -> str:
        """同步执行排行榜查询"""
        from ..skills.ranking import RankingSkill
        
        try:
            skill = RankingSkill()
            params = {
                "time_range": time_range,
                "platform": platform,
                "anime_type": anime_type,
                "sort_by": sort_by,
                "limit": limit
            }
            
            result = run_async(skill.execute({
                "query_params": params,
                "context": {}
            }))
            
            if result.get("success"):
                data = result.get("data", [])
                return self._format_ranking(data, sort_by)
            else:
                return f"查询失败: {result.get('error')}"
                
        except Exception as e:
            return f"执行错误: {str(e)}"
    
    def _format_ranking(self, data: list, sort_by: str) -> str:
        """格式化排行榜结果"""
        if not data:
            return "暂无排行榜数据"
        
        title = "评分排行" if sort_by == "rating" else "热门排行"
        result_lines = [f"🏆 番剧{title} TOP{len(data)}：\n"]
        
        for i, anime in enumerate(data, 1):
            name = anime.get("名称") or anime.get("name_cn") or anime.get("name", "未知")
            rating = anime.get("rating") or anime.get("评分", "暂无")
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            result_lines.append(f"{medal} {name} ★{rating}")
        
        return "\n".join(result_lines)


def create_tools() -> list[BaseTool]:
    """创建所有 LangChain Tools"""
    return [
        QueryAnimeTool(),
        GetAnimeDetailTool(),
        GetRankingTool()
    ]


def get_tool_by_name(name: str) -> BaseTool | None:
    """根据名称获取工具"""
    tools = create_tools()
    for tool in tools:
        if tool.name == name:
            return tool
    return None